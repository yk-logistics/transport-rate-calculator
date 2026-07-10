# -*- coding: utf-8 -*-
"""แกะแท็บ RM History — pure functions ไม่แตะ DB/เน็ต (ข้อมูลจริงย่อส่วน).

ต้นทาง: Google Sheets 3 ไฟล์ แยกแท็บตามทะเบียนรถ ปี 2018-2026
กฎเหล็ก: อ่านไม่ออก = ลง issue ห้ามเดา (ค่าซ่อมไปโผล่ผิดปีแล้วตามหายาก)
"""
from datetime import date

import pytest

from services import rm_history as rm


# ---- วันที่: พ.ศ./ค.ศ. ปนกันในไฟล์เดียว --------------------------------------
@pytest.mark.parametrize("raw,expect", [
    ("13/05/20", date(2020, 5, 13)),        # 2 หลัก 00-40 = ค.ศ.
    ("18/02/2021", date(2021, 2, 18)),      # 4 หลัก ค.ศ.
    ("1/3/67", date(2024, 3, 1)),           # 2 หลัก 60-79 = พ.ศ.
    ("05/11/2566", date(2023, 11, 5)),      # 4 หลัก พ.ศ.
    (" 04/08/20 ", date(2020, 8, 4)),       # เว้นวรรครอบๆ
])
def test_parse_date_ok(raw, expect):
    assert rm.parse_date(raw, today=date(2026, 7, 9)) == expect


@pytest.mark.parametrize("raw", ["", "-", "31/02/24", "13/05/29", "13/05/02", "abc", "45123"])
def test_parse_date_refuses(raw):
    """/29 = อนาคต · /02 = กำกวม · 31/02 = ไม่มีจริง → None (ไปลง issue)"""
    assert rm.parse_date(raw, today=date(2026, 7, 9)) is None


# ---- ทะเบียน -----------------------------------------------------------------
@pytest.mark.parametrize("tab,expect", [
    ("71-6802", "71-6802"),
    ("71-6802 อย", "71-6802"),
    ("72-2294(หางใหม่)", "72-2294"),
    (" 71-1802 ", "71-1802"),
])
def test_normalize_plate_ok(tab, expect):
    assert rm.normalize_plate(tab) == expect


@pytest.mark.parametrize("tab", ["หน้ารวม", "ชีต3", "ตู้1", "รับรถ 8682",
                                 "Stock  LCB", "แบตเตอรี่", "บษ2681"])
def test_normalize_plate_rejects_non_vehicle(tab):
    assert rm.normalize_plate(tab) is None


# ---- หมวดบรรทัด ---------------------------------------------------------------
@pytest.mark.parametrize("detail,kind", [
    ("ค่าแรงถอดยาง", "labor"),
    ("ค่าแรง", "labor"),
    ("บริการพ่นน้ำยาฆ่าเชื้อ", "service"),
    ("ตรวจแผ่นกรองอากาศ", "service"),
    ("อัดจารบีช่วงล่าง", "service"),
    ("น้ำกลั่น", "part"),
    ("ฝาครอบรีเลย์", "part"),
])
def test_classify_kind(detail, kind):
    assert rm.classify_kind(detail) == kind


# ---- แกะทั้งแท็บ ---------------------------------------------------------------
HDR = ["วันที่", "เลขกิโลเมตร", "บริษัท", "รายละเอียด", "จำนวน", "ราคา", "รวม",
       "ส่วนลด", "ภาษีมูลค่าเพิ่ม", "ราคาสุทธิ", "หมายเหตุ"]

TAB = [
    ["71-6802", "Isuzu"],                                    # 1
    [], [], [],                                              # 2-4
    ["รายการซ่อมรถ", "", "", "", "", " 700.00 ", " 700.00 ", " 103.50 ", " 41.76 ", " 638.26 "],   # 5
    HDR,                                                     # 6  ← header อยู่แถว 6
    ["", "", "", "", " Time/Qty", " Price", " Sum", " Discount", " Vat %", " Amount"],             # 7
    ["13/05/20", "12,029", "Isuzu บางปะอิน", "บริการพ่นน้ำยา", " 1.00 ", " -  ", " -  ", "", " -  ", " -  "],  # 8
    ["", "", "", "น้ำกลั่น", " 1.00 ", " 10.00 ", " 10.00 ", "", " 0.70 ", " 10.70 "],            # 9
    [],                                                       # 10 ว่าง → ข้ามเงียบ
    ["18/02/21", "", "Isuzu บางปะอิน", "ฝาครอบรีเลย์", " 1.00 ", " 690.00 ", " 690.00 ", " 103.50 ", " 41.06 ", " 627.56 "],  # 11
    ["13/05/29", "", "ร้านผี", "ของว่าง", " 1.00 ", " 5.00 ", " 5.00 ", "", "", " 5.00 "],        # 12 อนาคต → issue
]


def test_parse_tab_groups_lines_under_bill():
    p = rm.parse_tab("71-6802", TAB)
    assert p.plate == "71-6802"
    assert p.header_row == 6
    assert p.sheet_net_total == 638.26

    assert len(p.bills) == 2
    b1 = p.bills[0]
    assert b1.work_date == date(2020, 5, 13) and b1.mile == 12029.0
    assert b1.vendor == "Isuzu บางปะอิน"
    assert len(b1.lines) == 2                      # วันที่ว่าง = บรรทัดต่อของบิลเดิม
    assert b1.lines[1]["name"] == "น้ำกลั่น" and b1.lines[1]["net"] == 10.70

    b2 = p.bills[1]
    assert b2.work_date == date(2021, 2, 18)
    assert b2.lines[0]["discount"] == 103.50 and b2.lines[0]["vat"] == 41.06
    assert b2.lines[0]["kind"] == "part"
    assert b2.sheet_row == 11


def test_parse_tab_records_issue_for_bad_date():
    p = rm.parse_tab("71-6802", TAB)
    reasons = [i["reason"] for i in p.issues]
    assert any("วันที่" in r for r in reasons)
    assert all(b.work_date.year != 2029 for b in p.bills)   # บิลผีไม่เข้า


def test_parse_tab_keeps_zero_price_checklist_lines():
    """รายการตรวจเช็คของศูนย์ ราคา 0 = ประวัติบำรุงรักษา ต้องเก็บไว้ (สเปคข้อ 8)."""
    p = rm.parse_tab("71-6802", TAB)
    first = p.bills[0].lines[0]
    assert first["name"] == "บริการพ่นน้ำยา" and first["kind"] == "service"
    assert first["total"] == 0.0 and first["net"] == 0.0


def test_parse_tab_missing_header_returns_issue():
    p = rm.parse_tab("หน้ารวม", [["ทะเบียน", "ยี่ห้อ"], ["71-8000", "Isuzu"]])
    assert p.bills == [] and p.header_row == 0
    assert any("หัวตาราง" in i["reason"] for i in p.issues)
