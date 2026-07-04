# -*- coding: utf-8 -*-
"""โหมดจ่าย AYU (ayu_mao / ayu_trip_self_fuel / ayu_trip+การันตี) — ยึดกติกาที่เคยเป็นบั๊กจริง.

เขียน 4 ก.ค. 2026 หลัง coverage ชี้ว่า branch พวกนี้ไม่มีเทสต์:
- ayu_mao เคยคิด revenue×60% ใหม่ทุกเที่ยว ทับค่าที่โอแก้มือ (งานฝากเฮงเค็ล 100฿) → จ่ายผิด
  แก้เป็น Σ trip_fee_driver (single source ตรงเดลี่/สลิป) — เทสต์นี้กันถอยหลัง
- ayu_mao หักน้ำมันเฉพาะบิล exclude_from_driver=False + หักทางด่วน (petty category=toll)
- ayu_trip การันตี: เติมเฉพาะเมื่อค่าเที่ยว < การันตี prorate ตามวันมีสิทธิ์
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
from models import (AppUser, DailyJob, Employee, FuelTxn, PayRun, PayRunItem,
                    PettyCashTxn)
from services.payroll import compute_pay_run

MAO, SELF_FUEL, GUAR = 201, 202, 203
D1, D2 = date(2026, 6, 2), date(2026, 6, 10)   # ในรอบ AYU 2026-06 (26พ.ค.–25มิ.ย.)


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)

        s.add(Employee(id=MAO, code="A201", full_name="นาย เหมา ทดสอบ",
                       pay_mode="ayu_mao", home_site_code="AYU", status="active"))
        s.add(Employee(id=SELF_FUEL, code="A202", full_name="นาย เที่ยวน้ำมันเอง",
                       pay_mode="ayu_trip_self_fuel", home_site_code="AYU", status="active"))
        s.add(Employee(id=GUAR, code="A203", full_name="นาย การันตี ทดสอบ",
                       pay_mode="ayu_trip", home_site_code="AYU", status="active",
                       has_guarantee=True, guarantee_monthly_amount=15000.0))

        # --- ayu_mao: 2 เที่ยว — เที่ยวปกติ 1,000 + งานฝากแก้มือ 100 (revenue สูงลวง)
        s.add(DailyJob(site_code="AYU", driver_id=MAO, work_date=D1,
                       status_code="DHL", plate_no_raw="71-0556",
                       revenue_customer=5000.0, trip_fee_driver=1000.0))
        s.add(DailyJob(site_code="AYU", driver_id=MAO, work_date=D2,
                       status_code="DHL", plate_no_raw="71-0556",
                       revenue_customer=163.0, trip_fee_driver=100.0))
        # น้ำมันหักจริง 1,500 + บิลธง "ไม่หัก" 750 (ต้องไม่ถูกหัก)
        s.add(FuelTxn(site_code="AYU", txn_date=D1, driver_id=MAO,
                      plate_no_raw="71-0556", liter=45.0, amount=1500.0,
                      exclude_from_driver=False))
        s.add(FuelTxn(site_code="AYU", txn_date=D2, driver_id=MAO,
                      plate_no_raw="71-0556", liter=22.0, amount=750.0,
                      exclude_from_driver=True))
        # ทางด่วน/Mflow ที่สดย่อยออกแทน → หักคืน
        s.add(PettyCashTxn(site_code="AYU", txn_date=D1, driver_id=MAO,
                           direction="out", category="toll", amount=240.0,
                           pay_cycle_tag="2026-06", description="Mflow"))

        # --- ayu_trip_self_fuel: เที่ยว 2,000 − น้ำมันเอง 800
        s.add(DailyJob(site_code="AYU", driver_id=SELF_FUEL, work_date=D1,
                       status_code="HomePro", plate_no_raw="71-0557",
                       revenue_customer=3000.0, trip_fee_driver=2000.0))
        s.add(FuelTxn(site_code="AYU", txn_date=D1, driver_id=SELF_FUEL,
                      plate_no_raw="71-0557", liter=25.0, amount=800.0,
                      exclude_from_driver=False))

        # --- ayu_trip + การันตี 15,000: ทำงาน 2 วัน ค่าเที่ยวน้อย (100+100)
        for d in (D1, D2):
            s.add(DailyJob(site_code="AYU", driver_id=GUAR, work_date=d,
                           status_code="DHL", plate_no_raw="71-0558",
                           revenue_customer=500.0, trip_fee_driver=100.0))

        s.add(PayRun(id=1, site_code="AYU", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 26), period_end=date(2026, 6, 25),
                     status="draft"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _compute_and_get(emp_id: int) -> PayRunItem:
    with Session(engine) as s:
        compute_pay_run(s, s.get(PayRun, 1), recompute=True)
        return s.exec(select(PayRunItem).where(
            PayRunItem.pay_run_id == 1,
            PayRunItem.employee_id == emp_id)).one()


def test_ayu_mao_uses_trip_fee_not_revenue_share(client):
    it = _compute_and_get(MAO)
    # กติกาหลัง fix: Σ trip_fee_driver ตรงๆ — ไม่ใช่ revenue×60% (จะได้ 3,097.8)
    assert it.fuel_share_income == 1100.0
    assert it.fuel_cost_self == 1500.0          # บิลธงไม่หัก (750) ต้องไม่โผล่
    assert it.other_deduction >= 240.0          # ทางด่วน Mflow หักคืน


def test_ayu_self_fuel_trip_income_minus_own_fuel(client):
    it = _compute_and_get(SELF_FUEL)
    assert it.trip_fee_total == 2000.0
    assert it.fuel_cost_self == 800.0


def test_ayu_trip_guarantee_topup_when_low(client):
    it = _compute_and_get(GUAR)
    assert it.trip_fee_total == 200.0
    # การันตี prorate ตามวันมีสิทธิ์ (ทำงานจริง 2 วัน) — ต้องได้ topup > 0
    # และ trip+topup = ยอด prorate เป๊ะ (คิดจากวันที่ engine นับเอง)
    assert it.guarantee_topup > 0
    days_in_cycle = (date(2026, 6, 25) - date(2026, 5, 26)).days + 1   # 31
    eligible = it.days_worked + it.days_company_no_work
    expected = round(15000.0 / days_in_cycle * eligible - 200.0, 2)
    assert it.guarantee_topup == pytest.approx(expected, abs=0.02)


def test_ayu_trip_no_topup_when_trips_beat_guarantee(client):
    with Session(engine) as s:
        s.add(DailyJob(site_code="AYU", driver_id=GUAR, work_date=date(2026, 6, 15),
                       status_code="DHL", plate_no_raw="71-0558",
                       revenue_customer=50000.0, trip_fee_driver=30000.0))
        s.commit()
    it = _compute_and_get(GUAR)
    assert it.trip_fee_total == 30200.0
    assert it.guarantee_topup == 0.0
