# -*- coding: utf-8 -*-
"""W2: list BH/ตีเปล่า rows ที่คนคีย์ (ต้องเพิ่ม 50%) + เทียบกับ manual return ที่ระบบมีอยู่."""
import openpyxl, datetime as dt
import build_oatside_reports as M

cfg = M.load_oatside_config()
PLATES = ["71-5041","71-5042","71-6802","71-8001","71-8002","71-8005","71-8009"]

def s(v):
    return "" if v is None else str(v).replace("\n"," ").strip()

# ---- existing manual returns/extras in system ----
print("=== ระบบมี manual return/extra อยู่แล้ว (plate date amt pct) ===")
existing = set()
found_any = False
for attr in ("manual_return_trips","manual_extra_trips","manual_returns","manual_extras"):
    v = getattr(cfg, attr, None)
    if not v: continue
    found_any = True
    for m in v:
        plate = getattr(m,"plate","?"); d = getattr(m,"dest_date",getattr(m,"date","?"))
        amt = getattr(m,"amount_baht","?"); pct = getattr(m,"percent_of_trip_rate","?")
        print(f"  {attr}: {plate} {d} amt={amt} pct={pct}")
        existing.add((str(plate), str(d)))
if not found_any:
    print("  (ไม่มีใน config — ระบบยังไม่ได้เก็บ BH/ขากลับใด ๆ)")

# ---- BH / ตีเปล่า rows from keyed daily (file1 May 26) ----
print("\n=== BH / ตีเปล่า ที่คนคีย์ (file1 May 26) — ต้องเพิ่ม 50% ===")
wb = openpyxl.load_workbook(r"C:\Users\guole\Downloads\Daily โฮมโปร-ทั่วไป.xlsx", read_only=True, data_only=True)
ws = wb["May 26"]
total_add = 0
for row in ws.iter_rows(min_row=1, max_col=12, values_only=True):
    A,B,C,D,E,F,G,H,I,J,K,L = (list(row)+[None]*12)[:12]
    plate=s(B)
    if plate not in PLATES: continue
    if "oat" not in s(E).lower(): continue
    if not (isinstance(A,dt.datetime) and A.year==2026 and A.month==5): continue
    g,h,i,f = s(G),s(H),s(I),s(F)
    is_bh = ("bh" in g.lower()) or ("ตีเปล่า" in h) or ("ตีเปล่า" in i) or (f=="P&G" and "บ้านบึง" in h)
    if not is_bh: continue
    rate = int(M.trip_rate_baht(A.date(), cfg))
    fifty = rate//2
    has = "(ระบบมีแล้ว)" if (plate, str(A.date())) in existing else ">> ต้องเพิ่ม"
    total_add += fifty if has==">> ต้องเพิ่ม" else 0
    kind = "BH-ขากลับ" if (f=="P&G" or "bh" in g.lower()) else "ตีเปล่า"
    print(f"  {plate} {A:%d/%m} {kind:<10} F={f[:8]:<8} G={g[:6]:<6} H={h[:18]:<18} I={i[:14]:<14} rate={rate} 50%={fifty} {has}")
wb.close()
print(f"\nรวม 50% ที่ต้องเพิ่ม (ถ้ายังไม่มีในระบบ) = {total_add:,} บาท")
