# -*- coding: utf-8 -*-
"""กติการอบจ่ายต่อไซท์ (CLAUDE.md: critical — อย่าเดา) — ยึดกฎเป็นเทสต์กันแก้พลาดเงียบ.

| Site | วงรอบ            | cycle_tag = เดือนที่รอบจบ |
| BIGC | 1 → สิ้นเดือน     | YYYY-MM                    |
| LCB  | 16 → 15 ถัดไป    | เดือนที่ 15 อยู่            |
| AYU  | 26 → 25 ถัดไป    | เดือนที่ 25 อยู่            |

เขียน 4 ก.ค. 2026 หลัง coverage ชี้ว่าฟังก์ชันชุดนี้ไม่มีเทสต์เลย (จุดพังเงียบ:
น้ำมัน/สดย่อยเข้าผิดรอบทั้งไซท์). ฟังก์ชัน pure ไม่ต้องใช้ DB.
"""
from datetime import date

import pytest

from services.payroll import (
    compute_pay_cycle_tag,
    compute_pay_cycle_tag_by_policy,
    compute_period,
    normalize_pay_cycle_policy,
)


# ---- compute_period: tag → (start, end) ----

@pytest.mark.parametrize("site,tag,start,end", [
    ("BIGC", "2026-06", date(2026, 6, 1), date(2026, 6, 30)),
    ("BIGC", "2026-02", date(2026, 2, 1), date(2026, 2, 28)),      # ก.พ. ปีปกติ
    ("BIGC", "2028-02", date(2028, 2, 1), date(2028, 2, 29)),      # leap year
    ("LCB", "2026-07", date(2026, 6, 16), date(2026, 7, 15)),
    ("LCB", "2026-01", date(2025, 12, 16), date(2026, 1, 15)),     # คร่อมปี
    ("AYU", "2026-07", date(2026, 6, 26), date(2026, 7, 25)),
    ("AYU", "2026-01", date(2025, 12, 26), date(2026, 1, 25)),     # คร่อมปี
    ("XXX", "2026-06", date(2026, 6, 1), date(2026, 6, 30)),       # ไซท์ไม่รู้จัก = เดือนปฏิทิน
])
def test_compute_period(site, tag, start, end):
    assert compute_period(site, tag) == (start, end)


def test_compute_period_case_insensitive():
    assert compute_period("lcb", "2026-07") == compute_period("LCB", "2026-07")


# ---- compute_pay_cycle_tag: วันทำรายการ → tag (ขอบต้องเป๊ะวันเดียว) ----

@pytest.mark.parametrize("site,d,tag", [
    # LCB ตัด 16: วันที่ 15 = รอบเดือนนี้, 16 = รอบเดือนหน้า
    ("LCB", date(2026, 6, 15), "2026-06"),
    ("LCB", date(2026, 6, 16), "2026-07"),
    ("LCB", date(2026, 12, 16), "2027-01"),                        # ข้ามปี
    # AYU ตัด 26: วันที่ 25 = รอบเดือนนี้, 26 = รอบเดือนหน้า
    ("AYU", date(2026, 6, 25), "2026-06"),
    ("AYU", date(2026, 6, 26), "2026-07"),
    ("AYU", date(2026, 12, 26), "2027-01"),                        # ข้ามปี
    # BIGC = เดือนปฏิทินตรงๆ
    ("BIGC", date(2026, 6, 1), "2026-06"),
    ("BIGC", date(2026, 6, 30), "2026-06"),
])
def test_compute_pay_cycle_tag_boundaries(site, d, tag):
    assert compute_pay_cycle_tag(site, d) == tag


def test_tag_and_period_roundtrip():
    """ทุกวันในปี 2026 ของทุกไซท์: วันนั้นต้องอยู่ในช่วงของ tag ที่ตัวเองได้ — กติกาสองฟังก์ชันห้ามแย้งกัน."""
    d = date(2026, 1, 1)
    while d <= date(2026, 12, 31):
        for site in ("LCB", "AYU", "BIGC"):
            tag = compute_pay_cycle_tag(site, d)
            start, end = compute_period(site, tag)
            assert start <= d <= end, f"{site} {d} → tag {tag} แต่ช่วงคือ {start}..{end}"
        d = date.fromordinal(d.toordinal() + 1)


# ---- policy รายคน (v17: driver-policy-first) ----

@pytest.mark.parametrize("policy,d,tag", [
    ("calendar", date(2026, 6, 30), "2026-06"),
    ("calendar_m1", date(2026, 6, 5), "2026-05"),                  # เดือนก่อนหน้า
    ("calendar_m1", date(2026, 1, 5), "2025-12"),                  # ข้ามปีถอยหลัง
    ("cut_16_15", date(2026, 6, 16), "2026-07"),
    ("cut_26_25", date(2026, 6, 26), "2026-07"),
])
def test_policy_tags(policy, d, tag):
    assert compute_pay_cycle_tag_by_policy(policy, d) == tag


def test_policy_site_default_falls_back_to_site():
    d = date(2026, 6, 20)
    assert compute_pay_cycle_tag_by_policy("site_default", d, "LCB") == \
        compute_pay_cycle_tag("LCB", d) == "2026-07"


def test_unknown_policy_normalizes_to_site_default():
    assert normalize_pay_cycle_policy("อะไรก็ไม่รู้") == "site_default"
    assert normalize_pay_cycle_policy("") == "site_default"
    d = date(2026, 6, 26)
    assert compute_pay_cycle_tag_by_policy("อะไรก็ไม่รู้", d, "AYU") == "2026-07"
