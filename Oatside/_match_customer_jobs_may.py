# -*- coding: utf-8 -*-
"""จับคู่ใบงานลูกค้า (Oatside May 2026.xlsx) กับเที่ยว GPS ของเรา (รอบ พ.ค. 2569).

ลูกค้า Sheet1: B=Shipment Date, C=PO/Ref (เลขใบงาน), I=ทะเบียน
เรา: exports/05_Trip_Detail.csv (152 เที่ยว matched)
จับคู่ตามทะเบียน เป็นรอบ ๆ (เที่ยวละ 1 ใบงานก่อน):
  pass 1: วันเอกสาร == วันที่รถออกต้นทาง (Origin_Out date)
  pass 2: วันเอกสาร == วันเที่ยว (billed day / Trip_Date)
  pass 3: เหลื่อม ±1 วันจาก Origin_Out
  pass 4: ใบงานที่เหลือ ยอมซ้อนเที่ยวเดิม (หลายใบงานขึ้นรถเที่ยวเดียว) ±1 วัน
"""
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
CUSTOMER_XLSX = Path(r"C:\Users\guole\Downloads\Oatside May 2026.xlsx")
TRIP_CSV = HERE / "TransportRateCalculator" / "reports" / "oatside-apr2026" / "exports" / "05_Trip_Detail.csv"
JOBNUM_JSON = HERE / "oatside_job_numbers.json"
OUT_CSV = HERE / "customer_job_match_may2026.csv"


def parse_dt(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            pass
    return None


# --- customer rows ---
wb = openpyxl.load_workbook(CUSTOMER_XLSX, data_only=True)
ws = wb["Sheet1"]
cust = []
for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    job = str(r[2] or "").strip()
    plate = str(r[8] or "").strip()
    d = r[1]
    if not job or not plate or d is None:
        continue
    if isinstance(d, datetime):
        d = d.date()
    cust.append({"row": i, "ship_date": d, "job": job, "plate": plate,
                 "type": str(r[5] or "").strip(), "matched": None})

# --- our trips ---
trips = []
with open(TRIP_CSV, encoding="utf-8-sig") as f:
    for rec in csv.DictReader(f):
        o_out = parse_dt(rec["Origin_Out"])
        trips.append({
            "plate": str(rec["Plate"]).strip(),
            "trip_date": parse_dt(rec["Trip_Date"]).date(),
            "o_in": parse_dt(rec["Origin_In"]),
            "o_out": o_out,
            "cust_jobs": [],
        })

# --- daily job numbers (จากเดลี่คนคีย์ — ไม่ครบทุกคัน) ---
raw = json.loads(JOBNUM_JSON.read_text(encoding="utf-8")) if JOBNUM_JSON.exists() else {}
daily_jobs = raw.get("jobs", {})

trips_by_plate = defaultdict(list)
for t in trips:
    trips_by_plate[t["plate"]].append(t)


def try_match(c, pred, cap):
    cands = [t for t in trips_by_plate.get(c["plate"], [])
             if len(t["cust_jobs"]) < cap and pred(c, t)]
    if not cands:
        return False
    anchor = datetime.combine(c["ship_date"], datetime.min.time())
    best = min(cands, key=lambda t: abs(((t["o_out"] or t["o_in"]) - anchor).total_seconds()))
    best["cust_jobs"].append(c["job"])
    c["matched"] = best
    return True


passes = [
    ("p1_oout_same_day", lambda c, t: (t["o_out"] or t["o_in"]).date() == c["ship_date"], 1),
    ("p2_billed_day", lambda c, t: t["trip_date"] == c["ship_date"], 1),
    ("p3_pm1day", lambda c, t: abs(((t["o_out"] or t["o_in"]).date() - c["ship_date"]).days) <= 1, 1),
    ("p4_stack", lambda c, t: abs(((t["o_out"] or t["o_in"]).date() - c["ship_date"]).days) <= 1, 9),
]
for name, pred, cap in passes:
    for c in cust:
        if c["matched"] is None:
            try_match(c, pred, cap)

trips_no_doc = [t for t in trips if not t["cust_jobs"]]
cust_no_trip = [c for c in cust if not c["matched"]]
stacked = [t for t in trips if len(t["cust_jobs"]) > 1]

print(f"customer job rows: {len(cust)} | matched: {len(cust) - len(cust_no_trip)} | no matching trip: {len(cust_no_trip)}")
print(f"our trips: {len(trips)} | with doc: {len(trips) - len(trips_no_doc)} | WITHOUT doc: {len(trips_no_doc)} | multi-doc trips: {len(stacked)}")

print("\n=== OUR TRIPS WITHOUT CUSTOMER JOB DOC ===")
for t in sorted(trips_no_doc, key=lambda x: (x["trip_date"], x["plate"])):
    key = f'{t["plate"]}|{t["trip_date"].isoformat()}'
    key2 = f'{t["plate"]}|{(t["o_out"] or t["o_in"]).date().isoformat()}'
    dj = daily_jobs.get(key) or daily_jobs.get(key2)
    print(f'billed={t["trip_date"]} {t["plate"]} o_out={t["o_out"]} daily_jobs={";".join(dj) if dj else "-"}')

print("\n=== CUSTOMER DOCS WITHOUT OUR TRIP ===")
for c in sorted(cust_no_trip, key=lambda x: (x["ship_date"], x["plate"])):
    print(f'{c["ship_date"]} {c["plate"]} {c["job"]} type={c["type"]}')

print("\n=== MULTI-DOC TRIPS (หลายใบงานเที่ยวเดียว) ===")
for t in sorted(stacked, key=lambda x: (x["trip_date"], x["plate"])):
    print(f'billed={t["trip_date"]} {t["plate"]} o_out={t["o_out"]} jobs={";".join(t["cust_jobs"])}')

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["billed_day", "plate", "origin_in", "origin_out", "customer_jobs", "daily_jobs", "status"])
    for t in sorted(trips, key=lambda x: (x["trip_date"], x["plate"], x["o_in"])):
        key = f'{t["plate"]}|{t["trip_date"].isoformat()}'
        key2 = f'{t["plate"]}|{(t["o_out"] or t["o_in"]).date().isoformat()}'
        dj = daily_jobs.get(key) or daily_jobs.get(key2) or []
        st = "OK" if t["cust_jobs"] else "NO_CUSTOMER_DOC"
        w.writerow([t["trip_date"], t["plate"], t["o_in"], t["o_out"], ";".join(t["cust_jobs"]), ";".join(dj), st])
    for c in cust_no_trip:
        w.writerow([c["ship_date"], c["plate"], "", "", c["job"], "", "CUSTOMER_DOC_NO_TRIP"])
print(f"\nCSV: {OUT_CSV}")

# --- JSON สำหรับ builder: คอลัมน์ "เลขใบงาน (ลูกค้า)" — รูปแบบเดียวกับ oatside_job_numbers.json ---
OUT_JSON = HERE / "oatside_customer_jobs.json"
jobs_by_key = defaultdict(list)
for t in trips:
    if t["cust_jobs"]:
        key = f'{t["plate"]}|{t["trip_date"].isoformat()}'
        jobs_by_key[key].extend(j for j in t["cust_jobs"] if j not in jobs_by_key[key])
OUT_JSON.write_text(json.dumps({
    "version": 1,
    "_note": "เลขใบงานจากไฟล์ลูกค้า (Oatside May 2026.xlsx Sheet1: B=date, C=job, I=plate) จับคู่กับเที่ยว GPS โดย _match_customer_jobs_may.py; key = PLATE|billed_day; ใบงานลูกค้าที่หาเที่ยวไม่เจอ (71-8002 ช่วง 05-07/05) ไม่อยู่ในไฟล์นี้",
    "jobs": {k: jobs_by_key[k] for k in sorted(jobs_by_key)},
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"JSON: {OUT_JSON} ({len(jobs_by_key)} plate-days)")
