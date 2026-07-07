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
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from auth import hash_password
from models import AppUser, Employee


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
