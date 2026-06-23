from datetime import datetime, timedelta
from sqlmodel import Session
from db_config import engine
from models import AccessLink, Vehicle
import services.access_link as al


def _link(role="mechanic"):
    tok = al.make_token(role, 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
    return tok


def _vehicle(plate, ttype, kind="truck"):
    with Session(engine) as s:
        v = Vehicle(plate_no=plate, truck_type=ttype, vehicle_kind=kind)
        s.add(v); s.commit(); s.refresh(v)
        return v.id


def test_mechanic_can_change_truck_type(client):
    tok = _link("mechanic")
    vid = _vehicle("EDIT-1", "10W")
    r = client.post(f"/check/mechanic/edit-vehicle?t={tok}",
                    data={"t": tok, "vehicle_id": vid, "truck_type": "6W"},
                    follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        assert s.get(Vehicle, vid).truck_type == "6W"


def test_driver_cannot_edit_vehicle(client):
    tok = _link("driver")
    vid = _vehicle("EDIT-2", "10W")
    r = client.post(f"/check/mechanic/edit-vehicle?t={tok}",
                    data={"t": tok, "vehicle_id": vid, "truck_type": "6W"},
                    follow_redirects=False)
    assert r.status_code == 403
    with Session(engine) as s:
        assert s.get(Vehicle, vid).truck_type == "10W"  # unchanged


def test_edit_to_trailer_sets_kind_tail(client):
    tok = _link("mechanic")
    vid = _vehicle("EDIT-3", "10W")
    client.post(f"/check/mechanic/edit-vehicle?t={tok}",
                data={"t": tok, "vehicle_id": vid, "truck_type": "TRL8"},
                follow_redirects=False)
    with Session(engine) as s:
        assert s.get(Vehicle, vid).vehicle_kind == "tail"


def test_empty_truck_type_keeps_existing(client):
    tok = _link("mechanic")
    vid = _vehicle("EDIT-4", "10W")
    client.post(f"/check/mechanic/edit-vehicle?t={tok}",
                data={"t": tok, "vehicle_id": vid, "truck_type": ""},
                follow_redirects=False)
    with Session(engine) as s:
        assert s.get(Vehicle, vid).truck_type == "10W"


def test_mechanic_page_has_edit_and_add_ui(client):
    tok = _link("mechanic")
    r = client.get(f"/check/mechanic?t={tok}")
    assert r.status_code == 200
    assert "แก้ประเภทรถ" in r.text
    assert "เพิ่มทะเบียน" in r.text
