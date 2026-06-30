"""ayu_mao_recompute_run18.py — recompute ONLY the 4 AYU mao drivers in run 18 in place.

หลังแก้ engine ayu_mao (อ่าน trip_fee_driver ต่อเที่ยวแทน revenue×60%) ต้อง
อัปเดต PayRunItem ของ 4 คนเหมา AYU มิ.ย. ให้ตรง. ทำเฉพาะ 4 คนนี้ (ไม่เรียก
compute_pay_run ทั้งรอบ) เพื่อเลี่ยง gotcha office copy ถูกล้าง + ไม่แตะ trip/petty.

read-only กับ daily/fuel; เขียนเฉพาะ PayRunItem 4 แถวของ run 18.
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
from services.payroll import calc_one_employee  # noqa: E402

RUN_ID = 18
MAO_IDS = [139, 140, 143, 144]  # นิวัติ, เรวัตร, ธัชชนพล, เสรี

ITEM_FIELDS = [
    "days_worked", "days_leave", "days_absent", "days_company_no_work",
    "base_salary_earned", "care_allowance_earned", "trip_fee_total",
    "fuel_rate_income", "fuel_share_income", "guarantee_topup", "other_income",
    "special_income", "ot_income", "pickup_return_income", "gross_total",
    "fuel_budget_liter", "fuel_consumed_liter", "fuel_residual_liter",
    "social_security", "income_tax_withholding", "deposit_install",
    "accident_install", "petty_cash_deduction", "fuel_cost_self",
    "other_deduction", "deduction_total", "net_pay", "note",
]


def main() -> int:
    with Session(engine) as session:
        run = session.get(PayRun, RUN_ID)
        if run is None:
            print(f"FAIL run {RUN_ID} not found")
            return 1
        if run.status == "finalized":
            print(f"FAIL run {RUN_ID} is finalized — refuse (use force path deliberately)")
            return 1
        start, end, tag = run.period_start, run.period_end, run.pay_cycle_tag

        for emp_id in MAO_IDS:
            emp = session.get(Employee, emp_id)
            item = session.exec(
                select(PayRunItem).where(
                    PayRunItem.pay_run_id == RUN_ID,
                    PayRunItem.employee_id == emp_id,
                )
            ).first()
            if emp is None or item is None:
                print(f"SKIP emp {emp_id}: emp={emp is not None} item={item is not None}")
                continue
            if (emp.pay_mode or "") != "ayu_mao":
                print(f"SKIP emp {emp_id}: pay_mode={emp.pay_mode!r} (not ayu_mao)")
                continue
            old_net = item.net_pay
            calc = calc_one_employee(session, emp, start, end, tag, pay_run_id=RUN_ID)
            for f in ITEM_FIELDS:
                setattr(item, f, getattr(calc, f))
            session.add(item)
            print(f"emp {emp_id} {emp.full_name}: net {old_net:,.2f} -> {calc.net_pay:,.2f} "
                  f"(Δ {calc.net_pay - old_net:+,.2f}) | share_income={calc.fuel_share_income:,.2f}")

        session.commit()
    print("DONE — committed 4 ayu_mao items only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
