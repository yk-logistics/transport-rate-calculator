# -*- coding: utf-8 -*-
"""กติกาเงินชุด 2 (จาก coverage 4 ก.ค.): ภาษีก้าวหน้า / ราคาคิดเงินคนขับ /
จำแนกวัน LCB ผสม / รถจอดช่วงเหมา / BigC ค่าเรทน้ำมัน — ทุกกติกามาจากการเคาะจริงของโอ.
"""
import os
import tempfile
from datetime import date
from types import SimpleNamespace

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import DailyJob, Employee, FuelTxn
from services.payroll import (
    _annual_progressive_tax,
    _classify_lcb_days,
    _compute_bigc_fuel_rebate,
    _idle_dates_in_mao_phase,
    driver_calc_price,
)


# ---- ภาษีก้าวหน้าบุคคลธรรมดา: ขอบ bracket ตามกฎหมายทุกขั้น ----

@pytest.mark.parametrize("income,tax", [
    (0, 0.0), (-5000, 0.0),
    (150_000, 0.0),                       # ขั้นแรกยกเว้น
    (150_001, 0.05),                      # บาทแรกที่โดน 5%
    (300_000, 7_500.0),
    (500_000, 27_500.0),
    (750_000, 65_000.0),
    (1_000_000, 115_000.0),
    (2_000_000, 365_000.0),
    (5_000_000, 1_265_000.0),
    (6_000_000, 1_615_000.0),             # เข้าขั้น 35%
])
def test_progressive_tax_brackets(income, tax):
    assert _annual_progressive_tax(income) == pytest.approx(tax, abs=0.01)


# ---- ราคาคิดเงินคนขับ = (override ?? revenue) − KB (memory: kb-driver-calc-price) ----

def test_driver_calc_price():
    row = SimpleNamespace(revenue_customer=5000.0, price_override=None, kb_amount=500.0)
    assert driver_calc_price(row) == 4500.0
    row = SimpleNamespace(revenue_customer=5000.0, price_override=4800.0, kb_amount=500.0)
    assert driver_calc_price(row) == 4300.0        # override แทนฐาน แล้ว KB หักซ้อนได้
    row = SimpleNamespace(revenue_customer=0.0, price_override=None, kb_amount=0.0)
    assert driver_calc_price(row) == 0.0


# ---- รถจอดคั่นช่วงเหมา → หักน้ำมัน; คั่นช่วงเที่ยว → ไม่หัก (โอ 26 มิ.ย.) ----

def _split(mao_dates=(), trip_dates=(), idle_dates=()):
    mk = lambda ds: [SimpleNamespace(work_date=d) for d in ds]  # noqa: E731
    return {"mao_days": mk(mao_dates), "trip_days": mk(trip_dates),
            "ambiguous": [], "no_work": mk(idle_dates)}


def test_idle_in_mao_phase_deducted():
    s = _split(mao_dates=[date(2026, 6, 1), date(2026, 6, 5)],
               trip_dates=[date(2026, 6, 20)],
               idle_dates=[date(2026, 6, 3), date(2026, 6, 19)])
    out = _idle_dates_in_mao_phase(s)
    assert date(2026, 6, 3) in out          # คั่นกลางช่วงเหมา → หัก
    assert date(2026, 6, 19) not in out     # ชิดวันเที่ยว → ไม่หัก


def test_idle_tie_goes_to_mao():
    # ห่างเท่ากันทั้งสองฝั่ง → ฝั่งเหมาชนะ (ปลอดภัยกว่า = หัก)
    s = _split(mao_dates=[date(2026, 6, 1)], trip_dates=[date(2026, 6, 5)],
               idle_dates=[date(2026, 6, 3)])
    assert _idle_dates_in_mao_phase(s) == {date(2026, 6, 3)}


def test_idle_without_mao_never_deducts():
    s = _split(trip_dates=[date(2026, 6, 5)], idle_dates=[date(2026, 6, 3)])
    assert _idle_dates_in_mao_phase(s) == set()


# ---- จำแนกวัน LCB (โอ 24 มิ.ย.): ratio 0.60±0.05=เหมา, <0.15=เที่ยว, กลาง=ถามโอ ----

@pytest.fixture()
def db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    yield


def test_classify_lcb_days(db):
    E = 301
    with Session(engine) as s:
        s.add(Employee(id=E, code="L301", full_name="นาย ผสม ทดสอบ",
                       pay_mode="lcb_mixed", home_site_code="LCB", status="active"))
        rows = [
            (date(2026, 6, 1), 5000.0, 3000.0, 0.0),    # 0.60 → เหมา
            (date(2026, 6, 2), 5000.0, 3200.0, 0.0),    # 0.64 (ใน ±0.05) → เหมา
            (date(2026, 6, 3), 5000.0, 300.0, 0.0),     # 0.06 → เที่ยว
            (date(2026, 6, 4), 5000.0, 2000.0, 0.0),    # 0.40 กลางเมิร์ก → ถามโอ
            (date(2026, 6, 5), 0.0, 0.0, 0.0),          # rev=0 → รถจอด
            # KB กระทบ ratio: rev 5500 kb 500 → ฐาน 5000, fee 3000 = 0.60 → เหมา
            (date(2026, 6, 6), 5500.0, 3000.0, 500.0),
        ]
        for d, rev, fee, kb in rows:
            s.add(DailyJob(site_code="LCB", driver_id=E, work_date=d,
                           status_code="CY", plate_no_raw="71-9999",
                           revenue_customer=rev, trip_fee_driver=fee, kb_amount=kb))
        s.commit()
        split = _classify_lcb_days(s, E, date(2026, 6, 1), date(2026, 6, 30), "LCB")
    assert {r.work_date.day for r in split["mao_days"]} == {1, 2, 6}
    assert {r.work_date.day for r in split["trip_days"]} == {3}
    assert {r.work_date.day for r in split["ambiguous"]} == {4}
    assert {r.work_date.day for r in split["no_work"]} == {5}


# ---- BigC ค่าเรทน้ำมัน: เหลือ ×16 / เกิน ×32.15 (ติดลบ = หัก) ----

def test_bigc_fuel_rebate(db):
    E = 302
    with Session(engine) as s:
        s.add(Employee(id=E, code="B302", full_name="นาย บิ๊กซี ทดสอบ",
                       pay_mode="bigc_fuel_rate", home_site_code="BIGC", status="active"))
        s.add(DailyJob(site_code="BIGC", driver_id=E, work_date=date(2026, 6, 2),
                       plate_no_raw="71-8001", fuel_liter=100.0))
        s.add(FuelTxn(site_code="BIGC", txn_date=date(2026, 6, 2), driver_id=E,
                      plate_no_raw="71-8001", liter=80.0, amount=2600.0))
        s.commit()
        # เหลือ 20 ลิตร → 20×16 = 320
        rebate, budget, consumed, residual = _compute_bigc_fuel_rebate(
            s, E, date(2026, 6, 1), date(2026, 6, 30), "BIGC")
        assert (rebate, budget, consumed, residual) == (320.0, 100.0, 80.0, 20.0)
        # เติมเพิ่มจนเกินงบ 30 ลิตร → -30×32.15 = -964.50 (หักแรงกว่าเรทคืน)
        s.add(FuelTxn(site_code="BIGC", txn_date=date(2026, 6, 10), driver_id=E,
                      plate_no_raw="71-8001", liter=50.0, amount=1650.0))
        s.commit()
        rebate, _, consumed, residual = _compute_bigc_fuel_rebate(
            s, E, date(2026, 6, 1), date(2026, 6, 30), "BIGC")
        assert (consumed, residual) == (130.0, -30.0)
        assert rebate == pytest.approx(-964.50)


def test_bigc_no_budget_no_rebate(db):
    """ไม่มีงบในเดลี่เลย (คีย์ไม่ครบ) → ห้ามคิดเรท (กันหักคนขับเพราะข้อมูลขาด)."""
    E = 303
    with Session(engine) as s:
        s.add(Employee(id=E, code="B303", full_name="นาย ไม่มีงบ",
                       pay_mode="bigc_fuel_rate", home_site_code="BIGC", status="active"))
        s.add(FuelTxn(site_code="BIGC", txn_date=date(2026, 6, 2), driver_id=E,
                      plate_no_raw="71-8002", liter=80.0, amount=2600.0))
        s.commit()
        rebate, budget, consumed, residual = _compute_bigc_fuel_rebate(
            s, E, date(2026, 6, 1), date(2026, 6, 30), "BIGC")
        assert (rebate, budget, residual) == (0.0, 0.0, 0.0)
        assert consumed == 80.0
