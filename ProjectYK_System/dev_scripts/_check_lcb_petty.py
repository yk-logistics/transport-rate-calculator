import sys

from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from sqlmodel import Session, select
from sqlalchemy import func as sf

import main
from models import Employee, PettyCashTxn

with Session(main.engine) as s:
    for tag in ("2025-12", "2026-02", "2026-03"):
        print(f"\n=== Tag {tag}, LCB drivers ===")
        rows = s.exec(
            select(Employee.full_name, PettyCashTxn.source, sf.count(), sf.sum(PettyCashTxn.amount))
            .join(Employee, Employee.id == PettyCashTxn.driver_id)
            .where(
                PettyCashTxn.pay_cycle_tag == tag,
                PettyCashTxn.deduct_from_driver == True,
                Employee.home_site_code == "LCB",
            )
            .group_by(Employee.full_name, PettyCashTxn.source)
            .order_by(Employee.full_name)
        ).all()
        for name, src, cnt, amt in rows:
            print(f"  {name[:22]:<22} src={src!r:<30} cnt={cnt:>3}  amt={amt or 0:>12,.2f}")
