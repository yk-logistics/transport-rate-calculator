"""
Test payroll calculation for Jan-Mar 2026 cycles across all 3 sites.

Sheet-to-cycle-tag mapping (user labels sheet by payment month):
  AYU  JAN  →  tag 2026-01 (cycle 26 Dec - 25 Jan)
  AYU  FEB  →  tag 2026-02 (cycle 26 Jan - 25 Feb)
  AYU  MAR  →  tag 2026-03 (cycle 26 Feb - 25 Mar)
  BIGC JAN  →  tag 2025-12 (cycle Dec 2025, paid on Jan 1)
  BIGC FEB  →  tag 2026-01 (cycle Jan 2026, paid on Feb 1)
  BIGC MAR  →  tag 2026-02 (cycle Feb 2026, paid on Mar 1)
  LCB  JAN  →  tag 2025-12 (cycle 16 Nov - 15 Dec, paid "JAN"=Jan)
  LCB  FEB  →  tag 2026-02 (cycle 16 Jan - 15 Feb)
  LCB  MAR  →  tag 2026-03 (cycle 16 Feb - 15 Mar)
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select  # noqa: E402

import models  # noqa: E402
from models import PayRun, PayRunItem, Employee  # noqa: E402
from services.payroll import get_or_create_pay_run, compute_pay_run  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})


CYCLES_TO_RUN = [
    # (sheet_label, site, tag)
    ("BIGC JAN", "BIGC", "2025-12"),
    ("BIGC FEB", "BIGC", "2026-01"),
    ("BIGC MAR", "BIGC", "2026-02"),
    ("AYU JAN",  "AYU",  "2026-01"),
    ("AYU FEB",  "AYU",  "2026-02"),
    ("AYU MAR",  "AYU",  "2026-03"),
    ("LCB JAN",  "LCB",  "2025-12"),
    ("LCB FEB",  "LCB",  "2026-02"),
    ("LCB MAR",  "LCB",  "2026-03"),
]


def fmt_money(v: float) -> str:
    return f"{v:,.2f}" if v else "  -   "


def main():
    with Session(engine) as s:
        for label, site, tag in CYCLES_TO_RUN:
            print(f"\n{'=' * 70}")
            print(f"PAY RUN — {label}  (site={site}, tag={tag})")
            print("=" * 70)

            pr = get_or_create_pay_run(s, site, tag, notes=f"test Book2.xlsx — {label}")
            print(f"PayRun id={pr.id}  period={pr.period_start} .. {pr.period_end}  status={pr.status}")

            items = compute_pay_run(s, pr, recompute=True)
            print(f"Items computed: {len(items)}")

            # Pretty print
            if items:
                print(f"\n  {'Employee':<20} {'Mode':<14} {'Days':>5} {'Trip+Base':>12} {'FuelInc':>10} {'Gross':>12} "
                      f"{'Petty-':>10} {'SSO':>7} {'Other-':>10} {'NET':>12}")
                print(f"  {'-'*20} {'-'*14} {'-'*5} {'-'*12} {'-'*10} {'-'*12} {'-'*10} {'-'*7} {'-'*10} {'-'*12}")

                # sort by net desc
                items_sorted = sorted(items, key=lambda x: x.net_pay or 0, reverse=True)
                for it in items_sorted:
                    emp = s.get(Employee, it.employee_id)
                    name = (emp.full_name or emp.nickname or f"ID{emp.id}")[:20] if emp else f"ID{it.employee_id}"
                    pay_base = (it.base_salary_earned or 0) + (it.care_allowance_earned or 0) + (it.trip_fee_total or 0)
                    fuel_inc = (it.fuel_rate_income or 0) + (it.fuel_share_income or 0)
                    print(f"  {name:<20} {it.pay_mode:<14} {it.days_worked:>5.0f} "
                          f"{fmt_money(pay_base):>12} {fmt_money(fuel_inc):>10} {fmt_money(it.gross_total):>12} "
                          f"{fmt_money(it.petty_cash_deduction):>10} {fmt_money(it.social_security):>7} "
                          f"{fmt_money((it.deposit_install or 0)+(it.accident_install or 0)+(it.fuel_cost_self or 0)+(it.other_deduction or 0)):>10} "
                          f"{fmt_money(it.net_pay):>12}")

                # Totals
                g_sum = sum((it.gross_total or 0) for it in items)
                n_sum = sum((it.net_pay or 0) for it in items)
                p_sum = sum((it.petty_cash_deduction or 0) for it in items)
                print(f"\n  TOTAL   gross={g_sum:,.2f}  petty_deduct={p_sum:,.2f}  net={n_sum:,.2f}")


if __name__ == "__main__":
    main()
