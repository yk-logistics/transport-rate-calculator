"""Dedup duplicates between import_petty_mar26 (canonical for MAR 26 cycle)
and legacy sources (book2_2026, import) that are still 'pending'.

Strategy: Group by canonical (date, person, deduct_amount, direction).
If a group has both an import_petty_mar26 row AND any older-source row,
mark the older-source rows as 'settled_offline' (canonical wins).

Idempotent: only marks rows currently in 'pending' status.
"""
from __future__ import annotations
import sys

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, select  # noqa: E402
import main  # noqa: E402
from models import PettyCashTxn  # noqa: E402
from services.alias_map import normalize_person_name  # noqa: E402

OLDER_SOURCES = {"book2_2026", "import"}
CANONICAL_SOURCE = "import_petty_mar26"


def main_run(apply: bool = True) -> None:
    with Session(main.engine) as s:
        rows = s.exec(
            select(PettyCashTxn).where(
                PettyCashTxn.deduct_from_driver == True,  # noqa: E712
                PettyCashTxn.deduction_status == "pending",
                PettyCashTxn.deduct_amount > 0,
            )
        ).all()
        groups: dict[tuple, list[PettyCashTxn]] = {}
        for r in rows:
            k = (
                r.txn_date,
                normalize_person_name(r.requester_raw or ""),
                round(float(r.deduct_amount or 0), 2),
                r.direction,
            )
            groups.setdefault(k, []).append(r)

        marked = 0
        for k, v in groups.items():
            srcs = {r.source for r in v}
            if CANONICAL_SOURCE not in srcs:
                continue
            for r in v:
                if r.source in OLDER_SOURCES and r.deduction_status == "pending":
                    if apply:
                        r.deduction_status = "settled_offline"
                        note = (r.note or "").strip()
                        tag = f"[auto-dedup vs {CANONICAL_SOURCE}]"
                        if tag not in note:
                            r.note = (note + " " + tag).strip()
                        s.add(r)
                    marked += 1
        if apply:
            s.commit()
        print(f"groups_total={len(groups)}  rows_marked_settled_offline={marked}  apply={apply}")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    main_run(apply=apply)
