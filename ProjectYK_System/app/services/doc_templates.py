# -*- coding: utf-8 -*-
"""A2: แบบฟอร์มเอกสาร (ใบเสร็จรับเงิน + หนังสือรับรองหัก ณ ที่จ่าย 50 ทวิ) —
ฟอร์มมาตรฐาน (โอเคาะ 4ก.ค. "เอาตามมาตรฐานเลย") + **user ปรับ layout เองได้**
ที่ /admin/doc-designer (ลาก/ขยาย/แก้ข้อความ — เก็บ DocTemplate ใน DB, ไม่มีแถว =
default ในไฟล์นี้).

หน่วยพิกัด = มิลลิเมตรบนกระดาษ A4 (210×297) — render เป็น HTML absolute-position
แล้วพิมพ์/เซฟ PDF ผ่านเบราว์เซอร์ (ทางเดียวกับสลิป — ฟอนต์ไทยชัวร์).

placeholder ใช้ {{key}} — รายการ key อยู่ใน PLACEHOLDER_DOC ต่อชนิดเอกสาร.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

COMPANY = {
    "name": "บริษัท วาย.เค. ลอจิสติค จำกัด (สำนักงานใหญ่)",
    "name_en": "Y.K. Logistics Co., Ltd.",
    "address": "70 หมู่ 5 ตำบลเชียงรากน้อย อำเภอบางปะอิน จังหวัดพระนครศรีอยุธยา 13180",
    "tax_id": "0125548009248",
}

# ---- ฟอร์มมาตรฐาน (default — user แก้ได้ที่ designer แล้วเก็บ DB override) ----

def _t(x, y, w, h, text, size=11, bold=False, align="left"):
    return {"type": "text", "x": x, "y": y, "w": w, "h": h,
            "text": text, "size": size, "bold": bold, "align": align}


def _box(x, y, w, h):
    return {"type": "box", "x": x, "y": y, "w": w, "h": h}


def _line(x, y, w):
    return {"type": "line", "x": x, "y": y, "w": w, "h": 0}


_RECEIPT_ELEMENTS = [
    _t(20, 15, 120, 8, COMPANY["name"], size=14, bold=True),
    _t(20, 22, 120, 6, COMPANY["address"], size=9),
    _t(20, 27, 120, 6, "เลขประจำตัวผู้เสียภาษี " + COMPANY["tax_id"], size=9),
    _t(140, 15, 50, 10, "ใบเสร็จรับเงิน", size=16, bold=True, align="right"),
    _t(140, 24, 50, 6, "เลขที่ {{doc_no}}", size=10, align="right"),
    _t(140, 29, 50, 6, "วันที่ {{doc_date}}", size=10, align="right"),
    _line(20, 38, 170),
    _t(20, 44, 25, 6, "ได้รับเงินจาก", size=11),
    _t(48, 44, 100, 6, "{{payer_name}}", size=11, bold=True),
    _t(20, 51, 25, 6, "รายการ", size=11),
    _t(48, 51, 140, 12, "{{description}}", size=11),
    _box(20, 66, 170, 22),
    _t(24, 70, 100, 6, "จำนวนเงิน (ตัวอักษร): {{amount_text}}", size=11),
    _t(120, 70, 66, 8, "{{amount}} บาท", size=14, bold=True, align="right"),
    _t(24, 79, 120, 6, "อ้างอิงอินวอย: {{invs}}", size=9),
    _t(20, 96, 90, 6, "ชำระโดย: โอนเข้าบัญชี", size=10),
    _t(110, 110, 76, 6, "ลงชื่อ ....................................... ผู้รับเงิน", size=11, align="center"),
    _t(110, 118, 76, 6, "( {{receiver_name}} )", size=10, align="center"),
    _t(20, 130, 170, 6, "หมายเหตุ: {{note}}", size=9),
]

_WHT_ELEMENTS = [
    _t(20, 12, 170, 8, "หนังสือรับรองการหักภาษี ณ ที่จ่าย", size=15, bold=True, align="center"),
    _t(20, 20, 170, 6, "ตามมาตรา 50 ทวิ แห่งประมวลรัษฎากร", size=10, align="center"),
    _t(150, 28, 40, 6, "เล่มที่/เลขที่ {{doc_no}}", size=10, align="right"),
    _box(20, 34, 170, 24),
    _t(24, 37, 160, 6, "ผู้มีหน้าที่หักภาษี ณ ที่จ่าย:", size=10, bold=True),
    _t(24, 43, 160, 6, COMPANY["name"], size=11),
    _t(24, 49, 160, 6, COMPANY["address"] + "  เลขประจำตัวผู้เสียภาษี " + COMPANY["tax_id"], size=9),
    _box(20, 60, 170, 24),
    _t(24, 63, 160, 6, "ผู้ถูกหักภาษี ณ ที่จ่าย:", size=10, bold=True),
    _t(24, 69, 160, 6, "{{payee_name}}", size=11),
    _t(24, 75, 160, 6, "เลขประจำตัวผู้เสียภาษี/บัตรประชาชน: {{payee_tax_id}}    ที่อยู่: {{payee_address}}", size=9),
    _box(20, 88, 170, 30),
    _t(24, 91, 80, 6, "ประเภทเงินได้พึงประเมินที่จ่าย", size=10, bold=True),
    _t(110, 91, 35, 6, "วันที่จ่าย", size=10, bold=True, align="center"),
    _t(140, 91, 24, 6, "จำนวนเงินที่จ่าย", size=10, bold=True, align="right"),
    _t(166, 91, 22, 6, "ภาษีที่หัก", size=10, bold=True, align="right"),
    _line(22, 98, 166),
    _t(24, 101, 80, 6, "{{income_type}}", size=10),
    _t(110, 101, 35, 6, "{{pay_date}}", size=10, align="center"),
    _t(140, 101, 24, 6, "{{amount}}", size=10, align="right"),
    _t(166, 101, 22, 6, "{{wht}}", size=10, align="right"),
    _line(22, 109, 166),
    _t(24, 111, 80, 6, "รวม", size=10, bold=True),
    _t(140, 111, 24, 6, "{{amount}}", size=10, bold=True, align="right"),
    _t(166, 111, 22, 6, "{{wht}}", size=10, bold=True, align="right"),
    _t(20, 122, 170, 6, "รวมภาษีที่หักนำส่ง (ตัวอักษร): {{wht_text}}", size=10),
    _t(20, 132, 100, 6, "ผู้จ่ายเงิน: ☑ หักภาษี ณ ที่จ่าย    นำส่งตามแบบ ภ.ง.ด.3", size=9),
    _t(20, 145, 170, 10, "ขอรับรองว่าข้อความและตัวเลขดังกล่าวข้างต้นถูกต้องตรงกับความจริงทุกประการ", size=10, align="center"),
    _t(110, 160, 76, 6, "ลงชื่อ ....................................... ผู้จ่ายเงิน", size=11, align="center"),
    _t(110, 168, 76, 6, "วันที่ {{doc_date}}", size=10, align="center"),
]

DEFAULT_TEMPLATES: dict[str, dict] = {
    "kb_receipt": {"name": "ใบเสร็จรับเงิน (KB เจ้าของงาน)", "paper": "A4",
                   "elements": _RECEIPT_ELEMENTS},
    "kb_wht": {"name": "หนังสือรับรองหัก ณ ที่จ่าย 50 ทวิ (KB)", "paper": "A4",
               "elements": _WHT_ELEMENTS},
}

# placeholder ที่ designer โชว์เป็น legend ให้คนแก้ฟอร์มรู้ว่ามีอะไรใช้ได้
PLACEHOLDER_DOC = {
    "kb_receipt": "doc_no, doc_date, payer_name, description, amount, amount_text, invs, receiver_name, note",
    "kb_wht": "doc_no, doc_date, payee_name, payee_tax_id, payee_address, income_type, pay_date, amount, wht, wht_text",
}


def get_template(session, key: str) -> dict:
    """template ที่ใช้จริง: DB override > default ในโค้ด."""
    from sqlmodel import select
    from models import DocTemplate

    row = session.exec(select(DocTemplate).where(DocTemplate.key == key)).first()
    if row and row.elements_json:
        try:
            return {"name": row.name or DEFAULT_TEMPLATES[key]["name"],
                    "paper": row.paper or "A4",
                    "elements": json.loads(row.elements_json)}
        except ValueError:
            pass
    if key not in DEFAULT_TEMPLATES:
        raise KeyError(f"ไม่รู้จักฟอร์ม {key}")
    return DEFAULT_TEMPLATES[key]


_PH_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render_elements(template: dict, ctx: dict) -> list[dict]:
    """แทนค่า placeholder ลง elements (คืนสำเนา — ไม่แก้ template)."""
    out = []
    for el in template["elements"]:
        el = dict(el)
        if el.get("type") == "text":
            el["text"] = _PH_RE.sub(
                lambda m: str(ctx.get(m.group(1), m.group(0))), el.get("text", ""))
        out.append(el)
    return out


def next_doc_no(session, doc_type: str, ref: str, by: str = "") -> str:
    """เลขเอกสาร idempotent: ชุด ref เดิม = เลขเดิม; ใหม่ = max(no ปีนี้)+1."""
    from sqlmodel import select
    from models import DocIssue

    year = datetime.now().year
    ref = ",".join(sorted(x.strip() for x in ref.split(",") if x.strip()))
    existing = session.exec(select(DocIssue).where(
        DocIssue.doc_type == doc_type, DocIssue.ref == ref)).first()
    if existing:
        return f"{existing.year}-{existing.no:04d}"
    last = session.exec(select(DocIssue).where(
        DocIssue.doc_type == doc_type, DocIssue.year == year)
        .order_by(DocIssue.no.desc())).first()  # type: ignore[union-attr]
    no = (last.no if last else 0) + 1
    session.add(DocIssue(doc_type=doc_type, year=year, no=no, ref=ref, issued_by=by))
    session.commit()
    return f"{year}-{no:04d}"


def baht_text(amount: float) -> str:
    """จำนวนเงินเป็นตัวอักษรไทย (BAHTTEXT อย่างย่อ — รองรับถึงร้อยล้าน+สตางค์)."""
    num = ("ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า")
    pos = ("", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน")

    def read_int(n: int) -> str:
        if n == 0:
            return "ศูนย์"
        if n >= 1_000_000:
            return read_int(n // 1_000_000) + "ล้าน" + (read_int(n % 1_000_000) if n % 1_000_000 else "")
        s = ""
        digits = str(n)
        ln = len(digits)
        for i, ch in enumerate(digits):
            d = int(ch)
            p = ln - i - 1
            if d == 0:
                continue
            if p == 0 and d == 1 and ln > 1:
                s += "เอ็ด"
            elif p == 1 and d == 2:
                s += "ยี่สิบ"
            elif p == 1 and d == 1:
                s += "สิบ"
            else:
                s += num[d] + pos[p]
        return s

    baht = int(round(amount * 100)) // 100
    satang = int(round(amount * 100)) % 100
    s = read_int(baht) + "บาท"
    s += read_int(satang) + "สตางค์" if satang else "ถ้วน"
    return s
