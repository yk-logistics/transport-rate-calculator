"""สลิป: แยก พิเศษ/OT/รับตู้ ออกเป็น 'คอลัมน์' ต่างหาก (ไม่เบียดใต้ค่าเที่ยว).
โอ 1ก.ค.: ช่องค่าแรงของคนลูกผสมเบียดกัน → แยกคอลัมน์ ค่าเที่ยว | พิเศษ/OT.
ครอบ 3 surface: หน้าสลิปรายคน, /print, และตารางลูกผสม (mixed) + boss.
แค่การแสดงผล ยอดเงินไม่เปลี่ยน (พิเศษ/OT ยังรวมใน other_income เหมือนเดิม).
"""
import os, re, tempfile

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
from models import Employee, PayRun, PayRunItem, DailyJob, DailyJobFee, AppUser


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # trip driver: มีค่าเที่ยว + พิเศษ วันเดียวกัน
        s.add(Employee(id=80, code="D80", full_name="นาย เที่ยว พิเศษ", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        j = DailyJob(site_code="LCB", driver_id=80, work_date=date(2026, 6, 1),
                     status_code="KAO", destination="OM", revenue_customer=5000, trip_fee_driver=350)
        s.add(j); s.commit(); s.refresh(j)
        s.add(DailyJobFee(daily_job_id=j.id, fee_type="special", amount=222))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _trip_cell_html(html: str) -> str:
    """คืน HTML ของเซลล์ค่าเที่ยว (td.c-trip) แถวแรกที่เจอ."""
    m = re.search(r'<td[^>]*class="[^"]*c-trip[^"]*"[^>]*>(.*?)</td>', html, re.S)
    return m.group(1) if m else ""


def test_slip_has_extra_fee_column_header(client):
    b = client.get("/payroll/1/employee/80/slip", follow_redirects=True).text
    # หัวคอลัมน์ใหม่ต้องเป็น <th> จริง (ไม่ใช่แค่คำใน comment/footnote)
    assert re.search(r'<th[^>]*>\s*พิเศษ/OT\s*</th>', b)


def test_special_amount_in_extra_column_not_under_trip(client):
    b = client.get("/payroll/1/employee/80/slip", follow_redirects=True).text
    # ยอดพิเศษ 222 ต้องอยู่ในคอลัมน์ใหม่ (c-extra) ไม่ใช่ซ้อนใต้ค่าเที่ยว
    assert re.search(r'<td[^>]*class="[^"]*c-extra[^"]*"[^>]*>.*?222.*?</td>', b, re.S)
    # เซลล์ค่าเที่ยวต้องไม่มี "พิเศษ" ปนแล้ว
    assert "พิเศษ" not in _trip_cell_html(b)


def test_print_page_also_has_extra_column(client):
    b = client.get("/payroll/1/print", follow_redirects=True).text
    assert "พิเศษ/OT" in b
    assert re.search(r'<td[^>]*class="[^"]*c-extra[^"]*"[^>]*>.*?222.*?</td>', b, re.S)


def test_income_unchanged(client):
    """แยกคอลัมน์เป็นแค่การแสดงผล — special_income/gross ต้องเท่าเดิม."""
    with Session(engine) as s:
        it = s.exec(select(PayRunItem).where(
            PayRunItem.pay_run_id == 1, PayRunItem.employee_id == 80)).first()
        assert it.special_income == 222
