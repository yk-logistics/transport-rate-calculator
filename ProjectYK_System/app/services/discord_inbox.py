"""ดึงข้อความ+รูปจากช่อง Discord 📌01-inbox-โยนมาก่อน เข้า /todo (13ก.ค.).

โอ forward อะไรก็ตามที่อยากจดเข้าช่องนี้เอง (มือถือ/คอม) → ระบบ poll ด้วย bot token
ตัวเดียวกับ line_archiver แล้วสร้าง TodoItem หมวด "inbox" ให้เลย — ของที่โยนเอง
ถือว่าตั้งใจแล้ว ไม่ต้องผ่านกล่องรอคัดแบบข้อความไลน์.

dedupe ด้วย watermark id ข้อความล่าสุด (AppSetting: discord_inbox_last_id) —
Discord snowflake id เพิ่มตามเวลาเสมอ. ต้องเปิด Message Content Intent ใน
developer portal ไม่งั้น content/attachments กลับมาว่างทั้งที่ HTTP 200 (เปิดแล้ว 13ก.ค.).
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlmodel import Session

from db_config import engine
from models import AppSetting, TodoItem

API = "https://discord.com/api/v10"
DEFAULT_CHANNEL_ID = "1458138638213710058"   # 📌01-inbox-โยนมาก่อน (guild YK)
CATEGORY = "inbox"
MEDIA_DIR = Path(__file__).resolve().parents[1] / "_todo_media"
_MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".heic")
_MAX_FILE = 20 * 1024 * 1024
_FIRST_RUN_LIMIT = 20   # รอบแรกไม่มี watermark — เอาแค่ 20 ข้อความล่าสุด กันประวัติเก่าทะลัก
_WATERMARK_KEY = "discord_inbox_last_id"
_TZ_TH = timezone(timedelta(hours=7))

def _token() -> str:
    """ต้องตั้ง env ชัดๆ ถึงเปิดใช้ — ห้าม fallback อัตโนมัติ ไม่งั้นเทสต์/dev ที่มี
    .env ของ archiver ในเครื่องจะแอบยิง Discord จริงตอนเปิด /todo.
    YK_DISCORD_TOKEN_FILE รับได้ทั้งไฟล์ token ดิบ และ .env ของ line_archiver."""
    tok = (os.environ.get("YK_DISCORD_TOKEN") or "").strip()
    if tok:
        return tok
    f = os.environ.get("YK_DISCORD_TOKEN_FILE", "")
    if f and Path(f).exists():
        text = Path(f).read_text(encoding="utf-8").strip()
        for line in text.splitlines():
            if line.strip().startswith("DISCORD_BOT_TOKEN="):
                return line.split("=", 1)[1].strip()
        return "" if "=" in text else text   # ไฟล์ .env แต่ไม่มีคีย์ = ไม่เปิดใช้
    return ""


def available() -> bool:
    return bool(_token())


def _get_setting(s: Session, key: str, default: str = "") -> str:
    row = s.get(AppSetting, key)
    return row.value if row else default


def _set_setting(s: Session, key: str, value: str) -> None:
    row = s.get(AppSetting, key)
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        row = AppSetting(key=key, value=value)
    s.add(row)
    s.commit()


def _fetch_new(http: httpx.Client, headers: dict, channel: str, after: str) -> list[dict]:
    """ดึงข้อความ id > after ทั้งหมด (วนเพจ) — คืนเรียงเก่า→ใหม่."""
    out: list[dict] = []
    cursor = after
    while True:
        params = {"limit": 100, "after": cursor} if cursor else {"limit": _FIRST_RUN_LIMIT}
        r = http.get(f"{API}/channels/{channel}/messages",
                     headers=headers, params=params)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if not cursor or len(batch) < 100:
            break
        cursor = str(max(int(m["id"]) for m in batch))
    out.sort(key=lambda m: int(m["id"]))
    return out


def _msg_text(m: dict) -> str:
    parts = [(m.get("content") or "").strip()]
    for sn in m.get("message_snapshots") or []:
        parts.append(((sn.get("message") or {}).get("content") or "").strip())
    return "\n".join(p for p in parts if p)


def _msg_attachments(m: dict) -> list[dict]:
    atts = list(m.get("attachments") or [])
    for sn in m.get("message_snapshots") or []:
        atts.extend((sn.get("message") or {}).get("attachments") or [])
    keep = []
    for a in atts:
        ext = Path(a.get("filename") or "").suffix.lower()
        if ext not in _MEDIA_EXT:
            if not str(a.get("content_type") or "").startswith("image/"):
                continue
            ext = ".jpg"
        if int(a.get("size") or 0) > _MAX_FILE:
            continue
        keep.append({"url": a["url"], "ext": ext})
    return keep


def _header(m: dict) -> str:
    who = (m.get("author") or {}).get("username") or "?"
    sent = ""
    try:
        dt = datetime.fromisoformat(m["timestamp"]).astimezone(_TZ_TH)
        sent = dt.strftime("%Y-%m-%d %H:%M")
    except (KeyError, ValueError):
        pass
    return f"💬 Discord inbox — {who} {sent}".rstrip()


def pull(username: str, http: httpx.Client | None = None) -> dict:
    """ดึงข้อความใหม่จากช่อง inbox → TodoItem ของ username. คืน {"added", "media"}.

    watermark ขยับทีละข้อความหลัง commit — พังกลางทางรอบหน้าดึงต่อจากที่ค้าง
    ไม่สร้างซ้ำ. ข้อความบอท/ว่างเปล่า = ข้ามแต่ watermark ขยับ."""
    tok = _token()
    if not tok:
        return {"added": 0, "media": 0}
    channel = os.environ.get("YK_DISCORD_INBOX_CHANNEL", DEFAULT_CHANNEL_ID)
    headers = {"Authorization": f"Bot {tok}"}
    own_http = http is None
    # เรียกจากหน้า /todo แบบ sync — timeout ระดับ client กันหน้าโหลดค้างถ้า Discord อืด
    http = http or httpx.Client(timeout=15)
    added = media_n = 0
    try:
        with Session(engine) as s:
            after = _get_setting(s, _WATERMARK_KEY, "")
        msgs = _fetch_new(http, headers, channel, after)
        for m in msgs:
            text = _msg_text(m)
            atts = _msg_attachments(m)
            skip = (m.get("author") or {}).get("bot") or (not text and not atts)
            if not skip:
                body = (text + "\n\n" if text else "") + _header(m)
                item = TodoItem(username=username, text=body, category=CATEGORY)
                with Session(engine) as s:
                    s.add(item)
                    s.commit()
                    s.refresh(item)
                    names = []
                    for a in atts:
                        try:
                            r = http.get(a["url"])
                            r.raise_for_status()
                        except httpx.HTTPError:
                            continue   # รูปโหลดพลาด — เก็บข้อความไว้ ไม่ล้มทั้งรอบ
                        d = MEDIA_DIR / str(item.id)
                        d.mkdir(parents=True, exist_ok=True)
                        name = f"{len(names) + 1}{a['ext']}"
                        (d / name).write_bytes(r.content)
                        names.append(name)
                    if names:
                        item.media_json = ",".join(names)
                        s.add(item)
                        s.commit()
                    media_n += len(names)
                added += 1
            with Session(engine) as s:
                _set_setting(s, _WATERMARK_KEY, str(m["id"]))
    finally:
        if own_http:
            http.close()
    return {"added": added, "media": media_n}
