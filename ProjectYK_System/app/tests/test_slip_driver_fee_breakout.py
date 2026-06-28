"""Slips break out พิเศษ/OT/รับตู้คืนตู้ instead of lumping into 'รายได้อื่น'.
Covers all three printable surfaces: per-employee slip, print-all (คนขับ), print-all (boss).
gross_total must NOT change (these are a subset of other_income).
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import Employee, PayRun, PayRunItem, DailyJob, DailyJobFee, AppUser


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=50, code="D50", full_name="นาย ทดสอบ ค่าพิเศษ", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        job = DailyJob(site_code="LCB", driver_id=50, work_date=date(2026, 6, 1),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=350)
        s.add(job); s.commit(); s.refresh(job)
        s.add(DailyJobFee(daily_job_id=job.id, fee_type="special", amount=100))
        s.add(DailyJobFee(daily_job_id=job.id, fee_type="ot", amount=80))
        s.add(DailyJobFee(daily_job_id=job.id, fee_type="pickup_return", amount=50))
        # ค่าเสียเวลา = ของบริษัท ต้องไม่โผล่ฝั่งคนขับ
        s.add(DailyJobFee(daily_job_id=job.id, fee_type="ค่าเสียเวลา", amount=999))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _item():
    with Session(engine) as s:
        return s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == 1,
                                               PayRunItem.employee_id == 50)).first()


def test_engine_split_into_fields(client):
    it = _item()
    assert it.special_income == 100
    assert it.ot_income == 80
    assert it.pickup_return_income == 50
    # ค่าเสียเวลา must NOT count as driver pay
    assert (it.other_income or 0) == 100 + 80 + 50


def test_per_employee_slip_breaks_out(client):
    b = client.get("/payroll/1/employee/50/slip", follow_redirects=True).text
    assert "พิเศษ" in b
    assert "OT" in b
    assert "รับตู้คืนตู้" in b
    # ค่าเสียเวลา (company) must not show on the driver slip (label nor amount)
    assert "ค่าเสียเวลา" not in b
    assert "999.00" not in b


def test_print_all_driver_breaks_out(client):
    b = client.get("/payroll/1/print", follow_redirects=True).text
    assert "พิเศษ" in b and "OT" in b and "รับตู้คืนตู้" in b
    assert "ค่าเสียเวลา" not in b
    assert "999.00" not in b


def test_print_all_boss_breaks_out(client):
    b = client.get("/payroll/1/print?for=boss", follow_redirects=True).text
    assert "พิเศษ" in b and "OT" in b and "รับตู้คืนตู้" in b
