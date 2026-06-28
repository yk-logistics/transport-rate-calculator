# BIGC Daily Import — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** นำเดลี่รายเที่ยว BIGC 6 เดือน (cycle_tag 2025-12 → 2026-05) เข้าระบบเป็น `DailyJob` (+ FuelTxn แยก) โดยไม่แตะ payrun net ที่ลอกจากแบงค์ไว้

**Architecture:** importer ตัวใหม่ `import_bigc_daily.py` เลียนโครง `import_lcb_may_jun2026_xlsx.py` — แยก "ชั้น parse บริสุทธิ์" (รวมหัว 2 แถว, ทำความสะอาดค่า, column-map by header, แปลงแถว→dict) ออกมาให้ unit-test ได้โดยไม่แตะ DB/ไฟล์จริง แล้วชั้น CLI รับ `--cycle YYYY-MM` map ไป folder/หน้าต่างวันที่/source tag พร้อม `--dry-run`/`--wipe-prior`

**Tech Stack:** Python 3.12, openpyxl (read-only data_only), SQLModel + SQLite (`app.db`), pytest (in-memory `sqlite://`)

## Global Constraints

- ไซต์ = `BIGC`; รอบจ่าย BIGC = วันที่ 1 → วันสุดท้ายของเดือน; cycle_tag = `YYYY-MM` ของเดือนนั้น
- source tag = `bigc_<cycle_tag>` (1 ตัว/เดือน); `--wipe-prior` ลบ **เฉพาะ source tag เดือนนั้น** ไม่ลบด้วย work_date/site
- ไม่เปลี่ยน schema — ใช้ field ที่มีอยู่ใน `DailyJob`/`FuelTxn`/`DailyJobFee` เท่านั้น
- ไม่แตะ `models.py`, `main.py`, services, templates, payrun/PayRunItem, LCB, AYU
- `FuelTxn.exclude_from_driver = True` เสมอสำหรับน้ำมัน BIGC (เงินเดือน ไม่หักน้ำมันคนขับ)
- ไฟล์ต้นทาง: โฟลเดอร์เดือน **ถัดไป** ของ cycle, ไฟล์ `2564Daily Report (04.21).xlsx`, ชีต `เดือน06.21`
- เชื่อ **วันที่ในเซลล์** ไม่เชื่อชื่อไฟล์; กรองแถวให้อยู่ในหน้าต่าง cycle เท่านั้น
- critical columns (block ถ้าไม่เจอ): `work_date`, `plate`, `driver`, `revenue`, `trip_fee`
- ทุก task รันจากราก repo `Project YK`; python = `ProjectYK_System/app/.venv/Scripts/python.exe`
- test รันด้วย: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest <path> -v` (จากใน `ProjectYK_System/app`)

---

## File Structure

- **Create** `ProjectYK_System/tools/import_bigc_daily.py` — importer (parse layer + CLI)
- **Create** `ProjectYK_System/app/tests/test_import_bigc_daily.py` — unit tests ของ parse layer
- ไม่มีไฟล์อื่นถูกแก้

---

## Task 1: BIGC parse layer (header-merge, cleaners, column-map, row→record)

**Files:**
- Create: `ProjectYK_System/tools/import_bigc_daily.py`
- Test: `ProjectYK_System/app/tests/test_import_bigc_daily.py`

**Interfaces:**
- Produces (ฟังก์ชันบริสุทธิ์ที่ task หลัง/test เรียก):
  - `merge_header(top: list, bottom: list) -> list[str]` — รวมหัว 2 แถวเป็นชื่อเดียวต่อคอลัมน์ (`"top bottom"` ตัดช่องว่าง; ถ้า bottom ว่าง = top เฉย ๆ)
  - `clean_float(v) -> float` และ `clean_str(v) -> str` — ทำความสะอาด `#DIV/0! / #N/A / #REF! / #VALUE! / - / –`, คอมมา, ช่องว่าง
  - `clean_date(v) -> datetime.date | None`
  - `build_col_index(merged_header: list[str]) -> dict[str,int]` — header→index (ตัวแรกที่เจอ)
  - `find_col(col: dict, *substrings) -> int | None` — exact ก่อน แล้วค่อย substring (เลียน LCB `find()`)
  - `map_columns(merged_header: list[str]) -> dict[str,int|None]` — คืน dict คีย์ field ของเรา → index
  - `row_to_record(row: list, C: dict, cycle_start, cycle_end) -> dict | None` — คืน dict
    `{daily: {...}, fuel: {...}|None}` หรือ `None` ถ้าแถวควร skip (ไม่มี work_date / นอกหน้าต่าง / ว่างล้วน)

- [ ] **Step 1: เขียน test ที่ fail — merge_header + cleaners**

สร้าง `ProjectYK_System/app/tests/test_import_bigc_daily.py`:

```python
"""BIGC daily importer — pure parse-layer unit tests (no DB, no real files)."""
import sys
from datetime import date
from pathlib import Path

# importer อยู่ใต้ tools/ — เพิ่ม path ให้ import ได้
TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

import import_bigc_daily as imp  # noqa: E402


def test_merge_header_joins_two_rows():
    top    = ["วันที่", "ทะเบียน", "ทะเบียน", "ชื่อ-นามสกุล", "ค่าขนส่ง", "ค่าเที่ยวพขร"]
    bottom = ["รับงาน", "รถหัวลาก", "หางลาก", None,           "โดยประมาณ", "จุดพ่วง/BH"]
    out = imp.merge_header(top, bottom)
    assert out[0] == "วันที่ รับงาน"
    assert out[1] == "ทะเบียน รถหัวลาก"
    assert out[2] == "ทะเบียน หางลาก"
    assert out[3] == "ชื่อ-นามสกุล"          # bottom ว่าง → top เฉย ๆ
    assert out[4] == "ค่าขนส่ง โดยประมาณ"


def test_clean_float_handles_excel_errors():
    assert imp.clean_float("#DIV/0!") == 0.0
    assert imp.clean_float("-") == 0.0
    assert imp.clean_float("1,234.5") == 1234.5
    assert imp.clean_float(None) == 0.0
    assert imp.clean_float(600) == 600.0


def test_clean_str_blanks_dash_and_errors():
    assert imp.clean_str("-") == ""
    assert imp.clean_str("#N/A") == ""
    assert imp.clean_str("  PTT B20  ") == "PTT B20"
    assert imp.clean_str(None) == ""
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run (จากใน `ProjectYK_System/app`):
`.venv/Scripts/python.exe -m pytest tests/test_import_bigc_daily.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'import_bigc_daily'`

- [ ] **Step 3: เขียน parse layer ขั้นต่ำให้ test ผ่าน**

สร้าง `ProjectYK_System/tools/import_bigc_daily.py` (เฉพาะส่วน parse + helper ก่อน):

```python
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


def merge_header(top: list, bottom: list) -> list[str]:
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
```

- [ ] **Step 4: รัน test ให้ผ่าน (3 ตัวแรก)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_import_bigc_daily.py -v`
Expected: PASS ทั้ง 3 (`test_merge_header_joins_two_rows`, `test_clean_float_handles_excel_errors`, `test_clean_str_blanks_dash_and_errors`)

- [ ] **Step 5: เขียน test ที่ fail — column-map + row_to_record**

เพิ่มท้ายไฟล์ test:

```python
# หัวรวมจริงของ BIGC (index 0..18) ตาม spec section 4
BIGC_MERGED = [
    "วันที่ รับงาน", "ทะเบียน รถหัวลาก", "ทะเบียน หางลาก", "ชื่อ-นามสกุล",
    "รับตู้ สถานที่", "รหัส สาขา", "ที่ส่งสินค้า สถานที่", "เลขที่ เอกสาร",
    "ค่าขนส่ง โดยประมาณ", "ค่าเที่ยวพขร จุดพ่วง/BH", "เงินเดือน",
    "น้ำมันที่ กำหนด", "เลขไมล์ ตอนเติม", "จำนวน น้ำมันลิตร",
    "ราคาน้ำมัน ฿ / L", "จำนวน เงินบาท", "เรท น้ำมัน", "จำนวน น้ำมันทำได้",
    "หมายเหตุ",
]


def test_map_columns_finds_money_and_fuel():
    C = imp.map_columns(BIGC_MERGED)
    assert C["work_date"] == 0
    assert C["plate"] == 1
    assert C["tail_plate"] == 2
    assert C["driver"] == 3
    assert C["revenue"] == 8          # ค่าขนส่ง = รายได้
    assert C["trip_fee"] == 9         # ค่าเที่ยวพขร = เงินคนขับ
    assert C["fuel_liter"] == 13
    assert C["fuel_amount"] == 15
    assert C["remark"] == 18


CYC_START, CYC_END = date(2026, 5, 1), date(2026, 5, 31)


def _row(d, plate="71-8001", driver="ธนวัฒน์", rev=600.0, trip=200.0,
         liter=159.76, baht=5400.0, note="PTT B20"):
    r = [None] * 19
    r[0] = d; r[1] = plate; r[2] = "-"; r[3] = driver
    r[8] = rev; r[9] = trip; r[13] = liter; r[15] = baht; r[18] = note
    return r


def test_row_to_record_maps_trip_and_fuel():
    C = imp.map_columns(BIGC_MERGED)
    rec = imp.row_to_record(_row(date(2026, 5, 1)), C, CYC_START, CYC_END)
    assert rec is not None
    assert rec["daily"]["site_code"] == "BIGC"
    assert rec["daily"]["driver_raw_name"] == "ธนวัฒน์"
    assert rec["daily"]["revenue_customer"] == 600.0
    assert rec["daily"]["trip_fee_driver"] == 200.0
    assert rec["fuel"]["liter"] == 159.76
    assert rec["fuel"]["amount"] == 5400.0
    assert rec["fuel"]["exclude_from_driver"] is True
    assert round(rec["fuel"]["price_per_liter"], 2) == round(5400.0 / 159.76, 2)


def test_row_to_record_keeps_idle_row_without_fuel():
    # รถจอด: ไม่มีรายได้/ค่าเที่ยว/น้ำมัน แต่มีวันที่+ชื่อ → เก็บแถว, fuel=None
    C = imp.map_columns(BIGC_MERGED)
    rec = imp.row_to_record(
        _row(date(2026, 5, 2), rev=0, trip=0, liter=0, baht=0, note=""),
        C, CYC_START, CYC_END)
    assert rec is not None
    assert rec["fuel"] is None
    assert rec["daily"]["revenue_customer"] == 0.0


def test_row_to_record_skips_out_of_window():
    C = imp.map_columns(BIGC_MERGED)
    assert imp.row_to_record(_row(date(2026, 1, 31)), C, CYC_START, CYC_END) is None


def test_row_to_record_skips_empty():
    C = imp.map_columns(BIGC_MERGED)
    blank = [None] * 19
    assert imp.row_to_record(blank, C, CYC_START, CYC_END) is None
```

- [ ] **Step 6: รัน test ใหม่ให้เห็น fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_import_bigc_daily.py -v`
Expected: FAIL — `AttributeError: module 'import_bigc_daily' has no attribute 'map_columns'`

- [ ] **Step 7: เขียน column-map + row_to_record ให้ผ่าน**

เพิ่มใน `import_bigc_daily.py`:

```python
def build_col_index(merged_header: list[str]) -> dict:
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


def map_columns(merged_header: list[str]) -> dict:
    col = build_col_index(merged_header)
    return {
        "work_date":  find_col(col, "วันที่"),
        "plate":      find_col(col, "ทะเบียน รถหัวลาก", "รถหัวลาก"),
        "tail_plate": find_col(col, "ทะเบียน หางลาก", "หางลาก"),
        "driver":     find_col(col, "ชื่อ-นามสกุล", "ชื่อ"),
        "origin":     find_col(col, "รับตู้"),
        "store_code": find_col(col, "รหัส สาขา", "สาขา"),
        "destination": find_col(col, "ที่ส่งสินค้า"),
        "doc_no":     find_col(col, "เลขที่ เอกสาร", "เอกสาร"),
        "revenue":    find_col(col, "ค่าขนส่ง"),
        "trip_fee":   find_col(col, "ค่าเที่ยวพขร", "ค่าเที่ยว"),
        "mile":       find_col(col, "เลขไมล์"),
        "fuel_liter": find_col(col, "น้ำมันลิตร", "จำนวน น้ำมันลิตร"),
        "fuel_rate":  find_col(col, "เรท น้ำมัน"),
        "fuel_amount": find_col(col, "เงินบาท", "จำนวน เงินบาท"),
        "remark":     find_col(col, "หมายเหตุ"),
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

    liter   = clean_float(_g(row, C["fuel_liter"]))
    amount  = clean_float(_g(row, C["fuel_amount"]))
    mile    = clean_float(_g(row, C["mile"]))
    rate    = clean_float(_g(row, C["fuel_rate"]))

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
```

- [ ] **Step 8: รัน test ทั้งไฟล์ให้ผ่านหมด**

Run: `.venv/Scripts/python.exe -m pytest tests/test_import_bigc_daily.py -v`
Expected: PASS ทั้ง 9 ตัว

- [ ] **Step 9: Commit**

```bash
git add ProjectYK_System/tools/import_bigc_daily.py ProjectYK_System/app/tests/test_import_bigc_daily.py
git commit -m "feat(import): BIGC parse layer (header-merge + column-map + row→record) TDD"
```

---

## Task 2: CLI (cycle→folder/window/source map) + dry-run ทั้ง 6 เดือน

**Files:**
- Modify: `ProjectYK_System/tools/import_bigc_daily.py` (เพิ่ม CLI + loader + dry-run report; ไม่แตะ parse layer)

**Interfaces:**
- Consumes: `merge_header`, `map_columns`, `row_to_record`, `clean_*` จาก Task 1
- Produces:
  - `CYCLES: dict[str, dict]` — `{"2026-05": {"folder": "6.Jun", "start": date(2026,5,1), "end": date(2026,5,31)}, ...}` ครบ 6 cycle (2025-12 → 2026-05)
  - `load_rows(xlsx_path: str, sheet="เดือน06.21") -> list[list]`
  - `parse_cycle(cycle_tag: str) -> dict` — อ่านไฟล์จริง คืน
    `{"records":[...], "sum_revenue":float, "sum_trip":float, "n_jobs":int, "n_fuel":int}` (parse อย่างเดียว ไม่เขียน DB)

- [ ] **Step 1: เพิ่ม CYCLES map + loader + parse_cycle**

เพิ่มใน `import_bigc_daily.py` (ใต้ parse layer):

```python
import os
from pathlib import Path

# ราก Work\Salary — แก้ที่เดียวถ้าย้ายเครื่อง
SALARY_BASE = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026"
PRIMARY_FILE = "2564Daily Report (04.21).xlsx"
DATA_SHEET = "เดือน06.21"

# cycle_tag → โฟลเดอร์เดือนถัดไป + หน้าต่างวันที่ (1 → สิ้นเดือน)
CYCLES = {
    "2025-12": {"folder": "1.Jan", "start": date(2025, 12, 1),  "end": date(2025, 12, 31)},
    "2026-01": {"folder": "2.Feb", "start": date(2026, 1, 1),   "end": date(2026, 1, 31)},
    "2026-02": {"folder": "3.Mar", "start": date(2026, 2, 1),   "end": date(2026, 2, 28)},
    "2026-03": {"folder": "4.Apr", "start": date(2026, 3, 1),   "end": date(2026, 3, 31)},
    "2026-04": {"folder": "5.May", "start": date(2026, 4, 1),   "end": date(2026, 4, 30)},
    "2026-05": {"folder": "6.Jun", "start": date(2026, 5, 1),   "end": date(2026, 5, 31)},
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
```

- [ ] **Step 2: เพิ่ม CLI + dry-run report + (stub) write**

เพิ่มท้ายไฟล์:

```python
SOURCE_PREFIX = "bigc_"


def _print_dry(cycle_tag: str, res: dict) -> None:
    print(f"--- {cycle_tag}  (source={SOURCE_PREFIX}{cycle_tag}) ---")
    print(f"  jobs={res['n_jobs']}  fuel={res['n_fuel']}")
    print(f"  SUM revenue (ค่าขนส่ง) = {res['sum_revenue']:,.2f}")
    print(f"  SUM trip_fee (ค่าเที่ยว) = {res['sum_trip']:,.2f}")


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
            write_cycle(ct, res, wipe_prior=args.wipe_prior)   # Task 3


if __name__ == "__main__":
    main()
```

> หมายเหตุ: `write_cycle` ยังไม่นิยามใน task นี้ — โหมด `--dry-run` ไม่เรียกมัน เลยรัน dry-run ได้ก่อน เขียน `write_cycle` ใน Task 3

- [ ] **Step 3: รัน dry-run ทุก cycle**

Run (จากราก repo):
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/import_bigc_daily.py --dry-run`
Expected: พิมพ์ 6 บล็อก (2025-12 … 2026-05) แต่ละบล็อกมี jobs/fuel/SUM revenue/SUM trip — ไม่มี error, ไม่เขียน DB

- [ ] **Step 4: ตรวจ reverse-check เดือน พ.ค. (ค่าที่รู้ล่วงหน้า)**

ยืนยันบล็อก `2026-05`:
- `SUM revenue (ค่าขนส่ง)` = **31,070.03**
- `SUM trip_fee (ค่าเที่ยว)` = **136,300.00**

ถ้าไม่ตรง → หยุด ตรวจ column-map/หน้าต่างวันที่ ก่อนไปต่อ (อย่าเขียน DB)

- [ ] **Step 5: บันทึก dry-run ทั้ง 6 เดือนเป็นไฟล์อ้างอิง (ให้โอดู)**

Run:
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/import_bigc_daily.py --dry-run > reports/bigc_daily_dryrun_2026-06-28.txt 2>&1`
แล้วเปิดดูว่าครบ 6 เดือน ตัวเลขสมเหตุผล (revenue/trip ไม่ติดลบ, jobs > 0 ทุกเดือน)

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/tools/import_bigc_daily.py
git commit -m "feat(import): BIGC CLI + cycle map + dry-run (6 cycles, reverse-check พ.ค. ตรง)"
```

> **GATE:** หยุดให้โอดูตัวเลข dry-run (โดยเฉพาะ revenue/trip รวมต่อเดือน) ก่อนเริ่ม Task 3 (เขียน DB จริง)

---

## Task 3: เขียน DB จริง (per cycle) + กันซ้ำ + reverse-check หลังเขียน

**Files:**
- Modify: `ProjectYK_System/tools/import_bigc_daily.py` (เพิ่ม `write_cycle` + DB engine)
- Test: `ProjectYK_System/app/tests/test_import_bigc_daily.py` (เพิ่ม test write+wipe ด้วย in-memory DB)

**Interfaces:**
- Consumes: `parse_cycle` (Task 2), models `DailyJob`/`FuelTxn` จาก app
- Produces:
  - `make_engine(db_path=None)` — engine ของ `app.db` (หรือ path ที่ส่งมา สำหรับ test)
  - `wipe_prior(session, source_tag) -> int`
  - `write_cycle(cycle_tag, res, wipe_prior=False, engine=None) -> dict` — เขียน DailyJob+FuelTxn,
    คืน `{"jobs":int, "fuel":int}`

- [ ] **Step 1: เขียน test ที่ fail — write_cycle ลง in-memory DB + wipe กันซ้ำ**

เพิ่มท้ายไฟล์ test (ต้องเข้าถึง models ของ app — เพิ่ม app ใน path บนหัวไฟล์ test ถ้ายังไม่มี):

```python
# (บนหัวไฟล์ test เพิ่ม path ของ app ด้วย — วางใกล้ TOOLS)
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
```

```python
from sqlmodel import SQLModel, Session, select   # noqa: E402
from models import DailyJob, FuelTxn              # noqa: E402


def _fake_res():
    # 2 records: หนึ่งมีน้ำมัน หนึ่งรถจอด (fuel=None)
    return {
        "records": [
            {"daily": {"work_date": date(2026, 5, 1), "site_code": "BIGC",
                       "driver_raw_name": "ธนวัฒน์", "plate_no_raw": "71-8001",
                       "tail_plate_raw": "", "origin": "", "store_code": "",
                       "destination": "", "doc_no": "", "revenue_customer": 600.0,
                       "trip_fee_driver": 200.0, "fuel_liter": 159.76,
                       "fuel_amount": 5400.0, "fuel_rate_km_per_l": 0.0,
                       "mile_snapshot": 0.0, "remark": "PTT B20"},
             "fuel": {"site_code": "BIGC", "txn_date": date(2026, 5, 1),
                      "plate_no_raw": "71-8001", "driver_raw_name": "ธนวัฒน์",
                      "liter": 159.76, "amount": 5400.0,
                      "price_per_liter": 5400.0 / 159.76, "rate_km_per_l": 0.0,
                      "mile_snapshot": 0.0, "exclude_from_driver": True}},
            {"daily": {"work_date": date(2026, 5, 2), "site_code": "BIGC",
                       "driver_raw_name": "สมัย", "plate_no_raw": "71-8002",
                       "tail_plate_raw": "", "origin": "", "store_code": "",
                       "destination": "", "doc_no": "", "revenue_customer": 0.0,
                       "trip_fee_driver": 0.0, "fuel_liter": 0.0,
                       "fuel_amount": 0.0, "fuel_rate_km_per_l": 0.0,
                       "mile_snapshot": 0.0, "remark": ""},
             "fuel": None},
        ],
        "sum_revenue": 600.0, "sum_trip": 200.0, "n_jobs": 2, "n_fuel": 1,
    }


def test_write_cycle_inserts_jobs_and_fuel(tmp_path):
    eng = imp.make_engine(str(tmp_path / "t.db"))
    SQLModel.metadata.create_all(eng)
    out = imp.write_cycle("2026-05", _fake_res(), engine=eng)
    assert out == {"jobs": 2, "fuel": 1}
    with Session(eng) as s:
        jobs = s.exec(select(DailyJob).where(DailyJob.source == "bigc_2026-05")).all()
        assert len(jobs) == 2
        assert all(j.site_code == "BIGC" for j in jobs)
        fuels = s.exec(select(FuelTxn).where(FuelTxn.source == "bigc_2026-05")).all()
        assert len(fuels) == 1
        assert fuels[0].exclude_from_driver is True


def test_write_cycle_wipe_prior_no_duplicate(tmp_path):
    eng = imp.make_engine(str(tmp_path / "t.db"))
    SQLModel.metadata.create_all(eng)
    imp.write_cycle("2026-05", _fake_res(), engine=eng)
    imp.write_cycle("2026-05", _fake_res(), wipe_prior=True, engine=eng)  # รันซ้ำ
    with Session(eng) as s:
        jobs = s.exec(select(DailyJob).where(DailyJob.source == "bigc_2026-05")).all()
        assert len(jobs) == 2   # ไม่ซ้อนเป็น 4
```

- [ ] **Step 2: รัน test ใหม่ให้เห็น fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_import_bigc_daily.py -k write -v`
Expected: FAIL — `AttributeError: ... has no attribute 'make_engine'`

- [ ] **Step 3: เขียน make_engine + wipe_prior + write_cycle**

เพิ่มใน `import_bigc_daily.py`:

```python
from sqlmodel import Session, create_engine, delete, select  # noqa: E402

_APP_ADDED = False


def _ensure_app_on_path():
    global _APP_ADDED
    if not _APP_ADDED:
        app_dir = Path(__file__).resolve().parents[1] / "app"
        sys.path.insert(0, str(app_dir))
        _APP_ADDED = True


def make_engine(db_path: Optional[str] = None):
    if db_path is None:
        db_path = str(Path(__file__).resolve().parents[1] / "app" / "app.db")
    return create_engine(f"sqlite:///{db_path}", echo=False,
                         connect_args={"check_same_thread": False})


def wipe_prior(session, source_tag: str) -> int:
    _ensure_app_on_path()
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
    from models import DailyJob, FuelTxn
    src = SOURCE_PREFIX + cycle_tag
    eng = engine or make_engine()
    n_jobs = n_fuel = 0
    with Session(eng) as s:
        if wipe_prior:
            removed = globals()["wipe_prior"](s, src)
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
```

> ชื่อ local param `wipe_prior` ชนกับฟังก์ชัน module-level — ภายใน `write_cycle` เรียกผ่าน
> `globals()["wipe_prior"]` เพื่อความชัด (param เป็น bool, ฟังก์ชันเป็น callable)

- [ ] **Step 4: รัน test write ให้ผ่าน**

Run: `.venv/Scripts/python.exe -m pytest tests/test_import_bigc_daily.py -v`
Expected: PASS ทั้งหมด (parse 9 + write 2 = 11)

- [ ] **Step 5: backup app.db ก่อนเขียนจริง**

Run (จากราก repo):
`ProjectYK_System/app/.venv/Scripts/python.exe -c "import shutil,datetime;p='ProjectYK_System/app/app.db';shutil.copy(p,p+'.bak_bigc_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));print('backed up')"`
Expected: `backed up`

- [ ] **Step 6: snapshot ยอด payrun BIGC + จำนวน DailyJob ก่อนเขียน (ตัวเทียบ)**

Run:
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/_bigc_guard_snapshot.py before`
(ดู Step 7 — สร้างสคริปต์ guard ก่อน) — เก็บ net 6 รอบ BIGC + COUNT(DailyJob site=BIGC) + COUNT(LCB)

- [ ] **Step 7: สร้างสคริปต์ guard (snapshot ก่อน/หลัง) — read-only**

สร้าง `ProjectYK_System/tools/_bigc_guard_snapshot.py`:

```python
"""Read-only guard: เทียบ payrun BIGC net + DailyJob counts ก่อน/หลัง import.
รับรองว่า import เดลี่ 'ไม่' ขยับ net ที่ลอกจากแบงค์ และ 'ไม่' แตะ LCB."""
import io, json, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import sqlite3

DB = str(Path(__file__).resolve().parents[1] / "app" / "app.db")
OUT = Path(__file__).resolve().parents[2] / "reports" / "_bigc_guard.json"


def snap():
    con = sqlite3.connect(DB); cur = con.cursor()
    net = {}
    for r in cur.execute("""SELECT pr.pay_cycle_tag, ROUND(SUM(pi.net_pay),2)
                            FROM payrun pr JOIN payrunitem pi ON pi.pay_run_id=pr.id
                            WHERE pr.site_code='BIGC' GROUP BY pr.pay_cycle_tag"""):
        net[r[0]] = r[1]
    cnt = {}
    for r in cur.execute("SELECT site_code, COUNT(*) FROM dailyjob GROUP BY site_code"):
        cnt[r[0]] = r[1]
    con.close()
    return {"bigc_net": net, "dailyjob_count": cnt}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "show"
    cur = snap()
    if mode == "before":
        OUT.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        print("BEFORE saved:", json.dumps(cur, ensure_ascii=False))
    elif mode == "after":
        before = json.loads(OUT.read_text(encoding="utf-8"))
        print("BEFORE:", json.dumps(before, ensure_ascii=False))
        print("AFTER :", json.dumps(cur, ensure_ascii=False))
        net_same = before["bigc_net"] == cur["bigc_net"]
        lcb_same = before["dailyjob_count"].get("LCB") == cur["dailyjob_count"].get("LCB")
        print(f"BIGC net unchanged: {net_same}")
        print(f"LCB DailyJob unchanged: {lcb_same}")
        if not (net_same and lcb_same):
            raise SystemExit("[GUARD FAIL] net หรือ LCB เปลี่ยน — ตรวจด่วน")
        print("[GUARD OK]")
    else:
        print(json.dumps(cur, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

รัน `before` ก่อน:
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/_bigc_guard_snapshot.py before`
Expected: `BEFORE saved: {"bigc_net": {"2025-12":116187.48, ...}, "dailyjob_count": {"LCB":1116}}`

- [ ] **Step 8: เขียนจริงทั้ง 6 เดือน**

Run (จากราก repo):
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/import_bigc_daily.py --wipe-prior`
Expected: 6 บล็อก แต่ละบล็อก `wrote jobs=... fuel=...` ไม่มี error

- [ ] **Step 9: รัน guard `after` — net ต้องเท่าเดิม + LCB ไม่ขยับ**

Run:
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/_bigc_guard_snapshot.py after`
Expected: `BIGC net unchanged: True`, `LCB DailyJob unchanged: True`, `[GUARD OK]`

- [ ] **Step 10: ยืนยันจำนวน DailyJob BIGC ต่อ cycle ตรง dry-run**

Run:
`ProjectYK_System/app/.venv/Scripts/python.exe -c "import sqlite3;c=sqlite3.connect('ProjectYK_System/app/app.db');[print(r) for r in c.execute(\"SELECT source,COUNT(*) FROM dailyjob WHERE site_code='BIGC' GROUP BY source ORDER BY source\")]"`
Expected: 6 แถว `bigc_2025-12 … bigc_2026-05` จำนวนตรงกับ jobs ใน dry-run

- [ ] **Step 11: Commit**

```bash
git add ProjectYK_System/tools/import_bigc_daily.py ProjectYK_System/tools/_bigc_guard_snapshot.py ProjectYK_System/app/tests/test_import_bigc_daily.py
git commit -m "feat(import): BIGC write_cycle + guard snapshot; เขียนจริง 6 เดือน net คงเดิม"
```

---

## Task 4: รายงาน driver-name → emp_id ที่ผูกไม่ติด (read-only, ส่งโอ)

**Files:**
- Create: `ProjectYK_System/tools/_bigc_link_report.py` (read-only audit)

**Interfaces:**
- Consumes: `DailyJob` (BIGC rows ที่เพิ่ง import), `Employee` (จาก app models)
- Produces: รายงาน stdout — รายชื่อ raw ที่ map เข้า emp (site=BIGC) ได้/ไม่ได้

- [ ] **Step 1: สร้างสคริปต์รายงาน (ยังไม่ผูกจริง — แค่ audit)**

สร้าง `ProjectYK_System/tools/_bigc_link_report.py`:

```python
"""Read-only: BIGC daily driver_raw_name → Employee(site=BIGC) ตรงไหม.
ไม่เขียน DB — ส่งรายชื่อ unlinked ให้โอยืนยันก่อนผูกจริง (ไม่เดา map)."""
import io, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select
from models import DailyJob, Employee
from import_bigc_daily import make_engine

# Employee fields (verified 2026-06-28): full_name="ชื่อ นามสกุล", home_site_code="BIGC"
def first_name(full: str) -> str:
    parts = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").split()
    return parts[0] if parts else ""

eng = make_engine()
with Session(eng) as s:
    raws = sorted({j.driver_raw_name for j in
                   s.exec(select(DailyJob).where(DailyJob.site_code == "BIGC")).all()
                   if j.driver_raw_name})
    bigc_emps = s.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all()
    linked, unlinked = [], []
    for raw in raws:
        rfn = first_name(raw)
        hit = [e for e in bigc_emps if first_name(e.full_name) == rfn and rfn]
        (linked if hit else unlinked).append(raw)
    print(f"BIGC daily distinct drivers: {len(raws)}")
    print(f"  linked (มี emp ไซต์ BIGC ชื่อต้นตรง): {len(linked)} -> {linked}")
    print(f"  UNLINKED (ให้โอยืนยัน): {len(unlinked)} -> {unlinked}")
    print(f"BIGC employees ในระบบ: {len(bigc_emps)} (home_site_code='BIGC')")
```

> Employee fields ยืนยันแล้ว: `full_name`, `home_site_code='BIGC'` (13 คน). audit อ่านอย่างเดียว ไม่เขียน DB

- [ ] **Step 2: รันรายงาน**

Run:
`ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/_bigc_link_report.py`
Expected: พิมพ์ distinct drivers + รายชื่อ linked/unlinked (ไม่เขียน DB)

- [ ] **Step 3: ส่งรายชื่อ unlinked ให้โอ (ในแชต) — ไม่ผูกจริงจนกว่าโอยืนยัน**

สรุปให้โอ: มีกี่ชื่อผูกติด/ไม่ติด, ชื่อไหนต้องยืนยันตัวสะกด/ตัวซ้ำ. **หยุดตรงนี้** — การผูก
`driver_id` จริงเป็นงานแยก (ทำเมื่อโอยืนยัน map)

- [ ] **Step 4: Commit**

```bash
git add ProjectYK_System/tools/_bigc_link_report.py
git commit -m "feat(import): BIGC driver-name link audit (read-only, รายงาน unlinked ให้โอ)"
```

---

## After all tasks

- verify หน้าเว็บ: เปิด `/daily` เลือก BIGC เห็นแถว, `/finance/revenue` ช่วงเดือน BIGC เห็นรายได้
- deploy (Tailscale; restart kill by 8010-PID + YK_MVP path — ไม่ใช้ `\.venv` filter กว้าง โดน LINE archiver)
- finishing-a-development-branch: merge `feat/bigc-daily-import` → main

## Verification checklist (จาก spec section 9)

- [ ] dry-run 6 เดือน: revenue/trip ตรงยอดในไฟล์ (พ.ค. = 31,070.03 / 136,300)
- [ ] DailyJob BIGC > 0 ต่อ cycle, นับตรง dry-run
- [ ] payrun BIGC 6 รอบ net ไม่เปลี่ยน (guard `after` = OK)
- [ ] LCB DailyJob ยัง = 1116
- [ ] `/daily` + `/finance/revenue` แสดง BIGC
- [ ] รายงาน unlinked driver ให้โอแล้ว
