"""
Onboard AYU site by COPYING actual-paid net from the bank sheet (AYU rev.1.pdf).

Rationale (โอ-approved 2026-06-27 night-run): AYU has multiple pay sub-models AND
some drivers run TWO systems (เที่ยว vs เหมา) where the company picks whichever per
person. The chosen amount is whatever hit the bank — so the bank figure is ground
truth (ANCHOR). We load net-paid directly; the engine does not re-derive AYU.

Cycle: 26 → 25 (tag = month cycle ends). Folder 5.May/AYU = cycle 26/4–25/5,
paid ~1 Jun. We tag this payrun 2026-05.

Idempotent: wipes & recreates only AYU emps/payruns (never touches LCB/BIGC).
Source: docs/ground-truth/ayu_paid.csv

Special cases (net=0 or no-bank) are still loaded as items with net=0 and a note,
so the roster is complete and โอ can see them flagged. They are NOT money owed out.

Run (from repo root):
  python ProjectYK_System/tools/onboard_ayu_from_paid.py
"""
from __future__ import annotations

import csv
import io
import sys
from datetime import date, datetime

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, REPO_ROOT  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select, delete  # noqa: E402
from models import Employee, PayRun, PayRunItem  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

CSV = REPO_ROOT / "docs" / "ground-truth" / "ayu_paid.csv"

TAG = "2026-05"
PERIOD = (date(2026, 4, 26), date(2026, 5, 25))

# map survey's system_chosen -> internal pay_mode + role
MODE_MAP = {
    "office_monthly": ("office_monthly", "office"),
    "per_trip_flat": ("ayu_flat", "driver"),
    "per_trip_fuel_rate": ("ayu_trip", "driver"),
    "per_trip_fuel_baht": ("ayu_trip", "driver"),
}


def split_bank(acct_field: str):
    """survey put 'BANK 123-456' or 'เงินสด' in account_no; split into name+no."""
    acct_field = (acct_field or "").strip()
    if not acct_field or acct_field == "เงินสด":
        return ("เงินสด" if acct_field == "เงินสด" else "", "")
    parts = acct_field.split(None, 1)
    if len(parts) == 2 and any(ch.isdigit() for ch in parts[1]):
        return (parts[0], parts[1])
    return ("", acct_field)


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8")))
    now = datetime.now()

    with Session(engine) as s:
        # idempotent wipe AYU only
        old_runs = s.exec(select(PayRun).where(PayRun.site_code == "AYU")).all()
        for pr in old_runs:
            s.exec(delete(PayRunItem).where(PayRunItem.pay_run_id == pr.id))
            s.delete(pr)
        old_emps = s.exec(select(Employee).where(Employee.home_site_code == "AYU")).all()
        for e in old_emps:
            s.delete(e)
        s.commit()
        if old_emps:
            print(f"wiped {len(old_emps)} AYU emps + {len(old_runs)} runs")

        # create employees
        name_to_id = {}
        for r in rows:
            nm = r["driver_name"].strip()
            chosen = r["system_chosen"].strip()
            pay_mode, role = MODE_MAP.get(chosen, ("ayu_trip", "driver"))
            bank_name, acct = split_bank(r["account_no"])
            emp = Employee(
                code=f"AYU-{nm.split()[0][:12]}",
                full_name=nm,
                home_site_code="AYU",
                status="active",
                pay_mode=pay_mode,
                base_salary=0.0,
                care_allowance=0.0,
                social_security_base=0.0,
                social_security_rate=0.05,
                deposit_target=0.0,
                deposit_balance=0.0,
                role=role,
                pay_cycle_policy="site_default",
                bank_name=bank_name,
                account_no=acct,
                notes=f"onboarded night-run 2026-06-27 (AYU paid copy); {r['marker']}",
                created_at=now, updated_at=now,
            )
            s.add(emp)
            s.commit()
            s.refresh(emp)
            name_to_id[nm] = emp.id
        print(f"created {len(name_to_id)} AYU employees (ids {min(name_to_id.values())}-{max(name_to_id.values())})")

        # one payrun, items = net paid
        pr = PayRun(
            site_code="AYU", pay_cycle_tag=TAG,
            period_start=PERIOD[0], period_end=PERIOD[1],
            status="draft",
            notes=f"AYU {TAG} (รอบ 26/4–25/5) — net ลอกจากแบงค์จริง (AYU rev.1.pdf). "
                  f"2-ระบบเที่ยว/เหมา resolved ตามที่บริษัทจ่ายจริง. engine ไม่คำนวณเอง.",
            created_at=now,
        )
        s.add(pr)
        s.commit()
        s.refresh(pr)

        n = 0
        net_sum = 0.0
        zero_cases = []
        for r in rows:
            nm = r["driver_name"].strip()
            net = float(r["net_paid"] or 0)
            item = PayRunItem(
                pay_run_id=pr.id, employee_id=name_to_id[nm], site_code="AYU",
                pay_mode=MODE_MAP.get(r["system_chosen"].strip(), ("ayu_trip", "driver"))[0],
                days_worked=0,
                gross_total=net,  # we only have net; gross unknown for copy-load
                net_pay=net,
                computed_at=now,
                note=f"ลอกจากแบงค์ {TAG}: {r['system_chosen']}; {r['marker']}",
            )
            s.add(item)
            n += 1
            net_sum += net
            if net == 0:
                zero_cases.append(nm)
        s.commit()
        print(f"PayRun {TAG}: {n} items, net {net_sum:,.0f}  (run_id={pr.id}, draft)")
        if zero_cases:
            print(f"  net=0 (flagged, ไม่โอน): {', '.join(zero_cases)}")

    print("\nDONE. AYU onboarded by copy. โอ review + กด finalize เอง.")


if __name__ == "__main__":
    main()
