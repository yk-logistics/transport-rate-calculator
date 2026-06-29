"""Backfill FuelTxn.fuel_grade จากราคา/ลิตร (relative-per-group).

เซฟเฉพาะ fuel_grade ของแถวที่ยังว่าง — ไม่แตะ liter/amount/exclude/อื่น ๆ.
Default = dry-run (พิมพ์สรุป). ต้อง --commit ถึงเขียนจริง.

รันจาก ProjectYK_System/app/:
    .venv/Scripts/python.exe ../tools/backfill_fuel_grade.py            # dry-run
    .venv/Scripts/python.exe ../tools/backfill_fuel_grade.py --commit   # เขียนจริง
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

# Windows console เริ่มต้นเป็น cp1252 — print ภาษาไทยจะ crash. บังคับ stdout เป็น utf-8
# กันเครื่อง/เซิร์ฟเวอร์ที่ไม่ได้ตั้ง PYTHONIOENCODING (เช่น deploy run).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from sqlmodel import Session, select  # noqa: E402
from db_config import engine  # noqa: E402
from models import FuelTxn  # noqa: E402
from services.fuel_grade import assign_grades_for_group  # noqa: E402


def plan_backfill(session: Session, site: str | None = None) -> list[tuple[int, str]]:
    stmt = select(FuelTxn).where(FuelTxn.fuel_grade == "")
    if site:
        stmt = stmt.where(FuelTxn.site_code == site)
    rows = session.exec(stmt).all()
    groups: dict[tuple, list[FuelTxn]] = defaultdict(list)
    for r in rows:
        groups[(r.site_code, r.txn_date, r.plate_no_raw)].append(r)
    plan: list[tuple[int, str]] = []
    for _, members in groups.items():
        prices = [((m.amount or 0) / m.liter) if (m.liter or 0) > 0 else 0.0 for m in members]
        grades = assign_grades_for_group(prices)
        for m, g in zip(members, grades):
            if g:
                plan.append((m.id, g))
    return plan


def apply_backfill(session: Session, plan: list[tuple[int, str]]) -> int:
    n = 0
    for rid, grade in plan:
        row = session.get(FuelTxn, rid)
        if row is not None and row.fuel_grade == "":
            row.fuel_grade = grade
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="เขียนจริง (default dry-run)")
    ap.add_argument("--site", default=None, help="จำกัดไซต์ เช่น LCB")
    args = ap.parse_args()
    with Session(engine) as s:
        plan = plan_backfill(s, site=args.site)
        from collections import Counter
        c = Counter(g for _, g in plan)
        print(f"จะตั้งเกรด: B7={c['B7']}  B20={c['B20']}  (รวม {len(plan)} แถว, แถวที่เดาไม่ได้/มีเกรดแล้ว ไม่นับ)")
        if args.commit:
            n = apply_backfill(s, plan)
            s.commit()
            print(f"COMMITTED: เปลี่ยน {n} แถว")
        else:
            print("DRY-RUN: ยังไม่เขียน — ใส่ --commit เพื่อเขียนจริง")


if __name__ == "__main__":
    main()
