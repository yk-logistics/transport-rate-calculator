from sqlmodel import Session
from db_config import engine
from models import TireEvent, Tire
from datetime import date


def test_tireevent_has_magiclink_fields(client):
    with Session(engine) as s:
        t = Tire(code="T9001", spec="11R22.5", status="in_use")
        s.add(t); s.commit(); s.refresh(t)
        ev = TireEvent(
            tire_id=t.id, event_date=date(2026, 6, 22), event_type="inspect",
            photo_paths="check/2026-06-22/abc.jpg,check/2026-06-22/def.jpg",
            actor_name="สมชาย", actor_role="driver",
            condition_flag="problem",
            tread_after_mm=0.0,
        )
        s.add(ev); s.commit(); s.refresh(ev)
        assert ev.id is not None
        assert ev.actor_role == "driver"
        assert ev.condition_flag == "problem"
        assert "abc.jpg" in ev.photo_paths
