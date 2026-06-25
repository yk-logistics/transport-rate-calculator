import sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlmodel import SQLModel, Session, create_engine
from models import DailyJob
from services.payroll import _count_work_days


def _mk_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add(s, emp_id, d, status, rev=0, fee=0):
    s.add(DailyJob(driver_id=emp_id, site_code="LCB", work_date=d,
                   status_code=status, revenue_customer=rev, trip_fee_driver=fee))


def test_accident_repair_dhloverflow_count_as_idle():
    s = _mk_session()
    _add(s, 1, date(2026, 6, 2), "รถอุบัติเหตุ")
    _add(s, 1, date(2026, 6, 3), "รถซ่อม")
    _add(s, 1, date(2026, 6, 4), "DHL Overflow")
    _add(s, 1, date(2026, 6, 5), "รถจอด")        # เดิมก็จับได้
    s.commit()
    out = _count_work_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    # ทั้ง 4 วันต้องนับเป็นรถจอด ไม่ตกหายและไม่กลายเป็นลา
    # (absent มาจาก implicit-absent ของวันที่ไม่มี row ใน 15-day window —
    #  เป็น artifact ของ test ที่ไม่มี Employee record กำหนด window, ไม่เกี่ยวกับ idle)
    assert out["company_no_work"] == 4.0
    assert out["leave"] == 0.0


def test_leave_still_not_idle():
    s = _mk_session()
    _add(s, 1, date(2026, 6, 2), "ลา / ไม่พร้อม")
    s.commit()
    out = _count_work_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert out["leave"] == 1.0
    assert out["company_no_work"] == 0.0
