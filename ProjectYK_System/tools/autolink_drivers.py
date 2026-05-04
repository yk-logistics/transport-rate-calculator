"""
Auto-link DailyJob.driver_raw_name and PettyCashTxn.requester_raw to existing
Employee records (by normalized full_name and nickname).

Use this after re-importing Daily/Petty from Book2 without wiping Employee master.

Run:
  python ProjectYK_System/tools/autolink_drivers.py [--dry-run]
"""
from __future__ import annotations

import io
import sys
from argparse import ArgumentParser
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select  # noqa: E402

import models  # noqa: E402
from models import DailyJob, Employee, FuelTxn, PettyCashTxn  # noqa: E402
from services.promote import normalize_name  # noqa: E402
from main import _cycle_tag_for_site  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})


def build_name_index(emps: list[Employee]) -> dict[str, Employee]:
    """Build map: normalized name → Employee. Covers full_name + nickname + any aliases."""
    idx: dict[str, Employee] = {}
    for e in emps:
        for candidate in [e.full_name, e.nickname]:
            if not candidate:
                continue
            k = normalize_name(candidate)
            if not k:
                continue
            # First-write-wins (active drivers before inactive)
            if k not in idx:
                idx[k] = e
            else:
                # if current entry is inactive and new one is active, replace
                prev = idx[k]
                if prev.status != "active" and e.status == "active":
                    idx[k] = e
    return idx


def main():
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with Session(engine) as s:
        emps = s.exec(select(Employee)).all()
        name_idx = build_name_index(emps)
        print(f"Employees: {len(emps)}   name variants indexed: {len(name_idx)}")

        # DailyJob
        unlinked_dj = s.exec(
            select(DailyJob).where(DailyJob.driver_id.is_(None), DailyJob.driver_raw_name != "")
        ).all()
        dj_linked = 0
        dj_by_emp: dict[int, int] = {}
        for dj in unlinked_dj:
            k = normalize_name(dj.driver_raw_name)
            if k in name_idx:
                emp = name_idx[k]
                if not args.dry_run:
                    dj.driver_id = emp.id
                    if not dj.site_code:
                        dj.site_code = emp.home_site_code
                dj_linked += 1
                dj_by_emp[emp.id] = dj_by_emp.get(emp.id, 0) + 1
        print(f"DailyJob: {dj_linked}/{len(unlinked_dj)} will be linked")

        # PettyCashTxn
        unlinked_p = s.exec(
            select(PettyCashTxn).where(
                PettyCashTxn.driver_id.is_(None), PettyCashTxn.requester_raw != ""
            )
        ).all()
        p_linked = 0
        tag_fixed = 0
        for p in unlinked_p:
            k = normalize_name(p.requester_raw)
            if k in name_idx:
                emp = name_idx[k]
                if not args.dry_run:
                    p.driver_id = emp.id
                    # Recompute pay_cycle_tag using driver's home site — the sheet's
                    # site_code may have been wrong (dedup across backup copies).
                    if p.txn_date and emp.home_site_code:
                        new_tag = _cycle_tag_for_site(emp.home_site_code, p.txn_date)
                        if new_tag and new_tag != p.pay_cycle_tag:
                            p.pay_cycle_tag = new_tag
                            tag_fixed += 1
                        # also override site_code to driver's home so cycle consistency holds
                        if p.site_code != emp.home_site_code:
                            p.site_code = emp.home_site_code
                p_linked += 1
        print(f"PettyCashTxn: {p_linked}/{len(unlinked_p)} will be linked   (pay_cycle_tag recomputed: {tag_fixed})")

        # Also recompute pay_cycle_tag for ALREADY-LINKED petty rows where
        # the stored site_code doesn't match driver's home site.
        linked_p = s.exec(
            select(PettyCashTxn).where(PettyCashTxn.driver_id.is_not(None))
        ).all()
        already_linked_fixed = 0
        emp_by_id = {e.id: e for e in emps}
        for p in linked_p:
            emp = emp_by_id.get(p.driver_id)
            if not emp or not emp.home_site_code or not p.txn_date:
                continue
            if p.site_code == emp.home_site_code:
                continue
            if not args.dry_run:
                new_tag = _cycle_tag_for_site(emp.home_site_code, p.txn_date)
                p.site_code = emp.home_site_code
                if new_tag:
                    p.pay_cycle_tag = new_tag
            already_linked_fixed += 1
        print(f"PettyCashTxn (already linked): {already_linked_fixed} will be re-tagged to driver's home site")

        # FuelTxn
        unlinked_f = s.exec(
            select(FuelTxn).where(FuelTxn.driver_id.is_(None), FuelTxn.driver_raw_name != "")
        ).all()
        f_linked = 0
        for f in unlinked_f:
            k = normalize_name(f.driver_raw_name)
            if k in name_idx:
                emp = name_idx[k]
                if not args.dry_run:
                    f.driver_id = emp.id
                f_linked += 1
        print(f"FuelTxn: {f_linked}/{len(unlinked_f)} will be linked")

        if not args.dry_run:
            s.commit()
            print("✓ committed")
        else:
            print("(dry run — no changes saved)")

        # Top unlinked raw names (for diagnosis)
        remaining_dj = [dj for dj in unlinked_dj if normalize_name(dj.driver_raw_name) not in name_idx]
        if remaining_dj:
            from collections import Counter
            ctr = Counter(dj.driver_raw_name for dj in remaining_dj)
            print("\nTop 15 unlinked DailyJob raw names:")
            for raw, n in ctr.most_common(15):
                print(f"  {n:>5}  {raw!r}")

        remaining_p = [p for p in unlinked_p if normalize_name(p.requester_raw) not in name_idx]
        if remaining_p:
            from collections import Counter
            ctr = Counter(p.requester_raw for p in remaining_p)
            print("\nTop 15 unlinked PettyCashTxn raw requesters:")
            for raw, n in ctr.most_common(15):
                print(f"  {n:>5}  {raw!r}")


if __name__ == "__main__":
    main()
