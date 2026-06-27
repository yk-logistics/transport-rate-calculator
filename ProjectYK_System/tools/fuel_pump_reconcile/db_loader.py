"""Load system fuel rows (FuelTxn) for one cycle, resolving driver name and
pay_mode from the matching PayRun item. Read-only. See spec
docs/superpowers/specs/2026-06-27-fuel-pump-reconcile-design.md."""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Union

from models import SysFuel


def load_sys_fuel(
    db: Union[str, sqlite3.Connection],
    source_tag: str,
    start: date,
    end: date,
    site_code: str = "LCB",
    cycle_tag: str = "",
) -> list[SysFuel]:
    con = sqlite3.connect(db) if isinstance(db, str) else db
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # employee_id -> pay_mode for this cycle's pay run
    mode: dict[int, str] = {}
    pr = cur.execute(
        "SELECT id FROM payrun WHERE site_code=? AND pay_cycle_tag=?",
        (site_code, cycle_tag),
    ).fetchone()
    if pr:
        for row in cur.execute(
            "SELECT employee_id, pay_mode FROM payrunitem WHERE pay_run_id=?",
            (pr["id"],),
        ):
            mode[row["employee_id"]] = row["pay_mode"]

    rows: list[SysFuel] = []
    q = """
        SELECT f.txn_date AS d, f.plate_no_raw AS plate, f.driver_id AS did,
               f.liter AS liter, f.amount AS amount, e.full_name AS name
        FROM fueltxn f LEFT JOIN employee e ON f.driver_id = e.id
        WHERE f.source = ? AND f.txn_date >= ? AND f.txn_date <= ?
    """
    for r in cur.execute(q, (source_tag, start.isoformat(), end.isoformat())):
        rows.append(SysFuel(
            date=date.fromisoformat(str(r["d"])[:10]),
            plate=(r["plate"] or "").strip(),
            liter=r["liter"] or 0.0,
            amount=r["amount"] or 0.0,
            driver_id=r["did"],
            driver_name=r["name"] or "",
            pay_mode=mode.get(r["did"], ""),
        ))
    return rows
