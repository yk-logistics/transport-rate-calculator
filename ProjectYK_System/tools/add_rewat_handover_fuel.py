"""add_rewat_handover_fuel.py — insert the 1/6 handover fuel bill for เรวัตร (emp 140).

โอ added this line to the AYU Google Sheet AFTER the last gsheet re-import, so it
never landed in the DB. โอ ruled (2026-06-30): หักเต็มเหมือนบิลอื่น → exclude_from_driver=0.

Line: 71-0556, 1/6, 122.58 L × 40.70 = 4,989.03 ฿, note "น้ำมันในถัง ขึ้นขับ".
Writes ONE FuelTxn row. Idempotent: refuses if a matching row already exists.
"""
from __future__ import annotations

import io
import sys
from datetime import date, datetime
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from sqlmodel import Session, select  # noqa: E402

from db_config import engine  # noqa: E402
from models import FuelTxn  # noqa: E402

TXN_DATE = date(2026, 6, 1)
PLATE = "71-0556"
EMP_ID = 140
LITER = 122.58
PRICE = 40.70
AMOUNT = 4989.03
NOTE = "น้ำมันในถัง ขึ้นขับ 1/6 (เรวัตรขึ้นขับ 71-0556) — โอใส่ในชีท AYU หลัง re-import; หักเต็ม"


def main() -> int:
    with Session(engine) as session:
        dup = session.exec(
            select(FuelTxn).where(
                FuelTxn.driver_id == EMP_ID,
                FuelTxn.txn_date == TXN_DATE,
                FuelTxn.plate_no_raw == PLATE,
                FuelTxn.amount == AMOUNT,
            )
        ).first()
        if dup is not None:
            print(f"SKIP — already exists (FuelTxn id={dup.id})")
            return 0

        row = FuelTxn(
            site_code="AYU",
            txn_date=TXN_DATE,
            plate_no_raw=PLATE,
            driver_id=EMP_ID,
            driver_raw_name="นายเรวัตร บันทะสารย์",
            liter=LITER,
            amount=AMOUNT,
            price_per_liter=PRICE,
            source="ayu_2026-06_handover_manual",
            note=NOTE,
            exclude_from_driver=False,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        print(f"INSERTED FuelTxn id={row.id}: {PLATE} {TXN_DATE} {LITER}L × {PRICE} = {AMOUNT} "
              f"exclude=0 driver={EMP_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
