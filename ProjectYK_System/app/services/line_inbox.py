# -*- coding: utf-8 -*-
"""F2: กล่องงานเข้าจากกลุ่มไลน์ลูกค้า — สแกนข้อความหา pattern "งาน" (read-only).

อ่านข้อความจาก line_archive (ผ่าน services.line_archive — mode=ro) เฉพาะกลุ่มที่
โอ mark เป็น "ลูกค้า" (LineGroupMap ใน app.db) แล้วให้คะแนนว่าเหมือนสั่งงานแค่ไหน:
  - เลขตู้คอนเทนเนอร์ (4 ตัวอักษร + 7 ตัวเลข เช่น TEXU1234567) = สัญญาณแรงสุด
  - คำสั่งงาน (เข้า/โหลด/ส่ง/รับตู้/คืนตู้/บรรจุ/booking/ใบงาน) + มีวันที่หรือเวลา
ผลเป็น candidate ให้คนกด "รับเป็นงาน" (เปิด planner prefill) หรือ "ไม่ใช่งาน"
— ระบบไม่สร้างงานเองเด็ดขาด (คนตัดสินเสมอ)

เกณฑ์ผ่านสเปค (จับงานจริง ≥80% จากข้อความจริง 1 สัปดาห์) ต้องวัดบน server
ที่มี archive จริง — dev มีแต่เทสต์สังเคราะห์ (ดู tests/test_line_inbox.py)
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta

from services import line_archive as la

# เลขตู้: 4 ตัวอักษร (ตัวที่ 4 มัก U/J/Z) + 7 ตัวเลข — ยอมมีช่องว่าง/ขีดคั่น
CONTAINER_RE = re.compile(r"\b([A-Z]{4})\s?-?(\d{7})\b")
DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b")
TIME_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\s*(?:น\.?)?\b")
KEYWORDS = ("เข้าโหลด", "โหลด", "ส่งตู้", "รับตู้", "คืนตู้", "บรรจุ",
            "booking", "ใบงาน", "แผนงาน", "เข้าท่า", "ปล่อยตู้", "แผนพรุ่งนี้")
_WEAK_KEYWORDS = ("เข้า", "ส่ง", "พรุ่งนี้")


def _guess_work_date(text: str, sent_iso: str) -> str:
    """เดาวันที่งานจากข้อความ (คืน ISO หรือ '') — เดาไม่ได้ = ว่าง ให้คนเลือกเอง."""
    try:
        sent = date.fromisoformat(str(sent_iso)[:10])
    except ValueError:
        return ""
    if "พรุ่งนี้" in text:
        return (sent + timedelta(days=1)).isoformat()
    m = DATE_RE.search(text)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = sent.year
        raw_y = m.group(3)
        if raw_y:
            y = int(raw_y)
            if y < 100:
                y += 2500 if y > 60 else 2000   # พ.ศ. 2 หลัก vs ค.ศ. 2 หลัก
            if y > 2400:
                y -= 543
        try:
            guess = date(y, mo, d)
        except ValueError:
            return ""
        # วันที่ในอดีตไกล = คงไม่ใช่วันงาน (เช่นเลขบิล) — ยอมย้อนหลัง 2 วัน
        if guess < sent - timedelta(days=2) or guess > sent + timedelta(days=45):
            return ""
        return guess.isoformat()
    return ""


def score_message(text: str) -> dict | None:
    """ให้คะแนนข้อความ — None = ไม่ใช่ candidate."""
    t = (text or "").strip()
    if not t:
        return None
    up = t.upper()
    containers = [f"{a}{b}" for a, b in CONTAINER_RE.findall(up)]
    has_kw = any(k.upper() in up for k in KEYWORDS)
    has_weak = any(k in t for k in _WEAK_KEYWORDS)
    has_date = bool(DATE_RE.search(t))
    has_time = bool(TIME_RE.search(t))
    score = len(containers) * 3 + (2 if has_kw else 0) + \
        (1 if (has_date or has_time) else 0)
    if containers or (has_kw and (has_date or has_time)) \
            or (has_weak and has_date and has_time):
        return {"score": score, "containers": containers,
                "has_date": has_date, "has_time": has_time, "has_kw": has_kw}
    return None


def scan_candidates(group_ids: list[str], days: int = 7,
                    exclude_ids: set[int] | None = None, limit: int = 200) -> list[dict]:
    """สแกนข้อความ text ของกลุ่มที่เลือก ย้อนหลัง N วัน → candidate เรียงคะแนน+ใหม่ก่อน."""
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
        rows = con.execute(f"""
            SELECT m.id, m.group_id, m.text, m.sent_at,
                   g.name AS group_name, COALESCE(u.alias, u.display_name) AS who
            FROM line_message m
            LEFT JOIN line_group g ON g.group_id = m.group_id
            LEFT JOIN line_user u ON u.user_id = m.user_id
            WHERE m.group_id IN ({marks}) AND m.msg_type = 'text'
              AND substr(m.sent_at, 1, 10) >= ?
            ORDER BY m.sent_at DESC LIMIT 2000""",
            (*group_ids, since)).fetchall()
    finally:
        con.close()

    out = []
    for r in rows:
        if r["id"] in exclude_ids:
            continue
        sc = score_message(r["text"])
        if sc is None:
            continue
        out.append({
            "msg_id": r["id"], "group_id": r["group_id"],
            "group_name": r["group_name"] or "", "who": r["who"] or "",
            "sent_at": str(r["sent_at"])[:16], "text": r["text"],
            "work_date": _guess_work_date(r["text"], r["sent_at"]),
            **sc,
        })
        if len(out) >= limit:
            break
    # คะแนนสูงก่อน — คะแนนเท่ากันเอาข้อความใหม่ก่อน (สอง pass, sort เสถียร)
    out.sort(key=lambda c: c["sent_at"], reverse=True)
    out.sort(key=lambda c: -c["score"])
    return out
