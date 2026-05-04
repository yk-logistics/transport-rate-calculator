"""Quick stats on imported petty cash data."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from collections import Counter

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select
from models import PettyCashTxn

engine = create_engine(f"sqlite:///{APP_DIR/'app.db'}")
with Session(engine) as s:
    rows = s.exec(select(PettyCashTxn)).all()

print(f"Total rows: {len(rows):,}")
print(f"With deduct_from_driver: {sum(1 for r in rows if r.deduct_from_driver):,}")
print(f"With pending_amount>0 or pending_note: {sum(1 for r in rows if r.pending_amount>0 or r.pending_note):,}")
print(f"With plate extracted: {sum(1 for r in rows if r.linked_vehicle_plate_raw):,}")

print("\nBy site:")
for site, c in Counter(r.site_code for r in rows).most_common():
    print(f"  {site}: {c:,}")

print("\nBy direction:")
for d, c in Counter(r.direction for r in rows).most_common():
    print(f"  {d}: {c:,}")

print("\nBy category:")
for cat, c in Counter(r.category for r in rows).most_common():
    pct = c / len(rows) * 100
    print(f"  {cat:18s}: {c:>7,}  ({pct:5.2f}%)")

print("\nYear range:")
dates = [r.txn_date for r in rows if r.txn_date]
if dates:
    print(f"  earliest: {min(dates)}")
    print(f"  latest:   {max(dates)}")

print("\nBy year:")
for y, c in sorted(Counter(r.txn_date.year for r in rows if r.txn_date).items()):
    print(f"  {y}: {c:,}")

print("\nTop 10 drivers by transaction count (raw names):")
names = Counter(r.requester_raw for r in rows if r.requester_raw)
for name, c in names.most_common(10):
    print(f"  {name:20s}: {c:,}")

print("\nTotal amount out by site (all years):")
from collections import defaultdict
by_site_out = defaultdict(float)
for r in rows:
    if r.direction == "out":
        by_site_out[r.site_code] += r.amount
for site, total in sorted(by_site_out.items()):
    print(f"  {site}: {total:,.0f} บ.")

print("\nTotal pending deductions (pending status):")
total_pend = sum(r.deduct_amount for r in rows if r.deduct_from_driver and r.deduction_status == "pending")
print(f"  {total_pend:,.0f} บ.")
