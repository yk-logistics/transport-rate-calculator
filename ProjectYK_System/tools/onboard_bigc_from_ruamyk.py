"""
Onboard BIGC site by COPYING the authoritative net from Book1.xlsx "รวม YK" sheet.

Rationale (โอ-approved 2026-06-27 night-run): BIGC base-salary rule (1,800-9,000/คน)
and per-route trip rate are NOT written down anywhere — the engine cannot re-derive
them without guessing. So we treat โอ's hand-computed "รวม YK" numbers as ground truth
(ANCHOR = ยอดในชีท = คำตอบสุดท้าย) and load them directly as PayRunItem rows.
The engine's bigc_monthly mode stays available for a future cross-check, but the
loaded numbers are the source of truth.

Creates (idempotent — wipes & recreates only BIGC emps/payruns, never touches LCB):
  - 11 BIGC employees (new ids, pay_mode=bigc_monthly) with bank info
  - PayRun 2026-04 (work month, paid 1 Jun) status=finalized-equivalent? -> draft (โอ กดเอง)
  - PayRun 2026-05 (work month, paid 1 Jul) status=draft
  - PayRunItem per driver with trip_fee_total/base/fuel rebate(other_income)/deduction/net
    copied from docs/ground-truth/bigc_ruamyk.csv

Run (from repo root, after the CSV exists):
  python ProjectYK_System/tools/onboard_bigc_from_ruamyk.py
"""
from __future__ import annotations

import csv
import io
import sys
from datetime import date, datetime
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, REPO_ROOT  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select, delete  # noqa: E402
from models import Employee, PayRun, PayRunItem  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

CSV = REPO_ROOT / "docs" / "ground-truth" / "bigc_ruamyk.csv"

# bank info from survey (docs/ground-truth/bigc_survey.md)
BANK = {
    "เกรียงไกร สายแก้ว": ("SCB", "409-455-1326"),
    "สมัย ราศรี": ("ธกส", "020-164-172-905"),
    "ธนวัฒน์ ไชยนอก": ("กสิกร", "142-895-7861"),
    "สมประสงค์ กุมประสิทธิ์": ("SCB", "583-264-4907"),
    "เกศศักดิ์ ชาวยศ": ("กรุงไทย", "496-051-5384"),
    "ณัชพน หอมหวน": ("กสิกร", "116-337-9992"),
    "บุญชอบ พูลสวัสดิ์": ("กรุงเทพ", "249-082-0194"),
    "พรศักดิ์ เด่นดวง": ("SCB", "314-443-4729"),
    "เสกสรร": ("SCB", "959-243-0210"),
    "มานพ": ("TTB", "760-772-8727"),
    "กฤษฎา": ("SCB", "424-207-1942"),
}

PERIODS = {
    "2026-04": (date(2026, 4, 1), date(2026, 4, 30)),
    "2026-05": (date(2026, 5, 1), date(2026, 5, 31)),
}


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8")))
    drivers = []
    seen = set()
    for r in rows:
        nm = r["driver_name"].strip()
        if nm not in seen:
            seen.add(nm)
            drivers.append(nm)

    now = datetime.now()
    with Session(engine) as s:
        # --- idempotent wipe of BIGC only ---
        bigc_emp_ids = [e.id for e in s.exec(
            select(Employee).where(Employee.home_site_code == "BIGC")).all()]
        bigc_runs = s.exec(select(PayRun).where(PayRun.site_code == "BIGC")).all()
        for pr in bigc_runs:
            s.exec(delete(PayRunItem).where(PayRunItem.pay_run_id == pr.id))
            s.delete(pr)
        for e in s.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all():
            s.delete(e)
        s.commit()
        if bigc_emp_ids:
            print(f"wiped {len(bigc_emp_ids)} existing BIGC emps + {len(bigc_runs)} runs")

        # --- create employees ---
        name_to_id = {}
        for nm in drivers:
            bank_name, acct = BANK.get(nm, ("", ""))
            emp = Employee(
                code=f"BIGC-{nm.split()[0]}",
                full_name=nm,
                home_site_code="BIGC",
                status="active",
                pay_mode="bigc_monthly",
                base_salary=9000.0,
                care_allowance=0.0,
                social_security_base=9000.0,
                social_security_rate=0.05,
                deposit_target=0.0,
                deposit_balance=0.0,
                role="driver",
                pay_cycle_policy="site_default",
                bank_name=bank_name,
                account_no=acct,
                notes="onboarded night-run 2026-06-27 (รวม YK copy)",
                created_at=now, updated_at=now,
            )
            s.add(emp)
            s.commit()
            s.refresh(emp)
            name_to_id[nm] = emp.id
        print(f"created {len(name_to_id)} BIGC employees (ids {min(name_to_id.values())}-{max(name_to_id.values())})")

        # --- create payruns + items ---
        for tag, (ps, pe) in PERIODS.items():
            pr = PayRun(
                site_code="BIGC", pay_cycle_tag=tag,
                period_start=ps, period_end=pe,
                status="draft",
                notes=f"BIGC {tag} — net ลอกจาก รวม YK (โอคำนวณมือ). engine ยังไม่คำนวณเอง (รอ route/base rule).",
                created_at=now,
            )
            s.add(pr)
            s.commit()
            s.refresh(pr)
            n = 0
            net_sum = 0.0
            for r in rows:
                if r["pay_month"] != tag:
                    continue
                nm = r["driver_name"].strip()
                eid = name_to_id[nm]
                trip = float(r["trip_income"] or 0)
                base = float(r["base_salary"] or 0)
                rebate = float(r["fuel_rebate"] or 0)
                gross = float(r["gross"] or 0)
                ded = float(r["deductions"] or 0)
                net = float(r["net"] or 0)
                item = PayRunItem(
                    pay_run_id=pr.id, employee_id=eid, site_code="BIGC",
                    pay_mode="bigc_monthly",
                    days_worked=0,
                    base_salary_earned=base,
                    care_allowance_earned=0.0,
                    trip_fee_total=trip,
                    other_income=rebate,  # ค่าเรทน้ำมัน (อาจ +/-)
                    gross_total=gross,
                    petty_cash_deduction=ded,
                    deduction_total=ded,
                    net_pay=net,
                    computed_at=now,
                    note=f"ลอกจาก รวม YK {tag}: เที่ยว {trip:,.0f}+เงินเดือน {base:,.0f}+เรทน้ำมัน {rebate:+,.0f}; x={r['workday_ratio']}",
                )
                s.add(item)
                n += 1
                net_sum += net
            s.commit()
            print(f"PayRun {tag}: {n} items, net {net_sum:,.2f}  (run_id={pr.id}, draft)")

    print("\nDONE. BIGC onboarded by copy. Verify in /payroll. โอ กด finalize เอง.")


if __name__ == "__main__":
    main()
