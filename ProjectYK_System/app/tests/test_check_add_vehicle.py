from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle
import services.access_link as al


def _link(role="driver"):
    tok = al.make_token(role, 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
    return tok


def test_add_vehicle_creates_and_redirects(client):
    tok = _link("driver")
    r = client.post(f"/check/add-vehicle?t={tok}",
                    data={"t": tok, "role": "driver", "plate_no": "71-5555",
                          "truck_type": "TRL8", "nickname": "หางA"},
                    follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert "/check/driver" in loc and "vehicle_id=" in loc
    with Session(engine) as s:
        v = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-5555")).first()
        assert v is not None
        assert v.truck_type == "TRL8"
        assert v.vehicle_kind == "tail"


def test_add_existing_plate_reuses_without_overwrite(client):
    tok = _link("driver")
    with Session(engine) as s:
        s.add(Vehicle(plate_no="71-6666", truck_type="10W", vehicle_kind="head"))
        s.commit()
    r = client.post(f"/check/add-vehicle?t={tok}",
                    data={"t": tok, "role": "driver", "plate_no": "71-6666",
                          "truck_type": "6W"}, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        rows = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-6666")).all()
        assert len(rows) == 1
        assert rows[0].truck_type == "10W"   # unchanged


def test_add_vehicle_rejects_bad_token(client):
    r = client.post("/check/add-vehicle?t=bad",
                    data={"t": "bad", "role": "driver", "plate_no": "x", "truck_type": "6W"},
                    follow_redirects=False)
    assert r.status_code in (400, 403)
