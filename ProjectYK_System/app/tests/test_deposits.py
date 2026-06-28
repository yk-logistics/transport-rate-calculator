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


def test_dep_install_filter():
    # หน่วยงวด = 1,000 → 'สะสม//1000 / เพดาน//1000'
    f = appmod._fmt_dep_install
    assert f(Employee(deposit_balance=3000, deposit_target=10000)) == "3/10"
    assert f(Employee(deposit_balance=10000, deposit_target=10000)) == "10/10"
    assert f(Employee(deposit_balance=0, deposit_target=10000)) == "0/10"
    assert f(Employee(deposit_balance=0, deposit_target=0)) == ""   # ไม่มีเงินประกัน
    assert f(None) == ""


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
        # ออกแล้ว (inactive) มีเงินประกัน → default ต้องซ่อน, show=all ค่อยโผล่
        s.add(Employee(id=14, code="D14", full_name="อดีต", home_site_code="LCB",
                       status="inactive", deposit_balance=7000, deposit_target=10000))
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


def test_deposits_shows_installment_number(client):
    # คอลัมน์ "งวดที่ X/Y" = สะสม//1000 / เพดาน//1000 (ตรงกับชีต SSO)
    r = client.get("/deposits", follow_redirects=True)
    b = r.text
    assert ">งวดที่<" in b              # หัวคอลัมน์
    assert "3/10" in b                  # เอ 3,000/10,000
    assert "10/10" in b                 # บี เก็บครบ
    assert "5/10" in b                  # ซี 5,000/10,000


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


def test_deposits_default_hides_resigned(client):
    # default = เฉพาะคนทำงาน (active) → ไม่เห็น "อดีต" (inactive)
    r = client.get("/deposits", follow_redirects=True)
    b = r.text
    assert "เอ" in b and "บี" in b and "ซี" in b   # active ยังเห็น
    assert "อดีต" not in b                          # inactive ถูกซ่อน default


def test_deposits_show_all_includes_resigned(client):
    # show=all → เห็นคนออกแล้วด้วย
    r = client.get("/deposits?show=all", follow_redirects=True)
    b = r.text
    assert "อดีต" in b
    assert "เอ" in b


def test_deposits_default_summary_excludes_resigned(client):
    # default summary นับเฉพาะ active: 3 คน, สะสม 18,000 (ไม่รวม อดีต 7,000)
    r = client.get("/deposits", follow_redirects=True)
    b = r.text
    assert "18,000" in b      # 3000+10000+5000, ไม่บวก 7000
    # 25,000 (รวม อดีต) ต้องไม่โผล่ใน default
    assert "25,000" not in b


def test_deposits_default_site_filter_still_hides_resigned(client):
    # กรองไซต์ LCB + default → เอ,บี เห็น; อดีต(LCB,inactive) ยังซ่อน
    r = client.get("/deposits?site=LCB", follow_redirects=True)
    b = r.text
    assert "เอ" in b and "บี" in b
    assert "อดีต" not in b


def test_edit_updates_balance_and_writes_audit(client):
    r = client.post("/deposits/10/edit",
                    data={"deposit_balance": "4000", "deposit_target": "10000",
                          "reason": "หักเพิ่ม มิ.ย."})
    assert r.status_code == 200
    with Session(engine) as s:
        e = s.get(Employee, 10)
        assert e.deposit_balance == 4000
        audits = s.exec(select(DepositAudit).where(DepositAudit.employee_id == 10)).all()
        assert len(audits) == 1
        assert audits[0].field_name == "deposit_balance"
        assert audits[0].old_value == "3000.0"
        assert audits[0].new_value == "4000.0"
        assert audits[0].changed_by == "yk1"
        assert audits[0].reason == "หักเพิ่ม มิ.ย."


def test_edit_no_change_writes_no_audit(client):
    # ส่งค่าเดิม (เอ: balance 3000, target 10000) → ไม่มี audit
    r = client.post("/deposits/10/edit",
                    data={"deposit_balance": "3000", "deposit_target": "10000", "reason": ""})
    assert r.status_code == 200
    with Session(engine) as s:
        audits = s.exec(select(DepositAudit).where(DepositAudit.employee_id == 10)).all()
        assert len(audits) == 0


def test_edit_negative_rejected(client):
    r = client.post("/deposits/10/edit",
                    data={"deposit_balance": "-500", "deposit_target": "10000", "reason": ""})
    assert r.status_code == 400
    with Session(engine) as s:
        e = s.get(Employee, 10)
        assert e.deposit_balance == 3000      # ไม่เปลี่ยน
        audits = s.exec(select(DepositAudit).where(DepositAudit.employee_id == 10)).all()
        assert len(audits) == 0


@pytest.fixture()
def client_hist():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # บี: balance 10000 แต่ระบบหักจริงแค่ 2 รอบ × 1000 = 2000 → carried 8000 (ลอกยอด)
        s.add(Employee(id=11, code="D11", full_name="บี", home_site_code="LCB",
                       status="active", deposit_balance=10000, deposit_target=10000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-05",
                     period_start=date(2026,4,16), period_end=date(2026,5,15), status="final"))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026,5,16), period_end=date(2026,6,15), status="draft"))
        s.add(PayRunItem(pay_run_id=1, employee_id=11, deposit_install=1000))
        s.add(PayRunItem(pay_run_id=2, employee_id=11, deposit_install=1000))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_history_shows_deductions_and_carried_diff(client_hist):
    r = client_hist.get("/deposits/11/history", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "2026-05" in b and "2026-06" in b      # 2 รอบที่หักจริง
    # carried = 10000 - 2000 = 8000 → โชว์ส่วนต่าง "ยอดยกมา"
    assert "8,000" in b
    assert "ยอดยกมา" in b or "ไม่ได้หักผ่านระบบ" in b
