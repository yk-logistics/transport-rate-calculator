"""
Lock AYU historical payruns ม.ค.–เม.ย. 2026 by copying bank-sheet net.

ground truth: docs/ground-truth/ayu_paid_jan_mar.csv (ม.ค.-มี.ค.) + ayu_paid_apr.csv (เม.ย.).
ลอก net จริงจากแบงค์ (pypdf). AYU cycle 26→25, tag = เดือนจ่าย (folder month).

จัดการ pypdf Thai artifacts:
- ำ↔า เพี้ยน (รัตนำวดี=รัตนาวดี, นรศำต=นรศาต), space แทรกกลางชื่อ (ศักดิ์ สิทธิ์=ศักดิ์สิทธิ์).
- match_key() = normalize aggressive เพื่อ map/dedup. ใช้ชื่อจาก AYU ที่มีอยู่เป็นหลัก;
  คนใหม่ใช้ชื่อที่ clean แล้ว (เลือก variant ที่ดีสุด = ตัวที่ไม่มี space แทรก).

คนใหม่ = ลาออกก่อน พ.ค. / รับ deposit คืน → สร้าง emp status=inactive.
ลำ (เม.ย., เงินสด) = คนพม่าเข้าใหม่. payrun ติด [COPY-LOCK]. idempotent.

Run (from repo root):
  python ProjectYK_System/tools/lock_ayu_history_jan_apr.py
"""
from __future__ import annotations

import csv
import io
import re
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

CSV_JANMAR = REPO_ROOT / "docs" / "ground-truth" / "ayu_paid_jan_mar.csv"
CSV_APR = REPO_ROOT / "docs" / "ground-truth" / "ayu_paid_apr.csv"

# AYU cycle 26→25, tag = pay month (folder month)
PERIODS = {
    "2026-01": (date(2025, 12, 26), date(2026, 1, 25)),
    "2026-02": (date(2026, 1, 26), date(2026, 2, 25)),
    "2026-03": (date(2026, 2, 26), date(2026, 3, 25)),
    "2026-04": (date(2026, 3, 26), date(2026, 4, 25)),
}


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", (s or "")).strip()
    return re.sub(r"\s+", " ", s)


def match_key(s: str) -> str:
    s = clean(s)
    s = re.sub(r"\(.*?\)", "", s)  # drop (nickname)
    for p in ("นาย", "นาง", "สาว"):
        s = s.replace(p, "")
    return s.replace("ำ", "า").replace("ั", "").replace("์", "").replace(" ", "").strip()


def load_rows():
    rows = []
    for r in csv.DictReader(io.open(CSV_JANMAR, encoding="utf-8")):
        rows.append({"month": r["pay_month"], "name": r["driver_name"],
                     "net": r["net_paid"], "acct": r.get("account_no", ""),
                     "marker": r.get("marker", "")})
    # April CSV has different columns (driver_name,net_paid,account_no,marker)
    for r in csv.DictReader(io.open(CSV_APR, encoding="utf-8")):
        rows.append({"month": "2026-04", "name": r["driver_name"],
                     "net": r["net_paid"], "acct": r.get("account_no", ""),
                     "marker": r.get("marker", "")})
    return rows


def best_variant(names: set) -> str:
    """pick the cleanest display name: prefer one without stray internal spaces, longer."""
    return sorted(names, key=lambda n: (n.count(" "), -len(n)))[0]


def main():
    rows = load_rows()
    now = datetime.now()

    with Session(engine) as s:
        # existing AYU index by match_key
        existing = {}
        for e in s.exec(select(Employee).where(Employee.home_site_code == "AYU")).all():
            existing[match_key(e.full_name)] = e.id

        # collect all distinct people from csv (dedupe by key), choose best display name
        by_key = {}
        for r in rows:
            k = match_key(r["name"])
            by_key.setdefault(k, set()).add(clean(r["name"]))

        # create missing emps (inactive — historical)
        created = 0
        for k, names in by_key.items():
            if k in existing:
                continue
            disp = best_variant(names)
            is_cash = any("cash" in r["marker"] or "เงินสด" in r["acct"]
                          for r in rows if match_key(r["name"]) == k)
            emp = Employee(
                code=f"AYU-{disp.split()[0][:12]}",
                full_name=disp, home_site_code="AYU", status="inactive",
                pay_mode="ayu_trip", base_salary=0.0, care_allowance=0.0,
                social_security_base=0.0, social_security_rate=0.05,
                deposit_target=0.0, deposit_balance=0.0,
                role="driver", pay_cycle_policy="site_default",
                bank_name="", account_no="" if is_cash else "",
                notes="AYU historical (night-run); ลาออก/เดือนเก่า",
                created_at=now, updated_at=now,
            )
            s.add(emp); s.commit(); s.refresh(emp)
            existing[k] = emp.id
            created += 1
        print(f"created {created} missing AYU emps (inactive)")

        for tag, (ps, pe) in PERIODS.items():
            for pr in s.exec(select(PayRun).where(
                    PayRun.site_code == "AYU", PayRun.pay_cycle_tag == tag)).all():
                s.exec(delete(PayRunItem).where(PayRunItem.pay_run_id == pr.id))
                s.delete(pr)
            s.commit()

            pr = PayRun(
                site_code="AYU", pay_cycle_tag=tag,
                period_start=ps, period_end=pe, status="draft",
                notes=f"[COPY-LOCK] AYU {tag} (รอบ 26→25) — net ลอกจากแบงค์จริง (pypdf). ประวัติย้อนหลัง.",
                created_at=now,
            )
            s.add(pr); s.commit(); s.refresh(pr)

            n = 0; net_sum = 0.0
            for r in rows:
                if r["month"] != tag:
                    continue
                eid = existing[match_key(r["name"])]
                net = float(r["net"] or 0)
                s.add(PayRunItem(
                    pay_run_id=pr.id, employee_id=eid, site_code="AYU",
                    pay_mode="ayu_trip", days_worked=0,
                    gross_total=net, net_pay=net, computed_at=now,
                    note=f"ลอกแบงค์ {tag}: {r['marker']}".strip(),
                ))
                n += 1; net_sum += net
            s.commit()
            print(f"PayRun {tag}: {n} items, net {net_sum:,.0f} (run_id={pr.id}, draft)")

    print("\nDONE. AYU ม.ค.–เม.ย. locked. AYU ครบ 5 เดือน (ม.ค.–พ.ค.).")


if __name__ == "__main__":
    main()
