"""Survey unique raw driver/plate names in DB, show counts + site majority."""
from __future__ import annotations
import io, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select
from models import DailyJob, PettyCashTxn, FuelTxn, Employee, Vehicle

e = create_engine(f"sqlite:///{APP_DIR / 'app.db'}")

with Session(e) as s:
    emp = s.exec(select(Employee)).all()
    veh = s.exec(select(Vehicle)).all()
    print(f"Current master: Employee={len(emp)}, Vehicle={len(veh)}")
    print()

    drv: dict[str, dict] = {}
    def bump_drv(raw: str, site: str, src: str, plate: str = ""):
        n = (raw or "").strip()
        if not n or n in ("-", "รถจอด", "ขาด", "ลาป่วย", "ลากิจ", "รับรถ"):
            return
        k = n.lower().replace(" ", "")
        d = drv.setdefault(k, {"raw": n, "sites": Counter(), "sources": Counter(), "plates": Counter()})
        d["sites"][site or "?"] += 1
        d["sources"][src] += 1
        if plate:
            d["plates"][plate] += 1

    for dj in s.exec(select(DailyJob)).all():
        bump_drv(dj.driver_raw_name, dj.site_code, "DailyJob", dj.plate_no_raw)
    for p in s.exec(select(PettyCashTxn)).all():
        bump_drv(p.requester_raw, p.site_code, "PettyCash", p.linked_vehicle_plate_raw or "")
    for f in s.exec(select(FuelTxn)).all():
        bump_drv(f.driver_raw_name, f.site_code, "Fuel", f.plate_no_raw or "")

    print(f"Unique raw driver names: {len(drv)}")
    total_rows = sum(sum(x["sources"].values()) for x in drv.values())
    print(f"Total rows referencing driver: {total_rows}")
    print()

    ranked = sorted(drv.items(), key=lambda kv: -sum(kv[1]["sources"].values()))
    print("Top 40 drivers by frequency:")
    for k, d in ranked[:40]:
        total = sum(d["sources"].values())
        sites = ",".join(f"{s}:{c}" for s, c in d["sites"].most_common())
        srcs = ",".join(f"{s}:{c}" for s, c in d["sources"].most_common())
        print(f"  {d['raw'][:40]:40s} total={total:4d}  sites=[{sites}]  srcs=[{srcs}]")

    print()

    plates: dict[str, dict] = {}
    def bump_plate(raw: str, site: str, src: str):
        p = (raw or "").strip().upper().replace(" ", "")
        if not p or p == "-":
            return
        d = plates.setdefault(p, {"raw": raw.strip(), "sites": Counter(), "sources": Counter(), "count": 0})
        d["sites"][site or "?"] += 1
        d["sources"][src] += 1
        d["count"] += 1

    for dj in s.exec(select(DailyJob)).all():
        bump_plate(dj.plate_no_raw, dj.site_code, "DailyJob")
    for f in s.exec(select(FuelTxn)).all():
        bump_plate(f.plate_no_raw, f.site_code, "Fuel")
    for p in s.exec(select(PettyCashTxn)).all():
        if p.linked_vehicle_plate_raw:
            bump_plate(p.linked_vehicle_plate_raw, p.site_code, "PettyCash")

    print(f"Unique plates: {len(plates)}")
    ranked_p = sorted(plates.items(), key=lambda kv: -kv[1]["count"])
    print("Top 30 plates:")
    for p, d in ranked_p[:30]:
        sites = ",".join(f"{s}:{c}" for s, c in d["sites"].most_common())
        print(f"  {p:12s} count={d['count']:4d}  sites=[{sites}]")
