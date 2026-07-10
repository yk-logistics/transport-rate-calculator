# -*- coding: utf-8 -*-
"""แกะตารางประวัติซ่อม (RM History Google Sheets) → บิล + บรรทัดรายการ.

pure functions: ไม่แตะ DB ไม่แตะเน็ต → เทสต์ได้ตรงๆ
กฎเหล็ก: อ่านไม่ออก = คืน None / ลง issues **ห้ามเดา**
(ค่าซ่อมไปโผล่ผิดปีแล้วตามหายาก — ดู docs/superpowers/specs/2026-07-09-rm-history-backfill-design.md)

โครงตารางในแท็บรถ (หัวตารางอยู่คนละแถวกันทุกแท็บ — ต้องค้นหา):
    รายการซ่อมรถ | | | | | ราคา | รวม | ส่วนลด | ภาษี | ราคาสุทธิ   ← ยอดที่ชีทคำนวณเอง
    วันที่ | เลขกิโลเมตร | บริษัท | รายละเอียด | จำนวน | ราคา | รวม | ส่วนลด | ภาษีมูลค่าเพิ่ม | ราคาสุทธิ | หมายเหตุ
    13/05/20 | 12,029 | Isuzu บางปะอิน | บริการพ่นน้ำยา | 1.00 | - | - | | - | -
             |        |                | น้ำกลั่น       | 1.00 | 10.00 | 10.00 | | 0.70 | 10.70   ← วันที่ว่าง = บิลใบเดิม
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

_LABOR = ("ค่าแรง", "ค่าถอด", "ค่าประกอบ", "แรงงาน")
_SERVICE = ("บริการ", "ตรวจ", "เช็ค", "อัดจารบี", "เปลี่ยนถ่าย", "ค่าเดินทาง", "ล้าง")
_PLATE_RE = re.compile(r"^\d{2}-\d{4}$")
_DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$")
_REQUIRED_HEADERS = ("วันที่", "บริษัท", "รายละเอียด", "จำนวน", "ราคา", "รวม", "ราคาสุทธิ")


@dataclass
class Bill:
    work_date: date
    mile: float
    vendor: str
    sheet_row: int                       # แถวของ "วันที่" ในชีท (1-based) — ใช้ทำ import_key
    lines: list[dict] = field(default_factory=list)


@dataclass
class ParsedTab:
    plate: str | None
    header_row: int
    bills: list[Bill] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    sheet_net_total: float | None = None    # ยอดสุทธิที่ชีทคำนวณไว้ — ใช้ตรวจทานหลัง import


def _num(v) -> float:
    s = str(v or "").replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date(raw: str, today: date | None = None) -> date | None:
    """dd/mm/yy(yy) — พ.ศ./ค.ศ. ปนกันในไฟล์เดียว. อ่านไม่ออก/อนาคต = None."""
    today = today or date.today()
    m = _DATE_RE.match(str(raw or ""))
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if len(m.group(3)) == 4:
        year = y - 543 if y >= 2500 else y
        if not (1990 <= year <= 2100):
            return None
    elif 60 <= y <= 79:            # พ.ศ. 2 หลัก (2560-2579)
        year = 2500 + y - 543
    elif 15 <= y <= 40:            # ค.ศ. 2 หลัก — ข้อมูลบริษัทเริ่ม 2018
        year = 2000 + y            # '00'/'02'/'11' = พิมพ์ผิด ไม่ใช่ 2002/2011 → ลง issue
    else:
        return None
    try:
        out = date(year, mo, d)
    except ValueError:
        return None
    return None if out > today else out


def normalize_plate(tab_title: str) -> str | None:
    """ชื่อแท็บ → ทะเบียนมาตรฐาน; ไม่ใช่รูปแบบทะเบียน = None (ไม่ใช่แท็บรถ)."""
    t = re.sub(r"\(.*?\)", "", str(tab_title or ""))
    t = re.sub(r"\s*อย\.?\s*$", "", t.strip())
    t = t.strip()
    return t if _PLATE_RE.match(t) else None


def classify_kind(detail: str) -> str:
    d = str(detail or "")
    if any(k in d for k in _LABOR):
        return "labor"
    if any(k in d for k in _SERVICE):
        return "service"
    return "part"


def _find_header(values: list[list[str]]) -> int:
    """เลขแถว (1-based) ของหัวตาราง — พบตั้งแต่แถว 1 ถึง 22 แล้วแต่แท็บ ห้ามล็อกเลข."""
    for i, row in enumerate(values):
        if row and str(row[0]).strip() == "วันที่" and len(row) > 3:
            return i + 1
    return 0


def _col_map(header: list[str]) -> dict[str, int]:
    return {str(v).strip(): i for i, v in enumerate(header) if str(v).strip()}


def parse_tab(tab_title: str, values: list[list[str]]) -> ParsedTab:
    plate = normalize_plate(tab_title)
    hdr = _find_header(values)
    p = ParsedTab(plate=plate, header_row=hdr)
    if not hdr:
        p.issues.append({"row": 0, "reason": "ไม่พบหัวตาราง (คอลัมน์แรกต้องเป็น 'วันที่')",
                         "raw": tab_title})
        return p

    col = _col_map(values[hdr - 1])
    missing = [h for h in _REQUIRED_HEADERS if h not in col]
    if missing:
        p.issues.append({"row": hdr, "reason": f"หัวตารางขาด: {', '.join(missing)}",
                         "raw": tab_title})
        return p

    # ยอดสุทธิที่ชีทคำนวณไว้ (แถว "รายการซ่อมรถ" เหนือหัวตาราง) — ใช้ตรวจทานหลัง import
    for row in values[max(0, hdr - 4):hdr - 1]:
        if row and "รายการซ่อมรถ" in str(row[0]):
            j = col["ราคาสุทธิ"]
            if len(row) > j:
                p.sheet_net_total = _num(row[j])
            break

    def cell(row, name):
        j = col[name]
        return row[j] if len(row) > j else ""

    cur: Bill | None = None
    for i in range(hdr + 1, len(values) + 1):
        row = values[i - 1]
        if not row or not any(str(c).strip() for c in row):
            continue
        raw_date = str(cell(row, "วันที่")).strip()
        detail = str(cell(row, "รายละเอียด")).strip()

        if raw_date:
            d = parse_date(raw_date)
            if d is None:
                p.issues.append({"row": i, "reason": f"วันที่อ่านไม่ออก/อนาคต: {raw_date!r}",
                                 "raw": detail})
                cur = None                      # ทิ้งทั้งบิล รวมบรรทัดต่อของมัน
                continue
            cur = Bill(work_date=d, mile=_num(cell(row, "เลขกิโลเมตร")),
                       vendor=str(cell(row, "บริษัท")).strip(), sheet_row=i)
            p.bills.append(cur)

        if not detail:
            continue
        if cur is None:
            p.issues.append({"row": i, "reason": "บรรทัดไม่มีบิลแม่ (วันที่ก่อนหน้าใช้ไม่ได้)",
                             "raw": detail})
            continue
        total = _num(cell(row, "รวม")) or _num(cell(row, "จำนวน")) * _num(cell(row, "ราคา"))
        cur.lines.append({
            "kind": classify_kind(detail), "name": detail,
            "qty": _num(cell(row, "จำนวน")) or 1.0,
            "unit_price": _num(cell(row, "ราคา")),
            "total": total,
            "discount": _num(cell(row, "ส่วนลด")),
            "vat": _num(cell(row, "ภาษีมูลค่าเพิ่ม")),
            "net": _num(cell(row, "ราคาสุทธิ")),
        })

    p.bills = [b for b in p.bills if b.lines]     # บิลที่ไม่มีบรรทัดเลย = ไม่มีความหมาย
    return p
