"""Assign 4 AYU drivers to the new 'ayu_trip_self_fuel' pay_mode.

These drivers pay their own fuel, so payroll logic deducts fuel_cost_self
from their gross trip fees.
"""
import sys, io, os
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from sqlmodel import Session, select

import main
from models import Employee

TARGETS = ["นิวัติ", "เรวัตร", "ธัชชนพล", "เสรี"]

with Session(main.engine) as s:
    for prefix in TARGETS:
        emp = s.exec(
            select(Employee).where(
                Employee.home_site_code == "AYU",
                Employee.full_name.like(f"{prefix}%"),
            )
        ).first()
        if not emp:
            print(f"  NOT FOUND: {prefix}*")
            continue
        old = emp.pay_mode
        emp.pay_mode = "ayu_trip_self_fuel"
        s.add(emp)
        print(f"  {emp.full_name[:30]:<30}  {old!r:<20} -> 'ayu_trip_self_fuel'")
    s.commit()
    print("Done.")
