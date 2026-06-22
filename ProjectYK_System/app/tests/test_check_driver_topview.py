from datetime import datetime, timedelta
from sqlmodel import Session
from db_config import engine
from models import AccessLink, Vehicle
import services.access_link as al


def _setup():
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="driver", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-2345", truck_type="10W", vehicle_kind="head", status="active")
        s.add(v); s.commit(); s.refresh(v)
        return tok, v.id


def test_topview_renders_axle_tags_and_all_positions(client):
    tok, vid = _setup()
    r = client.get(f"/check/driver?t={tok}&actor_name=x&vehicle_id={vid}")
    assert r.status_code == 200
    assert "เพลาหน้า" in r.text
    assert "เพลาหลัง (ตัวหลัง)" in r.text
    for pos in ("FL", "FR", "RLO1", "RLI1", "RRI1", "RRO1",
                "RLO2", "RLI2", "RRI2", "RRO2"):
        assert f'name="cond_{pos}"' in r.text


def test_add_vehicle_form_present(client):
    tok, _vid = _setup()
    r = client.get(f"/check/driver?t={tok}&actor_name=x")
    assert r.status_code == 200
    assert "/check/add-vehicle" in r.text
    assert "เพิ่มทะเบียน" in r.text
