"""
Import LCB daily data for cycle 2026-05-16 – 2026-06-15 (pay Jun 2026, cycle_tag 2026-06)
Source: Google Sheet 'Daily LCB' (เดลี่แหลม), tab "Daily 16.05.69 - 15.06.69"  — pulled live via gspread.

Mirror of import_lcb_jan2026.py, but reads rows directly from the live sheet (โอ's "แบบ 1").
Column mapping verified against the tab header (2026-06-18) before import.
Source tag: 'lcb_may-jun2026'  (safe rollback with --wipe-prior).

เงินเบิก / ค่าเสียเวลา columns are intentionally NOT imported (โอ: those live in สดย่อย/petty cash).

Run (from repo root "Project YK", with app venv that has gspread):
  ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/import_lcb_may_jun2026.py --dry-run
  ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/import_lcb_may_jun2026.py --wipe-prior
  ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/import_lcb_may_jun2026.py
"""
from __future__ import annotations

import io
import sys
from argparse import ArgumentParser
from datetime import date, datetime
from typing import Optional

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, SYSTEM_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

import gspread  # noqa: E402
from sqlmodel import Session, create_engine, delete, select  # noqa: E402

import models  # noqa: E402
from models import DailyJob, DailyJobFee, FuelTxn  # noqa: E402

DB_PATH = APP_DIR / "app.db"
KEY_FILE = (SYSTEM_DIR.parent / "noble-history-446303-e4-c36409a0122c.json")
SHEET_ID = "1Tm1i7kHGkiYtNwM-HQWEnQReg6VZmLzj7T1DjXr8zqg"
TAB_NAME = "Daily 16.05.69 - 15.06.69"
IMPORT_SOURCE = "lcb_may-jun2026"
CYCLE_START = date(2026, 5, 16)
CYCLE_END   = date(2026, 6, 15)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# Fee columns by header name → fee_type (driver-pay side). Note: OT here = col AN "OT"
# (driver overtime), NOT col V "ค่าล่วงเวลา" (customer-charge side) — confirmed with โอ.
FEE_HEADERS = {
    "ค่ายกตู้":           "lift",
    "ค่าผ่านลาน":         "yard",
    "ค่าคลีน":            "clean",
    "ค่าชอร์":            "shore",
    "เข้าท่า":            "port_entry",
    "ค่าชั่งน้ำหนัก":    "weighing",
    "รับตู้/คืนตู้แทน":  "pickup_return",
    "OT":                 "ot",
    "พิเศษ":              "special",
    "M-Flow":             "mflow",
}


def _date(v) -> Optional[date]:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            d = datetime.strptime(s, fmt).date()
            if 2015 <= d.year <= 2030:
                return d
        except ValueError:
            pass
    return None


def _float(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        try:
            f = float(v)
            return 0.0 if (f != f or f in (float("inf"), float("-inf"))) else f
        except (ValueError, TypeError):
            return 0.0
    s = str(v).strip().replace(",", "").replace(" ", "")
    if s in ("-", "–", "", "#DIV/0!", "#N/A", "#REF!", "#VALUE!"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _str(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s if s not in ("-", "–", "#DIV/0!", "#N/A", "#REF!", "#VALUE!") else ""


def build_col_map(header_row: list) -> dict:
    """Map header text → column index (0-based). First occurrence wins."""
    col = {}
    for idx, v in enumerate(header_row):
        if v and str(v).strip() and str(v).strip() not in col:
            col[str(v).strip()] = idx
    return col


def wipe_prior(session: Session) -> int:
    jobs = session.exec(select(DailyJob).where(DailyJob.source == IMPORT_SOURCE)).all()
    ids = [j.id for j in jobs]
    if ids:
        session.exec(delete(DailyJobFee).where(DailyJobFee.daily_job_id.in_(ids)))  # type: ignore[attr-defined]
        session.exec(delete(FuelTxn).where(FuelTxn.daily_job_id.in_(ids)))          # type: ignore[attr-defined]
        session.exec(delete(DailyJob).where(DailyJob.source == IMPORT_SOURCE))
    session.commit()
    return len(ids)


def fetch_rows() -> list:
    gc = gspread.service_account(filename=str(KEY_FILE))
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(TAB_NAME)
    return ws.get_all_values()  # rows as strings; row1=totals, row2=header, row3+=data


def run_import(dry_run: bool = False) -> None:
    all_rows = fetch_rows()
    if len(all_rows) < 3:
        print(f"ERROR: tab '{TAB_NAME}' has fewer than 3 rows.")
        return

    col = build_col_map(all_rows[1])

    # Header substrings to tolerate the long header labels (e.g. "STARTDING (...)").
    def find(*names) -> Optional[int]:
        for n in names:                       # exact first
            if n in col:
                return col[n]
        for n in names:                       # substring fallback
            for h, idx in col.items():
                if n in h:
                    return idx
        return None

    C = {
        "work_date":        find("วันที่"),
        "status":           find("Status"),
        "plate":            find("ทะเบียนรถ"),
        "truck_type":       find("ประเภท"),
        "driver":           find("พนักงานขับรถ"),
        "phone":            find("เบอร์โทร"),
        "trip_type":        find("Type"),
        "starting_point":   find("STARTDING"),
        "loading_point":    find("Loading"),
        "destination":      find("Destination"),
        "job_ref":          find("Job."),
        "bl_booking":       find("BL./Booking"),
        "container_no":     find("เบอร์ตู้"),
        "container_size":   find("ขนาด"),
        "revenue_customer": find("ค่าขนส่ง"),          # exact "ค่าขนส่ง" (Y), not "รวมเก็บค่าขนส่ง"
        "revenue_total":    find("รวมเก็บค่าขนส่ง"),    # Z
        "wht_53":           find("หัก ณ ที่จ่าย"),
        "invoice_no":       find("ออกอินวอย"),
        "invoice_date":     find("ลงวันที่"),
        "mile":             find("ไมล์"),
        "fuel_l":           find("น้ำมัน(ลิตร)"),
        "fuel_amt":         find("น้ำมัน(บาท)"),
        "fuel_rate":        find("เรท กม/ล"),
        "trip_fee":         find("ค่าเที่ยวพขร."),
        "shared_vehicle":   find("ใช้รถร่วม"),
        "receive_invno":    find("Receive/Inv.No."),
        "remark":           find("หมายเหตุ"),
    }
    missing = [k for k in ("work_date", "plate", "driver", "revenue_total", "trip_fee") if C[k] is None]
    if missing:
        print(f"[BLOCKED] critical columns not found: {missing}")
        return

    fee_cols = {col[h]: ft for h, ft in FEE_HEADERS.items() if h in col}

    print(f"Tab: {TAB_NAME}  |  {len(all_rows)-2} data rows")
    print(f"Cycle: {CYCLE_START} – {CYCLE_END}  |  source={IMPORT_SOURCE}  |  dry_run={dry_run}")
    print(f"Key cols: driver={C['driver']}, trip_fee={C['trip_fee']}, "
          f"rev_cust={C['revenue_customer']}, rev_total={C['revenue_total']}, fuel_l={C['fuel_l']}")

    stats = {"jobs": 0, "fees": 0, "fuel": 0, "skip_empty": 0,
             "skip_nodate": 0, "skip_outrange": 0,
             "sum_trip_fee": 0.0, "sum_revenue": 0.0}

    def g(row, key):
        idx = C.get(key)
        return row[idx] if idx is not None and idx < len(row) else None

    with Session(engine) as session:
        for data_row in all_rows[2:]:
            if not data_row:
                continue
            row = list(data_row)

            work_date = _date(g(row, "work_date"))
            plate     = _str(g(row, "plate"))
            driver    = _str(g(row, "driver"))
            rev_cust  = _float(g(row, "revenue_customer"))
            rev_total = _float(g(row, "revenue_total"))
            trip_fee  = _float(g(row, "trip_fee"))

            if not work_date and not any([plate, driver, rev_total, trip_fee]):
                stats["skip_empty"] += 1
                continue
            if not work_date:
                stats["skip_nodate"] += 1
                continue
            if work_date < CYCLE_START or work_date > CYCLE_END:
                stats["skip_outrange"] += 1
                continue

            phone = _str(g(row, "phone"))
            note_parts = []
            if phone and phone != "-":
                note_parts.append(f"tel={phone}")
            bl = _str(g(row, "bl_booking"))
            if bl:
                note_parts.append(f"bl={bl}")
            shared = _str(g(row, "shared_vehicle"))
            if shared:
                note_parts.append(f"shared={shared}")
            recv = _str(g(row, "receive_invno"))
            if recv:
                note_parts.append(f"receive={recv}")
            remark = _str(g(row, "remark"))
            note = " | ".join(note_parts)
            final_note = f"{remark} || {note}" if remark and note else (remark or note)

            fuel_l    = _float(g(row, "fuel_l"))
            fuel_amt  = _float(g(row, "fuel_amt"))
            fuel_rate = _float(g(row, "fuel_rate"))
            mile      = _float(g(row, "mile"))

            stats["jobs"] += 1
            stats["sum_trip_fee"] += trip_fee
            stats["sum_revenue"] += rev_total

            if dry_run:
                continue

            dj = DailyJob(
                work_date=work_date, site_code="LCB",
                driver_raw_name=driver,
                plate_no_raw=plate,
                truck_type_raw=_str(g(row, "truck_type")),
                trip_type_code=_str(g(row, "trip_type")),
                status_code=_str(g(row, "status")),
                origin=_str(g(row, "starting_point")),
                pickup_location=_str(g(row, "loading_point")),
                destination=_str(g(row, "destination")),
                job_ref=_str(g(row, "job_ref")),
                container_no=_str(g(row, "container_no")),
                container_size=_str(g(row, "container_size")),
                revenue_customer=rev_cust if rev_cust else rev_total,
                trip_fee_driver=trip_fee,
                fuel_liter=fuel_l, fuel_amount=fuel_amt,
                fuel_rate_km_per_l=fuel_rate, mile_snapshot=mile,
                invoice_no=_str(g(row, "invoice_no")),
                invoice_date=_date(g(row, "invoice_date")),
                wht_53=_float(g(row, "wht_53")),
                remark=final_note,
                source=IMPORT_SOURCE,
            )
            session.add(dj)
            session.flush()

            for col_idx, fee_type in fee_cols.items():
                amt = _float(row[col_idx]) if col_idx < len(row) else 0.0
                if amt:
                    session.add(DailyJobFee(daily_job_id=dj.id, fee_type=fee_type, amount=amt))
                    stats["fees"] += 1

            if fuel_l > 0 or fuel_amt > 0:
                session.add(FuelTxn(
                    site_code="LCB", txn_date=work_date,
                    plate_no_raw=plate, driver_raw_name=driver,
                    liter=fuel_l, amount=fuel_amt,
                    price_per_liter=(fuel_amt / fuel_l) if fuel_l else 0,
                    mile_snapshot=mile,
                    daily_job_id=dj.id, source=IMPORT_SOURCE,
                ))
                stats["fuel"] += 1

        if not dry_run:
            session.commit()

    print(f"\nResult: jobs={stats['jobs']}  fees={stats['fees']}  fuel={stats['fuel']}")
    print(f"Skipped: empty={stats['skip_empty']}  no_date={stats['skip_nodate']}  "
          f"out_of_range={stats['skip_outrange']}")
    print(f"SUM trip_fee (driver pay) = {stats['sum_trip_fee']:,.2f}")
    print(f"SUM revenue_total         = {stats['sum_revenue']:,.2f}")
    if dry_run:
        print("(dry-run — nothing written to DB)")


def main() -> None:
    ap = ArgumentParser()
    ap.add_argument("--wipe-prior", action="store_true",
                    help="delete existing source='lcb_may-jun2026' rows before import")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and count rows without writing to DB")
    args = ap.parse_args()

    if not KEY_FILE.exists():
        print(f"ERROR: service-account key not found: {KEY_FILE}")
        return

    if args.wipe_prior and not args.dry_run:
        with Session(engine) as s:
            n = wipe_prior(s)
        print(f"Wiped {n} existing {IMPORT_SOURCE} DailyJob rows")

    run_import(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
