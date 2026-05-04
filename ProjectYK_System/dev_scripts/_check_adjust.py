import sys

from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from sqlmodel import Session, select
from sqlalchemy import func as sf

import main
from models import PayRunAdjust, PayRun, Employee

with Session(main.engine) as s:
    adjusts = s.exec(select(PayRunAdjust)).all()
    print(f"PayRunAdjust total: {len(adjusts)}")
    for a in adjusts[:30]:
        emp = s.get(Employee, a.employee_id)
        pr = s.get(PayRun, a.pay_run_id)
        print(f"  emp={emp.full_name if emp else '?'} / run={pr.site_code if pr else '?'} {pr.pay_cycle_tag if pr else '?'}  fuel_adj_L={a.fuel_adjust_liter}  override_thb={a.fuel_rate_override_thb}")
