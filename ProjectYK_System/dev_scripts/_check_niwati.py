import sys

from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from datetime import date
from sqlmodel import Session, select
from sqlalchemy import func as sf

import main
from models import Employee, DailyJob

with Session(main.engine) as s:
    emp = s.exec(select(Employee).where(Employee.full_name.like("%นิวัติ%"))).first()
    print(f"Emp: {emp.full_name}  id={emp.id}  pay_mode={emp.pay_mode}")

    # Jan cycle: 26 Dec - 25 Jan
    rows = s.exec(
        select(DailyJob).where(
            DailyJob.driver_id == emp.id,
            DailyJob.work_date >= date(2025, 12, 26),
            DailyJob.work_date <= date(2026, 1, 25),
        ).order_by(DailyJob.work_date)
    ).all()
    print(f"\nDailyJob count: {len(rows)}")
    total_trip, total_rev, total_fuel_b = 0, 0, 0
    for r in rows[:5]:
        print(f"  {r.work_date} plate={r.plate_no_raw!r:<12} trip={r.trip_fee_driver}  revenue={r.revenue_customer}  fuel_L={r.fuel_liter}  fuel_amt={r.fuel_amount}  dest={r.destination[:20] if r.destination else ''}")
    for r in rows:
        total_trip += r.trip_fee_driver or 0
        total_rev += r.revenue_customer or 0
    print(f"\n  sum trip_fee_driver = {total_trip:,.2f}")
    print(f"  sum revenue_customer = {total_rev:,.2f}")
