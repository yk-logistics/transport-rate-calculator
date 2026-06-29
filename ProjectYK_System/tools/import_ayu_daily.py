"""Import AYU daily (per-trip DailyJob + FuelTxn) จากไฟล์
'Daily โฮมโปร-ทั่วไป.xlsx' ชีท 'Jun 26'. โครงคอลัมน์ AYU (verified 29มิ.ย.):

  0 วันที่ · 1 ทะเบียนรถ · 2 ประเภทรถ · 3 ชื่อ-พขร. · 4 ลูกค้า ·
  5 ขึ้นสินค้า(โหลด) · 6 รหัสสาขา · 7 ส่งสินค้า(ปลายทาง) · 8 เลขที่ ·
  9 ค่าขนส่ง · 10 ค่าเที่ยว พขร. · 11 ไมล์รถ · 12 ลิตร · 13 ราคา · 14 บาท · 15 หมายเหตุ

route AYU = ขึ้นสินค้า(pickup_location) → ส่งสินค้า(destination); ลูกค้า → customer_name_raw.
AYU รอบจ่าย = 26 → 25 เดือนถัดไป. cycle_tag 2026-06 = work_date 2026-05-26..2026-06-25.
แถวนอกหน้าต่าง (26-30 มิ.ย. = รอบถัดไป) ถูกตัดอัตโนมัติ.

reuse helper clean_* / make_engine จาก import_bigc_daily. FuelTxn exclude_from_driver?
— AYU บางคนเหมาน้ำมัน (ayu_mao) บางคนบริษัทออก. รอบนี้ตั้ง exclude_from_driver=True
(ไม่หักรายเที่ยว) เหมือน BigC; การหักจริงคิดที่ engine ผ่าน pay_mode. (โอยืนยันภายหลังได้)

idempotent: --wipe-prior ลบ source=ayu_<cycle> ก่อนเขียน. --dry-run นับ+ผลรวม ไม่เขียน.
"""
import io
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from import_bigc_daily import clean_float, clean_str, clean_date, make_engine  # noqa: E402

SALARY_BASE = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026"
SOURCE_PREFIX = "ayu_"

# cycle_tag → folder/file/sheet/window (AYU 26→25)
CYCLES = {
    "2026-06": {
        "file": rf"{SALARY_BASE}\6.Jun\AYU\Daily โฮมโปร-ทั่วไป.xlsx",
        "sheet": "Jun 26",
        "start": date(2026, 5, 26), "end": date(2026, 6, 25),
    },
}

# AYU column map (0-based, fixed layout — header row 0)
COL = {
    "work_date": 0, "plate": 1, "truck_type": 2, "driver": 3, "customer": 4,
    "pickup": 5, "store_code": 6, "destination": 7, "doc_no": 8,
    "revenue": 9, "trip_fee": 10, "mile": 11, "fuel_liter": 12,
    "fuel_price": 13, "fuel_amount": 14, "remark": 15,
}


def _g(row: list, idx: int):
    return row[idx] if idx < len(row) else None


def row_to_record(row: list, start: date, end: date) -> Optional[dict]:
    wd = clean_date(_g(row, COL["work_date"]))
    if not wd or wd < start or wd > end:
        return None
    plate = clean_str(_g(row, COL["plate"]))
    driver = clean_str(_g(row, COL["driver"]))
    revenue = clean_float(_g(row, COL["revenue"]))
    trip = clean_float(_g(row, COL["trip_fee"]))
    if not driver and not plate and not revenue and not trip:
        return None
    liter = clean_float(_g(row, COL["fuel_liter"]))
    amount = clean_float(_g(row, COL["fuel_amount"]))
    mile = clean_float(_g(row, COL["mile"]))
    customer = clean_str(_g(row, COL["customer"]))

    daily = {
        "work_date": wd, "site_code": "AYU",
        "driver_raw_name": driver,
        "plate_no_raw": plate,
        "truck_type_raw": clean_str(_g(row, COL["truck_type"])),
        "customer_name_raw": customer,
        "status_code": customer,           # AYU "งาน" = ลูกค้า (DHL/Oatside/HomePro)
        "pickup_location": clean_str(_g(row, COL["pickup"])),   # ขึ้นสินค้า (โหลด)
        "store_code": clean_str(_g(row, COL["store_code"])),
        "destination": clean_str(_g(row, COL["destination"])),  # ส่งสินค้า (ปลายทาง)
        "doc_no": clean_str(_g(row, COL["doc_no"])),
        "revenue_customer": revenue,
        "trip_fee_driver": trip,
        "fuel_liter": liter, "fuel_amount": amount,
        "mile_snapshot": mile,
        "remark": clean_str(_g(row, COL["remark"])),
    }
    fuel = None
    if liter > 0 or amount > 0:
        fuel = {
            "site_code": "AYU", "txn_date": wd,
            "plate_no_raw": plate, "driver_raw_name": driver,
            "liter": liter, "amount": amount,
            "price_per_liter": (amount / liter) if liter else 0.0,
            "mile_snapshot": mile, "exclude_from_driver": True,
        }
    return {"daily": daily, "fuel": fuel}


def parse_cycle(cycle_tag: str) -> dict:
    import openpyxl
    c = CYCLES[cycle_tag]
    wb = openpyxl.load_workbook(c["file"], data_only=True, read_only=True)
    rows = [list(r) for r in wb[c["sheet"]].iter_rows(values_only=True)]
    wb.close()
    records, sr, st, nf = [], 0.0, 0.0, 0
    for r in rows[1:]:
        rec = row_to_record(r, c["start"], c["end"])
        if rec is None:
            continue
        records.append(rec)
        sr += rec["daily"]["revenue_customer"]
        st += rec["daily"]["trip_fee_driver"]
        if rec["fuel"]:
            nf += 1
    return {"records": records, "sum_revenue": round(sr, 2),
            "sum_trip": round(st, 2), "n_jobs": len(records), "n_fuel": nf}


def write_cycle(cycle_tag: str, res: dict, wipe_prior: bool, engine=None):
    from sqlmodel import Session, select, delete
    from models import DailyJob, FuelTxn
    eng = engine or make_engine()
    src = f"{SOURCE_PREFIX}{cycle_tag}"
    with Session(eng) as s:
        if wipe_prior:
            old = s.exec(select(DailyJob).where(DailyJob.source == src)).all()
            old_ids = [d.id for d in old]
            if old_ids:
                s.exec(delete(FuelTxn).where(FuelTxn.daily_job_id.in_(old_ids)))
            s.exec(delete(DailyJob).where(DailyJob.source == src))
            s.commit()
        n_d = n_f = 0
        for rec in res["records"]:
            dj = DailyJob(source=src, **rec["daily"])
            s.add(dj)
            s.flush()
            n_d += 1
            if rec["fuel"]:
                s.add(FuelTxn(source=src, daily_job_id=dj.id, **rec["fuel"]))
                n_f += 1
        s.commit()
    print(f"  wrote DailyJob={n_d} FuelTxn={n_f} (source={src})")


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--cycle", default="2026-06")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wipe-prior", action="store_true")
    args = ap.parse_args()
    ct = args.cycle
    if ct not in CYCLES:
        raise SystemExit(f"unknown cycle {ct}; valid {list(CYCLES)}")
    if not os.path.exists(CYCLES[ct]["file"]):
        raise SystemExit(f"file not found: {CYCLES[ct]['file']}")
    res = parse_cycle(ct)
    print(f"--- AYU {ct} (source={SOURCE_PREFIX}{ct}) ---")
    print(f"  jobs={res['n_jobs']}  fuel={res['n_fuel']}")
    print(f"  SUM ค่าขนส่ง  = {res['sum_revenue']:,.2f}")
    print(f"  SUM ค่าเที่ยว = {res['sum_trip']:,.2f}")
    if not args.dry_run:
        write_cycle(ct, res, wipe_prior=args.wipe_prior)


if __name__ == "__main__":
    main()
