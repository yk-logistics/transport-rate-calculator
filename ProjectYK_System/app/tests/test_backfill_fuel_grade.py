# ProjectYK_System/app/tests/test_backfill_fuel_grade.py
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import pytest
from sqlmodel import SQLModel, Session, delete
from db_config import engine
from models import FuelTxn
from backfill_fuel_grade import plan_backfill, apply_backfill


@pytest.fixture(autouse=True, scope="module")
def _ensure_schema():
    SQLModel.metadata.create_all(engine)


def _mk(s, plate, d, liter, amount, grade=""):
    r = FuelTxn(txn_date=d, site_code="LCB", plate_no_raw=plate,
                liter=liter, amount=amount, fuel_grade=grade, source="test_bf")
    s.add(r); s.flush()
    return r.id


def test_backfill_splits_same_day_pair():
    with Session(engine) as s:
        d = date(2026, 6, 20)
        cheap = _mk(s, "ZZ-BF-1", d, 50, 1760)   # 35.2 -> B20
        pricey = _mk(s, "ZZ-BF-1", d, 50, 2060)  # 41.2 -> B7
        s.flush()
        plan = plan_backfill(s)
        pmap = dict(plan)
        assert pmap[cheap] == "B20"
        assert pmap[pricey] == "B7"
        s.exec(delete(FuelTxn).where(FuelTxn.source == "test_bf"))
        s.commit()


def test_backfill_skips_already_set():
    with Session(engine) as s:
        d = date(2026, 6, 21)
        already = _mk(s, "ZZ-BF-2", d, 50, 1760, grade="B7")  # ตั้งไว้แล้ว
        s.flush()
        plan = plan_backfill(s)
        assert already not in dict(plan)
        s.exec(delete(FuelTxn).where(FuelTxn.source == "test_bf"))
        s.commit()


def test_apply_sets_only_grade_not_amount():
    with Session(engine) as s:
        d = date(2026, 6, 22)
        rid = _mk(s, "ZZ-BF-3", d, 50, 1760)
        s.flush()
        before_amt = s.get(FuelTxn, rid).amount
        n = apply_backfill(s, [(rid, "B20")])
        s.commit()
        got = s.get(FuelTxn, rid)
        assert n == 1
        assert got.fuel_grade == "B20"
        assert got.amount == before_amt  # เงินไม่ขยับ
        s.exec(delete(FuelTxn).where(FuelTxn.source == "test_bf"))
        s.commit()
