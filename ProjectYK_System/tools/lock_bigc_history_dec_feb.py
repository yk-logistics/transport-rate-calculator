"""
Lock BIGC historical payruns 2025-12, 2026-01, 2026-02 by copying รวม YK net.

ต่อจาก onboard_bigc_from_ruamyk.py (ทำ เม.ย./พ.ค. = 2026-03? no — เม.ย.=2026-04, พ.ค.=2026-05).
ตัวนี้เติมเดือนเก่า: work months 2025-12, 2026-01, 2026-02 (folder 1.Jan/2.Feb/3.Mar).
ground truth = docs/ground-truth/bigc_ruamyk_jan_mar.csv (สกัด night-run).

สร้าง emp ที่ขาด (อภิรักษ์ บริสุทธิ์, สมพร โม่งปราณีต = คน BIGC เดิมที่ลาออก, status inactive).
payrun ติด [COPY-LOCK]. idempotent (ลบ-สร้างใหม่เฉพาะ 3 tag นี้). ไม่แตะ payrun อื่น.

Run (from repo root):
  python ProjectYK_System/tools/lock_bigc_history_dec_feb.py
"""
from __future__ import annotations

import csv
import io
import sys
import unicodedata
from datetime import date, datetime

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, REPO_ROOT  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select, delete  # noqa: E402
from models import Employee, PayRun, PayRunItem  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
CSV = REPO_ROOT / "docs" / "ground-truth" / "bigc_ruamyk_jan_mar.csv"

# BIGC = calendar month 1→end, tag = work month
PERIODS = {
    "2025-12": (date(2025, 12, 1), date(2025, 12, 31)),
    "2026-01": (date(2026, 1, 1), date(2026, 1, 31)),
    "2026-02": (date(2026, 2, 1), date(2026, 2, 28)),
}


def first(s: str) -> str:
    s = unicodedata.normalize("NFC", (s or "")).strip()
    return s.split()[0] if s else ""


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8")))
    now = datetime.now()

    with Session(engine) as s:
        # index existing BIGC emps by first name
        bigc = {}
        for e in s.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all():
            bigc[first(e.full_name)] = e.id

        # create missing emps (inactive — historical drivers no longer in current roster)
        for r in rows:
            nm = r["driver_name"].strip()
            f = first(nm)
            if f not in bigc:
                emp = Employee(
                    code=f"BIGC-{f[:12]}",
                    full_name=nm,
                    home_site_code="BIGC",
                    status="inactive",
                    pay_mode="bigc_monthly",
                    base_salary=0.0, care_allowance=0.0,
                    social_security_base=0.0, social_security_rate=0.05,
                    deposit_target=0.0, deposit_balance=0.0,
                    role="driver", pay_cycle_policy="site_default",
                    bank_name="", account_no="",
                    notes="BIGC historical (night-run); ลาออกแล้ว",
                    created_at=now, updated_at=now,
                )
                s.add(emp); s.commit(); s.refresh(emp)
                bigc[f] = emp.id
                print(f"created missing emp: {nm} (id={emp.id}, inactive)")

        for tag, (ps, pe) in PERIODS.items():
            existing = s.exec(
                select(PayRun).where(PayRun.site_code == "BIGC", PayRun.pay_cycle_tag == tag)
            ).all()
            for pr in existing:
                s.exec(delete(PayRunItem).where(PayRunItem.pay_run_id == pr.id))
                s.delete(pr)
            s.commit()

            pr = PayRun(
                site_code="BIGC", pay_cycle_tag=tag,
                period_start=ps, period_end=pe, status="draft",
                notes=f"[COPY-LOCK] BIGC {tag} — net ลอกจาก รวม YK (ประวัติย้อนหลัง). engine ไม่คำนวณ.",
                created_at=now,
            )
            s.add(pr); s.commit(); s.refresh(pr)

            n = 0; net_sum = 0.0
            for r in rows:
                if r["pay_month"] != tag:
                    continue
                eid = bigc[first(r["driver_name"])]
                trip = float(r["trip_income"] or 0)
                base = float(r["base_salary"] or 0)
                rebate = float(r["fuel_rebate"] or 0)
                gross = float(r["gross"] or 0)
                ded = float(r["deductions"] or 0)
                net = float(r["net"] or 0)
                s.add(PayRunItem(
                    pay_run_id=pr.id, employee_id=eid, site_code="BIGC",
                    pay_mode="bigc_monthly", days_worked=0,
                    base_salary_earned=base, trip_fee_total=trip, other_income=rebate,
                    gross_total=gross, petty_cash_deduction=ded, deduction_total=ded,
                    net_pay=net, computed_at=now,
                    note=f"ลอก รวม YK {tag}: เที่ยว{trip:,.0f}+เงินเดือน{base:,.0f}+น้ำมัน{rebate:+,.0f}",
                ))
                n += 1; net_sum += net
            s.commit()
            print(f"PayRun {tag}: {n} items, net {net_sum:,.0f} (run_id={pr.id}, draft)")

    print("\nDONE. BIGC ม.ค.–มี.ค. (work 2025-12..2026-02) locked. ระบบมีประวัติ BIGC ครบขึ้น.")


if __name__ == "__main__":
    main()
