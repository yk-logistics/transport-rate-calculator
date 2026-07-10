# -*- coding: utf-8 -*-
"""เขียนบิลจาก RM History ลง DB — idempotent + rollback ได้ + dry-run เป็นค่าเริ่มต้น.

กฎเงิน:
- จับคู่ทะเบียนไม่ได้ = ไม่เขียนทั้งแท็บ (ห้ามมี MaintRecord ลอยไม่มีเจ้าของ)
- ทุกแถวที่ import มี import_key ขึ้นต้น "rm:<file>:"; บันทึกที่คนคีย์เองมีค่าว่าง
  → rollback ไม่มีวันแตะ
- บรรทัดที่ชีทไม่กรอกช่อง "ราคาสุทธิ" ยังนับ (รวม−ส่วนลด+VAT) — โอเคาะ 9 ก.ค. 2026
"""
from __future__ import annotations

import hashlib

from sqlalchemy import delete
from sqlmodel import Session, select

from models import MaintPart, MaintRecord, Vehicle, Vendor
from services.rm_history import ParsedTab

SHEETS = {
    "bigc":    "1rM00xNmUVL3XT4lCHf8Ooh9FHRlFp211cIrkszoCZXE",
    "wangnoi": "1trglO8b727sUcGC5n7kd3v2aYnXf9h0su8eJGtOzfOw",
    "lcb":     "169mraSWWU0l9HOL7_dkKCVIMZU5vlaWXspAK2ItDUnQ",
}


def make_import_key(file_slug: str, sheet_id: str, tab: str, first_row: int) -> str:
    """ขึ้นต้นด้วย rm:<file>: เพื่อให้ rollback กรองตามไฟล์ได้ (sha1 ล้วนกรองไม่ได้)."""
    h = hashlib.sha1(f"{sheet_id}|{tab}|{first_row}".encode()).hexdigest()[:16]
    return f"rm:{file_slug}:{h}"


def _next_record_no(session: Session) -> str:
    rows = session.exec(select(MaintRecord.record_no)).all()
    n = max((int(r[1:]) for r in rows if r and r[0] == "M" and r[1:].isdigit()), default=0)
    return f"M{n + 1:06d}"


def _find_or_create_vendor(session: Session, name: str, dry_run: bool) -> tuple[int | None, bool]:
    clean = " ".join((name or "").split())
    if not clean or clean == "-":
        return None, False
    v = session.exec(select(Vendor).where(Vendor.name == clean)).first()
    if v:
        return v.id, False
    if dry_run:
        return None, True
    codes = session.exec(select(Vendor.code)).all()
    n = max((int(c[1:]) for c in codes if c and c[0] == "V" and c[1:].isdigit()), default=0)
    v = Vendor(code=f"V{n + 1:04d}", name=clean, kind="service")
    session.add(v)
    session.commit()
    session.refresh(v)
    return v.id, True


def import_tab(session: Session, file_slug: str, sheet_id: str, tab: str,
               parsed: ParsedTab, dry_run: bool = True) -> dict:
    stats: dict = {"bills": 0, "lines": 0, "skipped_dup": 0, "skipped_tab": 0,
                   "new_vendors": [], "system_net": 0.0, "blank_net_lines": 0,
                   "blank_net_baht": 0.0}

    vehicle = None
    if parsed.plate:
        vehicle = session.exec(select(Vehicle).where(Vehicle.plate_no == parsed.plate)).first()
    if vehicle is None:
        stats["skipped_tab"] = 1
        return stats

    for bill in parsed.bills:
        key = make_import_key(file_slug, sheet_id, tab, bill.sheet_row)
        if session.exec(select(MaintRecord).where(MaintRecord.import_key == key)).first():
            stats["skipped_dup"] += 1
            continue

        vendor_id, is_new = _find_or_create_vendor(session, bill.vendor, dry_run)
        if is_new:
            clean = " ".join(bill.vendor.split())
            if clean not in stats["new_vendors"]:
                stats["new_vendors"].append(clean)

        parts = sum(l["total"] for l in bill.lines if l["kind"] == "part")
        labor = sum(l["total"] for l in bill.lines if l["kind"] == "labor")
        other = sum(l["total"] for l in bill.lines if l["kind"] == "service")
        disc = sum(l["discount"] for l in bill.lines)
        vat = sum(l["vat"] for l in bill.lines)
        net = round(parts + labor + other - disc + vat, 2)

        for l in bill.lines:                      # บรรทัดที่ชีทไม่กรอกช่องสุทธิ (แต่มีราคา)
            calc = round(l["total"] - l["discount"] + l["vat"], 2)
            if l["net"] == 0.0 and calc > 0:
                stats["blank_net_lines"] += 1
                stats["blank_net_baht"] = round(stats["blank_net_baht"] + calc, 2)

        stats["bills"] += 1
        stats["lines"] += len(bill.lines)
        stats["system_net"] = round(stats["system_net"] + net, 2)
        if dry_run:
            continue

        rec = MaintRecord(
            record_no=_next_record_no(session), work_date=bill.work_date,
            vehicle_id=vehicle.id, plate_raw=parsed.plate, mile_snapshot=bill.mile,
            kind="repair", status="done", vendor_id=vendor_id,
            parts_cost=parts, labor_cost=labor, other_cost=other,
            discount=disc, vat=vat, total_cost=net, import_key=key,
            notes=f"นำเข้าจาก RM History ({file_slug}!{tab} แถว {bill.sheet_row})")
        session.add(rec)
        session.commit()
        session.refresh(rec)
        for l in bill.lines:
            session.add(MaintPart(
                maint_record_id=rec.id, kind=l["kind"], part_name_raw=l["name"],
                qty=l["qty"], unit_price=l["unit_price"], total=l["total"],
                discount=l["discount"], vat=l["vat"]))
        session.commit()
    return stats


def rollback_file(session: Session, file_slug: str, dry_run: bool = True) -> int:
    """ลบเฉพาะแถวที่ import จากไฟล์นี้ — บันทึกที่คนคีย์เอง (import_key='') ไม่โดนแตะ."""
    prefix = f"rm:{file_slug}:"
    recs = session.exec(select(MaintRecord).where(
        MaintRecord.import_key.startswith(prefix))).all()   # type: ignore[union-attr]
    if dry_run or not recs:
        return len(recs)
    ids = [r.id for r in recs]
    session.exec(delete(MaintPart).where(MaintPart.maint_record_id.in_(ids)))  # type: ignore[attr-defined]
    session.exec(delete(MaintRecord).where(MaintRecord.id.in_(ids)))           # type: ignore[attr-defined]
    session.commit()
    return len(ids)
