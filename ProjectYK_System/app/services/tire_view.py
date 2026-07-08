"""Presentation + read helpers for the tire-check flows. No mutations."""
import re

from sqlmodel import Session, select

import models
from models import Tire, TireEvent


def th_label(pos: str) -> str:
    return models.TIRE_POSITION_TH.get((pos or "").upper(), pos)


def short_label(pos: str) -> str:
    """Tile-sized label: position name without the axle qualifier in parentheses.
    The axle caption above the tile already says which axle, so '(เพลาหน้า)' is
    redundant inside each tile and makes them too wide for a phone.
    e.g. 'ซ้ายหลังนอก (เพลาหน้า)' -> 'ซ้ายหลังนอก'."""
    return re.sub(r"\s*\(.*\)\s*$", "", th_label(pos)).strip()


def is_outer(pos: str) -> bool:
    p = (pos or "").upper()
    if p in ("FL", "FR"):
        return True
    # strip a trailing axle digit, then classify by O/I suffix
    base = re.sub(r"\d+$", "", p)
    if base.endswith("O"):
        return True
    if base.endswith("I"):
        return False
    return True  # singles / unknown default to outer (2 photos)


def photo_count(pos: str) -> int:
    return 2 if is_outer(pos) else 1


def awaiting_mechanic(session: Session) -> list[TireEvent]:
    rows = session.exec(
        select(TireEvent).where(
            TireEvent.event_type == "inspect",
            TireEvent.condition_flag != "",
            TireEvent.tread_after_mm == 0.0,
        ).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())
    ).all()
    return list(rows)


def distance_since_last(session: Session, vehicle_id: int, current_mile: float) -> float:
    prior = session.exec(
        select(TireEvent).where(
            TireEvent.event_type == "inspect",
            TireEvent.to_vehicle_id == vehicle_id,
            TireEvent.mile > 0,
        ).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())
    ).first()
    if not prior:
        return 0.0
    diff = current_mile - prior.mile
    return diff if diff > 0 else 0.0


def _cell(pos: str) -> dict:
    return {"pos": pos, "label": th_label(pos), "short": short_label(pos),
            "photos": photo_count(pos), "outer": is_outer(pos)}


def axle_layout(positions) -> list[dict]:
    """Group position codes into axles for a top-view diagram.

    Returns a list of axles, front-to-back. Each axle:
      {"tag": <thai caption>, "left": [cell...], "right": [cell...]}
    Left side ordered outer->inner; right side ordered inner->outer
    (so the diagram reads outer-edge ... spine ... outer-edge).
    """
    pos = list(positions)
    axles: list[dict] = []

    # Front steer axle (single tyre each side)
    if "FL" in pos or "FR" in pos:
        axles.append({"tag": "เพลาหน้า",
                      "left": [_cell("FL")] if "FL" in pos else [],
                      "right": [_cell("FR")] if "FR" in pos else []})

    # Rear drive axles: RL*/RR* grouped by trailing axle digit ("", "1", "2", ...)
    rear = [p for p in pos if p.startswith(("RL", "RR"))]
    digits = []
    for p in rear:
        d = "".join(ch for ch in p if ch.isdigit())
        if d not in digits:
            digits.append(d)
    rear_tags = {1: ["เพลาหลัง"], 2: ["เพลาหลัง (ตัวหน้า)", "เพลาหลัง (ตัวหลัง)"]}
    captions = rear_tags.get(len(digits), [f"เพลาหลัง {i+1}" for i in range(len(digits))])
    for i, d in enumerate(digits):
        lout, lin = f"RLO{d}", f"RLI{d}"
        rin, rout = f"RRI{d}", f"RRO{d}"
        axles.append({
            "tag": captions[i],
            "left":  [_cell(c) for c in (lout, lin) if c in pos],
            "right": [_cell(c) for c in (rin, rout) if c in pos],
        })

    # Trailer axles: TRL_L*1/2 ... grouped by trailing digit
    trl = [p for p in pos if p.startswith("TRL_")]
    tdigits = []
    for p in trl:
        d = "".join(ch for ch in p if ch.isdigit())
        if d not in tdigits:
            tdigits.append(d)
    for i, d in enumerate(tdigits):
        # Twin-tyre trailer (TRL8): outer/inner each side. Single-tyre
        # trailer (10WL/18W: TRL_L{d}/TRL_R{d}): one tyre each side.
        left  = [c for c in (f"TRL_LO{d}", f"TRL_LI{d}", f"TRL_L{d}") if c in pos]
        right = [c for c in (f"TRL_R{d}", f"TRL_RI{d}", f"TRL_RO{d}") if c in pos]
        tag = "หาง · เพลาหน้า" if i == 0 and len(tdigits) > 1 else (
              "หาง · เพลาหลัง" if i == 1 else "หาง")
        axles.append({
            "tag": tag,
            "left":  [_cell(c) for c in left],
            "right": [_cell(c) for c in right],
        })

    return axles


# ---------------------------------------------------------------------------
# Lifecycle / cost report — "หยุดเลือด": เทียบยางหล่อ vs แท้ + เหตุที่เปลี่ยน
# ---------------------------------------------------------------------------

_REMOVAL_TYPES = ("unmount", "scrap")


def _first_mount(events: list[TireEvent]) -> TireEvent | None:
    for e in sorted(events, key=lambda x: (x.event_date, x.id or 0)):
        if e.event_type == "mount":
            return e
    return None


def _last_removal(events: list[TireEvent]) -> TireEvent | None:
    for e in sorted(events, key=lambda x: (x.event_date, x.id or 0), reverse=True):
        if e.event_type in _REMOVAL_TYPES:
            return e
    return None


def tire_lifecycle_report(session: Session) -> dict:
    """Aggregate retired tyres (mounted then removed) into cost/longevity stats.

    Returns:
      {
        "by_type":   [ {tire_type, count, avg_days, avg_km|None, km_sample,
                        avg_price, baht_per_month|None, baht_per_1000km|None}, ... ],
        "by_reason": [ {reason_code, label, count, cost}, ... ]  (most-frequent first),
        "retired_count": int,
      }

    Longevity is per-tyre lifespan (first mount -> last removal). A tyre without
    odometer readings on both ends contributes to days but not km, so the km
    columns degrade gracefully (None) instead of crashing when miles are missing.
    """
    tires = session.exec(select(Tire)).all()
    events = session.exec(select(TireEvent)).all()
    ev_by_tire: dict[int, list[TireEvent]] = {}
    for e in events:
        ev_by_tire.setdefault(e.tire_id, []).append(e)

    # accumulator per tire_type
    agg: dict[str, dict] = {}
    reason_agg: dict[str, dict] = {}

    for t in tires:
        evs = ev_by_tire.get(t.id, [])
        mount = _first_mount(evs)
        removal = _last_removal(evs)
        if not mount or not removal:
            continue  # not a completed lifecycle yet

        days = (removal.event_date - mount.event_date).days
        if days < 0:
            days = 0
        has_km = bool(mount.mile) and bool(removal.mile) and removal.mile > mount.mile
        km = (removal.mile - mount.mile) if has_km else None
        price = t.purchase_price or 0.0
        ttype = t.tire_type or "new"

        a = agg.setdefault(ttype, {
            "tire_type": ttype, "count": 0, "days_sum": 0, "km_sum": 0.0,
            "km_sample": 0, "price_sum": 0.0,
        })
        a["count"] += 1
        a["days_sum"] += days
        a["price_sum"] += price
        if km is not None:
            a["km_sum"] += km
            a["km_sample"] += 1

        reason = removal.reason_code or t.removal_reason or "other"
        ra = reason_agg.setdefault(reason, {"reason_code": reason, "count": 0, "cost": 0.0})
        ra["count"] += 1
        ra["cost"] += price

    type_label = dict(models.TIRE_TYPES)
    reason_label = dict(models.TIRE_REMOVAL_REASONS)

    by_type = []
    for ttype, a in agg.items():
        n = a["count"]
        avg_days = round(a["days_sum"] / n) if n else 0
        avg_price = a["price_sum"] / n if n else 0.0
        avg_km = round(a["km_sum"] / a["km_sample"]) if a["km_sample"] else None
        baht_per_month = (avg_price / (avg_days / 30.0)) if avg_days else None
        baht_per_1000km = (avg_price / (avg_km / 1000.0)) if avg_km else None
        by_type.append({
            "tire_type": ttype,
            "label": type_label.get(ttype, ttype),
            "count": n,
            "avg_days": avg_days,
            "avg_km": avg_km,
            "km_sample": a["km_sample"],
            "avg_price": round(avg_price, 2),
            "baht_per_month": (round(baht_per_month, 2) if baht_per_month is not None else None),
            "baht_per_1000km": (round(baht_per_1000km, 2) if baht_per_1000km is not None else None),
        })
    by_type.sort(key=lambda r: r["tire_type"])

    by_reason = sorted(
        (
            {"reason_code": r, "label": reason_label.get(r, r),
             "count": d["count"], "cost": round(d["cost"], 2)}
            for r, d in reason_agg.items()
        ),
        key=lambda r: (-r["count"], r["reason_code"]),
    )

    return {
        "by_type": by_type,
        "by_reason": by_reason,
        "retired_count": sum(a["count"] for a in agg.values()),
    }
