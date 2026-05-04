"""Check if the 3 petty cash files are duplicates of same master book."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
from collections import defaultdict

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select
from models import PettyCashTxn

engine = create_engine(f"sqlite:///{APP_DIR/'app.db'}")
with Session(engine) as s:
    rows = s.exec(select(PettyCashTxn)).all()

# Build fingerprint per row, see how many appear in all 3 sites
by_key = defaultdict(set)
for r in rows:
    key = (str(r.txn_date), round(r.amount, 2), (r.requester_raw or "")[:20], (r.memo or "")[:40])
    by_key[key].add(r.site_code)

triple = sum(1 for v in by_key.values() if len(v) == 3)
double = sum(1 for v in by_key.values() if len(v) == 2)
single = sum(1 for v in by_key.values() if len(v) == 1)
print(f"Unique (date+amt+name+memo) keys: {len(by_key):,}")
print(f"  Appears in ALL 3 'sites'      : {triple:,}  ← duplicates (same book)")
print(f"  Appears in 2 'sites'          : {double:,}")
print(f"  Unique to 1 'site'            : {single:,}  ← genuinely unique")

# sample pairs of "different sites" for same key
print("\nSample rows present in all 3:")
n = 0
for k, sites in by_key.items():
    if len(sites) == 3 and n < 5:
        print(f"  {k}")
        n += 1
