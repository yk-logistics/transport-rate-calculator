"""CLI: reconcile pump PDF(s) against system FuelTxn for one LCB cycle.

Read-only. Writes a report to reports/, nothing to any DB. See spec
docs/superpowers/specs/2026-06-27-fuel-pump-reconcile-design.md.

Example:
  python ProjectYK_System/tools/fuel_pump_reconcile/run_reconcile.py \
      --pdf "C:/.../พฤษภาคม.pdf" --pdf "C:/.../มิถุนายน(5).pdf" \
      --cycle-start 2026-05-16 --cycle-end 2026-06-15 \
      --source-tag lcb_may-jun2026 --cycle-tag 2026-06
"""
from __future__ import annotations

import io
import os
import sys
from argparse import ArgumentParser
from datetime import date

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_loader import load_sys_fuel  # noqa: E402
from matcher import driver_impact, reconcile  # noqa: E402
from pdf_parser import parse_pdfs  # noqa: E402
from report import render  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = os.path.normpath(os.path.join(_HERE, "..", "..", "app", "app.db"))
_DEFAULT_OUT = os.path.normpath(os.path.join(_HERE, "..", "..", "app", "reports"))


def main() -> None:
    ap = ArgumentParser()
    ap.add_argument("--pdf", action="append", required=True, help="pump PDF path (repeatable)")
    ap.add_argument("--cycle-start", required=True)
    ap.add_argument("--cycle-end", required=True)
    ap.add_argument("--source-tag", required=True)
    ap.add_argument("--cycle-tag", required=True)
    ap.add_argument("--site-code", default="LCB")
    ap.add_argument("--db", default=_DEFAULT_DB)
    ap.add_argument("--out", default=_DEFAULT_OUT)
    ap.add_argument("--drift-days", type=int, default=3)
    ap.add_argument("--amount-tol", type=float, default=1.0)
    args = ap.parse_args()

    start = date.fromisoformat(args.cycle_start)
    end = date.fromisoformat(args.cycle_end)

    missing = [p for p in args.pdf if not os.path.exists(p)]
    if missing:
        print(f"ERROR: PDF not found: {missing}")
        return
    if not os.path.exists(args.db):
        print(f"ERROR: db not found: {args.db}")
        return

    bills_all = parse_pdfs(args.pdf)
    bills = [b for b in bills_all if start <= b.date <= end]
    sysf = load_sys_fuel(args.db, args.source_tag, start, end,
                         site_code=args.site_code, cycle_tag=args.cycle_tag)

    # only compare plates the system knows (LCB fleet); pump report has whole fleet
    lcb_plates = {s.plate for s in sysf}
    bills_lcb = [b for b in bills if b.plate in lcb_plates]

    result = reconcile(bills_lcb, sysf, start, end,
                       drift_days=args.drift_days, amount_tol=args.amount_tol)
    html_path, md_path = render(result, args.cycle_tag, args.out, start, end)

    pump_tot = result.matched_pump_baht + sum(b.amount for b in result.pump_only)
    sys_tot = result.matched_sys_baht + sum(s.amount for s in result.system_only)
    impact = driver_impact(result)
    print(f"PDF bills (in-cycle, all fleet): {len(bills)}  | LCB-plate: {len(bills_lcb)}")
    print(f"System FuelTxn rows: {len(sysf)}")
    print(f"Matched: {result.matched_pairs}  pump_only: {len(result.pump_only)}  "
          f"system_only: {len(result.system_only)}")
    print(f"Pump ฿{pump_tot:,.0f}  System ฿{sys_tot:,.0f}  Δ {pump_tot - sys_tot:+,.0f} "
          f"({(pump_tot - sys_tot) / sys_tot * 100 if sys_tot else 0:+.1f}%)")
    flagged = {d: r for d, r in impact.items() if abs(r["net_baht"]) >= 1}
    print(f"คนเหมา/mixed ที่ยอดน้ำมันไม่ตรง: {len(flagged)}")
    for did, r in sorted(flagged.items(), key=lambda kv: -abs(kv[1]["net_baht"])):
        print(f"  {r['driver_name']:<28} net {r['net_baht']:+,.0f} ฿  "
              f"กระทบเงิน≈{r['money_impact']:,.0f}")
    print(f"\nReport: {md_path}\n        {html_path}")


if __name__ == "__main__":
    main()
