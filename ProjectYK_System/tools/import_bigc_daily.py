"""Import BIGC daily (per-trip DailyJob + separate FuelTxn) from the monthly
'2564Daily Report (04.21).xlsx' files. See spec:
docs/superpowers/specs/2026-06-28-bigc-daily-import-design.md

Pure parse helpers (merge_header / clean_* / map_columns / row_to_record) carry
no DB or file dependency so they are unit-tested directly.
"""
from __future__ import annotations

import io
import sys
from datetime import date, datetime
from typing import Optional

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

_ERR = {"#DIV/0!", "#N/A", "#REF!", "#VALUE!", "-", "–", ""}


def merge_header(top: list, bottom: list) -> list:
    n = max(len(top), len(bottom))
    out = []
    for i in range(n):
        t = top[i] if i < len(top) and top[i] is not None else ""
        b = bottom[i] if i < len(bottom) and bottom[i] is not None else ""
        t = str(t).replace("\n", " ").strip()
        b = str(b).replace("\n", " ").strip()
        out.append((t + " " + b).strip() if b else t)
    return out


def clean_float(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        f = float(v)
        return 0.0 if (f != f or f in (float("inf"), float("-inf"))) else f
    s = str(v).strip().replace(",", "").replace(" ", "")
    if s in _ERR:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def clean_str(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s if s not in _ERR else ""


def clean_date(v) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            d = datetime.strptime(s, fmt).date()
            if 2015 <= d.year <= 2030:
                return d
        except ValueError:
            pass
    return None


def build_col_index(merged_header: list) -> dict:
    col = {}
    for idx, name in enumerate(merged_header):
        name = (name or "").strip()
        if name and name not in col:
            col[name] = idx
    return col


def find_col(col: dict, *names) -> Optional[int]:
    for n in names:                       # exact match ก่อน
        if n in col:
            return col[n]
    for n in names:                       # แล้วค่อย substring
        for h, idx in col.items():
            if n in h:
                return idx
    return None


def map_columns(merged_header: list) -> dict:
    col = build_col_index(merged_header)
    return {
        "work_date":   find_col(col, "วันที่"),
        "plate":       find_col(col, "ทะเบียน รถหัวลาก", "รถหัวลาก"),
        "tail_plate":  find_col(col, "ทะเบียน หางลาก", "หางลาก"),
        "driver":      find_col(col, "ชื่อ-นามสกุล", "ชื่อ"),
        "origin":      find_col(col, "รับตู้"),
        "store_code":  find_col(col, "รหัส สาขา", "สาขา"),
        "destination": find_col(col, "ที่ส่งสินค้า"),
        "doc_no":      find_col(col, "เลขที่ เอกสาร", "เอกสาร"),
        "revenue":     find_col(col, "ค่าขนส่ง"),
        "trip_fee":    find_col(col, "ค่าเที่ยวพขร", "ค่าเที่ยว"),
        "mile":        find_col(col, "เลขไมล์"),
        "fuel_liter":  find_col(col, "น้ำมันลิตร", "จำนวน น้ำมันลิตร"),
        "fuel_rate":   find_col(col, "เรท น้ำมัน"),
        "fuel_amount": find_col(col, "เงินบาท", "จำนวน เงินบาท"),
        "remark":      find_col(col, "หมายเหตุ"),
    }


def _g(row: list, idx: Optional[int]):
    return row[idx] if (idx is not None and idx < len(row)) else None


def row_to_record(row: list, C: dict, cycle_start: date, cycle_end: date) -> Optional[dict]:
    work_date = clean_date(_g(row, C["work_date"]))
    plate     = clean_str(_g(row, C["plate"]))
    driver    = clean_str(_g(row, C["driver"]))
    revenue   = clean_float(_g(row, C["revenue"]))
    trip_fee  = clean_float(_g(row, C["trip_fee"]))

    if not work_date and not any([plate, driver, revenue, trip_fee]):
        return None                       # แถวว่างล้วน
    if not work_date:
        return None
    if work_date < cycle_start or work_date > cycle_end:
        return None                       # นอกหน้าต่างรอบ

    liter  = clean_float(_g(row, C["fuel_liter"]))
    amount = clean_float(_g(row, C["fuel_amount"]))
    mile   = clean_float(_g(row, C["mile"]))
    rate   = clean_float(_g(row, C["fuel_rate"]))

    daily = {
        "work_date": work_date, "site_code": "BIGC",
        "driver_raw_name": driver,
        "plate_no_raw": plate,
        "tail_plate_raw": clean_str(_g(row, C["tail_plate"])),
        "origin": clean_str(_g(row, C["origin"])),
        "store_code": clean_str(_g(row, C["store_code"])),
        "destination": clean_str(_g(row, C["destination"])),
        "doc_no": clean_str(_g(row, C["doc_no"])),
        "revenue_customer": revenue,
        "trip_fee_driver": trip_fee,
        "fuel_liter": liter, "fuel_amount": amount,
        "fuel_rate_km_per_l": rate, "mile_snapshot": mile,
        "remark": clean_str(_g(row, C["remark"])),
    }

    fuel = None
    if liter > 0 or amount > 0:
        fuel = {
            "site_code": "BIGC", "txn_date": work_date,
            "plate_no_raw": plate, "driver_raw_name": driver,
            "liter": liter, "amount": amount,
            "price_per_liter": (amount / liter) if liter else 0.0,
            "rate_km_per_l": rate, "mile_snapshot": mile,
            "exclude_from_driver": True,
        }
    return {"daily": daily, "fuel": fuel}
