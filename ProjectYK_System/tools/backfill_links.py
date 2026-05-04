"""
Backfill driver_id / head_vehicle_id on DailyJob / PettyCashTxn / FuelTxn
using existing Employee and Vehicle master.

Safe to run anytime (only fills NULL FKs; never overwrites).

Run:  python ProjectYK_System/tools/backfill_links.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select  # noqa: E402

from models import (  # noqa: E402
    DailyJob, Employee, FuelTxn, PettyCashTxn, Vehicle,
)
from services.promote import normalize_name, normalize_plate  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False,
                      connect_args={"check_same_thread": False})


def main() -> None:
    import main as app_main  # noqa: E402
    app_main.init_db()

    with Session(engine) as s:
        employees = s.exec(select(Employee)).all()
        vehicles = s.exec(select(Vehicle)).all()

        # Build lookup: normalized name -> Employee; include nickname
        name_map: dict[str, Employee] = {}
        for e in employees:
            keys = {normalize_name(e.full_name)}
            if e.nickname:
                keys.add(normalize_name(e.nickname))
            # also first-name only (common in Excel)
            first_only = (e.full_name or "").split()[0] if e.full_name else ""
            if first_only:
                keys.add(normalize_name(first_only))
            for k in keys:
                if k:
                    name_map.setdefault(k, e)

        plate_map: dict[str, Vehicle] = {}
        for v in vehicles:
            plate_map[normalize_plate(v.plate_no)] = v
            if v.old_plate_no:
                plate_map.setdefault(normalize_plate(v.old_plate_no), v)

        print(f"Master: {len(employees)} employees, {len(vehicles)} vehicles")
        print(f"Lookup: {len(name_map)} name keys, {len(plate_map)} plate keys")

        d_driver = d_veh = 0
        for dj in s.exec(select(DailyJob).where(DailyJob.driver_id.is_(None))).all():
            if dj.driver_raw_name:
                emp = name_map.get(normalize_name(dj.driver_raw_name))
                if emp:
                    dj.driver_id = emp.id
                    d_driver += 1
            if dj.head_vehicle_id is None and dj.plate_no_raw:
                v = plate_map.get(normalize_plate(dj.plate_no_raw))
                if v:
                    dj.head_vehicle_id = v.id
                    d_veh += 1
            if dj.tail_vehicle_id is None and dj.tail_plate_raw:
                v = plate_map.get(normalize_plate(dj.tail_plate_raw))
                if v:
                    dj.tail_vehicle_id = v.id
        s.commit()
        print(f"DailyJob: filled driver_id={d_driver}  head_vehicle_id={d_veh}")

        p_driver = p_veh = 0
        for p in s.exec(select(PettyCashTxn).where(PettyCashTxn.driver_id.is_(None))).all():
            if p.requester_raw:
                emp = name_map.get(normalize_name(p.requester_raw))
                if emp:
                    p.driver_id = emp.id
                    if not p.site_code:
                        p.site_code = emp.home_site_code or ""
                    p_driver += 1
            if p.linked_vehicle_id is None and p.linked_vehicle_plate_raw:
                v = plate_map.get(normalize_plate(p.linked_vehicle_plate_raw))
                if v:
                    p.linked_vehicle_id = v.id
                    p_veh += 1
        s.commit()
        print(f"PettyCashTxn: filled driver_id={p_driver}  linked_vehicle_id={p_veh}")

        f_driver = f_veh = 0
        for f in s.exec(select(FuelTxn).where(FuelTxn.driver_id.is_(None))).all():
            if f.driver_raw_name:
                emp = name_map.get(normalize_name(f.driver_raw_name))
                if emp:
                    f.driver_id = emp.id
                    f_driver += 1
            if f.vehicle_id is None and f.plate_no_raw:
                v = plate_map.get(normalize_plate(f.plate_no_raw))
                if v:
                    f.vehicle_id = v.id
                    f_veh += 1
        s.commit()
        print(f"FuelTxn: filled driver_id={f_driver}  vehicle_id={f_veh}")


if __name__ == "__main__":
    main()
