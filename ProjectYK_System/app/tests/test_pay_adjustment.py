"""C4 ค่าเที่ยวตกหล่น/จ่ายตามหลัง (PayAdjustment v36):
แก้ค่าเที่ยวของแถวในรอบ finalized (ห้าม recompute — สดย่อยหาย) → เก็บ Δ ไว้
จ่ายเพิ่ม/หักคืนรอบถัดไปอัตโนมัติ. เกณฑ์สเปค: จ่ายเพิ่ม/หักคืน/ไม่มี pending =
engine เดิมเป๊ะ + recompute ไม่ double + ไม่ดูดเข้ารอบเก่า + grid-save สร้างอัตโนมัติ.
"""
import os, tempfile
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
from models import AppUser, DailyJob, Employee, PayAdjustment, PayRun, PayRunItem
from services.payroll import compute_pay_run

EMP = 97


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=EMP, code="D97", full_name="นาย ทดสอบ ตกหล่น",
                       pay_mode="lcb_trip", home_site_code="LCB", status="active",
                       base_salary=9240, care_allowance=3000))
        # แถวเดลี่ในรอบเก่า (จะ finalize) + รอบใหม่ (draft)
        s.add(DailyJob(id=501, site_code="LCB", driver_id=EMP,
                       work_date=date(2026, 5, 20), status_code="KAO",
                       plate_no_raw="70-1111", revenue_customer=5000,
                       trip_fee_driver=3000))
        s.add(DailyJob(id=502, site_code="LCB", driver_id=EMP,
                       work_date=date(2026, 7, 1), status_code="KAO",
                       plate_no_raw="70-1111", revenue_customer=5000,
                       trip_fee_driver=3000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15),
                     status="finalized", notes="รอบปิดแล้ว"))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-07",
                     period_start=date(2026, 6, 16), period_end=date(2026, 7, 15),
                     status="draft"))
        # รอบเก่ากว่ารอบต้นเหตุ ยัง draft ค้าง — pending ต้องไม่ถูกดูดเข้ารอบนี้
        s.add(PayRun(id=3, site_code="LCB", pay_cycle_tag="2026-05",
                     period_start=date(2026, 4, 16), period_end=date(2026, 5, 15),
                     status="draft"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _item(run_id: int) -> PayRunItem:
    with Session(engine) as s:
        return s.exec(select(PayRunItem).where(
            PayRunItem.pay_run_id == run_id,
            PayRunItem.employee_id == EMP)).one()


def _compute(run_id: int):
    with Session(engine) as s:
        compute_pay_run(s, s.get(PayRun, run_id), recompute=True)


def test_no_pending_engine_identical(client):
    _compute(2)
    base = _item(2)
    _compute(2)
    again = _item(2)
    assert again.net_pay == base.net_pay
    assert again.other_income == base.other_income
    assert "ตกหล่น" not in (again.note or "")


def test_positive_adjustment_paid_next_run_no_double(client):
    _compute(2)
    base = _item(2)
    with Session(engine) as s:
        s.add(PayAdjustment(employee_id=EMP, site_code="LCB", source_run_id=1,
                            daily_job_id=501, amount=500.0,
                            reason="แก้ค่าเที่ยว 20/05 หลังปิดรอบ"))
        s.commit()
    _compute(2)
    it = _item(2)
    assert it.other_income == round(base.other_income + 500, 2)
    assert it.gross_total == round(base.gross_total + 500, 2)
    assert it.net_pay == round(base.net_pay + 500, 2)
    assert "ตกหล่นจากรอบก่อน" in (it.note or "")
    with Session(engine) as s:
        a = s.exec(select(PayAdjustment)).one()
        assert a.status == "applied" and a.applied_run_id == 2
    # recompute รอบเดิมซ้ำ — ต้องได้เท่าเดิม (ดูดชุด applied ของรอบนี้กลับมา ไม่ double)
    _compute(2)
    it2 = _item(2)
    assert it2.net_pay == it.net_pay and it2.other_income == it.other_income


def test_negative_clawback_deducted(client):
    _compute(2)
    base = _item(2)
    with Session(engine) as s:
        s.add(PayAdjustment(employee_id=EMP, site_code="LCB", source_run_id=1,
                            amount=-300.0, reason="ราคาจริงต่ำกว่าที่จ่าย — หักคืน"))
        s.commit()
    _compute(2)
    it = _item(2)
    assert it.other_deduction == round(base.other_deduction + 300, 2)
    assert it.net_pay == round(base.net_pay - 300, 2)


def test_pending_not_pulled_into_older_run(client):
    with Session(engine) as s:
        s.add(PayAdjustment(employee_id=EMP, site_code="LCB", source_run_id=1,
                            amount=500.0, reason="x"))
        # ให้รอบเก่า (run3) มีเดลี่ให้คำนวณ
        s.add(DailyJob(site_code="LCB", driver_id=EMP, work_date=date(2026, 5, 1),
                       status_code="KAO", trip_fee_driver=1000))
        s.commit()
    _compute(3)   # รอบจบ 15/5 < รอบต้นเหตุจบ 15/6 → ห้ามดูด
    with Session(engine) as s:
        a = s.exec(select(PayAdjustment)).one()
        assert a.status == "pending" and a.applied_run_id is None
    assert "ตกหล่น" not in (_item(3).note or "")


def test_grid_save_creates_adjustment_only_for_finalized_cycle(client):
    # แก้ค่าเที่ยวแถวในรอบ finalized (20/5 ∈ run1) 3000→3500 → Δ+500 pending
    r = client.post("/api/daily/grid-save", json={"rows": [
        {"id": 501, "trip_fee_driver": "3500"},
        {"id": 502, "trip_fee_driver": "3200"},   # อยู่รอบ draft → ไม่ตั้งตกหล่น
    ]})
    out = r.json()
    assert out["ok"] and out["updated"] == 2 and out["adjustments"] == 1
    with Session(engine) as s:
        adjs = s.exec(select(PayAdjustment)).all()
        assert len(adjs) == 1
        a = adjs[0]
        assert a.amount == 500.0 and a.status == "pending"
        assert a.source_run_id == 1 and a.daily_job_id == 501
        assert "หลังปิดรอบ 2026-06" in a.reason


def test_cancel_pending_blocks_apply(client):
    with Session(engine) as s:
        s.add(PayAdjustment(id=9, employee_id=EMP, site_code="LCB",
                            source_run_id=1, amount=500.0, reason="x"))
        s.commit()
    _compute(2)
    base_with = _item(2).net_pay          # applied +500 ไปแล้ว
    # ยกเลิกตัวที่ applied แล้ว → 409
    r = client.post("/payroll/adjustments/9/cancel", data={"run_id": "2"},
                    follow_redirects=False)
    assert r.status_code == 409
    # สร้างใหม่อีกตัวแล้วยกเลิกก่อนคำนวณ → ต้องไม่ถูกดูด
    with Session(engine) as s:
        s.add(PayAdjustment(id=10, employee_id=EMP, site_code="LCB",
                            source_run_id=1, amount=999.0, reason="y"))
        s.commit()
    r = client.post("/payroll/adjustments/10/cancel", data={"run_id": "2"},
                    follow_redirects=False)
    assert r.status_code == 303
    _compute(2)
    assert _item(2).net_pay == base_with  # ตัวที่ยกเลิกไม่ถูกบวก


def test_payroll_page_shows_adjustments(client):
    with Session(engine) as s:
        s.add(PayAdjustment(employee_id=EMP, site_code="LCB", source_run_id=1,
                            amount=500.0, reason="แก้ค่าเที่ยว 20/05"))
        s.commit()
    b = client.get("/payroll/2").text
    assert "ค่าเที่ยวตกหล่นรอรอบถัดไป" in b
    _compute(2)
    b = client.get("/payroll/2").text
    assert "ดูดเข้ารอบนี้แล้ว" in b and "+500.00" in b
