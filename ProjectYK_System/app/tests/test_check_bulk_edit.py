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


def test_bulk_updates_multiple_vehicles(client):
    tok = _link("mechanic")
    a = _vehicle("BULK-A", "10W")
    b = _vehicle("BULK-B", "10W")
    c = _vehicle("BULK-C", "10W")
    r = client.post(f"/check/mechanic/edit-vehicles?t={tok}",
                    data={"t": tok, f"type_{a}": "6W", f"type_{b}": "6W",
                          f"type_{c}": "10W"},
                    follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        assert s.get(Vehicle, a).truck_type == "6W"
        assert s.get(Vehicle, b).truck_type == "6W"
        assert s.get(Vehicle, c).truck_type == "10W"


def test_bulk_sets_kind_tail_for_trailer_type(client):
    tok = _link("mechanic")
    a = _vehicle("BULK-T", "10W", kind="truck")
    client.post(f"/check/mechanic/edit-vehicles?t={tok}",
                data={"t": tok, f"type_{a}": "TRL8"}, follow_redirects=False)
    with Session(engine) as s:
        v = s.get(Vehicle, a)
        assert v.truck_type == "TRL8"
        assert v.vehicle_kind == "tail"


def test_bulk_ignores_empty_and_unchanged(client):
    tok = _link("mechanic")
    a = _vehicle("BULK-E", "10W")
    client.post(f"/check/mechanic/edit-vehicles?t={tok}",
                data={"t": tok, f"type_{a}": ""}, follow_redirects=False)
    with Session(engine) as s:
        assert s.get(Vehicle, a).truck_type == "10W"


def test_driver_cannot_bulk_edit(client):
    tok = _link("driver")
    a = _vehicle("BULK-D", "10W")
    r = client.post(f"/check/mechanic/edit-vehicles?t={tok}",
                    data={"t": tok, f"type_{a}": "6W"}, follow_redirects=False)
    assert r.status_code == 403
    with Session(engine) as s:
        assert s.get(Vehicle, a).truck_type == "10W"


def test_mechanic_page_has_bulk_table(client):
    tok = _link("mechanic")
    _vehicle("TABLE-1", "10W")
    r = client.get(f"/check/mechanic?t={tok}")
    assert r.status_code == 200
    assert "แก้ประเภทรถหลายคัน" in r.text
    assert "TABLE-1" in r.text
    assert "บันทึกทั้งหมด" in r.text
