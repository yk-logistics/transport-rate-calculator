# -*- coding: utf-8 -*-
"""อ่านบิลซ่อม/บิลร้านจากรูปถ่าย → ร่างรายการ (v49).

กฎยืน: AI ได้แค่ "เสนอร่าง" — บรรทัดจริงเกิดตอนคนกด "เพิ่มเข้าบิล" บนหน้า
/maint/records/{id} เท่านั้น (กติกาเดียวกับกล่องรอคัดจากไลน์). บิลส่วนใหญ่เป็น
ลายมือ → ต้องให้คนตรวจเสมอ; ตัวเลขที่รวมไม่ลงตัวจะถูกเตือนบนหน้า ไม่ใช่แก้เงียบ.

ใช้ Claude sonnet ผ่าน `claude -p` (อ่านรูปด้วย Read tool) — Qwen gateway ไม่รับรูป.
"""
import json
import re

from services import ai_assist

_KIND_ALIASES = {
    "part": "part", "อะไหล่": "part", "ของ": "part", "สินค้า": "part",
    "labor": "labor", "ค่าแรง": "labor", "แรงงาน": "labor",
    "service": "service", "บริการ": "service", "ค่าบริการ": "service",
}

_PROMPT = """อ่านบิล/ใบเสร็จในรูปนี้: {path}

อาจเป็นบิลร้านซ่อม ร้านยาง ร้านอะไหล่ ปั๊มน้ำมัน หรือร้านค้าใดก็ได้ — ส่วนใหญ่เขียนมือ
อ่านให้ครบทุกบรรทัดในตาราง
แต่ละบรรทัดมี: จำนวน (QUANTITY) / รายการ (DESCRIPTION) / หน่วยละ (UNIT PRICE) / จำนวนเงิน (AMOUNT)

จัดหมวดแต่ละบรรทัดเป็นหนึ่งใน:
- "part" = ของที่จับต้องได้ (ยาง น็อต ลูกยาง ผ้าเบรก น้ำมันเครื่อง ไส้กรอง)
- "labor" = ค่าแรงช่าง (ค่าแรง ค่าถอด ค่าประกอบ)
- "service" = ค่าบริการ (บริการนอกสถานที่ ค่าเดินทาง ค่ารถออกไปหน้างาน)

กฎ:
- อ่านตัวเลขตามที่เห็น ห้ามเดา ถ้าอ่านไม่ออกให้ใส่ null
- ถ้าไม่มีช่องจำนวน ให้ qty = 1
- amount ควรเท่ากับ qty x unit_price ถ้าไม่ตรงให้คงตัวเลขตามบิล อย่าแก้ให้ตรงเอง
- total = ยอดรวมท้ายบิล (ช่อง TOTAL/รวมเงิน) ถ้าไม่มีให้ null
- plate = ทะเบียนรถถ้ามีเขียนไว้ (เช่น 71-8005) ไม่มีให้ null
- work_date = วันที่บนบิลรูปแบบ YYYY-MM-DD (บิลไทยมักเป็น พ.ศ. ให้แปลงเป็น ค.ศ.) ไม่มีให้ null
- ข้อความที่ขีดฆ่า/เขียนทับภายหลังด้วยปากกาสีอื่น ไม่ใช่รายการในบิล ให้ข้าม

ตอบ is_bill=false **เฉพาะเมื่อรูปไม่มีรายการที่มีราคาเลย** (เช่น รูปรถ รูปยางเสีย
ฟอร์มส่งของที่ไม่มีราคา) พร้อม note สั้นๆ ว่ารูปคืออะไร
ถ้ามีรายการราคาให้อ่านมาให้หมด แม้จะไม่ใช่ร้านซ่อม (ปั๊มน้ำมัน/ไปรษณีย์ ก็ถือว่าเป็นบิล)

ตอบเป็น JSON อย่างเดียว ห้ามเขียนคำอธิบายนอก JSON เด็ดขาด แม้รูปจะไม่ใช่บิล:
{{"is_bill": true, "note": "", "vendor": "ชื่อร้าน หรือ null", "work_date": null,
  "plate": null, "total": null,
  "lines": [{{"kind": "part", "name": "ชื่อรายการ", "qty": 1, "unit_price": 0, "amount": 0}}]}}
"""


def _num(v):
    """ตัวเลขจาก AI — None/ว่าง/อ่านไม่ออก = 0.0"""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[^\d.\-]", "", str(v))
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def _clean_line(d: dict) -> dict | None:
    name = str(d.get("name") or "").strip()
    if not name:
        return None
    qty = _num(d.get("qty")) or 1.0
    unit = _num(d.get("unit_price"))
    amount = _num(d.get("amount"))
    if not unit and amount:            # บิลเขียนแต่ยอดรวมบรรทัด
        unit = amount / qty if qty else amount
    if not amount:
        amount = qty * unit
    kind = _KIND_ALIASES.get(str(d.get("kind") or "").strip().lower(), "part")
    return {"kind": kind, "name": name, "qty": qty,
            "unit_price": round(unit, 2), "amount": round(amount, 2)}


def _extract_json(raw: str) -> dict:
    """AI ชอบพ่วงคำอธิบายไทยหน้า/หลัง JSON (เห็นจริงตอนรูปไม่ใช่บิล) — เอาเฉพาะก้อน JSON.
    ในโค้ดบล็อก ```json ... ``` ก่อน แล้วค่อยเดาจากปีกกาแรก→ปีกกาสุดท้าย."""
    for pat in (r"```(?:json)?\s*(\{.*?\})\s*```", r"(\{.*\})"):
        m = re.search(pat, raw, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    raise RuntimeError("AI ตอบมาไม่เป็นรูปแบบที่อ่านได้ — ลองกดใหม่อีกครั้ง")


def read_bill(image_path: str) -> dict:
    """รูปบิล → ร่าง {vendor, work_date, plate, total, lines[], sum_lines, mismatch}.

    พังทางไหนก็ตามโยน RuntimeError ข้อความภาษาคน (หน้าเว็บโชว์ตรงๆ ได้)."""
    raw = ai_assist.chat_claude(_PROMPT.format(path=image_path), timeout=240, model="sonnet")
    d = _extract_json(raw)

    if d.get("is_bill") is False:
        note = str(d.get("note") or "").strip()
        raise RuntimeError(f"รูปนี้ไม่ใช่บิลที่มีรายการราคา{' — ' + note if note else ''}")
    lines = [c for c in (_clean_line(x) for x in (d.get("lines") or [])
                         if isinstance(x, dict)) if c]
    if not lines:
        raise RuntimeError("ไม่พบรายการในบิล — ถ่ายให้เห็นตารางรายการทั้งตาราง แล้วลองใหม่")
    sum_lines = round(sum(ln["amount"] for ln in lines), 2)
    total = _num(d.get("total")) or None
    return {
        "vendor": str(d.get("vendor") or "").strip(),
        "work_date": str(d.get("work_date") or "").strip(),
        "plate": str(d.get("plate") or "").strip(),
        "total": total,
        "lines": lines,
        "sum_lines": sum_lines,
        # ยอดรวมท้ายบิลไม่ตรงผลบวกรายการ = ต้องให้คนดู ไม่ใช่แก้ให้เงียบ
        "mismatch": bool(total and abs(total - sum_lines) >= 0.5),
    }
