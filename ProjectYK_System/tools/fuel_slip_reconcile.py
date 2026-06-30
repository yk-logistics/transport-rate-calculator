"""fuel_slip_reconcile.py — ตรวจว่าสลิปคนเหมาน้ำมัน (mao) โชว์น้ำมันครบ = หักจริง.

กฎโอ (feedback-slip-fuel-must-reconcile): บนสลิป mao ผลรวมน้ำมันที่โชว์
(คอลัมน์น้ำมันในตาราง = Σ DailyJob.fuel_amount + แถว off-table) ต้อง == fuel_cost_self
(น้ำมันที่หักจริง). ถ้า ≠ = มีบิลซ่อน → ต้องทำให้โผล่.

read-only. usage: python ProjectYK_System/tools/fuel_slip_reconcile.py [run_id]
default run_id = ทุก payrun ที่ draft.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from sqlmodel import Session, select  # noqa: E402

from db_config import engine  # noqa: E402
from models import Employee, PayRun, PayRunItem  # noqa: E402
from services.payroll_slip import build_payroll_slip_context  # noqa: E402

MAO_MODES = {"ayu_mao", "lcb_mao", "lcb_mixed"}


def main() -> int:
    run_ids = [int(a) for a in sys.argv[1:] if a.isdigit()]
    bad = 0
    with Session(engine) as s:
        runs = (
            [s.get(PayRun, r) for r in run_ids]
            if run_ids
            else s.exec(select(PayRun)).all()
        )
        for run in runs:
            if run is None:
                continue
            items = s.exec(
                select(PayRunItem).where(PayRunItem.pay_run_id == run.id)
            ).all()
            for it in items:
                emp = s.get(Employee, it.employee_id)
                if (emp.pay_mode or "") not in MAO_MODES:
                    continue
                fcs = it.fuel_cost_self or 0.0
                ctx = build_payroll_slip_context(s, run, emp, it)
                djs = ctx.get("daily_jobs") or []
                table = round(sum((d.fuel_amount or 0) for d in djs), 2)
                off = round(sum(r["amount"] for r in ctx.get("tank_measure_rows", [])), 2)
                shown = round(table + off, 2)
                diff = round(shown - fcs, 2)
                if abs(diff) >= 0.01:
                    bad += 1
                    print(f"MISMATCH run{run.id} {emp.full_name} ({emp.pay_mode}): "
                          f"table={table:,.2f} + off={off:,.2f} = {shown:,.2f} "
                          f"vs หักจริง {fcs:,.2f}  diff={diff:+,.2f}")
    if bad:
        print(f"\nRESULT: {bad} mismatch — สลิปโชว์น้ำมันไม่ตรงหักจริง (มีบิลซ่อน)")
        return 1
    print("RESULT OK — สลิป mao ทุกคนโชว์น้ำมันครบ = หักจริง")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
