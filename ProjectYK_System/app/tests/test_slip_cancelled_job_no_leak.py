"""งานยกเลิก (เก็บเงินลูกค้าได้แต่ไม่จ่ายคนขับ) ต้องไม่รั่ว remark ออกสลิปคนขับ.

เคสจริง: 26/5/2026 KAO ตู้ยกเลิก — สุภาพ/นิพล ถูกตัดออกจากค่าจ้าง (rev=0, fee=0)
แต่ของเดิมถูกเก็บไว้ใน remark = "[งานยกเลิก-ตัดออกจากค่าจ้าง] เดิม: ... ค่าเที่ยว=1200".
แถวนั้นเป็น status_code='รถจอด'. สลิปต้องโชว์ 'รถจอด' เฉย ๆ ห้ามโชว์ remark
(โอ: ตัวเลข 'ค่าเที่ยว=1200' บนสลิป = อันตราย คนขับงงว่าโดนเบี้ยว).

ต้องไม่กระทบงานปกติ: แถวที่มี remark ธรรมดา (ไม่ใช่มาร์ก cut) ยังโชว์ได้.
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

CUT_REMARK = "[งานยกเลิก-ตัดออกจากค่าจ้าง 29/6] เดิม: KAO คาโอDC อมตะ ตู้=ยกเลิก ค่าขนส่ง=2000.0 ค่าเที่ยว=1200.0"


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=60, code="D60", full_name="นาย ทดสอบ สลิป", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        # แถวงานยกเลิก: เงินถูกตัดออกแล้ว (rev=0, fee=0) status=รถจอด แต่ remark ยังมีของเดิม
        s.add(DailyJob(site_code="LCB", driver_id=60, work_date=date(2026, 5, 26),
                       status_code="รถจอด", revenue_customer=0, trip_fee_driver=0,
                       price_override=0, remark=CUT_REMARK))
        # แถวงานจริงปกติ (กันไม่ให้ fix ไปกลบ remark ที่ควรโชว์)
        s.add(DailyJob(site_code="LCB", driver_id=60, work_date=date(2026, 5, 27),
                       status_code="KAO", origin="B4", destination="SIAMCOM",
                       revenue_customer=5000, trip_fee_driver=3000, remark="หมายเหตุปกติโชว์ได้"))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_per_employee_slip_hides_cancel_remark(client):
    b = client.get("/payroll/1/employee/60/slip", follow_redirects=True).text
    # อันตราย: ตัวเลขค่าเที่ยวที่ไม่ได้จ่าย ต้องไม่โผล่
    assert "1200" not in b
    assert "ยกเลิก" not in b
    assert "ตัดออกจากค่าจ้าง" not in b
    # แต่แถวนั้นยังต้องอยู่ โชว์เป็น 'รถจอด'
    assert "รถจอด" in b


def test_print_all_driver_hides_cancel_remark(client):
    b = client.get("/payroll/1/print", follow_redirects=True).text
    assert "1200" not in b
    assert "ยกเลิก" not in b
    assert "ตัดออกจากค่าจ้าง" not in b


def test_normal_remark_still_shows(client):
    # remark ปกติ (ไม่ใช่มาร์ก cut) ของแถวงานจริง ต้องยังโชว์ได้ตามเดิม
    b = client.get("/payroll/1/employee/60/slip", follow_redirects=True).text
    assert "หมายเหตุปกติโชว์ได้" in b


# ---- unit: helper ที่ตัดสินว่าจะโชว์อะไรในช่อง route ของสลิป ----

class _Row:
    def __init__(self, **kw):
        self.site_code = "LCB"; self.origin = ""; self.pickup_location = ""
        self.destination = ""; self.status_code = ""; self.doc_no = ""; self.remark = ""
        for k, v in kw.items(): setattr(self, k, v)


def test_helper_cut_remark_returns_status_not_remark():
    from services.payroll_slip import slip_route_cell, slip_route_remark
    r = _Row(status_code="รถจอด", remark=CUT_REMARK)
    # ช่องหลัก = รถจอด เฉย ๆ
    assert slip_route_cell(r) == "รถจอด"
    # remark ภายในถูกตัด ไม่รั่วเลขออก
    out = slip_route_remark(r)
    assert out == ""
    assert "1200" not in out and "ยกเลิก" not in out


def test_helper_real_route_unaffected():
    from services.payroll_slip import slip_route_cell
    r = _Row(origin="B4", destination="SIAMCOM", status_code="KAO")
    assert slip_route_cell(r) == "B4 → SIAMCOM"


def test_helper_normal_remark_safe_to_show():
    from services.payroll_slip import slip_route_remark
    r = _Row(origin="B4", destination="SIAMCOM", remark="หมายเหตุปกติ")
    assert slip_route_remark(r) == "หมายเหตุปกติ"


def test_helper_idle_no_remark_shows_status():
    from services.payroll_slip import slip_route_cell
    r = _Row(status_code="รถจอด")
    assert slip_route_cell(r) == "รถจอด"
