# -*- coding: utf-8 -*-
"""🔍 ค้นหากลาง /search: เจอข้ามแหล่ง + section กรองตามสิทธิ์ role."""
import os
import tempfile
from datetime import date

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
from models import AppUser, DailyJob, Employee, FuelTxn, Quotation, Vehicle


@pytest.fixture()
def clients():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        admin = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        admin.must_change_pw = False; s.add(admin)
        s.add(AppUser(username="off1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.add(DailyJob(work_date=date(2026, 7, 1), site_code="LCB", status_code="KLND",
                       plate_no_raw="71-8967", container_no="TEXU7778889",
                       invoice_no="KTIV2607-009", revenue_customer=100))
        s.add(Employee(code="E9", full_name="สมชาย ทดสอบค้นหา", home_site_code="LCB"))
        s.add(Vehicle(plate_no="71-8967", nickname="กระเพรา"))
        s.add(FuelTxn(txn_date=date(2026, 7, 1), site_code="LCB",
                      plate_no_raw="71-8967", liter=100, amount=3000, station="ปตท.คลองเจ็ด"))
        s.add(Quotation(record_id="r1", customer_name="KAO", factory_name="โรงงานทดสอบ",
                        price_offered=5500.0, raw_json="{}"))
        s.commit()
    with TestClient(appmod.app) as c_admin, TestClient(appmod.app) as c_off:
        c_admin.post("/login", data={"username": "yk1", "password": "changeme1"})
        c_off.post("/login", data={"username": "off1", "password": "pw12345678"})
        yield c_admin, c_off


def test_search_container_hits_daily(clients):
    c_admin, _ = clients
    b = c_admin.get("/search?q=TEXU7778889").text
    assert "เดลี่" in b and "KTIV2607-009" in b


def test_search_plate_hits_multiple_sources(clients):
    c_admin, _ = clients
    b = c_admin.get("/search?q=71-8967").text
    assert "เดลี่" in b and "รถ" in b and "น้ำมัน" in b
    assert "กระเพรา" in b


def test_search_driver_and_quote(clients):
    c_admin, _ = clients
    assert "สมชาย ทดสอบค้นหา" in c_admin.get("/search?q=สมชาย").text
    assert "โรงงานทดสอบ" in c_admin.get("/search?q=KAO").text


def test_office_does_not_see_quote_section(clients):
    c_admin, c_off = clients
    # admin เห็น section ใบเสนอ แต่ office (quote=deny) ต้องไม่เห็น — คำค้นเดียวกัน
    assert "ใบเสนอราคา" in c_admin.get("/search?q=KAO").text
    b = c_off.get("/search?q=KAO").text
    assert b and "ใบเสนอราคา" not in b
    # ค้นทะเบียน — office เห็นเดลี่/รถ/น้ำมันปกติ
    b2 = c_off.get("/search?q=71-8967").text
    assert "เดลี่" in b2 and "น้ำมัน" in b2


def test_short_query_no_results(clients):
    c_admin, _ = clients
    assert "อย่างน้อย 2 ตัวอักษร" in c_admin.get("/search?q=x").text
