from sqlmodel import Session, select
from db_config import engine
from models import AppUser
from auth import hash_password


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_admin_sees_check_links_menu(client):
    _login_admin(client)
    r = client.get("/maint")
    assert r.status_code == 200
    assert "/admin/check-links" in r.text
    assert "ลิงก์ตรวจสภาพรถ" in r.text
