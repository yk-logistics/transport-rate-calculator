"""Fix DailyJob rows incorrectly tagged as leave because the destination
contains a place name with substring 'ลา' (e.g. ลาดพร้าว, ตลาด...).

Rule: if status_code='leave' but the row has revenue or trip_fee > 0,
the driver was working that day → clear status_code and leave_status.
"""
from __future__ import annotations
import sys

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, select  # noqa: E402
import main  # noqa: E402
from models import DailyJob  # noqa: E402


def main_run(apply: bool = True) -> None:
    with Session(main.engine) as s:
        rows = s.exec(
            select(DailyJob).where(
                DailyJob.status_code == "leave",
                (DailyJob.revenue_customer > 0) | (DailyJob.trip_fee_driver > 0),
            )
        ).all()
        n = 0
        for r in rows:
            if apply:
                r.status_code = ""
                r.leave_status = ""
                s.add(r)
            n += 1
        if apply:
            s.commit()
        print(f"rows_fixed={n}  apply={apply}")


if __name__ == "__main__":
    main_run(apply="--apply" in sys.argv)
