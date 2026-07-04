# -*- coding: utf-8 -*-
"""โหมดจ่าย LCB ระดับ engine (lcb_mao / lcb_mixed) — ยึดกติกาที่โอเคาะ มิ.ย. 2026.

- lcb_mao: ค่าเที่ยว = Σ tfd − KB×60% เฉพาะแถว tfd>0 (โอ 30 มิ.ย.) + เหมาไม่ได้พิเศษ
  แต่ได้ OT/รับตู้แทน (โอ 25 มิ.ย.)
- lcb_mixed (ลูกผสม — ซับซ้อนสุดในระบบ): แยกวันด้วย ratio → ฝั่งเหมาได้ 60% ของ
  driver_calc_price + หักน้ำมันเฉพาะวันเหมา+วันจอดช่วงเหมา (ห้ามหักน้ำมันวันเที่ยว);
  ฝั่งเที่ยวได้ tfd; ฐาน+เบี้ยดูแล prorate ตาม (วันเที่ยว+วันจอด) — วันเหมาไม่มีฐาน
"""
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
from models import (AppUser, DailyJob, DailyJobFee, Employee, FuelTxn, PayRun,
                    PayRunItem)
from services.payroll import compute_pay_run

MAO, MIXED = 401, 402
# รอบ LCB 2026-07 = 16 มิ.ย. – 15 ก.ค. (30 วัน)
P_START, P_END = date(2026, 6, 16), date(2026, 7, 15)


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)

        s.add(Employee(id=MAO, code="L401", full_name="นาย เหมาแอลซีบี",
                       pay_mode="lcb_mao", home_site_code="LCB", status="active"))
        s.add(Employee(id=MIXED, code="L402", full_name="นาย ลูกผสม",
                       pay_mode="lcb_mixed", home_site_code="LCB", status="active",
                       base_salary=9240.0, care_allowance=3000.0))

        # --- lcb_mao: 2 เที่ยว fee 3000; เที่ยวแรกมี KB 500 (tfd>0 → หัก 500×0.6)
        j1 = DailyJob(site_code="LCB", driver_id=MAO, work_date=date(2026, 6, 17),
                      status_code="CY", plate_no_raw="71-6802",
                      revenue_customer=5000.0, trip_fee_driver=3000.0, kb_amount=500.0)
        s.add(j1)
        s.add(DailyJob(site_code="LCB", driver_id=MAO, work_date=date(2026, 6, 18),
                       status_code="CY", plate_no_raw="71-6802",
                       revenue_customer=5000.0, trip_fee_driver=3000.0))
        s.commit()
        # พิเศษ 200 (เหมาห้ามได้) + OT 150 (ได้)
        s.add(DailyJobFee(daily_job_id=j1.id, fee_type="พิเศษ", amount=200.0))
        s.add(DailyJobFee(daily_job_id=j1.id, fee_type="OT", amount=150.0))

        # --- lcb_mixed: เหมา 2 วัน (17-18) / จอด 1 วัน (19 — ติดช่วงเหมา) / เที่ยว 1 วัน (30)
        for d in (date(2026, 6, 17), date(2026, 6, 18)):
            s.add(DailyJob(site_code="LCB", driver_id=MIXED, work_date=d,
                           status_code="CY", plate_no_raw="71-8683",
                           revenue_customer=5000.0, trip_fee_driver=3000.0))
        s.add(DailyJob(site_code="LCB", driver_id=MIXED, work_date=date(2026, 6, 19),
                       status_code="รถจอด", plate_no_raw="71-8683",
                       revenue_customer=0.0, trip_fee_driver=0.0))
        s.add(DailyJob(site_code="LCB", driver_id=MIXED, work_date=date(2026, 6, 30),
                       status_code="KAO", plate_no_raw="71-8683",
                       revenue_customer=5000.0, trip_fee_driver=300.0))
        # น้ำมัน: วันเหมา 1,200 / วันจอดช่วงเหมา 500 / วันเที่ยว 900 (ห้ามหัก)
        s.add(FuelTxn(site_code="LCB", txn_date=date(2026, 6, 17), driver_id=MIXED,
                      plate_no_raw="71-8683", liter=35.0, amount=1200.0))
        s.add(FuelTxn(site_code="LCB", txn_date=date(2026, 6, 19), driver_id=MIXED,
                      plate_no_raw="71-8683", liter=15.0, amount=500.0))
        s.add(FuelTxn(site_code="LCB", txn_date=date(2026, 6, 30), driver_id=MIXED,
                      plate_no_raw="71-8683", liter=28.0, amount=900.0))

        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-07",
                     period_start=P_START, period_end=P_END, status="draft"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _item(emp_id: int) -> PayRunItem:
    with Session(engine) as s:
        compute_pay_run(s, s.get(PayRun, 1), recompute=True)
        return s.exec(select(PayRunItem).where(
            PayRunItem.pay_run_id == 1,
            PayRunItem.employee_id == emp_id)).one()


def test_lcb_mao_kb_share_and_no_special(client):
    it = _item(MAO)
    # Σ tfd 6,000 − KB share (500×0.60 เฉพาะแถว tfd>0) = 5,700
    assert it.fuel_share_income == 5700.0
    # เหมาไม่ได้พิเศษ แต่ได้ OT (โอ 25 มิ.ย.)
    assert it.special_income == 0.0
    assert it.ot_income == 150.0
    assert it.other_income >= 150.0


def test_lcb_mixed_full_math(client):
    it = _item(MIXED)
    # ฝั่งเหมา: (5000+5000)×0.60
    assert it.fuel_share_income == 6000.0
    # ฝั่งเที่ยว: เฉพาะวันเที่ยว
    assert it.trip_fee_total == 300.0
    # น้ำมัน: วันเหมา 1,200 + วันจอดช่วงเหมา 500 — วันเที่ยว 900 ห้ามหัก (โอ 26 มิ.ย.)
    assert it.fuel_cost_self == 1700.0
    # ฐาน+เบี้ยดูแล prorate ตาม (เที่ยว 1 + จอด 1)/30 วัน — วันเหมาไม่มีฐาน (โอ 25 มิ.ย.)
    days_in_cycle = (P_END - P_START).days + 1        # 30
    assert it.days_company_no_work == 1.0
    assert it.base_salary_earned == pytest.approx(9240.0 * 2 / days_in_cycle, abs=0.01)
    assert it.care_allowance_earned == pytest.approx(3000.0 * 2 / days_in_cycle, abs=0.01)
