import pytest
from sqlmodel import Session, select
from db_config import engine
from models import AppUser
from auth import hash_password


def _login_admin(client):
    # Deterministic admin login that doesn't depend on yk1's mutable password or
    # cross-test ordering: force a known hash directly, then log in.
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u)
        s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_admin_can_list_users(client):
    _login_admin(client)
    r = client.get("/admin/users")
    assert r.status_code == 200
    assert "yk1" in r.text


def test_admin_can_create_user(client):
    _login_admin(client)
    r = client.post("/admin/users/new",
                    data={"username": "yk2", "display_name": "Tester 2",
                          "role": "office", "temp_password": "temp1234"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk2")).first()
    assert u is not None and u.role == "office" and u.must_change_pw is True


def test_non_admin_cannot_reach_admin_users(client):
    with Session(engine) as s:
        if not s.exec(select(AppUser).where(AppUser.username == "off2")).first():
            s.add(AppUser(username="off2", password_hash=hash_password("pw123456"),
                          display_name="off2", role="office", status="active",
                          must_change_pw=False))
            s.commit()
    client.post("/login", data={"username": "off2", "password": "pw123456"})
    r = client.get("/admin/users", follow_redirects=False)
    assert r.status_code == 403


def test_admin_can_disable_user(client):
    _login_admin(client)
    client.post("/admin/users/new",
                data={"username": "yk3", "display_name": "T3",
                      "role": "viewer", "temp_password": "temp1234"})
    with Session(engine) as s:
        uid = s.exec(select(AppUser).where(AppUser.username == "yk3")).first().id
    r = client.post(f"/admin/users/{uid}/disable", follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        assert s.get(AppUser, uid).status == "disabled"
