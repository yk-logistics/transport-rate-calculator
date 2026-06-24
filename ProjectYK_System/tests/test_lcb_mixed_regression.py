import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from sqlmodel import Session, select
import main
from models import PayRun, Employee
from services.payroll import calc_one_employee

BASE = json.load(open(os.path.join(os.path.dirname(__file__), "_payrun2_baseline.json")))


def test_existing_modes_net_unchanged():
    """Recompute each non-mixed driver in payrun #2; net must equal baseline."""
    with Session(main.engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        for emp_id, info in BASE.items():
            if info["mode"] == "lcb_mixed":
                continue  # mixed drivers are allowed to change
            emp = s.get(Employee, int(emp_id))
            calc = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                     pr.pay_cycle_tag, pay_run_id=2)
            assert round(calc.net_pay, 2) == info["net"], (
                f"emp {emp_id} ({info['mode']}) net drifted: "
                f"{calc.net_pay:.2f} != {info['net']:.2f}"
            )
