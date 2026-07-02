# -*- coding: utf-8 -*-
"""ตัวรัน/ตัวจัดการเงื่อนไข Oatside สำหรับ MVP (C3+C5) — ห่อ engine ที่ vendor ไว้.

engine = app/oatside/build_oatside_reports.py (สำเนา byte-identical จาก Oatside/ ราก repo —
ห้ามแก้เนื้อ; ดู app/oatside/README.md). เรียกเป็น **subprocess** (ไม่ import) เพราะ:
engine ผูก path ทุกอย่างกับตำแหน่งไฟล์ตัวเอง + กัน crash/หน่วงกระทบตัวแอป.

ไฟล์เงื่อนไข 2 ตัวอยู่ข้าง engine: oatside_config.json / oatside_billing_overrides.json
— save_json() สำรองก่อนเขียนทุกครั้ง (เก็บ 20 ชุดล่าสุด) เพื่อให้โอแก้เองได้ไม่กลัวพัง.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
OATSIDE_DIR = APP_DIR / "oatside"
ENGINE = OATSIDE_DIR / "build_oatside_reports.py"
CONFIG = OATSIDE_DIR / "oatside_config.json"
OVERRIDES = OATSIDE_DIR / "oatside_billing_overrides.json"
UPLOADS = OATSIDE_DIR / "uploads"
LAST_BUILD = OATSIDE_DIR / "_last_build.json"
XLSX_OUT = OATSIDE_DIR / "Oatside_PG_Trip_Summary_By_Site.xlsx"
REPORT_DIR = OATSIDE_DIR / "TransportRateCalculator" / "reports" / "oatside-apr2026"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> str:
    """เขียน JSON เงื่อนไข: สำรองของเดิมเป็น .bak-<ts> ก่อนเสมอ (เก็บ 20 ชุดล่าสุด)."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = path.with_name(f"{path.name}.bak-{ts}")
    if path.exists():
        bak.write_bytes(path.read_bytes())
        baks = sorted(path.parent.glob(f"{path.name}.bak-*"))
        for old in baks[:-20]:
            old.unlink(missing_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return bak.name


def last_build() -> dict | None:
    try:
        return load_json(LAST_BUILD)
    except OSError:
        return None


def current_gps_files() -> dict:
    lb = last_build() or {}
    return {"origin": lb.get("origin"), "dest": lb.get("dest")}


# ---- สคีมาเงื่อนไขที่โอแก้เองได้ (C5) — field: (label, kind) ----
SECTIONS = {
    "rates": {
        "file": "config", "key": "trip_rates", "title": "ช่วงเรทค่าเที่ยว",
        "fields": [("from", "date"), ("to", "date"), ("rate_baht", "num"),
                   ("base_fuel_min", "num"), ("base_fuel_max", "num"),
                   ("step_pct_per_baht", "num"), ("floor_rate_baht", "num?"), ("_note", "str")],
        "labels": ["ตั้งแต่วันที่", "ถึงวันที่", "เรทฐาน ฿", "น้ำมันฐาน ต่ำสุด", "น้ำมันฐาน สูงสุด",
                   "% ต่อ 1 บาทน้ำมัน", "เรทต่ำสุด ฿ (เว้นได้)", "หมายเหตุ"],
    },
    "diesel": {
        "file": "config", "key": "diesel_price_history", "title": "ราคาดีเซลรายวัน",
        "fields": [("date", "date"), ("price", "num"), ("source", "str")],
        "labels": ["วันที่", "ราคา ฿/ลิตร", "ที่มา (เว้นได้)"],
    },
    "no_work": {
        "file": "config", "key": "customer_no_work", "title": "ช่วงลูกค้าหยุด (ไม่นับขั้นต่ำ)",
        "fields": [("from", "date"), ("to", "date"), ("note", "str")],
        "labels": ["ตั้งแต่", "ถึง", "หมายเหตุ"],
    },
    "remove_matched": {
        "file": "config", "key": "remove_matched_trips", "title": "ตัดเที่ยว GPS (ตีเปล่าที่ GPS นับเป็นเที่ยวเต็ม)",
        "fields": [("dest_date", "date"), ("plate", "str"), ("count", "num"), ("note", "str")],
        "labels": ["วันที่ (ฝั่งปลายทาง)", "ทะเบียน", "จำนวนเที่ยวที่ตัด", "หมายเหตุ"],
    },
    "manual_return": {
        "file": "config", "key": "manual_return_trips", "title": "เที่ยวขากลับ/ตีเปล่า (คิดเงินเพิ่มเอง)",
        "fields": [("dest_date", "date"), ("plate", "str"), ("percent_of_trip_rate", "num?"),
                   ("amount_baht", "num?"), ("kind", "str"), ("note", "str")],
        "labels": ["วันที่", "ทะเบียน", "% ของเรทเที่ยวหลัก (เว้นได้)", "หรือระบุยอด ฿ (เว้นได้)", "ชนิด เช่น deadhead", "หมายเหตุ"],
    },
    "manual_extra": {
        "file": "config", "key": "manual_extra_trips", "title": "เที่ยวเพิ่มที่ไม่มีใน GPS",
        "fields": [("dest_date", "date"), ("plate", "str"), ("amount_baht", "num"), ("note", "str")],
        "labels": ["วันที่", "ทะเบียน", "ยอด ฿", "หมายเหตุ"],
    },
    "overrides": {
        "file": "overrides", "key": "entries", "title": "ยกเว้น +50% รายเที่ยว (exclude_50)",
        "fields": [("dest_date", "date"), ("plate", "str"), ("action", "str"), ("note", "str")],
        "labels": ["วันที่", "ทะเบียน", "action (exclude_50)", "หมายเหตุ"],
    },
}
GENERAL_FIELDS = [
    ("one_trip_surcharge_pct", "num", "% เพิ่มเมื่อวิ่งวันละ 1 เที่ยว (ขั้นต่ำ)"),
    ("min_trips_per_truck_per_day", "num", "เที่ยวขั้นต่ำ/คัน/วัน"),
    ("max_travel_h", "num", "ชม.สูงสุด จับคู่ต้นทาง→ปลายทาง"),
    ("max_origin_chain_gap_h", "num", "ชม.สูงสุด รวมเที่ยวต้นทางต่อเนื่อง"),
    ("use_origin_24h_fifty", "bool", "คิด +50% กรณีจอดต้นทางเกิน 24 ชม."),
    ("report_start_date", "date", "รายงานตั้งแต่วันที่"),
    ("report_end_date", "date", "รายงานถึงวันที่"),
]

_DATE_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_section_rows(form, section: str) -> tuple[list[dict], str]:
    """อ่านแถวจากฟอร์ม (ชื่อช่อง i-field + ติ๊ก del-i + แถวใหม่ new-field) → (rows, error)."""
    spec = SECTIONS[section]
    rows: list[dict] = []
    idxs = sorted({int(k.split("-")[0]) for k in form.keys() if k.split("-")[0].isdigit()})
    for i in list(idxs) + ["new"]:
        if form.get(f"del-{i}") == "1":
            continue
        row: dict = {}
        empty = True
        for f, kind in spec["fields"]:
            v = (form.get(f"{i}-{f}") or "").strip()
            if v == "":
                if kind.endswith("?") or f in ("_note", "note", "source", "kind"):
                    continue
                if i == "new":
                    row = {}
                    break
                return [], f"แถวที่ {i}: ช่อง {f} ห้ามว่าง"
            empty = False
            if kind.startswith("num"):
                try:
                    n = float(v)
                except ValueError:
                    return [], f"แถวที่ {i}: {f} ต้องเป็นตัวเลข (ได้ '{v}')"
                row[f] = int(n) if n == int(n) else n
            elif kind == "date":
                if not _DATE_RE.match(v):
                    return [], f"แถวที่ {i}: {f} ต้องเป็น ปปปป-ดด-วว (ได้ '{v}')"
                row[f] = v
            else:
                row[f] = v
        if row and not empty:
            rows.append(row)
    return rows, ""


def run_build(origin: Path, dest: Path) -> dict:
    """รัน engine กับไฟล์ GPS 2 ไฟล์ → dict ผลลัพธ์ (บันทึกลง _last_build.json ด้วย)."""
    import os

    env = dict(os.environ)
    env["OATSIDE_ORIGIN"] = str(origin)
    env["OATSIDE_DEST"] = str(dest)
    env["PYTHONIOENCODING"] = "utf-8"
    py = Path(sys.executable)
    try:
        proc = subprocess.run(
            [str(py), str(ENGINE)], env=env, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=600,
            cwd=str(OATSIDE_DIR),
        )
        ok = proc.returncode == 0
        log = (proc.stdout or "") + ("\n--- STDERR ---\n" + proc.stderr if proc.stderr else "")
    except subprocess.TimeoutExpired:
        ok, log = False, "TIMEOUT: เกิน 10 นาที"
    result = {
        "at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "ok": ok,
        "origin": origin.name,
        "dest": dest.name,
        "log": log[-6000:],
        "report_exists": (REPORT_DIR / "index.html").exists(),
        "xlsx_exists": XLSX_OUT.exists(),
    }
    LAST_BUILD.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result
