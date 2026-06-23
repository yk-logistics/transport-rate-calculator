"""Photos are mandatory: a tyre marked with a condition but missing its
required photos (outer=2, inner=1) must be rejected server-side, not just
gated in the browser. A driver with a tampered/old client can't slip an
inspection through without proof.
"""
import io
from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle, TireEvent
import services.access_link as al


def _driver_link():
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="driver", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-2345", vehicle_kind="head", truck_type="6W")
        s.add(v); s.commit(); s.refresh(v)
        return tok, v.id


def _jpg_bytes(n=2000):
    # minimal JPEG-ish payload over the 100-byte threshold
    return b"\xff\xd8\xff\xe0" + b"\x00" * n + b"\xff\xd9"


def test_condition_without_photos_is_rejected(client):
    tok, vid = _driver_link()
    # FL is an outer wheel -> needs 2 photos; we send a condition but no files
    r = client.post(f"/check/driver?t={tok}",
                    data={"t": tok, "actor_name": "สมชาย", "vehicle_id": str(vid),
                          "mile": "1000", "cond_FL": "ok"},
                    follow_redirects=False)
    assert r.status_code == 400
    with Session(engine) as s:
        evs = s.exec(select(TireEvent).where(TireEvent.event_type == "inspect")).all()
        assert evs == []   # nothing saved


def test_outer_wheel_with_one_photo_rejected(client):
    tok, vid = _driver_link()
    files = {"photo_FL": ("side.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg")}
    r = client.post(f"/check/driver?t={tok}",
                    data={"t": tok, "actor_name": "x", "vehicle_id": str(vid),
                          "mile": "1000", "cond_FL": "ok"},
                    files=files, follow_redirects=False)
    assert r.status_code == 400   # outer needs 2, only 1 given
    with Session(engine) as s:
        assert s.exec(select(TireEvent)).all() == []


def test_complete_photos_accepted(client):
    tok, vid = _driver_link()
    # FL outer = 2 photos; send both with the SAME field name (multi-file)
    files = [
        ("photo_FL", ("side.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg")),
        ("photo_FL", ("face.jpg", io.BytesIO(_jpg_bytes()), "image/jpeg")),
    ]
    r = client.post(f"/check/driver?t={tok}",
                    data={"t": tok, "actor_name": "สมชาย", "vehicle_id": str(vid),
                          "mile": "1000", "cond_FL": "ok"},
                    files=files, follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        evs = s.exec(select(TireEvent).where(TireEvent.event_type == "inspect")).all()
        assert len(evs) == 1
        assert evs[0].to_position == "FL"
        assert evs[0].photo_paths.count(",") == 1   # two paths -> one comma
