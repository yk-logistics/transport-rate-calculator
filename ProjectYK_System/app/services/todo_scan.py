"""เฟส 4 LINE→todo: สแกนข้อความไลน์ → เสนองานเข้ากล่องรอคัด (TodoSuggest).

กฎยืน: AI ได้แค่ "เสนอ" — แถว pending รอโอกดรับบนหน้า /todo ถึงจะเกิด TodoItem จริง.
ใช้ Qwen ฟรี (chat_qwen) ก่อนเสมอ — งานคัดกรองปริมาณเยอะ ไม่ควรกินโควต้า Max;
Qwen ล่ม (gateway ฟรี ล่มยาวได้ — 9ก.ค. คืน content ว่างทุก prompt) ค่อยตก Claude
haiku จำกัด _MAX_CLAUDE_CHUNKS ก้อนต่อรอบ.
"""
import json
import re
from datetime import datetime, timedelta

from sqlmodel import Session, select

from db_config import engine
from models import TodoSuggest
from services import ai_assist, line_archive

# กรองหยาบก่อนส่ง AI — ลดจำนวนข้อความที่ต้องจ่ายเวลาคัด (แชทส่วนใหญ่คือรายงาน/ทักทาย)
_KEYWORDS = ("ซ่อม", "เสีย", "แตก", "รั่ว", "พัง", "เปลี่ยน", "เบิก", "ขอ", "สั่ง",
             "ซื้อ", "แจ้ง", "ด่วน", "พรุ่งนี้", "อย่าลืม", "ฝาก", "ต้อง", "ตรวจ",
             "เคลม", "ครบกำหนด", "ภาษี", "ประกัน", "ต่อทะเบียน", "นัด", "ติดต่อ")

_MAX_CLAUDE_CHUNKS = 4   # เพดานก้อนที่ยอมให้ตกไป Claude ต่อรอบ (≈100 ข้อความ/วัน)

_SYSTEM = (
    "คุณช่วยคัดข้อความจากกลุ่มไลน์ของบริษัทขนส่ง ว่าข้อความไหนเป็น \"งานที่ต้องมีคนทำต่อ\"\n"
    "นับเป็นงาน: แจ้งซ่อม/ของเสีย, ขอเบิกของ, สั่งงาน/ฝากงาน, นัดหมาย, ปัญหาที่ต้องตามแก้\n"
    "ไม่นับ: รายงานว่าทำเสร็จแล้ว, ทักทาย/ขอบคุณ, รับทราบ, คุยเล่น, "
    "แจ้งเติมน้ำมัน/รายการเติมดีเซลที่ปั๊ม (มีระบบน้ำมันแยกอยู่แล้ว), "
    "ประโยคถาม-ตอบสั้นๆ กลางบทสนทนา (เช่น 'มีของไหม' 'รับทราบ')\n"
    "อินพุตคือรายการ [id] ผู้ส่ง@กลุ่ม: ข้อความ — ตอบเป็น JSON array อย่างเดียว "
    "เฉพาะข้อความที่เป็นงาน:\n"
    '[{"id": <id>, "summary": "สรุปงานสั้นๆ ภาษาไทย ใส่ทะเบียนรถ/ของ/ชื่อคนให้ครบ", '
    '"category": "แจ้งซ่อม หรือ งาน หรือ เบิกของ"}]\n'
    "ห้ามแต่งข้อมูลเพิ่ม ถ้าไม่มีข้อความเป็นงานเลยตอบ []")


def _prefilter(text: str) -> bool:
    t = (text or "").strip()
    # ฟอร์แมตบอท/มาตรฐานแจ้งเติมน้ำมันที่ปั๊ม — F4 (/fuel/line-compare) ดูแยกอยู่แล้ว
    if "แจ้งเติม" in t and any(k in t for k in ("ดีเซล", "B20", "B7", "ลิตร", "ปั๊ม", "Caltex")):
        return False
    return len(t) >= 8 and any(k in t for k in _KEYWORDS)


def scan(hours: int = 26) -> dict:
    """สแกนข้อความ text ย้อนหลัง N ชม. → เติมแถว pending ใหม่ใน TodoSuggest.

    dedupe ถาวรด้วย line_msg_id (เคยเสนอ/เคยซ่อนแล้วไม่เสนอซ้ำ). คืน dict สรุปจำนวน
    (failed = ก้อนที่ AI ล่ม — เสนอได้บางส่วน). พังทุกก้อน / archive ไม่มี
    โยน RuntimeError ข้อความภาษาคน."""
    since = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    try:
        msgs = line_archive.recent_text_messages(since)
    except FileNotFoundError as e:
        raise RuntimeError(str(e))
    with Session(engine) as s:
        seen = set(s.exec(select(TodoSuggest.line_msg_id)).all())
        # กันโพสต์ซ้ำข้ามกลุ่ม (คนเดิมส่งข้อความเดียวกันหลายห้อง) — คีย์ (who, text)
        seen_txt = {(r[0], r[1]) for r in
                    s.exec(select(TodoSuggest.who, TodoSuggest.text)).all()}
    cand = []
    for m in msgs:
        key = (m["who"] or "", m["text"])
        if m["id"] in seen or key in seen_txt or not _prefilter(m["text"]):
            continue
        seen_txt.add(key)
        cand.append(m)
    added = 0
    failed = 0
    last_err = ""
    claude_left = _MAX_CLAUDE_CHUNKS
    chunks = [cand[i:i + 25] for i in range(0, len(cand), 25)]   # หั่นก้อน — Qwen context 128k
    for chunk in chunks:
        ids = {m["id"]: m for m in chunk}
        listing = "\n".join(
            f"[{m['id']}] {(m['who'] or '?')}@{(m['group_name'] or '?')}: "
            f"{m['text'][:300]}" for m in chunk)
        try:
            raw = ai_assist.chat_qwen(
                [{"role": "system", "content": _SYSTEM},
                 {"role": "user", "content": listing}], max_tokens=2000)
        except RuntimeError as e:
            # ก้อนที่ข้ามยังไม่ถูกจดว่าเสนอแล้ว → รอบหน้าได้คัดใหม่ (หน้าต่าง 26 ชม.)
            last_err = str(e)
            if claude_left <= 0 or not ai_assist.claude_available():
                failed += 1
                continue
            claude_left -= 1
            try:
                raw = ai_assist.chat_claude(
                    _SYSTEM + "\n\nรายการข้อความ:\n" + listing, timeout=180, model="haiku")
            except RuntimeError as e2:
                last_err = str(e2)
                failed += 1
                continue
        m2 = re.search(r"\[.*\]", raw, re.S)
        try:
            items = json.loads(m2.group()) if m2 else []
        except json.JSONDecodeError:
            items = []
        with Session(engine) as s:
            for it in items:
                if not isinstance(it, dict) or it.get("id") not in ids:
                    continue  # AI มั่ว id นอกก้อน — ทิ้ง
                src = ids[it["id"]]
                s.add(TodoSuggest(
                    line_msg_id=src["id"], group_name=src["group_name"] or "",
                    who=src["who"] or "", sent_at=str(src["sent_at"])[:16],
                    text=src["text"],
                    summary=str(it.get("summary") or "").strip() or src["text"][:120],
                    category=str(it.get("category") or "").strip() or "งาน"))
                added += 1
            s.commit()
    if chunks and failed == len(chunks):
        raise RuntimeError(f"สแกนไม่สำเร็จ — AI ล่มทุกก้อน: {last_err}")
    return {"scanned": len(msgs), "candidates": len(cand), "added": added, "failed": failed}
