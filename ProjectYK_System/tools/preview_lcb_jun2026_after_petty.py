"""Preview LCB payrun 2026-06 AFTER importing เงินเบิก/หัก — READ-ONLY, writes nothing.

Recomputes each of the 18 drivers in payrun draft #2 with the engine (which now
sees the freshly-imported pettycashtxn rows), and shows net before vs after the
deduction so โอ can sanity-check before finalize.
"""
from __future__ import annotations
import io, sys
from datetime import date
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR  # noqa: E402
sys.path.insert(0, str(APP_DIR))

import sqlite3  # noqa: E402
from sqlmodel import Session, create_engine, select  # noqa: E402
from models import Employee  # noqa: E402
from services.payroll import calc_one_employee  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
PAY_RUN_ID = 2
TAG = "2026-06"
START = date(2026, 5, 16)
END = date(2026, 6, 15)


def main():
    con = sqlite3.connect(DB_PATH)
    draft = {
        eid: net
        for eid, net in con.execute(
            "select employee_id, net_pay from payrunitem where pay_run_id=?", (PAY_RUN_ID,)
        )
    }
    con.close()

    print(f"LCB payrun {TAG} — recompute หลัง import เงินเบิก (READ-ONLY)")
    print("=" * 92)
    print(f"{'driver':22} {'mode':9} {'net_ก่อนหัก':>12} {'หักเบิก':>10} {'net_หลังหัก':>12}")
    print("-" * 92)
    tot_before = tot_petty = tot_after = 0.0
    with Session(engine) as session:
        emps = session.exec(select(Employee).where(Employee.id.in_(list(draft.keys())))).all()
        emps.sort(key=lambda e: -(draft.get(e.id, 0) or 0))
        for e in emps:
            calc = calc_one_employee(session, e, START, END, TAG, pay_run_id=PAY_RUN_ID)
            before = draft.get(e.id, 0.0) or 0.0
            petty = calc.petty_cash_deduction
            after = calc.net_pay
            nm = (e.full_name or "").replace("นาย", "").strip()
            tot_before += before; tot_petty += petty; tot_after += after
            print(f"{nm[:22]:22} {(e.pay_mode or '')[:9]:9} {before:12,.0f} {petty:10,.0f} {after:12,.2f}")
    print("-" * 92)
    print(f"{'TOTAL':22} {'':9} {tot_before:12,.0f} {tot_petty:10,.0f} {tot_after:12,.2f}")


if __name__ == "__main__":
    main()
