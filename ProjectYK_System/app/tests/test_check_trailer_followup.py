from datetime import datetime, timedelta
from sqlmodel import Session
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


def _trailer(plate):
    with Session(engine) as s:
        s.add(Vehicle(plate_no=plate, truck_type="TRL8", vehicle_kind="tail",
                      status="active"))
        s.commit()


def test_done_shows_trailer_followup_when_trailers_exist(client):
    _trailer("HANG-A1")
    tok = _link("driver")
    r = client.get(f"/check/driver?t={tok}&done=6")
    assert r.status_code == 200
    assert "ตรวจหัวเรียบร้อย" in r.text
    assert "HANG-A1" in r.text
    assert "ตรวจหางต่อ" in r.text


def test_done_without_trailers_shows_finish_only(client):
    tok = _link("driver")
    r = client.get(f"/check/driver?t={tok}&done=6")
    assert r.status_code == 200
    assert "ตรวจหัวเรียบร้อย" in r.text
    assert "ยังไม่มีทะเบียนหาง" in r.text
    assert "เสร็จแล้ว" in r.text


def test_no_done_no_panel(client):
    tok = _link("driver")
    r = client.get(f"/check/driver?t={tok}")
    assert r.status_code == 200
    assert "ตรวจหัวเรียบร้อย" not in r.text
