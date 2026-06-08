# -*- coding: utf-8 -*-
"""ยืนยันเรท/surcharge ฝั่งระบบ สำหรับ 7 คันที่ Gap != 0 (W1 confirm + ข้อมูลระบบ)."""
import build_oatside_reports as M
import datetime as dt

cfg = M.load_oatside_config()
folder = M._oatside_dir()
origin_path, dest_path = M.discover_gps_files(folder)
trips, unmatched, _ = M.build_trips(origin_path, dest_path, cfg)
o_legs = M.parse_legs(origin_path)
d_legs = M.parse_legs(dest_path)
overrides = M.load_billing_overrides()
fifty_rows, total = M.surcharge_billed_day(trips, o_legs, d_legs, overrides, cfg)

PLATES = ["71-5041", "71-5042", "71-6802", "71-8001", "71-8002", "71-8005", "71-8009"]

print("=== RATE per May day (trip_rate_baht, int) ===")
prev = None
for day in range(1, 32):
    d = dt.date(2026, 5, day)
    r = int(M.trip_rate_baht(d, cfg))
    mark = "" if r == prev else "  <-- change"
    print(f"{d.isoformat()} {r}{mark}")
    prev = r

print("\n=== SURCHARGE rows (7 plates) [plate date kind rate sur] ===")
for r in sorted(fifty_rows, key=lambda x: (x["plate"], str(x["dest_date"]))):
    if r["plate"] in PLATES:
        print(r["plate"], str(r["dest_date"]), r["fifty_kind"], "rate", int(r["trip_rate_baht"]), "sur", r["surcharge_baht"])

print("\n=== TRIPS (7 plates): o_in -> billed(trip_date), rate@billed ===")
for t in sorted(trips, key=lambda x: (x.plate, x.o_in)):
    if t.plate in PLATES:
        print(t.plate, "o_in", t.o_in.strftime("%m-%d %H:%M"), "billed", str(t.trip_date),
              "rate", int(M.trip_rate_baht(t.trip_date, cfg)))

# manual return / extra (BH ที่ระบบมีอยู่แล้ว) ถ้ามี loader
print("\n=== existing manual returns/extras in config (if any) ===")
for attr in ("manual_return_trips", "manual_extra_trips"):
    v = getattr(cfg, attr, None)
    if v:
        for m in v:
            print(attr, getattr(m, "plate", "?"), getattr(m, "dest_date", "?"),
                  getattr(m, "amount_baht", "?"), getattr(m, "percent_of_trip_rate", "?"))
    else:
        print(attr, "= (none)")
