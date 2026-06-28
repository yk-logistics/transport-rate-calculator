"""หน้า /deposits — ยอดเงินประกันตนรวม: ดู + แก้ (มี audit) + ประวัติรายคน."""
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
from models import Employee, PayRun, PayRunItem, AppUser, DepositAudit


def test_deposit_audit_model_exists():
    # ฟิลด์ครบตามสเปก
    a = DepositAudit(employee_id=1, changed_by="yk1",
                     field_name="deposit_balance", old_value="0", new_value="1000",
                     reason="test")
    assert a.employee_id == 1
    assert a.field_name == "deposit_balance"
    assert a.new_value == "1000"


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # มีเงินประกัน: 2 LCB + 1 BIGC
        s.add(Employee(id=10, code="D10", full_name="เอ", home_site_code="LCB",
                       status="active", deposit_balance=3000, deposit_target=10000))
        s.add(Employee(id=11, code="D11", full_name="บี", home_site_code="LCB",
                       status="active", deposit_balance=10000, deposit_target=10000))
        s.add(Employee(id=12, code="D12", full_name="ซี", home_site_code="BIGC",
                       status="active", deposit_balance=5000, deposit_target=10000))
        # ไม่มีเงินประกัน (target==0) → ต้องไม่โผล่
        s.add(Employee(id=13, code="D13", full_name="ดี", home_site_code="AYU",
                       status="active", deposit_balance=0, deposit_target=0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_deposits_page_lists_only_those_with_target(client):
    r = client.get("/deposits", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "เอ" in b and "บี" in b and "ซี" in b
    assert "ดี" not in b            # target==0 ไม่แสดง


def test_deposits_summary_totals(client):
    r = client.get("/deposits", follow_redirects=True)
    b = r.text
    # 3 คนมีเงินประกัน, รวมสะสม 18,000, ยังขาดรวม = (7000+0+5000)=12,000
    assert "18,000" in b
    assert "12,000" in b


def test_deposits_filter_by_site(client):
    r = client.get("/deposits?site=LCB", follow_redirects=True)
    b = r.text
    assert "เอ" in b and "บี" in b
    assert "ซี" not in b            # BIGC ถูกกรองออก
