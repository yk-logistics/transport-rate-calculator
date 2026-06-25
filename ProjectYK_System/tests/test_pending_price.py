import sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from sqlmodel import SQLModel, Session, create_engine
from models import DailyJob
from services.payroll import find_pending_price_days


def _mk_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add(s, d, status, rev=0, fee=0):
    s.add(DailyJob(driver_id=1, site_code="LCB", work_date=d,
                   status_code=status, revenue_customer=rev, trip_fee_driver=fee))


def test_pending_price_flags_customer_code_zero_revenue():
    s = _mk_session()
    _add(s, date(2026, 6, 2), "KAO")            # ลูกค้า, rev=0 -> รอลงราคา
    _add(s, date(2026, 6, 3), "รถจอด")           # idle -> ไม่ใช่
    _add(s, date(2026, 6, 4), "ลา / ไม่พร้อม")   # leave -> ไม่ใช่
    _add(s, date(2026, 6, 5), "KLND", rev=5000, fee=350)  # มีรายได้ -> ไม่ใช่
    s.commit()
    out = find_pending_price_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert [r["date"] for r in out] == ["2026-06-02"]
    assert out[0]["status"] == "KAO"
