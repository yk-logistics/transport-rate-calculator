"""Cleanup before re-running payroll for Book2 validation.

1. Delete PayRunAdjust rows from previous testing (stale fuel adjustments).
2. Zero out deposit_install auto-deduction by setting deposit_balance = deposit_target.
   (Per user PDFs, established drivers have already completed their 10k deposit,
   so no 1000/mo installment should be auto-applied.)

This is idempotent and safe to re-run.
"""
import sys, io, os
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from sqlmodel import Session, select, delete

import main
from models import Employee, PayRunAdjust, PayRun, PayRunItem

TEST_CYCLES = [
    ("BIGC", "2025-12"), ("BIGC", "2026-01"), ("BIGC", "2026-02"),
    ("AYU",  "2025-12"), ("AYU",  "2026-01"), ("AYU",  "2026-02"),
    ("LCB",  "2025-12"), ("LCB",  "2026-01"), ("LCB",  "2026-02"),
]

with Session(main.engine) as s:
    pr_ids = []
    for site, tag in TEST_CYCLES:
        pr = s.exec(
            select(PayRun).where(PayRun.site_code == site, PayRun.pay_cycle_tag == tag)
        ).first()
        if pr:
            pr_ids.append(pr.id)

    adjust_rows = s.exec(
        select(PayRunAdjust).where(PayRunAdjust.pay_run_id.in_(pr_ids))
    ).all() if pr_ids else []
    print(f"Deleting {len(adjust_rows)} PayRunAdjust rows for test cycles...")
    for a in adjust_rows:
        s.delete(a)

    item_rows = s.exec(
        select(PayRunItem).where(PayRunItem.pay_run_id.in_(pr_ids))
    ).all() if pr_ids else []
    print(f"Deleting {len(item_rows)} PayRunItem rows (will recompute)...")
    for it in item_rows:
        s.delete(it)

    emps = s.exec(select(Employee)).all()
    touched = 0
    for e in emps:
        target = e.deposit_target or 0.0
        if target > 0 and (e.deposit_balance or 0.0) < target:
            e.deposit_balance = target
            s.add(e)
            touched += 1
    print(f"Set deposit_balance = deposit_target for {touched} employees (stop auto 1000/mo).")

    s.commit()
    print("Done.")
