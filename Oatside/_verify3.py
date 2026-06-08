# -*- coding: utf-8 -*-
"""#3: เทียบค่าเสียเวลา/surcharge รวมทั้งคัน — ระบบ vs คนคีย์ (กฎโอ: ระบบ>=คนคีย์ = OK)."""
import openpyxl, datetime as dt
import build_oatside_reports as M

cfg = M.load_oatside_config()
folder = M._oatside_dir()
op, dp = M.discover_gps_files(folder)
trips, _, _ = M.build_trips(op, dp, cfg)
o_legs = M.parse_legs(op); d_legs = M.parse_legs(dp)
ov = M.load_billing_overrides()
fifty, _ = M.surcharge_billed_day(trips, o_legs, d_legs, ov, cfg)

PLATES = ["71-5041","71-5042","71-6802","71-8001","71-8002","71-8005","71-8009"]
sys_sur = {p: 0 for p in PLATES}
for r in fifty:
    if r["plate"] in PLATES:
        sys_sur[r["plate"]] += int(r["surcharge_baht"])

def s(v): return "" if v is None else str(v)

# keyer demurrage from file1 May 26 markers
key_dem = {p: 0 for p in PLATES}
key_detail = {p: [] for p in PLATES}
wb = openpyxl.load_workbook(r"C:\Users\guole\Downloads\Daily โฮมโปร-ทั่วไป.xlsx", read_only=True, data_only=True)
ws = wb["May 26"]
for row in ws.iter_rows(min_row=1, max_col=12, values_only=True):
    A,B,C,D,E,F,G,H,I,J,K,L = (list(row)+[None]*12)[:12]
    p = s(B).strip()
    if p not in PLATES or "oat" not in s(E).lower(): continue
    if not (isinstance(A,dt.datetime) and A.year==2026 and A.month==5): continue
    txt = (s(H)+" "+s(I)).replace(" ","")
    pct = 0
    if ("1วันเต็ม" in txt) or ("เกิน24" in txt) or ("ราคา1เที่ยว" in txt) or ("มีค่าเสียเวลาราคา1" in txt):
        pct = 100
    elif "เสียเวลา50" in txt or "ค่าเสียเวลา50%" in txt:
        pct = 50
    if pct:
        rate = int(M.trip_rate_baht(A.date(), cfg))
        amt = rate if pct==100 else rate//2
        key_dem[p] += amt
        key_detail[p].append(f"{A:%d/%m}={pct}%({amt})")
wb.close()

print(f"{'plate':<9}{'system_sur':>12}{'keyer_dem':>12}  result   keyer_marks")
for p in PLATES:
    ok = "OK" if sys_sur[p] >= key_dem[p] else "** REVIEW (system<keyer) **"
    print(f"{p:<9}{sys_sur[p]:>12,}{key_dem[p]:>12,}  {ok:<8} {' '.join(key_detail[p])}")
