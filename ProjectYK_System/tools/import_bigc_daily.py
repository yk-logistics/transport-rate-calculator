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


# ──────────────────────────────────────────────────────────────────────────
# CLI layer: cycle → folder/window/source + dry-run / write
# ──────────────────────────────────────────────────────────────────────────
import os                                          # noqa: E402
from pathlib import Path                           # noqa: E402

# ราก Work\Salary — แก้ที่เดียวถ้าย้ายเครื่อง
SALARY_BASE = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026"
PRIMARY_FILE = "2564Daily Report (04.21).xlsx"
DATA_SHEET = "เดือน06.21"
SOURCE_PREFIX = "bigc_"

# cycle_tag → โฟลเดอร์เดือนถัดไป + หน้าต่างวันที่ (1 → สิ้นเดือน)
CYCLES = {
    "2025-12": {"folder": "1.Jan", "start": date(2025, 12, 1), "end": date(2025, 12, 31)},
    "2026-01": {"folder": "2.Feb", "start": date(2026, 1, 1),  "end": date(2026, 1, 31)},
    "2026-02": {"folder": "3.Mar", "start": date(2026, 2, 1),  "end": date(2026, 2, 28)},
    "2026-03": {"folder": "4.Apr", "start": date(2026, 3, 1),  "end": date(2026, 3, 31)},
    "2026-04": {"folder": "5.May", "start": date(2026, 4, 1),  "end": date(2026, 4, 30)},
    "2026-05": {"folder": "6.Jun", "start": date(2026, 5, 1),  "end": date(2026, 5, 31)},
}


def cycle_xlsx_path(cycle_tag: str) -> str:
    c = CYCLES[cycle_tag]
    return os.path.join(SALARY_BASE, c["folder"], "BigC", PRIMARY_FILE)


def load_rows(xlsx_path: str, sheet: str = DATA_SHEET) -> list:
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb[sheet]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def parse_cycle(cycle_tag: str) -> dict:
    c = CYCLES[cycle_tag]
    rows = load_rows(cycle_xlsx_path(cycle_tag))
    if len(rows) < 3:
        raise SystemExit(f"sheet has <3 rows for {cycle_tag}")
    merged = merge_header(rows[1], rows[2])
    C = map_columns(merged)
    missing = [k for k in ("work_date", "plate", "driver", "revenue", "trip_fee") if C[k] is None]
    if missing:
        raise SystemExit(f"[BLOCKED] {cycle_tag}: critical cols not found: {missing}\n"
                         f"headers: {merged}")
    records, sr, st, nf = [], 0.0, 0.0, 0
    for r in rows[3:]:
        rec = row_to_record(r, C, c["start"], c["end"])
        if rec is None:
            continue
        records.append(rec)
        sr += rec["daily"]["revenue_customer"]
        st += rec["daily"]["trip_fee_driver"]
        if rec["fuel"]:
            nf += 1
    return {"records": records, "sum_revenue": round(sr, 2),
            "sum_trip": round(st, 2), "n_jobs": len(records), "n_fuel": nf}


def _print_dry(cycle_tag: str, res: dict) -> None:
    print(f"--- {cycle_tag}  (source={SOURCE_PREFIX}{cycle_tag}) ---")
    print(f"  jobs={res['n_jobs']}  fuel={res['n_fuel']}")
    print(f"  SUM revenue (ค่าขนส่ง)  = {res['sum_revenue']:,.2f}")
    print(f"  SUM trip_fee (ค่าเที่ยว) = {res['sum_trip']:,.2f}")


# ── DB write layer ──
_APP_ADDED = False


def _ensure_app_on_path() -> None:
    global _APP_ADDED
    if not _APP_ADDED:
        app_dir = Path(__file__).resolve().parents[1] / "app"
        sys.path.insert(0, str(app_dir))
        _APP_ADDED = True


def make_engine(db_path: Optional[str] = None):
    from sqlmodel import create_engine
    if db_path is None:
        db_path = str(Path(__file__).resolve().parents[1] / "app" / "app.db")
    return create_engine(f"sqlite:///{db_path}", echo=False,
                         connect_args={"check_same_thread": False})


def _wipe_source(session, source_tag: str) -> int:
    """ลบ DailyJob (+ FuelTxn ที่ผูก) ของ source tag เดียวเท่านั้น — ไม่ลบด้วย date/site."""
    _ensure_app_on_path()
    from sqlmodel import delete, select
    from models import DailyJob, FuelTxn
    jobs = session.exec(select(DailyJob).where(DailyJob.source == source_tag)).all()
    ids = [j.id for j in jobs]
    if ids:
        session.exec(delete(FuelTxn).where(FuelTxn.daily_job_id.in_(ids)))   # type: ignore[attr-defined]
        session.exec(delete(DailyJob).where(DailyJob.source == source_tag))
    session.commit()
    return len(ids)


def write_cycle(cycle_tag: str, res: dict, wipe_prior: bool = False, engine=None) -> dict:
    _ensure_app_on_path()
    from sqlmodel import Session
    from models import DailyJob, FuelTxn
    src = SOURCE_PREFIX + cycle_tag
    eng = engine or make_engine()
    n_jobs = n_fuel = 0
    with Session(eng) as s:
        if wipe_prior:
            removed = _wipe_source(s, src)
            print(f"  wiped {removed} prior rows ({src})")
        for rec in res["records"]:
            dj = DailyJob(source=src, **rec["daily"])
            s.add(dj)
            s.flush()
            n_jobs += 1
            if rec["fuel"]:
                s.add(FuelTxn(source=src, daily_job_id=dj.id, **rec["fuel"]))
                n_fuel += 1
        s.commit()
    print(f"  wrote jobs={n_jobs} fuel={n_fuel} ({src})")
    return {"jobs": n_jobs, "fuel": n_fuel}


def main() -> None:
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--cycle", help="cycle_tag เดียว เช่น 2026-05; ไม่ใส่ = ทุก cycle")
    ap.add_argument("--dry-run", action="store_true", help="parse + นับ ไม่เขียน DB")
    ap.add_argument("--wipe-prior", action="store_true",
                    help="ลบ source=bigc_<cycle> เดิมก่อนเขียน (เขียนจริงเท่านั้น)")
    args = ap.parse_args()

    cycles = [args.cycle] if args.cycle else list(CYCLES.keys())
    for ct in cycles:
        if ct not in CYCLES:
            raise SystemExit(f"unknown cycle {ct}; valid: {list(CYCLES.keys())}")
        path = cycle_xlsx_path(ct)
        if not os.path.exists(path):
            print(f"--- {ct} --- SKIP: ไฟล์ไม่พบ {path}")
            continue
        res = parse_cycle(ct)
        if args.dry_run:
            _print_dry(ct, res)
        else:
            write_cycle(ct, res, wipe_prior=args.wipe_prior)   # defined in Task 3


if __name__ == "__main__":
    main()
