# -*- coding: utf-8 -*-
"""สลิปเขียนเอง /payroll/manual-slip (โอ 7ก.ค.) — ทำสลิปย้อนหลังช่วงข้อมูลระบบยังไม่ครบ:
ทุกช่องพิมพ์แก้ได้ + เลือกพนักงานเติมข้อมูลที่มี (ชื่อ/รหัส/เลขบัตร/บัญชี) + พิมพ์.
ไม่เขียนอะไรลง DB — เป็นฟอร์มพิมพ์ล้วน."""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from auth import hash_password
from models import AppUser, Employee, PayRun, PayRunItem


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(AppUser(username="v1", password_hash=hash_password("pw12345678"),
                      role="viewer", must_change_pw=False))
        s.add(Employee(id=5, code="D05", full_name="สมชาย ทดสอบ", home_site_code="LCB",
                       status="active", id_card="1103700123456",
                       bank_name="กสิกรไทย", account_no="012-3-45678-9"))
        # รอบจริง 2 รอบ (ไว้ทดสอบ "ดึงข้อมูลจริง" หลายเดือน)
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-05",
                     period_start=date(2026, 4, 16), period_end=date(2026, 5, 15),
                     status="finalized"))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15),
                     status="finalized"))
        s.add(PayRunItem(pay_run_id=1, employee_id=5, site_code="LCB",
                         trip_fee_total=12345.0, special_income=500.0,
                         other_income=500.0, gross_total=12845.0,
                         social_security=462.0, deduction_total=462.0,
                         net_pay=12383.0))
        s.add(PayRunItem(pay_run_id=2, employee_id=5, site_code="LCB",
                         trip_fee_total=15000.0, gross_total=15000.0,
                         petty_cash_deduction=1000.0, deduction_total=1000.0,
                         net_pay=14000.0))
        s.commit()
    with TestClient(appmod.app) as c:
        yield c


def _login(c, user="yk1", pw="changeme1"):
    c.post("/login", data={"username": user, "password": pw})
    return c


def test_manual_slip_page_renders(client):
    _login(client)
    r = client.get("/payroll/manual-slip")
    assert r.status_code == 200
    assert "สลิปเขียนเอง" in r.text
    assert "เลขบัตรประชาชน" in r.text


def test_manual_slip_prefills_employee(client):
    _login(client)
    r = client.get("/payroll/manual-slip?emp_id=5")
    assert r.status_code == 200
    assert "สมชาย ทดสอบ" in r.text
    assert "1103700123456" in r.text     # เลขบัตร
    assert "012-3-45678-9" in r.text     # เลขบัญชี


def test_manual_slip_denied_for_viewer(client):
    _login(client, "v1", "pw12345678")
    r = client.get("/payroll/manual-slip", follow_redirects=False)
    assert r.status_code == 403


def test_manual_slip_prefills_from_real_run(client):
    """เลือกรอบจริง → เติมตัวเลขจากระบบ (ค่าเที่ยว/พิเศษ/หัก + ช่วงงวด)."""
    _login(client)
    r = client.get("/payroll/manual-slip?emp_id=5&run_ids=1")
    assert r.status_code == 200
    assert "12,345" in r.text            # ค่าเที่ยวจากรอบจริง
    assert "16/04/2026" in r.text        # ช่วงงวดจากรอบจริง
    assert "ประกันสังคม" in r.text


def test_manual_slip_multiple_months(client):
    """เลือกหลายรอบ → ได้หลายสลิปในหน้าเดียว (พิมพ์ทีเดียว)."""
    _login(client)
    r = client.get("/payroll/manual-slip?emp_id=5&run_ids=1,2")
    assert r.status_code == 200
    assert r.text.count('class="slip"') == 2
    assert "12,345" in r.text and "15,000" in r.text


def test_manual_slip_footer_no_authorized_signer(client):
    """โอสั่ง: ตัดช่อง 'ผู้มีอำนาจลงนาม' — เหลือ ผู้จัดทำ (มีลายเซ็น+ตรา) กับ ผู้รับเงิน."""
    _login(client)
    b = client.get("/payroll/manual-slip").text
    assert "ผู้มีอำนาจลงนาม" not in b
    assert "ผู้จัดทำ" in b and "ผู้รับเงิน" in b
    assert "/uploads/sig_oh.png" in b    # ลายเซ็น+ตราดิจิทัล (เสิร์ฟหลังล็อกอินเท่านั้น)
