"""
Preview re-compute of LCB payrun 2026-06 (มิ.ย., cycle 16/5-15/6) — READ-ONLY.

มิ.ย. ยังไม่มี แบ็งค์.pdf (ยังไม่จ่าย) → ground truth = input ดิบ.
เทียบ: draft ปัจจุบันใน DB  vs  recompute สดด้วย engine ปัจจุบัน.
ถ้าต่าง = draft stale (คำนวณก่อนงานล่าสุดวันนี้: fuel-exclude / bank / idle-days).

Run (from repo root):
  python ProjectYK_System/tools/preview_lcb_jun_recompute.py
"""
from __future__ import annotations

import io
import sys
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
        eid: (gross, petty, fuel, net)
        for eid, gross, petty, fuel, net in con.execute(
            "select employee_id, gross_total, petty_cash_deduction, fuel_cost_self, net_pay "
            "from payrunitem where pay_run_id=?",
            (PAY_RUN_ID,),
        )
    }
    con.close()

    print(f"LCB payrun {TAG} (cycle {START}..{END}) — preview recompute (READ-ONLY)")
    print("=" * 110)
    print(f"{'driver':22} {'mode':9} {'draft_net':>11} {'recomp_net':>11} {'Δnet':>9} "
          f"{'r_gross':>9} {'r_petty':>8} {'r_fuel':>8} {'note'}")
    print("-" * 110)

    with Session(engine) as session:
        emps = session.exec(
            select(Employee).where(Employee.id.in_(list(draft.keys())))
        ).all()
        emps.sort(key=lambda e: e.full_name or "")

        tot_draft = tot_recomp = 0.0
        big_moves = []
        for e in emps:
            calc = calc_one_employee(session, e, START, END, TAG, pay_run_id=PAY_RUN_ID)
            d_gross, d_petty, d_fuel, d_net = draft.get(e.id, (0, 0, 0, 0))
            dnet = calc.net_pay - (d_net or 0)
            tot_draft += d_net or 0
            tot_recomp += calc.net_pay
            nm = (e.full_name or "").replace("นาย", "").replace("นาง", "").strip()
            note = (calc.note or "")[:24]
            flag = ""
            if abs(dnet) >= 1:
                flag = "<-- changed"
                big_moves.append((nm, d_net or 0, calc.net_pay, dnet))
            print(f"{nm[:22]:22} {(e.pay_mode or '')[:9]:9} {d_net or 0:11,.0f} "
                  f"{calc.net_pay:11,.0f} {dnet:9,.0f} {calc.gross_total:9,.0f} "
                  f"{calc.petty_cash_deduction:8,.0f} {calc.fuel_cost_self:8,.0f} {note} {flag}")

    print("-" * 110)
    print(f"{'TOTAL':22} {'':9} {tot_draft:11,.0f} {tot_recomp:11,.0f} {tot_recomp-tot_draft:9,.0f}")
    print(f"\ndraft total net = {tot_draft:,.0f}")
    print(f"recompute total net = {tot_recomp:,.0f}")
    print(f"difference = {tot_recomp-tot_draft:,.0f}")
    if big_moves:
        print(f"\n{len(big_moves)} drivers changed on recompute (draft was stale):")
        for nm, old, new, d in sorted(big_moves, key=lambda x: -abs(x[3])):
            print(f"  {nm[:24]:24} {old:11,.0f} -> {new:11,.0f}  ({d:+,.0f})")
    print("\nREAD-ONLY: nothing written to DB.")


if __name__ == "__main__":
    main()
