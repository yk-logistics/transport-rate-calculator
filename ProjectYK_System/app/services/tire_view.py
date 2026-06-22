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
