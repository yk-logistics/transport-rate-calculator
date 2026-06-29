"""น้ำมัน "นอกตาราง" (วัดถังเริ่มเหมา + handover คนมาขับแทน) ต้องโผล่บนสลิปคนขับ.

บั๊กที่เจอ 29มิ.ย.:
  1. lcb_mixed (สุรเดช/พชร) — แถววัดถัง (mao_tank_measure, daily_job_id=None) อยู่ใน context
     แต่ template branch ของ mixed ไม่มี loop tank_measure_rows → หาย.
  2. lcb_mao (นิพล) — แถว handover (source=handover_measure) ถูก filter
     find("tank_measure") ตัดทิ้ง → ไม่เข้า tank_measure_rows เลย.
เงินหักถูก (เข้า fuel_cost_self แล้ว) แต่คนขับมองสลิปไม่เห็นว่าหักอะไร.
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
        # mixed driver (เหมาบางวัน) — มีวัดถังเริ่มเหมา
        s.add(Employee(id=70, code="D70", full_name="นาย ทดสอบ มิกซ์", pay_mode="lcb_mixed",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000))
        # mao driver — มี handover (รับรถคืนจากคนมาขับแทน)
        s.add(Employee(id=71, code="D71", full_name="นาย ทดสอบ เหมา", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active"))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        # mixed: วันเหมา (rev/fee ~60%) + วัดถัง off-table
        s.add(DailyJob(site_code="LCB", driver_id=70, work_date=date(2026, 6, 2),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=3000))
        s.add(FuelTxn(driver_id=70, site_code="LCB", txn_date=date(2026, 6, 2), liter=48.83,
                      amount=1988.36, source="mao_tank_measure", daily_job_id=None,
                      note="หักน้ำมันในถังตอนเริ่มเหมา 2/6 (วัดได้ 48.83L)"))
        # mao: วันเหมา + handover off-table
        s.add(DailyJob(site_code="LCB", driver_id=71, work_date=date(2026, 5, 28),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=3000))
        s.add(FuelTxn(driver_id=71, site_code="LCB", txn_date=date(2026, 5, 28), liter=28.0,
                      amount=1034.16, source="handover_measure", daily_job_id=None,
                      note="วัดน้ำมัน GPS: รับรถคืนจากคนมาขับแทน 28/5 หัก"))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 1), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_mixed_slip_shows_tank_measure(client):
    b = client.get("/payroll/1/employee/70/slip", follow_redirects=True).text
    assert "1,988" in b          # ยอดหักวัดถัง
    assert "วัดถัง" in b          # ป้ายบอกว่าน้ำมันในถังที่หัก


def test_mao_slip_shows_handover(client):
    b = client.get("/payroll/1/employee/71/slip", follow_redirects=True).text
    assert "1,034" in b                      # ยอดหัก handover
    assert "รับรถคืนจากคนมาขับแทน" in b      # ต้องเป็นบรรทัดที่บอกว่าคืออะไร ไม่จมในยอดรวม


def test_print_all_shows_offtable_fuel(client):
    b = client.get("/payroll/1/print", follow_redirects=True).text
    assert "วัดถัง" in b                      # mixed tank row label
    assert "รับรถคืนจากคนมาขับแทน" in b      # mao handover row label
