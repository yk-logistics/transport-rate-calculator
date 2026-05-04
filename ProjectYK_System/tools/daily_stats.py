"""Sanity check stats on imported DailyJob + FuelTxn data."""
from __future__ import annotations
import io, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select  # noqa: E402
from models import DailyJob, DailyJobFee, FuelTxn  # noqa: E402

engine = create_engine(f"sqlite:///{APP_DIR / 'app.db'}", echo=False)

with Session(engine) as s:
    dj = s.exec(select(DailyJob)).all()
    fees = s.exec(select(DailyJobFee)).all()
    fuel = s.exec(select(FuelTxn)).all()

print(f"DailyJob     = {len(dj)}")
print(f"DailyJobFee  = {len(fees)}")
print(f"FuelTxn      = {len(fuel)}")

print("\n--- Jobs by site ---")
by_site = Counter(r.site_code for r in dj)
for site, n in sorted(by_site.items()):
    print(f"  {site:5s} = {n}")

print("\n--- Jobs by site × status ---")
by_ss = Counter((r.site_code, r.status_code or "(job)") for r in dj)
sites = sorted({k[0] for k in by_ss.keys()})
for site in sites:
    print(f"  {site}:")
    entries = [(s, n) for (s0, s), n in by_ss.items() if s0 == site]
    for stat, n in sorted(entries, key=lambda x: -x[1]):
        print(f"      {stat:20s} {n:4d}")

print("\n--- Revenue/Trip-fee totals by site ---")
rev = defaultdict(float)
fee = defaultdict(float)
n_real = Counter()
for r in dj:
    rev[r.site_code] += r.revenue_customer
    fee[r.site_code] += r.trip_fee_driver
    if r.revenue_customer > 0 or r.trip_fee_driver > 0:
        n_real[r.site_code] += 1
for site in sorted(rev):
    print(f"  {site}: {n_real[site]} real jobs | revenue={rev[site]:>12,.0f}  driver-fee={fee[site]:>10,.0f}")

print("\n--- Fuel by site ---")
fuel_by = defaultdict(lambda: {"n": 0, "l": 0.0, "b": 0.0})
for f in fuel:
    fuel_by[f.site_code]["n"] += 1
    fuel_by[f.site_code]["l"] += f.liter
    fuel_by[f.site_code]["b"] += f.amount
for site, d in sorted(fuel_by.items()):
    avg = d["b"] / d["l"] if d["l"] else 0
    print(f"  {site}: {d['n']:4d} fills | {d['l']:>10,.1f} L | ฿{d['b']:>12,.0f} | avg ฿{avg:.2f}/L")

print("\n--- LCB extra fees (DailyJobFee) by type ---")
by_type = defaultdict(lambda: {"n": 0, "sum": 0.0})
for f in fees:
    by_type[f.fee_type]["n"] += 1
    by_type[f.fee_type]["sum"] += f.amount
for t, d in sorted(by_type.items(), key=lambda x: -x[1]["sum"]):
    print(f"  {t:15s}  n={d['n']:4d}  sum=฿{d['sum']:>10,.0f}")

print("\n--- Date range per site ---")
for site in sites:
    rows = [r for r in dj if r.site_code == site]
    if rows:
        mn = min(r.work_date for r in rows)
        mx = max(r.work_date for r in rows)
        print(f"  {site}: {mn} → {mx}")

print("\n--- Top 10 drivers by jobs ---")
drv = Counter(r.driver_raw_name for r in dj if r.driver_raw_name and r.status_code not in ("placeholder", "idle"))
for nm, n in drv.most_common(10):
    print(f"  {nm:30s} {n:4d}")

print("\n--- Top 10 plates (active jobs only) ---")
plates = Counter(r.plate_no_raw for r in dj if r.plate_no_raw and r.status_code not in ("placeholder", "idle", "leave"))
for p, n in plates.most_common(10):
    print(f"  {p:15s} {n:4d}")
