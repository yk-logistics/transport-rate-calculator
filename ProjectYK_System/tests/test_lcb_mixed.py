import sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlmodel import SQLModel, Session, create_engine
from models import Employee, DailyJob, FuelTxn, PayRun
from services.payroll import (
    _classify_lcb_days,
    _sum_fuel_cost_for_dates,
    calc_one_employee,
)


def _mk_session():
    engine = create_engine("sqlite://")  # in-memory
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add_day(s, emp_id, d, rev, trip):
    s.add(DailyJob(driver_id=emp_id, site_code="LCB", work_date=d,
                   revenue_customer=rev, trip_fee_driver=trip))


def test_classify_splits_mao_trip_ambiguous():
    s = _mk_session()
    # mao day: ratio = 3000/5000 = 0.60
    _add_day(s, 1, date(2026, 6, 2), 5000, 3000)
    # trip day: ratio = 350/5000 = 0.07
    _add_day(s, 1, date(2026, 6, 3), 5000, 350)
    # ambiguous: revenue 0
    _add_day(s, 1, date(2026, 6, 4), 0, 0)
    # ambiguous ratio: 0.30 (neither window)
    _add_day(s, 1, date(2026, 6, 5), 5000, 1500)
    s.commit()

    out = _classify_lcb_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert {d.work_date for d in out["mao_days"]} == {date(2026, 6, 2)}
    assert {d.work_date for d in out["trip_days"]} == {date(2026, 6, 3)}
    assert {d.work_date for d in out["ambiguous"]} == {date(2026, 6, 4), date(2026, 6, 5)}


def test_sum_fuel_cost_for_dates_only_listed_days():
    s = _mk_session()
    s.add(FuelTxn(driver_id=1, site_code="LCB", txn_date=date(2026, 6, 2), amount=1000))
    s.add(FuelTxn(driver_id=1, site_code="LCB", txn_date=date(2026, 6, 3), amount=500))
    s.commit()
    # only ask for the 2nd -> 1000, not 1500
    total = _sum_fuel_cost_for_dates(s, 1, {date(2026, 6, 2)}, "LCB")
    assert total == 1000.0


def test_lcb_mixed_splits_income_and_prorates_base():
    s = _mk_session()
    emp = Employee(full_name="ทดสอบ ลูกผสม", home_site_code="LCB",
                   pay_mode="lcb_mixed", base_salary=9240, care_allowance=3000,
                   gross_share_rate=0.60, start_date=date(2026, 5, 16))
    s.add(emp)
    s.commit()
    s.refresh(emp)
    # 1 mao day: rev 5000 ratio .60 ; fuel 1000 that day
    s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 2),
                   revenue_customer=5000, trip_fee_driver=3000))
    s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 2), amount=1000))
    # 1 trip day: rev 5000 fee 350
    s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 3),
                   revenue_customer=5000, trip_fee_driver=350))
    s.commit()

    calc = calc_one_employee(s, emp, date(2026, 5, 16), date(2026, 6, 15), "2026-06")

    # เหมา side: 5000 * 0.60 = 3000 income ; fuel 1000 self-cost
    assert calc.fuel_share_income == 3000.0
    assert calc.fuel_cost_self == 1000.0
    # เที่ยว side: trip fee 350
    assert calc.trip_fee_total == 350.0
    # พิเศษ 100 * 1 trip day = 100
    assert calc.other_income == 100.0
    # base prorated by trip days only: 1 trip day / 31-day cycle
    period_days = 31  # 16 May..15 Jun inclusive
    assert abs(calc.base_salary_earned - 9240 * (1 / period_days)) < 0.5
    assert abs(calc.care_allowance_earned - 3000 * (1 / period_days)) < 0.5
