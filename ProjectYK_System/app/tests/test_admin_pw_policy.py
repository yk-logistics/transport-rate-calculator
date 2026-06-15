"""Admin-set temp passwords (create + reset) must meet the same minimum length
as self-service change, so accounts can't be created with a 1-char password.
"""
from sqlmodel import Session, select
from db_config import engine
from models import AppUser
from auth import hash_password


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u)
        s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_create_rejects_short_temp_password(client):
    _login_admin(client)
    r = client.post("/admin/users/new",
                    data={"username": "shorty", "display_name": "S",
                          "role": "viewer", "temp_password": "abc"},
                    follow_redirects=False)
    assert r.status_code == 400
    with Session(engine) as s:
        assert s.exec(select(AppUser).where(AppUser.username == "shorty")).first() is None


def test_create_accepts_valid_temp_password(client):
    _login_admin(client)
    r = client.post("/admin/users/new",
                    data={"username": "okuser", "display_name": "OK",
                          "role": "viewer", "temp_password": "temp1234"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        assert s.exec(select(AppUser).where(AppUser.username == "okuser")).first() is not None


def test_reset_rejects_short_temp_password(client):
    _login_admin(client)
    client.post("/admin/users/new",
                data={"username": "rstuser", "display_name": "R",
                      "role": "viewer", "temp_password": "temp1234"})
    with Session(engine) as s:
        uid = s.exec(select(AppUser).where(AppUser.username == "rstuser")).first().id
    r = client.post(f"/admin/users/{uid}/reset",
                    data={"temp_password": "x"}, follow_redirects=False)
    assert r.status_code == 400
