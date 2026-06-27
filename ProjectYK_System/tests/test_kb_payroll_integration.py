import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import date
from sqlmodel import Session, SQLModel, create_engine
from models import DailyJob, Employee
from services import payroll


def _setup():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    emp = Employee(code="TEST-KB", full_name="ทดสอบ KB", home_site_code="LCB")
    s.add(emp)
    s.commit()
    s.refresh(emp)
    return s, emp


def test_classify_uses_driver_calc_price_not_billed():
    # bill 9000 with override 5000, fee 3000 -> ratio = 3000/5000 = 0.60 = mao day.
    # If it wrongly used revenue_customer 9000, ratio=0.33 -> ambiguous, NOT mao.
    s, emp = _setup()
    s.add(DailyJob(work_date=date(2026, 6, 1), site_code="LCB", driver_id=emp.id,
                   revenue_customer=9000, price_override=5000, trip_fee_driver=3000,
                   status_code="DHL Overflow"))
    s.commit()
    split = payroll._classify_lcb_days(s, emp.id, date(2026, 6, 1), date(2026, 6, 30), "LCB")
    assert len(split["mao_days"]) == 1
    assert len(split["ambiguous"]) == 0


def test_kb_deduction_shifts_classification():
    # NHL-style: bill 5000, kb 110 -> driver_calc 4890. trip fee 2934 -> ratio 0.60 = mao.
    # Using billed 5000 would give 2934/5000 = 0.587 -> still close; use a sharper case:
    # bill 6000, kb 1000 -> driver_calc 5000; fee 3000 -> 0.60 mao.
    # billed path: 3000/6000 = 0.50 -> ambiguous.
    s, emp = _setup()
    s.add(DailyJob(work_date=date(2026, 6, 2), site_code="LCB", driver_id=emp.id,
                   revenue_customer=6000, kb_amount=1000, trip_fee_driver=3000,
                   status_code="NHL"))
    s.commit()
    split = payroll._classify_lcb_days(s, emp.id, date(2026, 6, 1), date(2026, 6, 30), "LCB")
    assert len(split["mao_days"]) == 1
    assert len(split["ambiguous"]) == 0
