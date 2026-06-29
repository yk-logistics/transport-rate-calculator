from datetime import date
from sqlmodel import Session, delete
from db_config import engine
from models import Employee, DailyJob, FuelTxn, PayRun, PayRunItem
from services.payroll_slip import build_payroll_slip_context


def _cleanup(s):
    s.exec(delete(FuelTxn).where(FuelTxn.source == "test_slipgrade"))
    s.exec(delete(DailyJob).where(DailyJob.remark == "test_slipgrade"))


def test_context_has_fuel_grade_by_job(client):
    with Session(engine) as s:
        emp = Employee(code="D-SG-TEST", full_name="ทดสอบ เกรด", home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        dj = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 2),
                      plate_no_raw="ZZ-SG-1", fuel_liter=50, fuel_amount=2060,
                      remark="test_slipgrade")
        s.add(dj); s.flush()
        ft = FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 2),
                     plate_no_raw="ZZ-SG-1", liter=50, amount=2060, daily_job_id=dj.id,
                     fuel_grade="B7", source="test_slipgrade")
        s.add(ft); s.flush()
        pr = PayRun(site_code="LCB", pay_cycle_tag="2026-06",
                    period_start=date(2026, 5, 16), period_end=date(2026, 6, 15))
        item = PayRunItem(pay_mode="lcb_trip")
        ctx = build_payroll_slip_context(s, pr, emp, item)
        assert ctx["fuel_grade_by_job"].get(dj.id) == "B7"
        _cleanup(s)
        s.delete(emp); s.commit()
