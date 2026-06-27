"""Tests for the reconcile matcher — the core of the tool."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from matcher import reconcile, driver_impact  # noqa: E402
from models import FuelBill, SysFuel  # noqa: E402


def bill(d, plate, amt, liter=50.0):
    return FuelBill(date=date.fromisoformat(d), plate=plate, station="ทวีโชค",
                    ftype="Diesel B7", liter=liter, price=amt / liter, amount=amt)


def sys_(d, plate, amt, liter=50.0, did=1, name="วราวุฒิ", mode="lcb_mao"):
    return SysFuel(date=date.fromisoformat(d), plate=plate, liter=liter,
                   amount=amt, driver_id=did, driver_name=name, pay_mode=mode)


def test_exact_same_day_match():
    bills = [bill("2026-06-10", "71-8681", 2066.0)]
    sysf = [sys_("2026-06-10", "71-8681", 2066.0)]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    assert r.matched_pairs == 1
    assert r.pump_only == []
    assert r.system_only == []
    assert r.matched_pump_baht == 2066.0


def test_matches_within_drift():
    # pump dates 12th, system dates 13th (1-day shift) -> should match
    bills = [bill("2026-06-12", "71-8681", 2507.0)]
    sysf = [sys_("2026-06-13", "71-8681", 2507.0)]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    assert r.matched_pairs == 1
    assert r.pump_only == [] and r.system_only == []


def test_beyond_drift_is_unmatched():
    # 5-day gap > default drift 3 -> not matched
    bills = [bill("2026-06-01", "71-8681", 814.0)]
    sysf = [sys_("2026-06-08", "71-8681", 814.0)]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    assert r.matched_pairs == 0
    assert len(r.pump_only) == 1
    assert len(r.system_only) == 1


def test_pump_only_and_system_only():
    bills = [bill("2026-06-05", "71-9627", 1801.0)]      # pump has it
    sysf = [sys_("2026-06-05", "72-0419", 999.0)]        # system has a different one
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    assert r.matched_pairs == 0
    assert len(r.pump_only) == 1 and r.pump_only[0].plate == "71-9627"
    assert len(r.system_only) == 1 and r.system_only[0].plate == "72-0419"


def test_each_row_consumed_once():
    # two identical pump bills, one system row -> only one matches
    bills = [bill("2026-06-10", "71-8681", 826.0), bill("2026-06-10", "71-8681", 826.0)]
    sysf = [sys_("2026-06-10", "71-8681", 826.0)]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    assert r.matched_pairs == 1
    assert len(r.pump_only) == 1
    assert r.system_only == []


def test_nearest_date_wins():
    # one pump bill, two candidate system rows same amount -> closest date consumed
    bills = [bill("2026-06-10", "71-8681", 826.0)]
    sysf = [sys_("2026-06-08", "71-8681", 826.0), sys_("2026-06-11", "71-8681", 826.0)]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    assert r.matched_pairs == 1
    # the 11th (1 day away) should be consumed, the 8th (2 days) left over
    assert len(r.system_only) == 1
    assert r.system_only[0].date == date(2026, 6, 11) or r.system_only[0].date == date(2026, 6, 8)
    # closest is 11th -> it gets matched, 8th remains
    assert r.system_only[0].date == date(2026, 6, 8)


def test_driver_impact_aggregates_mao_only():
    # system has an extra 1000-baht fill for วราวุฒิ (mao) that pump lacks
    bills = []
    sysf = [sys_("2026-06-10", "71-8681", 1000.0, did=101, name="วราวุฒิ", mode="lcb_mao")]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    impact = driver_impact(r)
    # one mao driver, system_only 1000 -> sys_extra=1000, pump_extra=0, money≈1000*0.6
    assert 101 in impact
    row = impact[101]
    assert row["pay_mode"] == "lcb_mao"
    assert row["sys_only_baht"] == 1000.0
    assert row["pump_only_baht"] == 0.0
    assert abs(row["money_impact"] - 600.0) < 0.01


def test_driver_impact_excludes_trip_drivers():
    bills = []
    sysf = [sys_("2026-06-10", "71-6804", 1000.0, did=95, name="ชยุต", mode="lcb_trip")]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    impact = driver_impact(r)
    assert 95 not in impact  # trip driver = company pays fuel, no pay impact
