"""Fuel exclude-from-driver: per-bill flag that skips a FuelTxn from the
driver's fuel deduction (น้ำมันก่อนเริ่มวิ่ง / ถังเต็มแรก = ไม่หัก).

Engine-level unit tests against the two fuel-sum helpers. Default flag=False
must leave every existing number unchanged (regression-safe).
"""
from datetime import date

import pytest
from sqlmodel import SQLModel, Session, create_engine

from models import FuelTxn
from services.payroll import _sum_fuel_cost, _sum_fuel_cost_for_dates


@pytest.fixture()
def session():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s


def _fuel(s, emp_id, d, amount, exclude=False):
    s.add(FuelTxn(
        site_code="LCB", txn_date=d, driver_id=emp_id,
        amount=amount, liter=amount / 40.0, exclude_from_driver=exclude,
    ))


START, END = date(2026, 5, 16), date(2026, 6, 15)


def test_sum_fuel_cost_skips_excluded_bills(session):
    # 3 bills: two normal, one flagged not-to-deduct.
    _fuel(session, 100, date(2026, 5, 16), 2488.20, exclude=True)
    _fuel(session, 100, date(2026, 5, 19), 5800.00, exclude=True)
    _fuel(session, 100, date(2026, 5, 22), 1266.60)
    session.commit()
    total = _sum_fuel_cost(session, 100, START, END, site_code="LCB")
    assert total == 1266.60  # only the un-flagged bill


def test_sum_fuel_cost_default_counts_everything(session):
    # Regression: with no flag set, all bills count (existing behaviour).
    _fuel(session, 100, date(2026, 5, 16), 2488.20)
    _fuel(session, 100, date(2026, 5, 19), 5800.00)
    _fuel(session, 100, date(2026, 5, 22), 1266.60)
    session.commit()
    total = _sum_fuel_cost(session, 100, START, END, site_code="LCB")
    assert total == round(2488.20 + 5800.00 + 1266.60, 2)


def test_sum_fuel_cost_for_dates_skips_excluded(session):
    # lcb_mixed path: only sums given dates, and must also skip flagged bills.
    _fuel(session, 86, date(2026, 6, 2), 3000.00, exclude=True)
    _fuel(session, 86, date(2026, 6, 5), 1500.00)
    _fuel(session, 86, date(2026, 6, 6), 999.00)  # date NOT in the set
    session.commit()
    dates = {date(2026, 6, 2), date(2026, 6, 5)}
    total = _sum_fuel_cost_for_dates(session, 86, dates, site_code="LCB")
    assert total == 1500.00  # 6/2 excluded by flag, 6/6 excluded by date
