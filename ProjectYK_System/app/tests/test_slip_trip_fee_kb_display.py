"""สลิปคนขับ: ค่าเที่ยวต่อบรรทัดของแถวเหมา 60% ต้องโชว์ (ค่าขนส่ง−KB)×60%
ไม่ใช่ ค่าขนส่งเต็ม×60% — ให้บวกมือรายบรรทัดแล้วเท่ายอดรวม (item.fuel_share_income).

โอ 1ก.ค.: ปกรณ์ ค่าขนส่ง 2410 KB 110 → ค่าเที่ยว = (2410−110)×60% = 1380 (ไม่ใช่ 1446).
แก้เฉพาะ "การแสดงผล" บนสลิป — ไม่แตะเงินที่จ่าย, ไม่แตะหน้าเดลี่.
แถวค่าเที่ยวเหมาจ่ายแบบ flat (lcb_trip เช่น 200฿) ที่ ratio ไม่ใช่ ~60% ต้องคงเดิม (KB ไม่ลด).
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
from models import Employee, PayRun, PayRunItem, DailyJob, AppUser


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # ปกรณ์ = เหมา (lcb_mao). importer ลง tfd = revenue×60% (เต็ม ยังไม่หัก KB)
        s.add(Employee(id=60, code="D60", full_name="ปกรณ์ ศรีปุญเรือง", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active"))
        # คนเที่ยว flat (lcb_trip) วิ่ง NHL มี KB แต่ค่าเที่ยวเหมาจ่าย 200 (ratio ~0.08)
        s.add(Employee(id=61, code="D61", full_name="สุวิทย์ สุขล้อม", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        # ปกรณ์: NHL มี KB (แถวเหมา 60%) + KLND ไม่มี KB (แถวเหมา 60%)
        s.add(DailyJob(site_code="LCB", driver_id=60, work_date=date(2026, 6, 1),
                       status_code="NHL", revenue_customer=2410, kb_amount=110, trip_fee_driver=1446))
        s.add(DailyJob(site_code="LCB", driver_id=60, work_date=date(2026, 6, 2),
                       status_code="KLND", revenue_customer=5000, kb_amount=0, trip_fee_driver=3000))
        # สุวิทย์: NHL มี KB แต่ค่าเที่ยว flat 200 (ไม่ใช่ 60%) → ต้องคงเดิม
        s.add(DailyJob(site_code="LCB", driver_id=61, work_date=date(2026, 6, 1),
                       status_code="NHL", revenue_customer=2410, kb_amount=110, trip_fee_driver=200))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_helper_kb_adjusts_mao_row_not_flat_trip():
    """helper คำนวณค่าเที่ยวที่โชว์: แถวเหมา 60% หัก KB, แถว flat คงเดิม."""
    from services.payroll_slip import slip_trip_fee_display

    class Row:
        def __init__(self, rev, kb, tfd, ovr=None):
            self.revenue_customer = rev; self.kb_amount = kb
            self.trip_fee_driver = tfd; self.price_override = ovr

    # แถวเหมา 60% + KB → (2410−110)×0.6 = 1380
    assert slip_trip_fee_display(Row(2410, 110, 1446)) == 1380.0
    # แถวเหมา 60% ไม่มี KB → 5000×0.6 = 3000 (ไม่เปลี่ยน)
    assert slip_trip_fee_display(Row(5000, 0, 3000)) == 3000.0
    # แถว flat (ratio ~0.08) มี KB → คงค่าเที่ยวเดิม 200 (KB ไม่ลดค่าเหมาจ่าย)
    assert slip_trip_fee_display(Row(2410, 110, 200)) == 200.0
    # แถวว่าง (รถจอด tfd=0) → 0
    assert slip_trip_fee_display(Row(0, 0, 0)) == 0.0


def test_slip_shows_kb_adjusted_trip_fee(client):
    """สลิป ปกรณ์: โชว์ 1,380 (ไม่ใช่ 1,446) สำหรับแถว NHL ที่มี KB."""
    b = client.get("/payroll/1/employee/60/slip", follow_redirects=True).text
    assert "1,380" in b       # (2410−110)×60%
    assert "1,446" not in b    # ค่าขนส่งเต็ม×60% ต้องไม่โผล่แล้ว
    assert "3,000" in b        # แถวไม่มี KB ไม่เปลี่ยน


def test_slip_line_sum_matches_paid_total(client):
    """บวกค่าเที่ยวรายบรรทัดที่โชว์ = ยอดรวมที่จ่าย (item.fuel_share_income)."""
    with Session(engine) as s:
        it = s.exec(select(PayRunItem).where(
            PayRunItem.pay_run_id == 1, PayRunItem.employee_id == 60)).first()
        # ปกรณ์: 1380 (NHL−KB) + 3000 (KLND) = 4380 ; engine หัก KB×0.6=66 → 4446−66=4380
        assert round(it.fuel_share_income, 2) == 4380.0


def test_flat_trip_fee_untouched_on_slip(client):
    """สุวิทย์ (lcb_trip) แถว NHL flat 200 → ยังโชว์ 200 (KB ไม่ลด)."""
    b = client.get("/payroll/1/employee/61/slip", follow_redirects=True).text
    assert "200" in b
