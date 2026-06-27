"""
Lock LCB historical payruns ม.ค.–เม.ย. 2026 by copying actual-paid net.

มี ground truth ครบจาก แบงค์/BANK.pdf (สกัด night-run → docs/ground-truth/lcb_truth.csv).
ลอก net จริงลง payrun (เหมือน LCB พ.ค. #1, BIGC, AYU) ให้ระบบมีประวัติ LCB ครบ 6 เดือน
(ม.ค.–มิ.ย.) สำหรับ finance/CFO ย้อนหลัง.

ปลอดภัย: สร้างเฉพาะ payrun ม.ค.–เม.ย. (tag 2026-01..2026-04) ที่ยังไม่มี — ไม่แตะ
LCB พ.ค./มิ.ย. หรือ BIGC/AYU. ติด [COPY-LOCK]. idempotent (ลบ-สร้างใหม่เฉพาะ 4 tag นี้).

Name matching: relaxed (normalize ำ→า, ตัด ั) เพราะ PDF OCR สระเพี้ยน
(อภิชำติ→อภิชาติ, วิชำญ→วิชาญ). ทดสอบแล้ว match 100% ทุกเดือน.

Run (from repo root):
  python ProjectYK_System/tools/lock_lcb_history_jan_apr.py
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
CSV = REPO_ROOT / "docs" / "ground-truth" / "lcb_truth.csv"

# LCB cycle 16→15, tag = month cycle ends
PERIODS = {
    "2026-01": (date(2025, 12, 16), date(2026, 1, 15)),
    "2026-02": (date(2026, 1, 16), date(2026, 2, 15)),
    "2026-03": (date(2026, 2, 16), date(2026, 3, 15)),
    "2026-04": (date(2026, 3, 16), date(2026, 4, 15)),
}


def first_name(s: str) -> str:
    s = (s or "").replace("นาย", "").replace("นาง", "").replace("สาว", "").strip()
    s = unicodedata.normalize("NFC", s)
    return s.split()[0] if s else ""


def relaxed(a: str) -> str:
    return a.replace("ำ", "า").replace("ั", "")


def main():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8")))
    now = datetime.now()

    with Session(engine) as s:
        # build LCB employee first-name index (exact + relaxed)
        emp_exact, emp_relaxed = {}, {}
        for e in s.exec(select(Employee).where(Employee.home_site_code == "LCB")).all():
            fn = first_name(e.full_name)
            emp_exact.setdefault(fn, e.id)
            emp_relaxed.setdefault(relaxed(fn), e.id)

        def find_emp(name: str):
            fn = first_name(name)
            if fn in emp_exact:
                return emp_exact[fn]
            return emp_relaxed.get(relaxed(fn))

        for tag, (ps, pe) in PERIODS.items():
            # idempotent: wipe this tag's LCB payrun if exists
            existing = s.exec(
                select(PayRun).where(PayRun.site_code == "LCB", PayRun.pay_cycle_tag == tag)
            ).all()
            for pr in existing:
                s.exec(delete(PayRunItem).where(PayRunItem.pay_run_id == pr.id))
                s.delete(pr)
            s.commit()

            pr = PayRun(
                site_code="LCB", pay_cycle_tag=tag,
                period_start=ps, period_end=pe,
                status="draft",
                notes=f"[COPY-LOCK] LCB {tag} (cycle {ps:%d/%m}–{pe:%d/%m}) — net ลอกจาก "
                      f"แบงค์/BANK.pdf จริง (ประวัติย้อนหลังสำหรับ finance). engine ไม่คำนวณ.",
                created_at=now,
            )
            s.add(pr)
            s.commit()
            s.refresh(pr)

            mrows = [r for r in rows
                     if r["month"] == tag
                     and r["is_authoritative"].upper() == "TRUE"
                     and r["driver_name"] != "__TOTAL__"]
            n = miss = 0
            net_sum = 0.0
            missing = []
            for r in mrows:
                eid = find_emp(r["driver_name"])
                if eid is None:
                    miss += 1
                    missing.append(r["driver_name"])
                    continue
                net = float(r["net_transferred"] or 0)
                item = PayRunItem(
                    pay_run_id=pr.id, employee_id=eid, site_code="LCB",
                    pay_mode="lcb_copy",  # marker: historical copy, not engine-computed
                    days_worked=0,
                    gross_total=net,
                    net_pay=net,
                    computed_at=now,
                    note=f"ลอกจากแบงค์ {tag}: {r['marker']}".strip(),
                )
                s.add(item)
                n += 1
                net_sum += net
            s.commit()
            flag = f"  ⚠ unmatched: {missing}" if missing else ""
            print(f"PayRun {tag}: {n} items, net {net_sum:,.0f} (run_id={pr.id}, draft){flag}")

    print("\nDONE. LCB ม.ค.–เม.ย. locked by copy. ระบบมีประวัติ LCB ครบ 6 เดือน.")


if __name__ == "__main__":
    main()
