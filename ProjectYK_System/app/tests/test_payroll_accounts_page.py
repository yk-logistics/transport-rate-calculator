"""หน้าบัญชีโอนเงิน /payroll/{id}/accounts — ก็อป/แก้เลขบัญชี (A5 ส่วนแรก)."""
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
from models import AppUser, Employee, PayRun, PayRunItem


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=10, code="D10", full_name="นาย หนึ่ง ทดสอบ", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", bank_name="กสิกร", account_no="111-222-3333"))
        s.add(Employee(id=11, code="D11", full_name="นาย สอง ติดลบ", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", bank_name="ไทยพาณิชย์", account_no="444-555"))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="finalized"))
        s.add(PayRunItem(pay_run_id=1, employee_id=10, net_pay=12345.5, gross_total=13000))
        s.add(PayRunItem(pay_run_id=1, employee_id=11, net_pay=-500, gross_total=0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_accounts_page_lists_positive_net_only(client):
    b = client.get("/payroll/1/accounts", follow_redirects=True).text
    assert "111-222-3333" in b and "12,345.50" in b
    assert "นาย สอง ติดลบ" not in b        # net<=0 ไม่โชว์ (หนี้บริษัท ไม่ต้องโอน)
    assert "กสิกร" in b                    # จัดกลุ่มธนาคาร


def test_edit_account_saves_on_employee(client):
    client.post("/payroll/1/accounts/save",
                data={"emp_id": "10", "bank_name": "กรุงไทย", "account_no": "999-888-7777"})
    with Session(engine) as s:
        e = s.get(Employee, 10)
        assert e.bank_name == "กรุงไทย" and e.account_no == "999-888-7777"
    b = client.get("/payroll/1/accounts", follow_redirects=True).text
    assert "999-888-7777" in b
