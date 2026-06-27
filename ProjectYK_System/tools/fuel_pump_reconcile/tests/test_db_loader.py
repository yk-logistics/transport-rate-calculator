"""Tests for db_loader against a tiny in-memory sqlite mirroring the real schema."""
from __future__ import annotations

import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db_loader import load_sys_fuel  # noqa: E402


def _make_db():
    con = sqlite3.connect(":memory:")
    con.executescript(
        """
        CREATE TABLE employee (id INTEGER PRIMARY KEY, full_name TEXT);
        CREATE TABLE fueltxn (
            id INTEGER PRIMARY KEY, source TEXT, txn_date TEXT,
            plate_no_raw TEXT, driver_id INTEGER, liter REAL, amount REAL);
        CREATE TABLE payrun (id INTEGER PRIMARY KEY, site_code TEXT, pay_cycle_tag TEXT);
        CREATE TABLE payrunitem (
            id INTEGER PRIMARY KEY, pay_run_id INTEGER, employee_id INTEGER, pay_mode TEXT);
        INSERT INTO employee VALUES (101, 'นาย วราวุฒิ อาญาเมือง');
        INSERT INTO payrun VALUES (2, 'LCB', '2026-06');
        INSERT INTO payrunitem VALUES (1, 2, 101, 'lcb_mao');
        INSERT INTO fueltxn VALUES (1, 'lcb_may-jun2026', '2026-06-10', '71-8681', 101, 50.0, 2066.0);
        INSERT INTO fueltxn VALUES (2, 'lcb_may-jun2026', '2026-05-10', '71-8681', 101, 20.0, 800.0);
        INSERT INTO fueltxn VALUES (3, 'other_src',       '2026-06-10', '71-8681', 101, 50.0, 2066.0);
        """
    )
    con.commit()
    return con


def test_loads_only_source_and_cycle():
    con = _make_db()
    rows = load_sys_fuel(con, "lcb_may-jun2026", date(2026, 5, 16), date(2026, 6, 15),
                         site_code="LCB", cycle_tag="2026-06")
    # row 2 is out of cycle (May 10), row 3 is different source -> only row 1
    assert len(rows) == 1
    r = rows[0]
    assert r.plate == "71-8681"
    assert r.amount == 2066.0


def test_resolves_driver_and_mode():
    con = _make_db()
    rows = load_sys_fuel(con, "lcb_may-jun2026", date(2026, 5, 16), date(2026, 6, 15),
                         site_code="LCB", cycle_tag="2026-06")
    r = rows[0]
    assert r.driver_id == 101
    assert "วราวุฒิ" in r.driver_name
    assert r.pay_mode == "lcb_mao"
