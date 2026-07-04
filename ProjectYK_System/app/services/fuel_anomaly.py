# -*- coding: utf-8 -*-
"""E2: รายงานน้ำมันผิดปกติ — **อ่านอย่างเดียว ไม่แก้เงินอัตโนมัติ** (ตามสเปค F4/E2).

กติกา (จูนได้ที่ค่าคงที่ด้านล่าง):
  R1 เติมถี่ผิดปกติ — คันเดียวกันเติม ≥2 ครั้งในวันเดียว (ธงเหลือง; รวมลิตรให้ดู)
  R2 ลิตรเกินถัง — ลิตรครั้งเดียว > ขนาดถัง (Vehicle.tank_liters; ยังไม่กรอก =
     default ตามชนิดรถ) (ธงแดง)
  R3 เติมวันที่รถไม่มีงาน — วันนั้นทะเบียนนี้ไม่มีแถวเดลี่เลยทุกไซท์ (ธงฟ้า เบาสุด —
     **เติมข้ามไซท์เป็นเรื่องปกติ** จึงเช็คทุกไซท์รวมกันก่อนธง; ดู memory
     project-lcb-fuel-crosscheck-domain-rules)

หมายเหตุ: "ธงบนสลิป" ของสเปครอ template สลิปว่างจาก session อื่นก่อน — หน้านี้
คือรายงานกลางไว้ไล่ดูก่อน แล้วค่อยผูกธงเข้าสลิปทีหลัง.
"""
from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from models import DailyJob, FuelTxn, Vehicle

# default ขนาดถังตามชนิดรถ (ลิตร) — ใช้เมื่อ Vehicle.tank_liters = 0
DEFAULT_TANK = {"head": 500.0, "truck": 400.0}
FALLBACK_TANK = 500.0
REFILL_PER_DAY_THRESHOLD = 2   # เติม ≥N ครั้ง/วัน/คัน = ธง R1


def _plate_key(plate: str) -> str:
    return (plate or "").strip()


def scan(session: Session, d1: date, d2: date, site: str = "") -> dict:
    """สแกน FuelTxn ช่วงวัน → รายการธง (แถวเดียวติดได้หลายธง) + ตัวเลขสรุป."""
    q = select(FuelTxn).where(FuelTxn.txn_date >= d1, FuelTxn.txn_date <= d2)
    if site:
        q = q.where(FuelTxn.site_code == site)
    fills = session.exec(q.order_by(FuelTxn.txn_date, FuelTxn.id)).all()  # type: ignore[arg-type]

    vehicles = {v.id: v for v in session.exec(select(Vehicle)).all()}
    plate_of_vid = {vid: (v.plate_no or "").strip() for vid, v in vehicles.items()}

    # วันที่ทะเบียนมีงานในเดลี่ (ทุกไซท์ — เติมข้ามไซท์ปกติ)
    jobs = session.exec(select(DailyJob).where(
        DailyJob.work_date >= d1, DailyJob.work_date <= d2)).all()
    plate_days: set[tuple[str, date]] = set()
    for j in jobs:
        p = _plate_key(j.plate_no_raw) or plate_of_vid.get(j.head_vehicle_id or -1, "")
        if p:
            plate_days.add((p, j.work_date))

    # นับเติมต่อ (คัน, วัน)
    per_day: dict[tuple[str, date], list] = {}
    for f in fills:
        p = plate_of_vid.get(f.vehicle_id or -1, "") or _plate_key(f.plate_no_raw)
        per_day.setdefault((p or f"#veh{f.vehicle_id}", f.txn_date), []).append(f)

    rows = []
    n_r1 = n_r2 = n_r3 = 0
    for f in fills:
        p = plate_of_vid.get(f.vehicle_id or -1, "") or _plate_key(f.plate_no_raw)
        key = (p or f"#veh{f.vehicle_id}", f.txn_date)
        flags = []
        same_day = per_day.get(key, [])
        if len(same_day) >= REFILL_PER_DAY_THRESHOLD:
            day_liters = sum(x.liter or 0 for x in same_day)
            flags.append({"code": "R1", "level": "amber",
                          "text": f"เติม {len(same_day)} ครั้งในวัน (รวม {day_liters:,.0f} ลิตร)"})
        v = vehicles.get(f.vehicle_id or -1)
        tank = (v.tank_liters if v and v.tank_liters else 0) or \
            DEFAULT_TANK.get((v.truck_type or "").strip().lower() if v else "", FALLBACK_TANK)
        if (f.liter or 0) > tank:
            flags.append({"code": "R2", "level": "rose",
                          "text": f"ลิตรเกินถัง ({f.liter:,.0f} > {tank:,.0f} ลิตร"
                                  f"{' — ถังตามที่กรอก' if v and v.tank_liters else ' — ถัง default ตามชนิดรถ'})"})
        if p and (p, f.txn_date) not in plate_days:
            flags.append({"code": "R3", "level": "sky",
                          "text": "วันนั้นทะเบียนนี้ไม่มีแถวเดลี่ (ทุกไซท์)"})
        if not flags:
            continue
        n_r1 += any(x["code"] == "R1" for x in flags)
        n_r2 += any(x["code"] == "R2" for x in flags)
        n_r3 += any(x["code"] == "R3" for x in flags)
        rows.append({
            "id": f.id, "date": f.txn_date, "site": f.site_code,
            "plate": p or "—", "driver": f.driver_raw_name or "",
            "liter": f.liter or 0, "amount": f.amount or 0,
            "station": f.station or "", "flags": flags,
            "worst": ("rose" if any(x["level"] == "rose" for x in flags)
                      else "amber" if any(x["level"] == "amber" for x in flags)
                      else "sky"),
        })
    rows.sort(key=lambda r: ({"rose": 0, "amber": 1, "sky": 2}[r["worst"]], r["date"]))
    return {"rows": rows, "n_fills": len(fills),
            "n_r1": n_r1, "n_r2": n_r2, "n_r3": n_r3}
