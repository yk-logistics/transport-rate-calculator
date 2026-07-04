# -*- coding: utf-8 -*-
"""กติกาเงินชุด 4: คนเข้า-ออกงานกลางรอบ (effective window + implicit absent)
+ การหักสดย่อยตาม cycle tag — จุดที่เคยปวดจริงตอน onboard/ลาออกกลางรอบ.

กติกา (จาก docstring engine + นโยบายโอ):
- start_date คนใหม่ → วันก่อนเริ่มงานเป็น "ยังไม่เริ่ม" หักฐาน ไม่ใช่ absent
- ไม่มี start_date → ใช้วันแรกที่มีเดลี่ในรอบแทน
- คนลาออก (end_date) → ตัดท้ายเหลือวันสุดท้ายที่มีเดลี่จริง (วันยื่นใบลาออกมักไม่ใช่วันทำงาน)
- วันใน window ที่ไม่มีแถวเดลี่เลย = implicit absent ("ชื่อใครไม่มี ณ วันนั้น หักออกเลย")
- สดย่อย: หักเฉพาะ flag deduct_from_driver + status pending + tag ตรง; direction=in = ลดยอดหัก
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

from db_config import engine
import main as appmod
from models import DailyJob, Employee, PettyCashTxn
from services.payroll import (
    _count_work_days,
    _resolve_effective_window,
    _sum_petty_cash_deduction,
)

P_START, P_END = date(2026, 6, 16), date(2026, 7, 15)   # รอบ LCB 30 วัน


@pytest.fixture()
def db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    yield


def _emp(s, eid, **kw):
    s.add(Employee(id=eid, code=f"T{eid}", full_name=f"ทดสอบ {eid}",
                   pay_mode="lcb_trip", home_site_code="LCB", status="active", **kw))


def test_window_new_hire_trims_start(db):
    with Session(engine) as s:
        _emp(s, 501, start_date=date(2026, 7, 1))
        s.commit()
        assert _resolve_effective_window(s, 501, P_START, P_END) == (date(2026, 7, 1), P_END)


def test_window_no_start_date_uses_first_daily(db):
    with Session(engine) as s:
        _emp(s, 502)
        s.add(DailyJob(site_code="LCB", driver_id=502, work_date=date(2026, 6, 20),
                       status_code="CY", revenue_customer=5000.0, trip_fee_driver=300.0))
        s.commit()
        assert _resolve_effective_window(s, 502, P_START, P_END) == (date(2026, 6, 20), P_END)


def test_window_resignation_trims_to_last_real_workday(db):
    with Session(engine) as s:
        _emp(s, 503, start_date=date(2026, 1, 1), end_date=date(2026, 7, 10))
        # ทำงานจริงถึง 5 ก.ค. (10 ก.ค. คือวันยื่นใบลาออก — ไม่มีเดลี่)
        for d in (date(2026, 6, 20), date(2026, 7, 5)):
            s.add(DailyJob(site_code="LCB", driver_id=503, work_date=d,
                           status_code="CY", revenue_customer=5000.0, trip_fee_driver=300.0))
        s.commit()
        assert _resolve_effective_window(s, 503, P_START, P_END) == \
            (P_START, date(2026, 7, 5))


def test_implicit_absent_counted(db):
    """ทำงานแค่ 2 วันจาก window 30 วัน ไม่มีใบลา → วันที่เหลือ = ขาดเงียบ (หักฐาน)."""
    with Session(engine) as s:
        _emp(s, 504, start_date=P_START)
        for d in (date(2026, 6, 16), date(2026, 6, 17)):
            s.add(DailyJob(site_code="LCB", driver_id=504, work_date=d,
                           status_code="CY", revenue_customer=5000.0, trip_fee_driver=300.0))
        s.commit()
        days = _count_work_days(s, 504, P_START, P_END, "LCB")
    assert days["worked"] == 2.0
    assert days["absent"] == 28.0        # 30 − 2 = ขาดเงียบ ("ไม่มีชื่อ=หัก")
    assert days["company_no_work"] == 0.0


def test_no_daily_rows_no_implicit_absent(db):
    """ไม่มีเดลี่เลยทั้งรอบ (เช่น office ที่ไม่คีย์เดลี่) → ห้ามนับขาดเงียบ."""
    with Session(engine) as s:
        _emp(s, 505, start_date=P_START)
        s.commit()
        days = _count_work_days(s, 505, P_START, P_END, "LCB")
    assert days == {"worked": 0.0, "leave": 0.0, "absent": 0.0, "company_no_work": 0.0}


def test_petty_deduction_rules(db):
    """Data contract จริง (ตรวจ prod 5 ก.ค.: 0 แถวผิด): แถวที่ติ๊กหักจะมี deduct_amount
    ตั้งเสมอ (UI/import ตั้งให้) — deduct_amount เป็น float default 0.0 ไม่ใช่ None
    ดังนั้น engine ใช้ deduct_amount เท่านั้น (แถวติ๊กแต่ยอด 0 = หัก 0)."""
    with Session(engine) as s:
        _emp(s, 506)
        rows = [
            # หักเต็ม: flag + pending + tag ตรง
            dict(amount=800.0, deduct_amount=800.0, deduct_from_driver=True,
                 deduction_status="pending"),
            # หักบางส่วน
            dict(amount=1000.0, deduct_amount=400.0, deduct_from_driver=True,
                 deduction_status="pending"),
            # ไม่ flag → ไม่หัก
            dict(amount=999.0, deduct_from_driver=False, deduction_status="pending"),
            # หักไปแล้ว (ไม่ pending) → ไม่หักซ้ำ
            dict(amount=555.0, deduct_from_driver=True, deduction_status="applied"),
            # คนขับคืนเงินเข้า (direction=in) → ลดยอดหัก
            dict(amount=300.0, deduct_amount=300.0, deduct_from_driver=True,
                 deduction_status="pending", direction="in"),
            # tag คนละรอบ → ไม่เกี่ยว
            dict(amount=777.0, deduct_from_driver=True, deduction_status="pending",
                 tag="2026-08"),
        ]
        for r in rows:
            tag = r.pop("tag", "2026-07")
            s.add(PettyCashTxn(site_code="LCB", txn_date=date(2026, 6, 20),
                               driver_id=506, direction=r.pop("direction", "out"),
                               category="repair", pay_cycle_tag=tag, **r))
        s.commit()
        total = _sum_petty_cash_deduction(s, 506, "2026-07", "LCB")
    # 800 + 400 − 300 = 900
    assert total == 900.0
