from sqlmodel import Session
from db_config import engine
from models import Tire, TireEvent
from datetime import date
import services.tire_view as tv
import models


def test_outer_inner_classification():
    assert tv.is_outer("FL") is True
    assert tv.is_outer("RRO1") is True
    assert tv.is_outer("RLI2") is False
    assert tv.is_outer("TRL_RO2") is True
    assert tv.is_outer("TRL_LI1") is False


def test_photo_count():
    assert tv.photo_count("RLO1") == 2
    assert tv.photo_count("RLI1") == 1


def test_th_label_known_and_fallback():
    assert tv.th_label("FL") == "ซ้ายหน้า"
    assert tv.th_label("ZZZ") == "ZZZ"


def test_trailer_has_eight_positions():
    assert len(models.TIRE_POSITIONS_BY_KIND["TRL8"]) == 8


def test_awaiting_mechanic_lists_only_unmeasured(client):
    with Session(engine) as s:
        t = Tire(code="T7001", spec="11R22.5", status="in_use")
        s.add(t); s.commit(); s.refresh(t)
        # driver report, no tread yet -> awaiting
        s.add(TireEvent(tire_id=t.id, event_date=date(2026, 6, 22),
                        event_type="inspect", condition_flag="ok", tread_after_mm=0.0))
        # already measured -> NOT awaiting
        s.add(TireEvent(tire_id=t.id, event_date=date(2026, 6, 22),
                        event_type="inspect", condition_flag="ok", tread_after_mm=7.5))
        s.commit()
        rows = tv.awaiting_mechanic(s)
        assert len(rows) == 1
        assert rows[0].tread_after_mm == 0.0


def test_distance_since_last(client):
    with Session(engine) as s:
        t = Tire(code="T7002", spec="11R22.5", status="in_use", current_vehicle_id=5)
        s.add(t); s.commit(); s.refresh(t)
        s.add(TireEvent(tire_id=t.id, event_date=date(2026, 6, 1),
                        event_type="inspect", to_vehicle_id=5, mile=100000.0))
        s.commit()
        assert tv.distance_since_last(s, 5, 103150.0) == 3150.0
        assert tv.distance_since_last(s, 5, 99000.0) == 0.0   # negative clamped
        assert tv.distance_since_last(s, 999, 5000.0) == 0.0  # no prior
