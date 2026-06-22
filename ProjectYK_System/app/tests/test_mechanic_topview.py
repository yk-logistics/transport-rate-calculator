from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle, Tire, TireEvent
import services.access_link as al


def _setup():
    tok = al.make_token("mechanic", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="mechanic", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-2345", truck_type="10W", vehicle_kind="head", status="active")
        s.add(v); s.commit(); s.refresh(v)
        return tok, v.id


def test_mechanic_form_renders_topview_for_vehicle(client):
    tok, vid = _setup()
    r = client.get(f"/check/mechanic?t={tok}&vehicle_id={vid}")
    assert r.status_code == 200
    assert "เพลาหลัง (ตัวหลัง)" in r.text
    # mechanic gets a mm input per tyre (not just a condition select)
    assert 'name="mm_FL"' in r.text
    assert 'name="cond_FL"' in r.text


def test_mechanic_inspect_submit_stores_measured_tread(client):
    tok, vid = _setup()
    data = {"t": tok, "actor_name": "ช่างเอก", "vehicle_id": str(vid), "mile": "55000",
            "cond_FL": "ok", "mm_FL": "9.5",
            "cond_FR": "near", "mm_FR": "4.0"}
    r = client.post(f"/check/mechanic/inspect?t={tok}", data=data, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        evs = s.exec(select(TireEvent).where(TireEvent.event_type == "inspect")).all()
        assert len(evs) == 2
        assert all(e.actor_role == "mechanic" for e in evs)
        fl = next(e for e in evs if e.to_position == "FL")
        assert fl.tread_after_mm == 9.5     # measured, not 0
        # mechanic-measured events are NOT awaiting (tread filled)
        import services.tire_view as tv
        assert tv.awaiting_mechanic(s) == []


def test_mechanic_inspect_rejects_bad_token(client):
    _tok, vid = _setup()
    r = client.post("/check/mechanic/inspect?t=bad",
                    data={"vehicle_id": str(vid)}, follow_redirects=False)
    assert r.status_code in (400, 403)
