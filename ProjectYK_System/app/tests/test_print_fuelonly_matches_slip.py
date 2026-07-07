"""แถว "เติมน้ำมัน" (มีน้ำมันแต่ไม่มีงาน) — โอ 6ก.ค.: **สลิปคนขับไม่โชว์รายวันแล้ว**
(กลัวคนขับสับสนว่าวันไม่วิ่งทำไมมีรายการ) → เหลือบรรทัดสรุปเดียวเมื่อน้ำมันถูกหักจริง
(กันตารางบวกไม่ครบกับแถวรวม); **ชุดผู้บริหาร (?for=boss) ยังเห็นรายวันครบ** ไว้ตรวจ.
เป็นแค่การแสดงผล ไม่กระทบเงิน.
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
from models import Employee, PayRun, PayRunItem, DailyJob, FuelTxn, AppUser


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=70, code="D70", full_name="นาย ทดสอบ เติมน้ำมัน", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active", gross_share_rate=0.60))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        # แถวงานปกติ (เหมา) 1 แถว
        s.add(DailyJob(site_code="LCB", driver_id=70, work_date=date(2026, 5, 20),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=3000))
        # แถว "เติมน้ำมัน" — มีน้ำมันแต่ไม่มี route/ค่าเที่ยว/รายได้ → fuel_only
        fuelonly = DailyJob(site_code="LCB", driver_id=70, work_date=date(2026, 5, 22),
                            revenue_customer=0, trip_fee_driver=0,
                            fuel_liter=50, fuel_amount=2000, fuel_date=date(2026, 5, 22))
        s.add(fuelonly); s.commit(); s.refresh(fuelonly)
        s.add(FuelTxn(driver_id=70, site_code="LCB", txn_date=date(2026, 5, 22),
                      liter=50, amount=2000, daily_job_id=fuelonly.id))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


# marker "แถวเติมน้ำมันรายวัน" (ช่องส่งสินค้า) — บรรทัดสรุปใหม่จงใจไม่ใช้คำนี้
_FUELONLY_MARK = "🛢 เติมน้ำมัน"
# marker บรรทัดสรุปฝั่งคนขับ (โผล่เมื่อ fuel_cost_self > 0)
_SUMMARY_MARK = "น้ำมันวันไม่มีงานวิ่ง"


def test_driver_slip_hides_fuelonly_rows_shows_summary(client):
    """สลิปรายคน (คนขับ): ไม่มีแถวเติมน้ำมันรายวัน แต่มีบรรทัดสรุป (น้ำมันหักจริง)."""
    b = client.get("/payroll/1/employee/70/slip", follow_redirects=True).text
    assert _FUELONLY_MARK not in b
    assert _SUMMARY_MARK in b


def test_print_driver_hides_fuelonly_rows_shows_summary(client):
    b = client.get("/payroll/1/print", follow_redirects=True).text
    assert _FUELONLY_MARK not in b
    assert _SUMMARY_MARK in b


def test_print_boss_still_shows_fuelonly_rows(client):
    """ชุดผู้บริหารต้องเห็นรายวันครบ ไว้ตรวจการเติม."""
    b = client.get("/payroll/1/print?for=boss", follow_redirects=True).text
    assert _FUELONLY_MARK in b
