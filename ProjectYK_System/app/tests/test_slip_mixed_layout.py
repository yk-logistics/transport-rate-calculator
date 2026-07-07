# -*- coding: utf-8 -*-
"""จัดระเบียบตารางสลิปโหมด Mix (โอ 6ก.ค. — เคสสุรเดช):
1. วันรถจอด/ลา ที่ไม่มีเงิน/น้ำมัน ยุบเหลือแถวสรุปเดียวต่อป้าย (เดิมไล่ทีละวัน รก)
2. ชุดผู้บริหารของคน Mix ต้องมีคอลัมน์ ค่าขนส่งจริง/ราคากลาง/KB เหมือนคนโหมดปกติ
   (เดิมหายทั้งแถบ — ตรวจ 60% เหมาไม่ได้); สลิปคนขับห้ามมี
เป็นแค่การแสดงผล ไม่กระทบเงิน."""
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
from models import Employee, PayRun, PayRunItem, DailyJob, FuelTxn, AppUser


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=80, code="D80", full_name="นาย ทดสอบ มิกซ์เลย์เอาต์",
                       pay_mode="lcb_mixed", home_site_code="LCB", status="active",
                       base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        # วันเหมา (fee/rev = 0.6) + KB
        s.add(DailyJob(site_code="LCB", driver_id=80, work_date=date(2026, 6, 2),
                       status_code="KAO", destination="คลังปลาวาฬ",
                       revenue_customer=5000, trip_fee_driver=3000, kb_amount=300))
        # วันเที่ยว (ratio ต่ำ)
        s.add(DailyJob(site_code="LCB", driver_id=80, work_date=date(2026, 6, 3),
                       status_code="EVO", destination="ศรีราชา",
                       revenue_customer=4000, trip_fee_driver=700))
        # รถจอด 3 วัน ไม่มีเงิน/น้ำมัน → ต้องยุบเป็นแถวเดียว
        for d in (4, 5, 6):
            s.add(DailyJob(site_code="LCB", driver_id=80, work_date=date(2026, 6, d),
                           status_code="รถจอด"))
        # แถวเติมน้ำมันวันไม่มีงาน (จะถูกซ่อนฝั่งคนขับ / ชุดผู้บริหารเห็น)
        fo = DailyJob(site_code="LCB", driver_id=80, work_date=date(2026, 6, 7),
                      fuel_liter=40, fuel_amount=1600, fuel_date=date(2026, 6, 7))
        s.add(fo); s.commit(); s.refresh(fo)
        s.add(FuelTxn(driver_id=80, site_code="LCB", txn_date=date(2026, 6, 7),
                      liter=40, amount=1600, daily_job_id=fo.id))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_idle_days_merged_into_one_row(client):
    b = client.get("/payroll/1/employee/80/slip", follow_redirects=True).text
    assert "รวม 3 วัน" in b
    # ป้ายรถจอดในตารางเหลือแถวเดียว (นับเฉพาะจุดใช้งาน — ใน CSS มีชื่อ class อยู่ด้วย)
    assert b.count("k-tag k-idle") == 1


def test_mixed_driver_slip_has_no_boss_columns(client):
    b = client.get("/payroll/1/employee/80/slip", follow_redirects=True).text
    # เช็คที่หัวคอลัมน์จริง — คำนี้มีอยู่ใน CSS comment ของหน้าด้วย
    assert "<th class=\"num\">ค่าขนส่งจริง</th>" not in b
    assert "🛢 เติมน้ำมัน" not in b   # แถวเติมน้ำมันรายวันซ่อนฝั่งคนขับ (ตาราง mixed ด้วย)


def test_mixed_boss_print_has_boss_columns_and_fuelonly(client):
    b = client.get("/payroll/1/print?for=boss", follow_redirects=True).text
    assert "ค่าขนส่งจริง" in b        # หัวคอลัมน์โผล่ในตาราง mixed แล้ว
    assert "🛢 เติมน้ำมัน" in b       # รายวันยังครบ
    # ค่าขนส่งจริงวันเหมา 5,000 + KB 300 ต้องอยู่ในตาราง
    assert "5,000" in b and "300" in b
