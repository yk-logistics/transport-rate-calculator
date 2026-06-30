"""BigC วันหยุด + อนุโลม classification in _count_work_days.

BigC keys the day's status into column "ที่ส่งสินค้า" (DailyJob.destination):
  - "ลาหยุด"            → day off, DEDUCTED (counts as leave)
  - "ลาหยุด (อนุโลม)"  → exempt, NOT deducted (counts as worked)

Two behaviours under test:
  1. destination is scanned for leave tokens (it wasn't before).
  2. the token "อนุโลม" exempts the day even when "หยุด"/"ลา" is present.

Forward-ready: a separate status field (leave_status) takes precedence over
destination when present, so future keyers can fill that field instead.
"""
from datetime import date

import pytest
from sqlmodel import SQLModel, Session, create_engine

from models import DailyJob, Employee
from services.payroll import _count_work_days


@pytest.fixture()
def session():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s


def _emp(s, emp_id, start, end):
    """Employee with a tight employment window so implicit-absent padding
    doesn't leak into the day counts we assert on."""
    s.add(Employee(
        id=emp_id, code=f"E{emp_id}", full_name=f"emp{emp_id}",
        home_site_code="BIGC", pay_mode="bigc_monthly",
        start_date=start, end_date=end,
    ))


def _day(s, emp_id, d, destination="", status_code="", leave_status="",
         remark="", revenue=0.0):
    s.add(DailyJob(
        site_code="BIGC", work_date=d, driver_id=emp_id,
        destination=destination, status_code=status_code,
        leave_status=leave_status, remark=remark,
        revenue_customer=revenue, trip_fee_driver=0.0,
    ))


def test_lahyut_in_destination_counts_as_leave(session):
    # 3 days, all "ลาหยุด" in the delivery-location column → all deducted.
    _emp(session, 200, date(2026, 5, 1), date(2026, 5, 3))
    _day(session, 200, date(2026, 5, 1), destination="ลาหยุด")
    _day(session, 200, date(2026, 5, 2), destination="ลาหยุด")
    _day(session, 200, date(2026, 5, 3), destination="ลาหยุด")
    session.commit()
    out = _count_work_days(session, 200, date(2026, 5, 1), date(2026, 5, 3), "BIGC")
    assert out["leave"] == 3.0
    assert out["worked"] == 0.0
    assert out["absent"] == 0.0


def test_anuloom_exempts_the_day(session):
    # "ลาหยุด (อนุโลม)" must NOT be deducted — counts as worked.
    _emp(session, 201, date(2026, 5, 1), date(2026, 5, 3))
    _day(session, 201, date(2026, 5, 1), destination="ลาหยุด (อนุโลม)")
    _day(session, 201, date(2026, 5, 2), destination="ลาหยุด (อนุโลม)")
    _day(session, 201, date(2026, 5, 3), destination="ลาหยุด")  # plain → deducted
    session.commit()
    out = _count_work_days(session, 201, date(2026, 5, 1), date(2026, 5, 3), "BIGC")
    assert out["leave"] == 1.0   # only the plain ลาหยุด
    assert out["worked"] == 2.0  # two อนุโลม days paid full


def test_anuloom_in_dedicated_status_field_also_exempts(session):
    # Forward-ready: future keyers fill the dedicated status field instead of
    # the destination column. "อนุโลม" there must exempt the day just the same.
    _emp(session, 202, date(2026, 5, 1), date(2026, 5, 2))
    _day(session, 202, date(2026, 5, 1), leave_status="ลาหยุด (อนุโลม)")
    _day(session, 202, date(2026, 5, 2), leave_status="ลาหยุด")  # plain → deducted
    session.commit()
    out = _count_work_days(session, 202, date(2026, 5, 1), date(2026, 5, 2), "BIGC")
    assert out["leave"] == 1.0
    assert out["worked"] == 1.0


def test_real_destination_name_not_misread_as_leave(session):
    # Regression: a genuine place name must not trip the leave detector.
    # "ลาดหลุมแก้ว" / "ตลาดบุญเจริญ" contain "ลา"/"ตลาด" but are destinations.
    _emp(session, 203, date(2026, 5, 1), date(2026, 5, 2))
    _day(session, 203, date(2026, 5, 1), destination="ลาดหลุมแก้ว", revenue=1500.0)
    _day(session, 203, date(2026, 5, 2), destination="ตลาดบุญเจริญ", revenue=1200.0)
    session.commit()
    out = _count_work_days(session, 203, date(2026, 5, 1), date(2026, 5, 2), "BIGC")
    assert out["leave"] == 0.0
    assert out["worked"] == 2.0
