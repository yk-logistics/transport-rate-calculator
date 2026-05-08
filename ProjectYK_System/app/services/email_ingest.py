from __future__ import annotations

import email
import imaplib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime
from typing import Optional

from sqlmodel import Session, select

from models import InboxEmail, InboxSyncRun
from services import email_oauth


@dataclass
class InboxScope:
    enabled: bool
    account_label: str
    host: str
    port: int
    username: str
    password: str
    auth_mode: str
    mailbox: str
    max_fetch: int
    use_ssl: bool


def get_inbox_scope() -> InboxScope:
    """Safe default scope: one mailbox account only."""
    enabled = (os.environ.get("EMAIL_INGEST_ENABLED", "0").strip() == "1")
    auth_mode = ((os.environ.get("EMAIL_IMAP_AUTH", "password") or "password").strip().lower())
    if auth_mode not in {"password", "oauth2"}:
        auth_mode = "password"
    return InboxScope(
        enabled=enabled,
        account_label=(os.environ.get("EMAIL_ACCOUNT_LABEL", "ops") or "ops").strip(),
        host=(os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com") or "imap.gmail.com").strip(),
        port=int((os.environ.get("EMAIL_IMAP_PORT", "993") or "993").strip()),
        username=(os.environ.get("EMAIL_IMAP_USERNAME", "") or "").strip(),
        password=(os.environ.get("EMAIL_IMAP_PASSWORD", "") or "").strip(),
        auth_mode=auth_mode,
        mailbox=(os.environ.get("EMAIL_IMAP_MAILBOX", "INBOX") or "INBOX").strip(),
        max_fetch=max(1, min(200, int((os.environ.get("EMAIL_IMAP_MAX_FETCH", "30") or "30").strip()))),
        use_ssl=(os.environ.get("EMAIL_IMAP_SSL", "1").strip() != "0"),
    )


def _imap_connect_login(scope: InboxScope):
    client = imaplib.IMAP4_SSL(scope.host, scope.port) if scope.use_ssl else imaplib.IMAP4(scope.host, scope.port)
    if scope.auth_mode == "oauth2":
        refresh_token = email_oauth.load_google_refresh_token()
        access_token = email_oauth.refresh_access_token(refresh_token)
        xoauth2 = email_oauth.encode_xoauth2_for_imap(scope.username, access_token)
        client.authenticate("XOAUTH2", lambda _: xoauth2.encode("ascii"))
    else:
        client.login(scope.username, scope.password)
    return client


def _decode_header_value(raw: Optional[str]) -> str:
    if not raw:
        return ""
    out = []
    for part, enc in decode_header(raw):
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out.append(part.decode("utf-8", errors="replace"))
        else:
            out.append(str(part))
    return "".join(out).strip()


def _extract_text(msg: email.message.Message) -> tuple[str, bool]:
    text_parts: list[str] = []
    has_attachment = False
    if msg.is_multipart():
        for part in msg.walk():
            disp = (part.get("Content-Disposition", "") or "").lower()
            if "attachment" in disp:
                has_attachment = True
            ctype = (part.get_content_type() or "").lower()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                text_parts.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        text_parts.append(payload.decode(charset, errors="replace"))
    body = "\n".join(x.strip() for x in text_parts if x and x.strip())
    body = re.sub(r"\r\n?", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body[:12000], has_attachment


def _parse_sent_at(raw_date: str) -> Optional[datetime]:
    if not raw_date:
        return None
    try:
        dt = parsedate_to_datetime(raw_date)
        if dt.tzinfo:
            return dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _to_csv_emails(raw: str) -> str:
    addresses = getaddresses([raw or ""])
    values = [a[1].strip().lower() for a in addresses if a[1]]
    return ",".join(values[:30])


def _rule_classify(subject: str, body: str) -> dict:
    text = f"{subject}\n{body}".lower()
    cat = "other"
    conf = 0.35
    flags: list[str] = []
    action = "review_only"
    site = ""
    customer = ""
    if any(k in text for k in ("booking", "จอง", "เที่ยว", "dispatch", "pickup", "delivery")):
        cat = "booking"
        conf = 0.74
        action = "draft_daily_candidate"
    if any(k in text for k in ("invoice", "ใบแจ้งหนี้", "ใบวางบิล", "billing", "po", "ใบงาน")):
        cat = "document"
        conf = max(conf, 0.70)
    if any(k in text for k in ("ด่วน", "urgent", "asap")):
        flags.append("urgent")
        conf = min(0.95, conf + 0.08)
    if "bigc" in text:
        site = "BIGC"
    elif "lcb" in text or "แหลมฉบัง" in text:
        site = "LCB"
    elif "ayu" in text or "อยุธยา" in text:
        site = "AYU"
    if any(k in text for k in ("payment", "โอน", "ชำระ", "due date")):
        cat = "payment"
        conf = max(conf, 0.72)
    if any(k in text for k in ("unknown", "ไม่ชัดเจน", "ไม่พบข้อมูล")):
        flags.append("low_signal")
        conf = min(conf, 0.50)
    if conf < 0.75:
        flags.append("human_review")
    return {
        "category": cat,
        "confidence": round(conf, 2),
        "risk_flags": ",".join(flags),
        "suggested_site_code": site,
        "suggested_customer": customer,
        "suggested_action": action,
        "ai_provider": "rule",
        "ai_note": "rules_only",
        "needs_review": True,
    }


def _gemini_enabled() -> bool:
    return bool((os.environ.get("GEMINI_API_KEY", "") or "").strip()) and (
        os.environ.get("EMAIL_GEMINI_ENABLED", "0").strip() == "1"
    )


def _gemini_classify(subject: str, body: str) -> Optional[dict]:
    api_key = (os.environ.get("GEMINI_API_KEY", "") or "").strip()
    model = (os.environ.get("EMAIL_GEMINI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash").strip()
    if not api_key:
        return None
    prompt = (
        "Classify this email for transport ops. Return JSON keys only: "
        "category,confidence,risk_flags,suggested_site_code,suggested_customer,suggested_action,ai_note.\n"
        "Rules: never authorize auto-create payroll or money-impact transactions.\n"
        f"Subject: {subject[:500]}\nBody: {body[:3500]}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        txt = (
            raw.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        if not txt:
            return None
        data = json.loads(txt)
        out = {
            "category": str(data.get("category") or "other"),
            "confidence": float(data.get("confidence") or 0),
            "risk_flags": str(data.get("risk_flags") or ""),
            "suggested_site_code": str(data.get("suggested_site_code") or ""),
            "suggested_customer": str(data.get("suggested_customer") or ""),
            "suggested_action": str(data.get("suggested_action") or "review_only"),
            "ai_provider": "gemini",
            "ai_note": str(data.get("ai_note") or ""),
            "needs_review": True,
        }
        if out["suggested_action"] != "review_only":
            out["risk_flags"] = ",".join(x for x in [out["risk_flags"], "human_review"] if x)
            out["suggested_action"] = "review_only"
        return out
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
        return None


def classify_email_item(item: InboxEmail) -> None:
    base = _rule_classify(item.subject or "", item.body_text or "")
    if _gemini_enabled():
        ai = _gemini_classify(item.subject or "", item.body_text or "")
        if ai:
            # Keep guardrail: AI can suggest, but still mark needs_review=True and review_only.
            base.update(ai)
            base["needs_review"] = True
            base["suggested_action"] = "review_only"
    item.category = base["category"]
    item.confidence = float(base["confidence"])
    item.risk_flags = base["risk_flags"]
    item.suggested_site_code = base["suggested_site_code"]
    item.suggested_customer = base["suggested_customer"]
    item.suggested_action = base["suggested_action"]
    item.ai_provider = base["ai_provider"]
    item.ai_note = base["ai_note"]
    item.needs_review = bool(base["needs_review"])
    item.updated_at = datetime.utcnow()


def sync_inbox(session: Session) -> dict:
    scope = get_inbox_scope()
    run = InboxSyncRun(account_label=scope.account_label, mailbox=scope.mailbox, status="running")
    session.add(run)
    session.commit()
    session.refresh(run)

    if not scope.enabled:
        run.status = "error"
        run.error_message = "EMAIL_INGEST_ENABLED != 1"
        run.ended_at = datetime.utcnow()
        session.add(run)
        session.commit()
        return {"ok": False, "error": run.error_message, "run_id": run.id}
    if not scope.username:
        run.status = "error"
        run.error_message = "missing imap username"
        run.ended_at = datetime.utcnow()
        session.add(run)
        session.commit()
        return {"ok": False, "error": run.error_message, "run_id": run.id}
    if scope.auth_mode == "oauth2":
        rt = email_oauth.load_google_refresh_token()
        cid, csec, _ = email_oauth.oauth_client_config()
        if not rt:
            run.status = "error"
            run.error_message = "missing oauth refresh token"
            run.ended_at = datetime.utcnow()
            session.add(run)
            session.commit()
            return {"ok": False, "error": run.error_message, "run_id": run.id}
        if not cid or not csec:
            run.status = "error"
            run.error_message = "missing oauth client config"
            run.ended_at = datetime.utcnow()
            session.add(run)
            session.commit()
            return {"ok": False, "error": run.error_message, "run_id": run.id}
    elif not scope.password:
        run.status = "error"
        run.error_message = "missing imap password"
        run.ended_at = datetime.utcnow()
        session.add(run)
        session.commit()
        return {"ok": False, "error": run.error_message, "run_id": run.id}

    inserted = 0
    updated = 0
    ignored = 0
    fetched = 0
    try:
        client = _imap_connect_login(scope)
        client.select(scope.mailbox)
        typ, data = client.search(None, "ALL")
        if typ != "OK":
            raise RuntimeError("imap search failed")
        uids = [u.decode("utf-8", errors="ignore") for u in (data[0] or b"").split() if u]
        pick = uids[-scope.max_fetch :]
        for uid in pick:
            typ, msg_data = client.fetch(uid.encode("utf-8"), "(RFC822)")
            if typ != "OK" or not msg_data:
                ignored += 1
                continue
            fetched += 1
            raw = None
            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2:
                    raw = part[1]
                    break
            if not raw:
                ignored += 1
                continue
            msg = email.message_from_bytes(raw)
            message_id = (msg.get("Message-ID", "") or "").strip()
            subject = _decode_header_value(msg.get("Subject", ""))
            sent_at = _parse_sent_at(msg.get("Date", ""))
            from_name, from_email = ("", "")
            from_items = getaddresses([msg.get("From", "") or ""])
            if from_items:
                from_name = _decode_header_value(from_items[0][0])
                from_email = (from_items[0][1] or "").strip().lower()
            body_text, has_attach = _extract_text(msg)
            to_csv = _to_csv_emails(msg.get("To", ""))
            cc_csv = _to_csv_emails(msg.get("Cc", ""))

            row = session.exec(
                select(InboxEmail).where(
                    InboxEmail.account_label == scope.account_label,
                    InboxEmail.imap_uid == uid,
                )
            ).first()
            if row is None and message_id:
                row = session.exec(
                    select(InboxEmail).where(
                        InboxEmail.account_label == scope.account_label,
                        InboxEmail.message_id == message_id,
                    )
                ).first()
            if row is None:
                row = InboxEmail(account_label=scope.account_label, mailbox=scope.mailbox, imap_uid=uid)
                inserted += 1
            else:
                updated += 1

            row.message_id = message_id
            row.sent_at = sent_at
            row.from_name = from_name
            row.from_email = from_email
            row.to_emails = to_csv
            row.cc_emails = cc_csv
            row.subject = subject[:500]
            row.body_text = body_text
            row.has_attachment = has_attach
            row.source = "imap"
            classify_email_item(row)
            session.add(row)

        client.close()
        client.logout()
        session.commit()
        run.status = "ok"
    except Exception as ex:
        session.rollback()
        run.status = "error"
        run.error_message = str(ex)[:500]
    finally:
        run.fetched_count = fetched
        run.inserted_count = inserted
        run.updated_count = updated
        run.ignored_count = ignored
        run.ended_at = datetime.utcnow()
        session.add(run)
        session.commit()
    return {
        "ok": run.status == "ok",
        "run_id": run.id,
        "status": run.status,
        "error": run.error_message,
        "fetched": fetched,
        "inserted": inserted,
        "updated": updated,
        "ignored": ignored,
        "account_label": scope.account_label,
        "mailbox": scope.mailbox,
    }
