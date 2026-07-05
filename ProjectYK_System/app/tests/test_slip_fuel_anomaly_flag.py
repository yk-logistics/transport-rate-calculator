# -*- coding: utf-8 -*-
"""E2 ธงน้ำมันผิดปกติบนสลิป — โชว์เฉพาะชุดผู้บริหาร (is_boss) + กติกา R1 เฉพาะสลิป.

กติกาที่ล็อกไว้ (5 ก.ค. 2026):
  - R1 (เติมถี่) บนสลิปธงเมื่อ >=3 บิล/วัน เท่านั้น — ปั๊มออกบิล B7+B20 แยกใบต่อการ
    เติมครั้งเดียวเป็นปกติ (2 บิล/วันแทบทุกคัน) ; หน้า /fuel/anomaly ยังเกณฑ์ >=2 เดิม
  - สลิปคนขับ (ไม่มี is_boss) ห้ามมีธง — ธงไว้ให้โอตรวจตอนจ่าย ไม่ใช่ให้คนขับเห็น
  - ธง key ตามแถวที่บิลโชว์จริง (fuel_anomaly_by_job)
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date

import pytest
from sqlmodel import SQLModel, Session

from db_config import engine
import main as appmod
from models import DailyJob, Employee, FuelTxn, PayRun, PayRunItem, Vehicle
from services.payroll_slip import build_payroll_slip_context


@pytest.fixture()
def db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    yield


def _pr():
    return PayRun(site_code="LCB", pay_cycle_tag="2026-06",
                  period_start=date(2026, 5, 16), period_end=date(2026, 6, 15))


def _mk_driver_with_fills(s, n_fills_day1: int):
    """คนขับ 1 คน: วันที่ 10/6 มีงาน 1 แถว + เติม n บิลในวันนั้น (ผูกแถวเดียวกัน)."""
    emp = Employee(code=f"D-AN-{n_fills_day1}", full_name=f"ทดสอบ ธง{n_fills_day1}",
                   home_site_code="LCB", pay_mode="lcb_trip")
    s.add(emp); s.flush()
    v = Vehicle(plate_no=f"ZZ-AN-{n_fills_day1}", truck_type="head", tank_liters=500)
    s.add(v); s.flush()
    dj = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 10),
                  plate_no_raw=v.plate_no, origin="A", destination="B",
                  trip_fee_driver=350, fuel_liter=50, fuel_amount=1500)
    s.add(dj); s.flush()
    for i in range(n_fills_day1):
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 10),
                      plate_no_raw=v.plate_no, vehicle_id=v.id, liter=50, amount=1500,
                      daily_job_id=dj.id, fuel_grade="B7" if i % 2 == 0 else "B20"))
    s.flush()
    return emp, dj


def test_r1_two_bills_per_day_not_flagged_on_slip(db):
    """2 บิล/วัน (คู่ B7+B20 ปกติของปั๊ม) → สลิปต้องไม่ธง."""
    with Session(engine) as s:
        emp, dj = _mk_driver_with_fills(s, 2)
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        assert ctx["fuel_anomaly_by_job"] == {}


def test_r1_three_bills_per_day_flagged_on_slip(db):
    """3 บิล/วัน → ธง 'เติมถี่' (amber) ที่แถวงานนั้น."""
    with Session(engine) as s:
        emp, dj = _mk_driver_with_fills(s, 3)
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        an = ctx["fuel_anomaly_by_job"]
        assert dj.id in an
        assert "R1" in an[dj.id]["codes"]
        assert an[dj.id]["level"] == "amber"
        assert "เติมถี่" in an[dj.id]["short"]


def test_flag_visible_only_on_boss_render(db):
    """render จริง: ชุดผู้บริหารมี tag-anom / สลิปคนขับต้องไม่มี."""
    with Session(engine) as s:
        emp, dj = _mk_driver_with_fills(s, 3)
        pr = _pr()
        item = PayRunItem(pay_mode="lcb_trip")
        ctx = build_payroll_slip_context(s, pr, emp, item)
        assert ctx["fuel_anomaly_by_job"], "ต้องมีธงก่อนถึงจะทดสอบการโชว์ได้"
        boss_html = appmod.templates.get_template("payroll_slip.html").render(
            {**ctx, "is_boss": True})
        driver_html = appmod.templates.get_template("payroll_slip.html").render(dict(ctx))
        assert "tag-anom" in boss_html
        assert "tag-anom lv-" not in driver_html


def test_r2_over_tank_flagged_even_single_bill(db):
    """R2 ลิตรเกินถัง — บิลเดียวก็ธง (แดง) ไม่เกี่ยวเกณฑ์ R1."""
    with Session(engine) as s:
        emp = Employee(code="D-AN-R2", full_name="ทดสอบ เกินถัง",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        v = Vehicle(plate_no="ZZ-AN-R2", truck_type="head", tank_liters=300)
        s.add(v); s.flush()
        dj = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 10),
                      plate_no_raw=v.plate_no, origin="A", destination="B",
                      trip_fee_driver=350, fuel_liter=350, fuel_amount=10500)
        s.add(dj); s.flush()
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 10),
                      plate_no_raw=v.plate_no, vehicle_id=v.id, liter=350, amount=10500,
                      daily_job_id=dj.id, fuel_grade="B7"))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        an = ctx["fuel_anomaly_by_job"]
        assert dj.id in an
        assert "R2" in an[dj.id]["codes"]
        assert an[dj.id]["level"] == "rose"
