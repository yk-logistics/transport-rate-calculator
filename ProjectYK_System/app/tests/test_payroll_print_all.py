"""Payroll print-all page: สรุป + โอนเงิน + สลิปรายคน in one printable page,
plus per-driver transfer note (auto + manual override) and bank fields.
"""
import os, tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import Employee, PayRun, PayRunItem, DailyJob, AppUser


@pytest.fixture()
def client_with_run():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=97, code="D97", full_name="นาย นิพล สีโนนม่วง", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000,
                       gross_share_rate=0.60, bank_name="กสิกร", account_no="090-141-4432"))
        # วันชัย: ลาออกกลางรอบ (end_date ภายในรอบ) แต่ยังมีงาน → ยังได้รับเงินรอบนี้ + auto-note "ออก"
        s.add(Employee(id=2, code="D2", full_name="นาย วันชัย ออกแล้ว", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", end_date=date(2026, 5, 20),
                       base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        s.add(DailyJob(site_code="LCB", driver_id=97, work_date=date(2026, 5, 20),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=3000))
        s.add(DailyJob(site_code="LCB", driver_id=2, work_date=date(2026, 5, 18),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=350))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 2), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_print_page_has_three_blocks(client_with_run):
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    # three sections
    assert "สรุป" in b
    assert "โอนเงิน" in b
    # bank account shows on transfer page
    assert "090-141-4432" in b
    assert "กสิกร" in b


def test_transfer_note_auto_for_resigned(client_with_run):
    # วันชัย end_date in period -> auto note "ออก"
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert "ออก" in r.text


def test_transfer_note_manual_override(client_with_run):
    r = client_with_run.post("/payroll/2/employee/97/transfer-note",
                             data={"note": "คืนประกันตน 10,000"}, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        it = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == 2,
                                             PayRunItem.employee_id == 97)).first()
        assert it.transfer_note == "คืนประกันตน 10,000"
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert "คืนประกันตน 10,000" in r.text


def test_slip_does_not_show_ytd(client_with_run):
    """สลิปคนขับ (option 1, โอ 2026-06-28): ไม่โชว์ยอดสะสมทั้งปี — คนขับเห็นแค่
    งวดนี้ (รายได้/หัก/สุทธิ + ภาษีงวดนี้ถ้ามี). ยอดสะสมไปอยู่หน้าภาษีแทน."""
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "สะสมทั้งปี" not in b, "slip should NOT show YTD totals (moved to tax page)"


def test_tax_page_renders(client_with_run):
    """หน้าภาษี /payroll/{id}/tax โหลดได้ + โชว์คอลัมน์รายได้/ภาษีสะสม."""
    r = client_with_run.get("/payroll/2/tax", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "สรุปภาษีหัก ณ ที่จ่าย" in b
    assert "รายได้สะสมทั้งปี" in b
    assert "ภาษีสะสมทั้งปี" in b
    assert "นิพล" in b
