"""ผูก driver_id ให้ AYU DailyJob — **เฉพาะคนที่ home_site_code='AYU' เท่านั้น**
(กัน cross-site contamination). คนชื่อตรงกับ LCB/BigC หรือคนใหม่ที่ยังไม่มีในระบบ
→ ปล่อย driver_id=NULL, รายงานให้โอตัดสิน (ห้ามเดา cross-site).

--dry-run นับ ไม่เขียน. match first-name, accept เฉพาะ AYU-home unique.
"""
import io
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select  # noqa: E402
from models import DailyJob, Employee  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402


def first_name(full: str) -> str:
    p = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").replace("นางสาว", "").split()
    return p[0] if p else ""


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    eng = make_engine()
    with Session(eng) as s:
        ayu_emps = s.exec(select(Employee).where(Employee.home_site_code == "AYU")).all()
        by_fn = defaultdict(list)
        for e in ayu_emps:
            by_fn[first_name(e.full_name)].append(e)

        # คนชื่อตรงกับพนักงาน home≠AYU = cross-site (เที่ยวซ้ำ) → auto-tag _xsite
        non_ayu_fn = {first_name(e.full_name) for e in
                      s.exec(select(Employee).where(Employee.home_site_code != "AYU")).all()
                      if first_name(e.full_name)}
        ayu_fn = set(by_fn.keys())

        jobs = s.exec(select(DailyJob).where(DailyJob.site_code == "AYU")).all()
        linked, cross_or_new, xsite = 0, set(), 0
        per = {}
        for j in jobs:
            f = first_name(j.driver_raw_name)
            hit = by_fn.get(f, [])
            if len(hit) == 1:
                if j.driver_id != hit[0].id:
                    linked += 1
                    if not dry:
                        j.driver_id = hit[0].id
                        s.add(j)
                per[hit[0].full_name] = per.get(hit[0].full_name, 0) + 1
            elif j.driver_raw_name:
                cross_or_new.add(j.driver_raw_name)
                # cross-site duplicate → tag source _xsite (กัน CFO นับซ้ำ)
                if f in non_ayu_fn and f not in ayu_fn and not (j.source or "").endswith("_xsite"):
                    xsite += 1
                    if not dry:
                        j.source = (j.source or "") + "_xsite"
                        s.add(j)
        if not dry:
            s.commit()
        print(f"  auto-tagged cross-site _xsite: {xsite}")

        print(f"AYU jobs: {len(jobs)}")
        print(f"  {'would link' if dry else 'linked'} (AYU-home only): {linked}")
        for nm in sorted(per, key=lambda x: -per[x]):
            print(f"    {per[nm]:>4}  {nm}")
        print(f"  ปล่อยไว้ (cross-site/คนใหม่ — รอโอ): {len(cross_or_new)} ชื่อ")
        for nm in sorted(cross_or_new):
            print(f"    · {nm}")


if __name__ == "__main__":
    main()
