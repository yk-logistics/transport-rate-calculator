"""classify_driver_fee: single source of truth for which DailyJobFee rows count
as DRIVER income (พิเศษ/OT/รับตู้คืนตู้) vs company reserve (ค่าเสียเวลา/ยกตู้/...).

Both the payroll engine and the /daily grid endpoint use this, so the numbers
shown in เดลี่ == สลิป == หน้ารวม == engine. ค่าเสียเวลา MUST be company-only.
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pytest
from services.payroll import classify_driver_fee


@pytest.mark.parametrize("raw,bucket", [
    # พิเศษ
    ("special", "special"), ("พิเศษ", "special"), ("ค่าพิเศษ", "special"),
    # OT (case-insensitive)
    ("ot", "ot"), ("OT", "ot"), ("Ot", "ot"), ("ค่าล่วงเวลา", "ot"),
    # รับตู้คืนตู้
    ("pickup_return", "pickup_return"), ("รับตู้แทน", "pickup_return"),
])
def test_driver_buckets(raw, bucket):
    assert classify_driver_fee(raw) == bucket


@pytest.mark.parametrize("raw", [
    "ค่าเสียเวลา",          # ของบริษัท — โอยืนยัน ไม่เกี่ยวคนขับ
    "lift", "ค่ายกตู้",
    "yard", "ค่าผ่านลาน",
    "clean", "ค่าคลีน",
    "shore", "ค่าชอร์",
    "port_entry", "เข้าท่า",
    "weighing", "ค่าชั่งน้ำหนัก",
    "", None, "อะไรไม่รู้",
])
def test_company_or_unknown_is_none(raw):
    assert classify_driver_fee(raw) is None
