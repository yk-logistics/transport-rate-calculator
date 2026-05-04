"""
Backfill deduction_status='settled_offline' บนรายการ PettyCashTxn ที่มี
keyword ใน memo/note ว่าหักนอกระบบไปแล้ว (เช่น 'หักแล้ว', 'ทอนไม่คืน').

รันครั้งเดียวบน DB ที่ import มาก่อนหน้า เพื่อไม่ต้อง re-import ใหม่.

Usage (จากราก repo):
  python ProjectYK_System/tools/backfill_settled_offline.py               # dry-run
  python ProjectYK_System/tools/backfill_settled_offline.py --apply       # ใช้จริง
"""
from __future__ import annotations
import sys

from _repo_paths import APP_DIR, TOOLS_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

import main  # noqa: E402
from models import PettyCashTxn  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

# reuse the same keyword list as the importer
try:
    sys.path.insert(0, str(TOOLS_DIR))
    from import_petty_cash import _SETTLED_KEYWORDS  # type: ignore
except Exception:
    _SETTLED_KEYWORDS = (
        "หักแล้ว", "หักไปแล้ว", "หักเดือนก่อน", "หักรอบก่อน", "หักเรียบร้อย",
        "ทอนไม่คืน", "ไม่ได้ทอน", "ไม่ทอน", "ค้างทอน", "ทอนแล้ว",
        "หักจากเงินเบิก", "หักกับเงินเบิก", "หักกันเอง", "รับไปแล้ว",
    )


def matched(memo: str, note: str) -> str | None:
    text = f"{memo or ''}  {note or ''}".lower()
    for kw in _SETTLED_KEYWORDS:
        if kw.lower() in text:
            return kw
    return None


def main_run(apply: bool):
    with Session(main.engine) as s:
        stmt = select(PettyCashTxn).where(
            PettyCashTxn.deduct_from_driver == True,  # noqa: E712
            PettyCashTxn.deduction_status == "pending",
        )
        rows = s.exec(stmt).all()
        updated = 0
        print(f"scanning {len(rows)} pending deduction rows...")
        for r in rows:
            hit = matched(r.memo or "", r.note or "")
            if not hit:
                continue
            print(f"  [{r.site_code}] {r.txn_date} {r.requester_raw[:25]:<25} "
                  f"ded={r.deduct_amount:>8.0f} kw={hit!r}  memo={(r.memo or '')[:60]}")
            if apply:
                r.deduction_status = "settled_offline"
                s.add(r)
            updated += 1
        if apply:
            s.commit()
            print(f"\n✓ updated {updated} rows → settled_offline")
        else:
            print(f"\n(dry-run) would update {updated} rows. ใส่ --apply เพื่อบันทึก")


if __name__ == "__main__":
    main_run(apply=("--apply" in sys.argv))
