import io
from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle, Tire, TireEvent
import services.access_link as al


def _driver_link():
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="driver", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-2345", vehicle_kind="head", truck_type="10W")
        s.add(v); s.commit(); s.refresh(v)
        vid = v.id
    return tok, vid


def _jpg():
    return io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 2000 + b"\xff\xd9")


def test_driver_submit_creates_inspect_events_without_tread(client):
    tok, vid = _driver_link()
    data = {
        "t": tok, "actor_name": "สมชาย", "vehicle_id": str(vid), "mile": "103150",
        "cond_FL": "ok", "cond_FR": "problem",
    }
    # FL & FR are outer wheels -> each needs 2 photos (now mandatory)
    files = [
        ("photo_FL", ("a.jpg", _jpg(), "image/jpeg")),
        ("photo_FL", ("b.jpg", _jpg(), "image/jpeg")),
        ("photo_FR", ("c.jpg", _jpg(), "image/jpeg")),
        ("photo_FR", ("d.jpg", _jpg(), "image/jpeg")),
    ]
    r = client.post(f"/check/driver?t={tok}", data=data, files=files,
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        evs = s.exec(select(TireEvent).where(TireEvent.event_type == "inspect")).all()
        assert len(evs) == 2
        assert all(e.actor_role == "driver" for e in evs)
        assert all(e.tread_after_mm == 0.0 for e in evs)   # mechanic fills later
        assert any(e.condition_flag == "problem" for e in evs)
        assert all(e.mile == 103150.0 for e in evs)


def test_driver_submit_rejected_without_valid_link(client):
    _tok, vid = _driver_link()
    r = client.post("/check/driver?t=bad", data={"vehicle_id": str(vid)},
                    follow_redirects=False)
    assert r.status_code in (400, 403)
