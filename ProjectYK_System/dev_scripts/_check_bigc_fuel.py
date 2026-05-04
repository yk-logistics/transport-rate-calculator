import sys

from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from datetime import date
from sqlmodel import Session, select
from sqlalchemy import func as sf

import main
from models import Employee, DailyJob, FuelTxn

with Session(main.engine) as s:
    # Find ธนวัฒน์ (BIGC)
    emps = s.exec(
        select(Employee).where(Employee.home_site_code == "BIGC")
    ).all()
    print("BIGC drivers & their fuel totals in Dec 2025:")
    print(f"{'Driver':<25} {'DJ.fuel_L sum':>15} {'Fuel.liter sum':>15} {'Rebate':>12}")
    print("-" * 70)
    for e in emps:
        dj_sum = s.exec(
            select(sf.sum(DailyJob.fuel_liter)).where(
                DailyJob.driver_id == e.id,
                DailyJob.work_date >= date(2025, 12, 1),
                DailyJob.work_date <= date(2025, 12, 31),
            )
        ).one() or 0
        f_sum = s.exec(
            select(sf.sum(FuelTxn.liter)).where(
                FuelTxn.driver_id == e.id,
                FuelTxn.txn_date >= date(2025, 12, 1),
                FuelTxn.txn_date <= date(2025, 12, 31),
            )
        ).one() or 0
        f_count = s.exec(
            select(sf.count()).select_from(FuelTxn).where(
                FuelTxn.driver_id == e.id,
                FuelTxn.txn_date >= date(2025, 12, 1),
                FuelTxn.txn_date <= date(2025, 12, 31),
            )
        ).one() or 0
        rebate = (dj_sum - f_sum) * 16
        print(f"{e.full_name[:25]:<25} {dj_sum:>15,.2f} {f_sum:>15,.2f} ({f_count}rows) {rebate:>9,.2f}")

    # Also count FuelTxn sources in Dec 2025
    print("\nFuelTxn by source (Dec 2025):")
    rows = s.exec(
        select(FuelTxn.source, sf.count(), sf.sum(FuelTxn.liter))
        .where(
            FuelTxn.txn_date >= date(2025, 12, 1),
            FuelTxn.txn_date <= date(2025, 12, 31),
            FuelTxn.site_code == "BIGC",
        ).group_by(FuelTxn.source)
    ).all()
    for src, cnt, total in rows:
        print(f"  {src!r:<25} count={cnt}  liter_sum={total or 0:,.2f}")
