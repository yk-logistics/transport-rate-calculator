"""Fix Natchapon's employment dates: he resigned 24/2/26 and returned 3/3/26.
Set start_date = 2026-03-03 (effective for current employment) and preserve
original hire date 2025-02-07 in custom_terms.original_hire_date.
"""
from __future__ import annotations
import json
import sys
from datetime import date

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, select  # noqa: E402
import main  # noqa: E402
from models import Employee  # noqa: E402


def main_run(apply: bool = True) -> None:
    with Session(main.engine) as s:
        emp = s.exec(select(Employee).where(Employee.full_name.contains("ณัชพน"))).first()
        if not emp:
            print("not found"); return
        try:
            ct = json.loads(emp.custom_terms or "{}")
            if not isinstance(ct, dict):
                ct = {}
        except Exception:
            ct = {}
        if not ct.get("original_hire_date") and emp.start_date:
            ct["original_hire_date"] = emp.start_date.isoformat()
        rehire_log = ct.get("rehire_log") or []
        entry = {"left": "2026-02-24", "back": "2026-03-03"}
        if entry not in rehire_log:
            rehire_log.append(entry)
        ct["rehire_log"] = rehire_log
        before = (emp.start_date, emp.end_date, emp.status, emp.custom_terms)
        if apply:
            emp.custom_terms = json.dumps(ct, ensure_ascii=False)
            emp.start_date = date(2026, 3, 3)
            emp.end_date = None
            emp.status = "active"
            s.add(emp)
            s.commit()
        print(
            f"emp_id={emp.id} {emp.full_name}\n"
            f"  before: start={before[0]} end={before[1]} status={before[2]}\n"
            f"  after : start={emp.start_date} end={emp.end_date} status={emp.status}\n"
            f"  custom_terms={emp.custom_terms}\n"
            f"  apply={apply}"
        )


if __name__ == "__main__":
    main_run(apply="--apply" in sys.argv)
