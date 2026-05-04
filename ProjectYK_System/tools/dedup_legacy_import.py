"""Dedup legacy 'import' duplicates that came from importing 3 copies of
สดย่อยวังน้อย.xlsx (one per site folder). Within a duplicate group of pending
deductions sharing the SAME (date, person, amount, direction, memo-prefix),
keep the lowest id as canonical and mark the rest as settled_offline.

We add a memo similarity guard (first 25 chars exact match) to avoid mis-grouping
unrelated rows that happen to share date+amount.
"""
from __future__ import annotations
import sys

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, select  # noqa: E402
import main  # noqa: E402
from models import PettyCashTxn  # noqa: E402
from services.alias_map import normalize_person_name  # noqa: E402


def memo_key(memo: str) -> str:
    return (memo or "").strip()[:25]


def main_run(apply: bool = True) -> None:
    with Session(main.engine) as s:
        rows = s.exec(
            select(PettyCashTxn).where(
                PettyCashTxn.deduct_from_driver == True,  # noqa: E712
                PettyCashTxn.deduction_status == "pending",
                PettyCashTxn.deduct_amount > 0,
                PettyCashTxn.source == "import",
            )
        ).all()
        groups: dict[tuple, list[PettyCashTxn]] = {}
        for r in rows:
            k = (
                r.txn_date,
                normalize_person_name(r.requester_raw or ""),
                round(float(r.deduct_amount or 0), 2),
                r.direction,
                memo_key(r.memo or ""),
            )
            groups.setdefault(k, []).append(r)

        marked = 0
        affected_groups = 0
        for k, v in groups.items():
            if len(v) < 2:
                continue
            v_sorted = sorted(v, key=lambda r: r.id)
            keeper = v_sorted[0]
            losers = v_sorted[1:]
            affected_groups += 1
            for r in losers:
                if r.deduction_status == "pending":
                    if apply:
                        r.deduction_status = "settled_offline"
                        note = (r.note or "").strip()
                        tag = f"[legacy-dedup vs id={keeper.id}]"
                        if tag not in note:
                            r.note = (note + " " + tag).strip()
                        s.add(r)
                    marked += 1
        if apply:
            s.commit()
        print(
            f"groups_total={len(groups)}  affected_groups={affected_groups}  "
            f"rows_marked={marked}  apply={apply}"
        )


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    main_run(apply=apply)
