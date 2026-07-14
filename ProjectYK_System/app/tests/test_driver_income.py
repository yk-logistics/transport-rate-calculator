# -*- coding: utf-8 -*-
"""หน้าสรุปรายได้คนขับ /driver-income (โอสั่ง 14ก.ค.):
office ดูรวม/เฉลี่ยค่าเที่ยวรายคนขับได้ — เฉพาะคนขับ (ไม่โชว์พนักงาน role อื่น),
ตัวเลขยึดกติกาเดียวกับ payroll engine (trip_fee_driver + fee 3 หมวดของคนขับ),
ค่าสำรองจ่าย (lift/yard/ฯลฯ) ห้ามนับ, KB ห้ามโผล่, viewer เข้าไม่ได้."""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
import parts
from auth import hash_password
from models import AppUser, DailyJob, DailyJobFee, Employee


def _seed():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    parts.invalidate_cache()
    appmod.init_db()
    with Session(engine) as s:
        s.add(AppUser(username="office1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.add(AppUser(username="view1", password_hash=hash_password("pw12345678"),
                      role="viewer", must_change_pw=False))
        d1 = Employee(code="D001", full_name="สมชาย ขับดี", home_site_code="LCB", role="driver")
        d2 = Employee(code="D002", full_name="สมหญิง ขยัน", home_site_code="AYU", role="driver")
        o1 = Employee(code="O001", full_name="ออฟฟิศ ทดสอบ", home_site_code="LCB", role="office")
        s.add(d1); s.add(d2); s.add(o1)
        s.commit(); s.refresh(d1); s.refresh(d2); s.refresh(o1)

        # d1: 2 เที่ยวมีค่าเที่ยว (600+800) + 1 แถว tfd=0 → avg คิดเฉพาะเที่ยวที่จ่าย = 700.00
        j1 = DailyJob(work_date=date(2026, 7, 2), site_code="LCB", driver_id=d1.id,
                      trip_fee_driver=600.0, revenue_customer=3000.0, kb_amount=250.0)
        j2 = DailyJob(work_date=date(2026, 7, 3), site_code="LCB", driver_id=d1.id,
                      trip_fee_driver=800.0)
        j3 = DailyJob(work_date=date(2026, 7, 4), site_code="LCB", driver_id=d1.id,
                      trip_fee_driver=0.0)
        # นอกช่วงวันที่ (มิ.ย.) — ห้ามนับ
        j_out = DailyJob(work_date=date(2026, 6, 20), site_code="LCB", driver_id=d1.id,
                         trip_fee_driver=9999.0)
        # d2: ไซท์ AYU
        j4 = DailyJob(work_date=date(2026, 7, 5), site_code="AYU", driver_id=d2.id,
                      trip_fee_driver=512.34)
        # พนักงาน role=office มีแถวเดลี่ (ไม่ควรโผล่)
        j5 = DailyJob(work_date=date(2026, 7, 6), site_code="LCB", driver_id=o1.id,
                      trip_fee_driver=400.0)
        # แถวยังไม่ผูกคนขับ — ต้องโชว์แยกพร้อมคำเตือน
        j6 = DailyJob(work_date=date(2026, 7, 7), site_code="LCB", driver_id=None,
                      driver_raw_name="นายยังไม่ผูก", trip_fee_driver=300.0)
        for j in (j1, j2, j3, j_out, j4, j5, j6):
            s.add(j)
        s.commit(); s.refresh(j1)
        # fee ฝั่งคนขับ (special) นับรวม; ค่าสำรองจ่าย (lift) ห้ามนับ
        s.add(DailyJobFee(daily_job_id=j1.id, fee_type="special", amount=222.22))
        s.add(DailyJobFee(daily_job_id=j1.id, fee_type="lift", amount=999.99))
        s.commit()


@pytest.fixture()
def c_office():
    _seed()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "office1", "password": "pw12345678"})
        yield c
    parts.invalidate_cache()


URL = "/income/drivers?date_from=2026-07-01&date_to=2026-07-31"


def test_office_sees_driver_rows_with_sum_and_avg(c_office):
    r = c_office.get(URL)
    assert r.status_code == 200
    html = r.text
    assert "สมชาย ขับดี" in html
    assert "1,400.00" in html      # Σค่าเที่ยว d1 (ไม่รวมแถว มิ.ย.)
    assert "700.00" in html        # เฉลี่ยต่อเที่ยวที่มีค่าเที่ยว
    assert "1,622.22" in html      # รวม d1 = 1,400 + special 222.22
    assert "สมหญิง ขยัน" in html
    assert "512.34" in html
    assert "9,999" not in html     # นอกช่วงวันที่


def test_non_driver_employee_and_reserve_fee_and_kb_excluded(c_office):
    html = c_office.get(URL).text
    assert "ออฟฟิศ ทดสอบ" not in html   # เอาแค่คนขับ
    assert "999.99" not in html          # ค่าสำรองจ่าย ไม่ใช่รายได้คนขับ
    assert "250.0" not in html           # KB ห้ามโผล่ทุกกรณี


def test_unlinked_rows_shown_with_warning(c_office):
    html = c_office.get(URL).text
    assert "นายยังไม่ผูก" in html
    assert "ยังไม่ผูก" in html           # ป้ายเตือน unlinked
    assert "300.00" in html


def test_site_filter(c_office):
    html = c_office.get(URL + "&site=LCB").text
    assert "สมชาย ขับดี" in html
    assert "สมหญิง ขยัน" not in html


def test_grand_total_row(c_office):
    html = c_office.get(URL).text
    # รวมทุกคน: ค่าเที่ยว 1,400+512.34+300 = 2,212.34; รวมสุทธิ +222.22 = 2,434.56
    assert "2,212.34" in html
    assert "2,434.56" in html


def test_requires_login_not_public():
    # กัน gotcha PUBLIC_PREFIXES แบบ startswith ("/driver" เคยกิน "/driver-income")
    _seed()
    with TestClient(appmod.app) as c:
        r = c.get("/income/drivers", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"] == "/login"
    parts.invalidate_cache()


def test_viewer_denied():
    _seed()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "view1", "password": "pw12345678"})
        r = c.get("/income/drivers", follow_redirects=False)
        assert r.status_code == 403
    parts.invalidate_cache()
