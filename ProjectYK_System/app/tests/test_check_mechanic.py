from datetime import datetime, timedelta, date
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Tire, TireEvent
import services.access_link as al


def _mech_link():
    tok = al.make_token("mechanic", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="mechanic", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
    return tok


def _awaiting_event():
    with Session(engine) as s:
        t = Tire(code="T8001", spec="11R22.5", status="in_use",
                 current_vehicle_id=3, current_position="RLO1", tread_depth_mm=8.0)
        s.add(t); s.commit(); s.refresh(t)
        ev = TireEvent(tire_id=t.id, event_date=date(2026, 6, 22), event_type="inspect",
                       to_vehicle_id=3, to_position="RLO1", mile=103150,
                       actor_role="driver", condition_flag="near", tread_after_mm=0.0)
        s.add(ev); s.commit(); s.refresh(ev)
        return ev.id, t.id


def test_mechanic_measure_fills_tread_and_clears_queue(client):
    tok = _mech_link()
    ev_id, tire_id = _awaiting_event()
    r = client.post(f"/check/mechanic/measure?t={tok}",
                    data={"t": tok, "event_id": str(ev_id), "tread_mm": "6.3",
                          "actor_name": "ช่างต้น"}, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        ev = s.get(TireEvent, ev_id)
        assert ev.tread_after_mm == 6.3
        assert ev.actor_role == "mechanic"
        t = s.get(Tire, tire_id)
        assert t.tread_depth_mm == 6.3
        import services.tire_view as tv
        assert all(e.id != ev_id for e in tv.awaiting_mechanic(s))


def test_mechanic_scrap_job_updates_tire(client):
    tok = _mech_link()
    _ev_id, tire_id = _awaiting_event()
    r = client.post(f"/check/mechanic/job?t={tok}",
                    data={"t": tok, "tire_id": str(tire_id), "event_type": "scrap",
                          "actor_name": "ช่างต้น", "note": "ระเบิดข้างทาง"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        t = s.get(Tire, tire_id)
        assert t.status == "scrapped"
        ev = s.exec(select(TireEvent).where(TireEvent.tire_id == tire_id,
                    TireEvent.event_type == "scrap")).first()
        assert ev is not None
        assert ev.actor_role == "mechanic"
