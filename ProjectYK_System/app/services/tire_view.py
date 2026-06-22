"""Presentation + read helpers for the tire-check flows. No mutations."""
import re

from sqlmodel import Session, select

import models
from models import TireEvent


def th_label(pos: str) -> str:
    return models.TIRE_POSITION_TH.get((pos or "").upper(), pos)


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
    return {"pos": pos, "label": th_label(pos),
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
        lout, lin = f"TRL_LO{d}", f"TRL_LI{d}"
        rin, rout = f"TRL_RI{d}", f"TRL_RO{d}"
        tag = "หาง · เพลาหน้า" if i == 0 and len(tdigits) > 1 else (
              "หาง · เพลาหลัง" if i == 1 else "หาง")
        axles.append({
            "tag": tag,
            "left":  [_cell(c) for c in (lout, lin) if c in pos],
            "right": [_cell(c) for c in (rin, rout) if c in pos],
        })

    return axles
