"""ผูก driver_id ให้ LCB DailyJob (ตาม source ของรอบ) — เทียบ "ชื่อเต็ม" หลัง normalize
ช่องว่าง/คำนำหน้า กับ Employee ที่ home_site_code='LCB' เท่านั้น (กัน cross-site).

ชีทรอบ 2026-07 เป็นต้นไปลงชื่อ-นามสกุลเต็ม → full-name match ปลอดภัยกว่า first-name.
match เฉพาะตรงเป๊ะ+unique; ชื่อไม่ตรงใคร (คนใหม่/สะกดต่าง) → ปล่อย NULL รายงานให้โอตัดสิน.
รวมพนักงาน inactive ด้วย (คนกลับมาวิ่งใหม่ เช่น วันชัย รอบ 2026-07) — รายงานแยกให้เห็น.

Run:  python lcb_link_drivers.py --source lcb_jun-jul2026 [--dry-run]
"""
import io
import sys
from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select  # noqa: E402
from models import DailyJob, Employee, FuelTxn  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402

PREFIXES = ("นางสาว", "น.ส.", "นาย", "นาง")


def norm(full: str) -> str:
    s = str(full or "").strip()
    for p in PREFIXES:
        if s.startswith(p):
            s = s[len(p):]
            break
    return " ".join(s.split())


def main():
    ap = ArgumentParser()
    ap.add_argument("--source", required=True, help="DailyJob.source ของรอบ เช่น lcb_jun-jul2026")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    eng = make_engine()
    with Session(eng) as s:
        emps = s.exec(select(Employee).where(Employee.home_site_code == "LCB")).all()
        by_name = defaultdict(list)
        for e in emps:
            by_name[norm(e.full_name)].append(e)

        jobs = s.exec(select(DailyJob).where(DailyJob.source == args.source)).all()
        linked, inactive_hits, unmatched = 0, defaultdict(int), defaultdict(int)
        per = defaultdict(int)
        for j in jobs:
            n = norm(j.driver_raw_name)
            if not n:
                unmatched["(ว่าง)"] += 1
                continue
            hit = by_name.get(n, [])
            if len(hit) == 1:
                e = hit[0]
                if j.driver_id != e.id:
                    linked += 1
                    if not dry:
                        j.driver_id = e.id
                        s.add(j)
                per[f"{e.full_name} (id={e.id}{', INACTIVE' if e.status != 'active' else ''})"] += 1
                if e.status != "active":
                    inactive_hits[e.full_name] += 1
            else:
                unmatched[j.driver_raw_name] += 1
        if not dry:
            s.commit()

        # ผูกน้ำมันตามเดลี่ (engine หักน้ำมันจาก FuelTxn.driver_id — รอบ มิ.ย. ก็ผูกครบแบบนี้)
        fuels = s.exec(select(FuelTxn).where(FuelTxn.source == args.source)).all()
        jobs_by_id = {j.id: j for j in jobs}
        fuel_linked = 0
        for f in fuels:
            dj = jobs_by_id.get(f.daily_job_id)
            if dj is not None and dj.driver_id and f.driver_id != dj.driver_id:
                fuel_linked += 1
                if not dry:
                    f.driver_id = dj.driver_id
                    s.add(f)
        if not dry:
            s.commit()

        print(f"LCB jobs source={args.source}: {len(jobs)}")
        print(f"  fuel txns: {len(fuels)} | {'would link' if dry else 'linked'} via daily_job: {fuel_linked}")
        print(f"  {'would link' if dry else 'linked'}: {linked}")
        for nm in sorted(per, key=lambda x: -per[x]):
            print(f"    {per[nm]:>4}  {nm}")
        if inactive_hits:
            print(f"  ⚠ ผูกเข้าพนักงาน INACTIVE (คนกลับมาวิ่ง? แจ้งโอ): {dict(inactive_hits)}")
        print(f"  ปล่อยไว้ driver_id=NULL (คนใหม่/สะกดไม่ตรง — รอโอ): {len(unmatched)} ชื่อ")
        for nm, cnt in sorted(unmatched.items(), key=lambda x: -x[1]):
            print(f"    · {nm} ({cnt} แถว)")


if __name__ == "__main__":
    main()
