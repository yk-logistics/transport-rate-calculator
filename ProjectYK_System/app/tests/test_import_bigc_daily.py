"""BIGC daily importer — pure parse-layer unit tests (no DB, no real files)."""
import sys
from datetime import date
from pathlib import Path

# importer อยู่ใต้ tools/ — เพิ่ม path ให้ import ได้
TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
# app/ (สำหรับ models ใน test write ของ Task 3)
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import import_bigc_daily as imp  # noqa: E402


def test_merge_header_joins_two_rows():
    top    = ["วันที่", "ทะเบียน", "ทะเบียน", "ชื่อ-นามสกุล", "ค่าขนส่ง", "ค่าเที่ยวพขร"]
    bottom = ["รับงาน", "รถหัวลาก", "หางลาก", None,           "โดยประมาณ", "จุดพ่วง/BH"]
    out = imp.merge_header(top, bottom)
    assert out[0] == "วันที่ รับงาน"
    assert out[1] == "ทะเบียน รถหัวลาก"
    assert out[2] == "ทะเบียน หางลาก"
    assert out[3] == "ชื่อ-นามสกุล"          # bottom ว่าง → top เฉย ๆ
    assert out[4] == "ค่าขนส่ง โดยประมาณ"


def test_clean_float_handles_excel_errors():
    assert imp.clean_float("#DIV/0!") == 0.0
    assert imp.clean_float("-") == 0.0
    assert imp.clean_float("1,234.5") == 1234.5
    assert imp.clean_float(None) == 0.0
    assert imp.clean_float(600) == 600.0


def test_clean_str_blanks_dash_and_errors():
    assert imp.clean_str("-") == ""
    assert imp.clean_str("#N/A") == ""
    assert imp.clean_str("  PTT B20  ") == "PTT B20"
    assert imp.clean_str(None) == ""


# หัวรวมจริงของ BIGC (index 0..18) ตาม spec section 4
BIGC_MERGED = [
    "วันที่ รับงาน", "ทะเบียน รถหัวลาก", "ทะเบียน หางลาก", "ชื่อ-นามสกุล",
    "รับตู้ สถานที่", "รหัส สาขา", "ที่ส่งสินค้า สถานที่", "เลขที่ เอกสาร",
    "ค่าขนส่ง โดยประมาณ", "ค่าเที่ยวพขร จุดพ่วง/BH", "เงินเดือน",
    "น้ำมันที่ กำหนด", "เลขไมล์ ตอนเติม", "จำนวน น้ำมันลิตร",
    "ราคาน้ำมัน ฿ / L", "จำนวน เงินบาท", "เรท น้ำมัน", "จำนวน น้ำมันทำได้",
    "หมายเหตุ",
]


def test_map_columns_finds_money_and_fuel():
    C = imp.map_columns(BIGC_MERGED)
    assert C["work_date"] == 0
    assert C["plate"] == 1
    assert C["tail_plate"] == 2
    assert C["driver"] == 3
    assert C["revenue"] == 8          # ค่าขนส่ง = รายได้
    assert C["trip_fee"] == 9         # ค่าเที่ยวพขร = เงินคนขับ
    assert C["fuel_liter"] == 13
    assert C["fuel_amount"] == 15
    assert C["remark"] == 18


CYC_START, CYC_END = date(2026, 5, 1), date(2026, 5, 31)


def _row(d, plate="71-8001", driver="ธนวัฒน์", rev=600.0, trip=200.0,
         liter=159.76, baht=5400.0, note="PTT B20"):
    r = [None] * 19
    r[0] = d; r[1] = plate; r[2] = "-"; r[3] = driver
    r[8] = rev; r[9] = trip; r[13] = liter; r[15] = baht; r[18] = note
    return r


def test_row_to_record_maps_trip_and_fuel():
    C = imp.map_columns(BIGC_MERGED)
    rec = imp.row_to_record(_row(date(2026, 5, 1)), C, CYC_START, CYC_END)
    assert rec is not None
    assert rec["daily"]["site_code"] == "BIGC"
    assert rec["daily"]["driver_raw_name"] == "ธนวัฒน์"
    assert rec["daily"]["revenue_customer"] == 600.0
    assert rec["daily"]["trip_fee_driver"] == 200.0
    assert rec["fuel"]["liter"] == 159.76
    assert rec["fuel"]["amount"] == 5400.0
    assert rec["fuel"]["exclude_from_driver"] is True
    assert round(rec["fuel"]["price_per_liter"], 2) == round(5400.0 / 159.76, 2)


def test_row_to_record_keeps_idle_row_without_fuel():
    # รถจอด: ไม่มีรายได้/ค่าเที่ยว/น้ำมัน แต่มีวันที่+ชื่อ → เก็บแถว, fuel=None
    C = imp.map_columns(BIGC_MERGED)
    rec = imp.row_to_record(
        _row(date(2026, 5, 2), rev=0, trip=0, liter=0, baht=0, note=""),
        C, CYC_START, CYC_END)
    assert rec is not None
    assert rec["fuel"] is None
    assert rec["daily"]["revenue_customer"] == 0.0


def test_row_to_record_skips_out_of_window():
    C = imp.map_columns(BIGC_MERGED)
    assert imp.row_to_record(_row(date(2026, 1, 31)), C, CYC_START, CYC_END) is None


def test_row_to_record_skips_empty():
    C = imp.map_columns(BIGC_MERGED)
    blank = [None] * 19
    assert imp.row_to_record(blank, C, CYC_START, CYC_END) is None
