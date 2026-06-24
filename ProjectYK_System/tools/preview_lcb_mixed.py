"""Preview lcb_mixed for พชร(86)/สุรเดช(91) — READ-ONLY, writes nothing.

Shows per-day classification + เหมา/เที่ยว split + net, so โอ can compare to
hand calc before we flip pay_mode for real.
"""
from __future__ import annotations
import io, sys
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR
sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select
from models import Employee, PayRun
from services.payroll import calc_one_employee, _classify_lcb_days

engine = create_engine(f"sqlite:///{APP_DIR/'app.db'}",
                       connect_args={"check_same_thread": False})

TARGETS = [(86, "พชร"), (91, "สุรเดช")]


def main():
    with Session(engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        for eid, nm in TARGETS:
            emp = s.get(Employee, eid)
            split = _classify_lcb_days(s, eid, pr.period_start, pr.period_end, "LCB")
            orig = emp.pay_mode
            emp.pay_mode = "lcb_mixed"
            calc = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                     pr.pay_cycle_tag, pay_run_id=2)
            emp.pay_mode = orig
            print(f"=== {nm} (emp{eid}) ===")
            print(f"  เหมา {len(split['mao_days'])}วัน / เที่ยว {len(split['trip_days'])}วัน "
                  f"/ วันหยุด {len(split['no_work'])}วัน / กำกวม {len(split['ambiguous'])}วัน")
            print(f"  เหมา income {calc.fuel_share_income:,.2f}  − น้ำมัน {calc.fuel_cost_self:,.2f}")
            print(f"  เที่ยว fee {calc.trip_fee_total:,.2f}  + พิเศษ {calc.other_income:,.0f}")
            print(f"  ฐาน {calc.base_salary_earned:,.2f} + ดูแล {calc.care_allowance_earned:,.2f}")
            print(f"  gross {calc.gross_total:,.2f}  หักรวม {calc.deduction_total:,.2f}  NET {calc.net_pay:,.2f}")
            if split["ambiguous"]:
                print("  ⚠ วันกำกวม:", ", ".join(str(d.work_date) for d in split["ambiguous"]))
            print()
        s.rollback()


if __name__ == "__main__":
    main()
