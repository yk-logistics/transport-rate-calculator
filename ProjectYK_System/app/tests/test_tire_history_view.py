from sqlmodel import Session, select
from db_config import engine
from models import Vehicle, Tire, TireEvent, AppUser
from auth import hash_password
from datetime import date


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_office_by_vehicle_shows_inspect_actor(client):
    _login_admin(client)
    with Session(engine) as s:
        v = Vehicle(plate_no="71-7777", vehicle_kind="head", truck_type="6W", status="active")
        s.add(v); s.commit(); s.refresh(v)
        t = Tire(code="T6001", spec="11R22.5", status="in_use",
                 current_vehicle_id=v.id, current_position="FL", tread_depth_mm=6.0)
        s.add(t); s.commit(); s.refresh(t)
        s.add(TireEvent(tire_id=t.id, event_date=date(2026, 6, 22), event_type="inspect",
                        to_vehicle_id=v.id, to_position="FL", mile=50000,
                        actor_name="สมชาย", actor_role="driver", condition_flag="near",
                        tread_after_mm=6.0, photo_paths="check/2026-06-22/x.jpg"))
        s.commit()
        vid = v.id
    r = client.get(f"/maint/tires/by-vehicle/{vid}")
    assert r.status_code == 200
    assert "สมชาย" in r.text
