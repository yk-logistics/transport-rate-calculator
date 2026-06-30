"""สลิป: น้ำมันที่เติม "รอบเดียวกัน" (วันที่เติมจริงเดียวกัน) แต่แยกเป็น B7+B20
ให้รวมโชว์ช่องเดียว — แสดงผลอย่างเดียว ห้ามแตะยอดหัก/ผลรวม.

เคสจริง LCB มิ.ย.: ปั๊มออกบิล B7 ท่อนนึง + B20 อีกท่อนในการเติมครั้งเดียว แต่คนคีย์
ลงคนละ DailyJob (บางทีคนละ work_date) → สลิปโชว์ 2 บรรทัด คนขับงง.
แก้: group FuelTxn ตาม txn_date (วันเติมจริง) ต่อคน, รวมลิตร+ยอด โชว์บรรทัดแรก (anchor),
บรรทัดที่เหลือเว้นช่องน้ำมัน (merged). ผลรวมคอลัมน์ + fuel_cost_self เท่าเดิมเป๊ะ.
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
from models import Employee, DailyJob, FuelTxn, PayRun, PayRunItem
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


def test_same_fill_date_b7_b20_merge_to_one_anchor(db):
    with Session(engine) as s:
        emp = Employee(code="D-MF-1", full_name="ทดสอบ รวมเติม",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()

        # งานวันที่ 1 มิ.ย. (B7 36L) — บรรทัดบน
        dj1 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 1),
                       plate_no_raw="ZZ-MF-1", fuel_liter=36, fuel_amount=1494.7)
        # งานวันที่ 2 มิ.ย. (B20 50L) — แต่น้ำมันถูกเติม "จริง" วันที่ 1 มิ.ย. (เติมครั้งเดียวกับ dj1)
        dj2 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 2),
                       plate_no_raw="ZZ-MF-1", fuel_liter=50, fuel_amount=1801.0)
        s.add(dj1); s.add(dj2); s.flush()

        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 1),
                      plate_no_raw="ZZ-MF-1", liter=36, amount=1494.7, daily_job_id=dj1.id,
                      fuel_grade="B7"))
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 1),
                      plate_no_raw="ZZ-MF-1", liter=50, amount=1801.0, daily_job_id=dj2.id,
                      fuel_grade="B20"))
        s.flush()

        item = PayRunItem(pay_mode="lcb_trip")
        ctx = build_payroll_slip_context(s, _pr(), emp, item)

        merge = ctx["fuel_merge_by_job"]
        # dj1 (บรรทัดบน) = anchor : รวม 86L, 3295.7฿, เกรด B7+B20
        assert dj1.id in merge and merge[dj1.id]["role"] == "anchor"
        a = merge[dj1.id]
        assert abs(a["liter"] - 86) < 0.01
        assert abs(a["amount"] - 3295.7) < 0.01
        assert set(a["grades"]) == {"B7", "B20"}
        # dj2 = merged (เว้นช่องน้ำมัน ไม่โชว์ซ้ำ)
        assert dj2.id in merge and merge[dj2.id]["role"] == "merged"
        assert merge[dj2.id]["anchor"] == dj1.id


def test_single_fill_per_day_not_merged(db):
    """เติมวันละครั้ง (ไม่มี B7+B20 คู่) → ไม่มี entry ใน merge map (โชว์ปกติ)."""
    with Session(engine) as s:
        emp = Employee(code="D-MF-2", full_name="ทดสอบ เติมเดี่ยว",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        dj = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 3),
                      plate_no_raw="ZZ-MF-2", fuel_liter=40, fuel_amount=1628.8)
        s.add(dj); s.flush()
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 3),
                      plate_no_raw="ZZ-MF-2", liter=40, amount=1628.8, daily_job_id=dj.id,
                      fuel_grade="B7"))
        s.flush()
        item = PayRunItem(pay_mode="lcb_trip")
        ctx = build_payroll_slip_context(s, _pr(), emp, item)
        assert dj.id not in ctx["fuel_merge_by_job"]


def test_merge_preserves_column_total(db):
    """ผลรวมที่ "แสดง" (anchor รวม + บรรทัดที่ไม่ merged) = ผลรวมจริงทุกบรรทัด.
    พิสูจน์ว่า display merge ไม่ทำให้ยอดน้ำมันรวมเพี้ยน."""
    with Session(engine) as s:
        emp = Employee(code="D-MF-3", full_name="ทดสอบ ผลรวม",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        dj1 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 5),
                       plate_no_raw="ZZ-MF-3", fuel_liter=20, fuel_amount=830.4)
        dj2 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 5),
                       plate_no_raw="ZZ-MF-3", fuel_liter=100, fuel_amount=3522.0)
        dj3 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 7),
                       plate_no_raw="ZZ-MF-3", fuel_liter=40, fuel_amount=1628.8)
        s.add(dj1); s.add(dj2); s.add(dj3); s.flush()
        for dj, g in ((dj1, "B7"), (dj2, "B20")):
            s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 5),
                          plate_no_raw="ZZ-MF-3", liter=dj.fuel_liter, amount=dj.fuel_amount,
                          daily_job_id=dj.id, fuel_grade=g))
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 7),
                      plate_no_raw="ZZ-MF-3", liter=40, amount=1628.8,
                      daily_job_id=dj3.id, fuel_grade="B7"))
        s.flush()
        item = PayRunItem(pay_mode="lcb_trip")
        ctx = build_payroll_slip_context(s, _pr(), emp, item)
        merge = ctx["fuel_merge_by_job"]
        djs = ctx["daily_jobs"]

        true_total = sum((d.fuel_amount or 0) for d in djs)
        disp_total = 0.0
        for d in djs:
            m = merge.get(d.id)
            if m and m["role"] == "merged":
                continue
            if m and m["role"] == "anchor":
                disp_total += m["amount"]
            else:
                disp_total += d.fuel_amount or 0
        assert abs(true_total - disp_total) < 0.01, f"{true_total} != {disp_total}"
