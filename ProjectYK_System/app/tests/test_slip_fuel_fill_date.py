"""สลิป: น้ำมันโชว์ตาม "วันที่เติมจริง" (FuelTxn.txn_date) + รวมหลายบิลวันเดียวในแถวเดียว
เป็นบรรทัดย่อย — แสดงผลอย่างเดียว ไม่แตะยอด/เงิน.

โอสั่ง 30มิ.ย.: คนคีย์มักผูกบิลที่เติม "เมื่อวาน" ไว้กับงานวันนี้ → สลิปโชว์ผิดวัน.
เคสจริง LCB มิ.ย. = 74/384 บิล txn_date = work_date − 1 วัน (ทั้งหมดเป็น Case A:
วันเติมจริงมีแถวงานของวันนั้นอยู่แล้ว). ต้องการ: ย้ายบิลไปโชว์ใต้แถว work_date==txn_date
(วันเติมจริง), หลายบิลวันเดียว = อัดในแถวเดียวเป็นบรรทัดย่อย (lines).

โครงสร้างใหม่ ctx['fuel_lines_by_job']: dict[job_id -> list[line]]
  anchor (แถววันเติมจริง) -> [ {liter, amount, grade, excluded}, ... ] (>=1)
  job อื่นที่ถูกดูดเข้า group -> []  (merged: เว้นช่อง)
  job ที่ไม่มีบิล group -> ไม่อยู่ใน dict (template fallback r.fuel_*)
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
from services.payroll_slip import build_payroll_slip_context, slip_route_remark


@pytest.fixture()
def db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    yield


def _pr():
    return PayRun(site_code="LCB", pay_cycle_tag="2026-06",
                  period_start=date(2026, 5, 16), period_end=date(2026, 6, 15))


def test_misdated_fuel_anchors_to_work_date_equal_txn_date(db):
    """บิลเติมจริง 10/6 แต่ถูกคีย์ผูกกับงาน 11/6 → ต้องโชว์ใต้แถว 10/6 (วันเติมจริง),
    แถว 11/6 เว้นช่องน้ำมัน. (Case A: 10/6 มีงานอยู่แล้ว)"""
    with Session(engine) as s:
        emp = Employee(code="D-FD-1", full_name="ทดสอบ เลื่อนวัน",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        dj10 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 10),
                        plate_no_raw="ZZ-FD-1", fuel_liter=60, fuel_amount=2161.2)
        dj11 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 11),
                        plate_no_raw="ZZ-FD-1", fuel_liter=30, fuel_amount=1074.6)
        s.add(dj10); s.add(dj11); s.flush()
        # บิลของ dj10 เติมจริง 10/6 (ตรงวัน)
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 10),
                      plate_no_raw="ZZ-FD-1", liter=60, amount=2161.2, daily_job_id=dj10.id,
                      fuel_grade="B7"))
        # บิลที่ "เติมจริง 10/6" แต่คนคีย์ผูกกับงาน dj11 (work_date 11/6)
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 10),
                      plate_no_raw="ZZ-FD-1", liter=30, amount=1074.6, daily_job_id=dj11.id,
                      fuel_grade="B7"))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        lines = ctx["fuel_lines_by_job"]
        # dj10 (วันเติมจริง) = anchor : มี 2 บรรทัดย่อย รวม 90L/3235.8฿
        assert dj10.id in lines
        anc = lines[dj10.id]
        assert isinstance(anc, list) and len(anc) == 2
        assert abs(sum(l["liter"] for l in anc) - 90) < 0.01
        assert abs(sum(l["amount"] for l in anc) - 3235.8) < 0.01
        # dj11 = merged (เว้นช่อง)
        assert dj11.id in lines and lines[dj11.id] == []


def test_single_fill_same_date_not_in_map(db):
    """เติมวันเดียว 1 บิล ตรงวัน (txn==work) → ไม่อยู่ใน map (โชว์ปกติจาก r.fuel_*)."""
    with Session(engine) as s:
        emp = Employee(code="D-FD-2", full_name="ทดสอบ ปกติ",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        dj = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 3),
                      plate_no_raw="ZZ-FD-2", fuel_liter=40, fuel_amount=1628.8)
        s.add(dj); s.flush()
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 3),
                      plate_no_raw="ZZ-FD-2", liter=40, amount=1628.8, daily_job_id=dj.id,
                      fuel_grade="B7"))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        assert dj.id not in ctx["fuel_lines_by_job"]


def test_b7_b20_same_fill_date_merged_to_lines(db):
    """B7+B20 เติมครั้งเดียว (txn_date เดียว) คีย์คนละ DailyJob → รวมเป็นบรรทัดย่อยที่ anchor."""
    with Session(engine) as s:
        emp = Employee(code="D-FD-3", full_name="ทดสอบ บีเจ็ดยี่สิบ",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        dj1 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 1),
                       plate_no_raw="ZZ-FD-3", fuel_liter=36, fuel_amount=1494.7)
        dj2 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 2),
                       plate_no_raw="ZZ-FD-3", fuel_liter=50, fuel_amount=1801.0)
        s.add(dj1); s.add(dj2); s.flush()
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 1),
                      plate_no_raw="ZZ-FD-3", liter=36, amount=1494.7, daily_job_id=dj1.id, fuel_grade="B7"))
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 1),
                      plate_no_raw="ZZ-FD-3", liter=50, amount=1801.0, daily_job_id=dj2.id, fuel_grade="B20"))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        lines = ctx["fuel_lines_by_job"]
        # dj1 (บรรทัดบน, work_date 1/6 == txn_date) = anchor 2 บรรทัด, เกรด B7+B20
        assert dj1.id in lines and len(lines[dj1.id]) == 2
        assert {l["grade"] for l in lines[dj1.id]} == {"B7", "B20"}
        assert dj2.id in lines and lines[dj2.id] == []


def test_excluded_flag_per_bill(db):
    """ป้าย 'ไม่หัก' ต้องตามใบ (FuelTxn.exclude_from_driver) ไม่ใช่ตาม host row."""
    with Session(engine) as s:
        emp = Employee(code="D-FD-4", full_name="ทดสอบ ไม่หัก",
                       home_site_code="LCB", pay_mode="lcb_mao")
        s.add(emp); s.flush()
        dj9 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 9),
                       plate_no_raw="ZZ-FD-4", fuel_liter=100, fuel_amount=3920.0)
        dj10 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 10),
                        plate_no_raw="ZZ-FD-4", fuel_liter=50, fuel_amount=1801.0)
        s.add(dj9); s.add(dj10); s.flush()
        # บิลถังแรกไม่หัก เติมจริง 9/6 (ตรง dj9)
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 9),
                      plate_no_raw="ZZ-FD-4", liter=100, amount=3920.0, daily_job_id=dj9.id,
                      fuel_grade="B20", exclude_from_driver=True))
        # บิลปกติ เติมจริง 9/6 แต่ผูกกับงาน dj10 (10/6)
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 9),
                      plate_no_raw="ZZ-FD-4", liter=50, amount=1801.0, daily_job_id=dj10.id,
                      fuel_grade="B20", exclude_from_driver=False))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_mao"))
        lines = ctx["fuel_lines_by_job"]
        anc = lines[dj9.id]
        # 2 บรรทัด: ใบ 100L excluded=True, ใบ 50L excluded=False
        by_amt = {round(l["amount"]): l["excluded"] for l in anc}
        assert by_amt[3920] is True
        assert by_amt[1801] is False


def test_lines_total_reconciles_with_footer(db):
    """ผลรวมบรรทัดย่อยที่โชว์ + บรรทัด fallback = Σ DailyJob.fuel_amount (ไม่รั่ว/ไม่ซ้ำ)."""
    with Session(engine) as s:
        emp = Employee(code="D-FD-5", full_name="ทดสอบ ผลรวม",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        d1 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 5),
                      plate_no_raw="ZZ-FD-5", fuel_liter=20, fuel_amount=830.4)
        d2 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 6),
                      plate_no_raw="ZZ-FD-5", fuel_liter=30, fuel_amount=1074.6)  # บิลเติมจริง 5/6
        d3 = DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 8),
                      plate_no_raw="ZZ-FD-5", fuel_liter=40, fuel_amount=1628.8)  # เติมตรงวัน
        s.add(d1); s.add(d2); s.add(d3); s.flush()
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 5),
                      plate_no_raw="ZZ-FD-5", liter=20, amount=830.4, daily_job_id=d1.id, fuel_grade="B7"))
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 5),
                      plate_no_raw="ZZ-FD-5", liter=30, amount=1074.6, daily_job_id=d2.id, fuel_grade="B7"))
        s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 8),
                      plate_no_raw="ZZ-FD-5", liter=40, amount=1628.8, daily_job_id=d3.id, fuel_grade="B7"))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        lines = ctx["fuel_lines_by_job"]; djs = ctx["daily_jobs"]
        true_total = sum((d.fuel_amount or 0) for d in djs)
        disp = 0.0
        for d in djs:
            if d.id in lines:
                disp += sum(l["amount"] for l in lines[d.id])  # [] → 0
            else:
                disp += d.fuel_amount or 0
        assert abs(true_total - disp) < 0.01, f"{true_total} != {disp}"


def test_trip_count_excludes_idle_leave_fuelonly(db):
    """หัวสลิป 'X เที่ยว' = นับเฉพาะเที่ยววิ่งจริง (มี route/ค่าเที่ยว/รายได้),
    ตัด รถจอด / ลา / วันเติมน้ำมันล้วน ออก. วันเดียว 2 เที่ยว = นับ 2."""
    with Session(engine) as s:
        emp = Employee(code="D-TC-1", full_name="ทดสอบ นับเที่ยว",
                       home_site_code="LCB", pay_mode="lcb_trip")
        s.add(emp); s.flush()
        # 2 เที่ยวจริงวันเดียว (1/6)
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 1),
                       destination="OM", trip_fee_driver=500))
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 1),
                       destination="KCD", trip_fee_driver=300))
        # เที่ยวจริง (2/6)
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 2),
                       destination="TICS", revenue_customer=2000))
        # รถจอด (ไม่มี route/fee) — ไม่นับ
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 3),
                       status_code="รถจอด"))
        # ลา (มี destination แต่ leave) — ไม่นับ
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 4),
                       destination="ลาหยุด", leave_status="leave"))
        # วันเติมน้ำมันล้วน (มีน้ำมัน ไม่มีงาน) — ไม่นับ
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 5),
                       fuel_liter=40, fuel_amount=1600))
        # ลา ที่บันทึกเป็น origin='ลา' (ไม่มี leave_status) + status "ลา / ไม่พร้อม" — ไม่นับ
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 6),
                       origin="ลา", status_code="ลา / ไม่พร้อม", remark="tel=091-774-1369"))
        # รถจอด ที่มี tel= ใน remark — ไม่นับ
        s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 7),
                       status_code="รถจอด", remark="tel=0"))
        s.flush()
        ctx = build_payroll_slip_context(s, _pr(), emp, PayRunItem(pay_mode="lcb_trip"))
        # 3 เที่ยวจริง (2 วัน 1/6 + 1 วัน 2/6); ตัด รถจอด/ลา(leave+origin'ลา')/เติมน้ำมัน/tel
        assert ctx["trip_count"] == 3, ctx["trip_count"]


def test_route_remark_strips_tel(db):
    """ช่องส่งสินค้า: ไม่โชว์ tel=... (เลขโทรเทาๆ ไม่เกี่ยวคนขับ); คงข้อความ remark อื่น."""
    class R:
        def __init__(self, remark): self.remark = remark
    assert slip_route_remark(R("tel=091-774-1369")) == ""
    assert slip_route_remark(R("tel=0")) == ""
    assert slip_route_remark(R("ค้างคืน || tel=0")) == "ค้างคืน"
    assert slip_route_remark(R("ค้างคืน")) == "ค้างคืน"
    assert slip_route_remark(R("[งานยกเลิก] เดิม 1200")) == ""  # internal ยังตัด
