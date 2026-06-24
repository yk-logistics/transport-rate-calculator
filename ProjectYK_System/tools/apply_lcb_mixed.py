"""Flip พชร(86)/สุรเดช(91) to lcb_mixed and recompute payrun #2.

Backs up app.db first. Run ONLY after โอ approves preview_lcb_mixed numbers.
"""
from __future__ import annotations
import io, sys, shutil, datetime
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR
sys.path.insert(0, str(APP_DIR))

import main
from sqlmodel import Session, select
from models import Employee, PayRun
from services.payroll import compute_pay_run

TARGETS = [86, 91]


def main_run():
    db = APP_DIR / "app.db"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(db, APP_DIR / f"app.db.bak_before_lcb_mixed_{stamp}")
    print("backup done")
    with Session(main.engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        assert pr.status == "draft", f"payrun not draft: {pr.status}"
        for eid in TARGETS:
            emp = s.get(Employee, eid)
            print(f"emp{eid} {emp.full_name}: {emp.pay_mode} -> lcb_mixed")
            emp.pay_mode = "lcb_mixed"
            s.add(emp)
        s.commit()
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        print(f"recomputed {len(items)} items; net total {sum(i.net_pay for i in items):,.2f}")


if __name__ == "__main__":
    main_run()
