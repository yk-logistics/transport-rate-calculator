"""Add 3 new BIGC drivers (โอ-confirmed 2026-06-29: ชรินทร์/โกสินทร์/วิทัศน์ คนใหม่
พ.ค.) then link ALL BIGC DailyJob.driver_raw_name → Employee.id by first name.

Safe by design:
  * --dry-run prints what WOULD happen, writes nothing.
  * On real run, prints the new employee IDs it created (rollback = delete by id).
  * Links only BIGC DailyJob rows; matches existing _bigc_link_report.first_name().
  * New employees follow the verified BIGC template (code=BIGC-<firstname>,
    pay_mode=bigc_monthly, base_salary=0 → engine defaults 9000, SS base 9000 @5%).
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select  # noqa: E402
from models import DailyJob, Employee  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402
from _bigc_link_report import first_name  # reuse same matching convention  # noqa: E402

# Full names + head-plate from เรทน้ำมันเดือนพฤษภาคม69.xlsx ชีท รวมเรท (verified)
NEW_DRIVERS = [
    {"full_name": "ชรินทร์ ใยสอาด", "plate": "71-8009"},
    {"full_name": "โกสินทร์ สรีกันยา", "plate": "71-8003"},
    {"full_name": "วิทัศน์ คงรอด", "plate": "71-8004"},
]


def make_employee(full_name: str) -> Employee:
    fn = first_name(full_name)
    return Employee(
        code=f"BIGC-{fn}",
        full_name=full_name,
        nickname="",
        home_site_code="BIGC",
        status="active",
        pay_mode="bigc_monthly",
        base_salary=0.0,          # engine ใช้ default 9000 เมื่อ base==0
        care_allowance=0.0,
        deposit_target=0.0,
        deposit_balance=0.0,
        social_security_base=9000.0,
        social_security_rate=0.05,
        pay_cycle_policy="site_default",
    )


def main() -> None:
    from argparse import ArgumentParser

    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    eng = make_engine()
    with Session(eng) as s:
        existing = s.exec(
            select(Employee).where(Employee.home_site_code == "BIGC")
        ).all()
        existing_fn = {first_name(e.full_name) for e in existing}

        # 1) decide which of the 3 actually need creating (idempotent)
        to_create = [d for d in NEW_DRIVERS if first_name(d["full_name"]) not in existing_fn]
        print(f"=== ADD employees ({len(to_create)} of {len(NEW_DRIVERS)}) ===")
        for d in to_create:
            print(f"  + {d['full_name']!r}  code=BIGC-{first_name(d['full_name'])}  plate={d['plate']}")
        already = [d for d in NEW_DRIVERS if first_name(d["full_name"]) in existing_fn]
        for d in already:
            print(f"  (skip, มีแล้ว) {d['full_name']!r}")

        if not args.dry_run:
            created_ids = []
            for d in to_create:
                e = make_employee(d["full_name"])
                s.add(e)
                s.commit()
                s.refresh(e)
                created_ids.append((e.id, e.full_name))
            if created_ids:
                print("  CREATED ids (rollback = delete by id):")
                for cid, nm in created_ids:
                    print(f"    emp{cid}  {nm!r}")

        # 2) link BIGC DailyJob → driver_id (re-read employees incl. new)
        emps = s.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all()
        by_fn = {}
        for e in emps:
            by_fn.setdefault(first_name(e.full_name), []).append(e)

        jobs = s.exec(select(DailyJob).where(DailyJob.site_code == "BIGC")).all()
        link_counts, still_unlinked, ambiguous = {}, set(), set()
        n_would_link = 0
        for j in jobs:
            rfn = first_name(j.driver_raw_name)
            hit = by_fn.get(rfn, [])
            if len(hit) == 1:
                target = hit[0].id
                if j.driver_id != target:
                    n_would_link += 1
                    if not args.dry_run:
                        j.driver_id = target
                        s.add(j)
                link_counts[hit[0].full_name] = link_counts.get(hit[0].full_name, 0) + 1
            elif not hit:
                if j.driver_raw_name:
                    still_unlinked.add(j.driver_raw_name)
            else:
                ambiguous.add(rfn)

        if not args.dry_run:
            s.commit()

        print(f"\n=== LINK BIGC DailyJob → driver_id ===")
        print(f"  total BIGC jobs: {len(jobs)}")
        print(f"  {'would link' if args.dry_run else 'linked'} (driver_id changed): {n_would_link}")
        print("  per-driver job counts:")
        for nm in sorted(link_counts, key=lambda x: -link_counts[x]):
            print(f"    {link_counts[nm]:>4}  {nm!r}")
        if ambiguous:
            print(f"  AMBIGUOUS first-name (skipped): {sorted(ambiguous)}")
        if still_unlinked:
            print(f"  STILL UNLINKED: {sorted(still_unlinked)}")
        else:
            print("  STILL UNLINKED: none ✓")


if __name__ == "__main__":
    main()
