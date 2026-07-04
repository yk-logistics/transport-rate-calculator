# -*- coding: utf-8 -*-
"""F3: ชุดหลักฐานวางบิล (POD) — เสนอผูกรูปจากกลุ่มไลน์ลูกค้าเข้ากับแถวเดลี่.

หลักจับคู่ (ตามสเปค F3 — คนยืนยันเสมอ ระบบไม่ผูกเอง):
  1) รูปอยู่ในกลุ่มที่ mark เป็น "ลูกค้า" (LineGroupMap)
  2) บริบท = ข้อความ text ในกลุ่มเดียวกัน ±10 นาทีรอบรูป → ดึงเลขตู้/ทะเบียน
  3) แถวเดลี่ candidate: work_date = วันส่งรูป ±1 วัน และ
     (เลขตู้ตรง หรือ ทะเบียนตรง) — ถ้าบริบทไม่มีเลขเลย เสนอตามลูกค้า+วันอย่างเดียว (คะแนนต่ำ)
อ่าน archive แบบ read-only เท่านั้น; ผลผูกเก็บใน JobMedia (app.db).
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta

from services import line_archive as la
from services.line_inbox import CONTAINER_RE

PLATE_RE = re.compile(r"\b(\d{2,3})\s?-\s?(\d{4})\b")   # 71-8967 / 72 1220


def _extract_refs(texts: list[str]) -> tuple[set[str], set[str]]:
    containers: set[str] = set()
    plates: set[str] = set()
    for t in texts:
        up = (t or "").upper()
        containers |= {f"{a}{b}" for a, b in CONTAINER_RE.findall(up)}
        plates |= {f"{a}-{b}" for a, b in PLATE_RE.findall(up)}
    return containers, plates


def photo_candidates(group_ids: list[str], days: int = 7,
                     exclude_ids: set[int] | None = None, limit: int = 100) -> list[dict]:
    """รูปในกลุ่มลูกค้า (ยังไม่ผูก/ไม่ข้าม) + เลขตู้/ทะเบียนจากข้อความรอบ ๆ ±10 นาที."""
    if not group_ids:
        return []
    exclude_ids = exclude_ids or set()
    since = (date.today() - timedelta(days=days)).isoformat()
    p = la.db_path()
    if p is None:
        raise FileNotFoundError("ไม่พบ line_archive.db บนเครื่องนี้")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        marks = ",".join("?" * len(group_ids))
        photos = con.execute(f"""
            SELECT m.id, m.group_id, m.sent_at, g.name AS group_name,
                   COALESCE(u.alias, u.display_name) AS who
            FROM line_message m
            LEFT JOIN line_group g ON g.group_id = m.group_id
            LEFT JOIN line_user u ON u.user_id = m.user_id
            WHERE m.group_id IN ({marks}) AND m.msg_type = 'image'
              AND m.media_path IS NOT NULL AND m.media_path != ''
              AND substr(m.sent_at, 1, 10) >= ?
            ORDER BY m.sent_at DESC LIMIT ?""",
            (*group_ids, since, limit * 3)).fetchall()

        out = []
        for ph in photos:
            if ph["id"] in exclude_ids:
                continue
            try:
                sent = datetime.fromisoformat(str(ph["sent_at"]).replace("T", " ")[:16])
            except ValueError:
                continue
            lo = (sent - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
            hi = (sent + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
            ctx = con.execute("""
                SELECT text FROM line_message
                WHERE group_id = ? AND msg_type = 'text'
                  AND replace(substr(sent_at, 1, 16), 'T', ' ') BETWEEN ? AND ?
                ORDER BY sent_at""", (ph["group_id"], lo, hi)).fetchall()
            texts = [r["text"] for r in ctx]
            containers, plates = _extract_refs(texts)
            out.append({
                "msg_id": ph["id"], "group_id": ph["group_id"],
                "group_name": ph["group_name"] or "", "who": ph["who"] or "",
                "sent_at": str(ph["sent_at"])[:16], "sent_date": sent.date(),
                "containers": sorted(containers), "plates": sorted(plates),
                # ข้อความรอบรูปทั้งก้อน — ใช้ reverse-match เลข Job ของเดลี่
                # (วัดจริง 4ก.ค.: KLND โพสต์ "Job. KLND26-015737" ตรง job_ref เดลี่ 100%
                #  ส่วนเลขตู้อยู่ในรูปเอง อ่านจาก text ไม่ได้)
                "ctx_text": " ".join(t or "" for t in texts).upper(),
            })
            if len(out) >= limit:
                break
        return out
    finally:
        con.close()


def match_daily_jobs(session, cand: dict, customer_status_codes: tuple) -> list[dict]:
    """เสนอแถวเดลี่สำหรับรูป 1 ใบ — วัน ±1 + ตู้/ทะเบียนตรง = คะแนนสูง."""
    from sqlmodel import select
    from models import DailyJob

    d = cand["sent_date"]
    q = select(DailyJob).where(
        DailyJob.work_date >= d - timedelta(days=1),
        DailyJob.work_date <= d + timedelta(days=1))
    if customer_status_codes:
        q = q.where(DailyJob.status_code.in_(customer_status_codes))  # type: ignore[attr-defined]
    jobs = session.exec(q).all()
    ctx_text = cand.get("ctx_text", "")
    out = []
    for j in jobs:
        score = 0
        # เลข Job ของเดลี่โผล่ในข้อความรอบรูป = สัญญาณแรงสุด (reverse-match)
        jr = (j.job_ref or "").strip().upper()
        if len(jr) >= 6 and jr in ctx_text:
            score += 4
        dn = (j.doc_no or "").strip().strip('"').split("/")[0].strip().upper()
        if len(dn) >= 8 and dn in ctx_text:
            score += 4
        # เดลี่ตู้คู่คีย์เป็น "AAAA1234567/BBBB7654321" (2 ตู้เที่ยวเดียว — เจอจริง 12 แถว/ไตรมาส)
        # → แยกเทียบทีละตู้ ไม่งั้นแถวตู้คู่ไม่มีวัน match รูป
        j_conts = [x.strip().upper() for x in (j.container_no or "").split("/") if x.strip()]
        if cand["containers"] and any(c in cand["containers"] for c in j_conts):
            score += 3
        if cand["plates"] and (j.plate_no_raw or "").strip() in cand["plates"]:
            score += 2
        if j.work_date == d:
            score += 1
        # ไม่มีเลขอ้างอิงเลย → เสนอเฉพาะวันตรง (คะแนน 1) กัน list ท่วม
        if score == 0 and (cand["containers"] or cand["plates"] or j.work_date != d):
            continue
        out.append({
            "job_id": j.id, "work_date": j.work_date, "score": score,
            "container": j.container_no or "", "plate": j.plate_no_raw or "",
            "customer": j.status_code or "", "invoice_no": j.invoice_no or "",
            "destination": j.destination or j.pickup_location or "",
        })
    out.sort(key=lambda x: -x["score"])
    return out[:8]
