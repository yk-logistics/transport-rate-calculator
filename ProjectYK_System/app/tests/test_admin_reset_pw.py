import pytest
from sqlmodel import Session, select
from db_config import engine
from models import AppUser
from auth import hash_password, verify_password


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u)
        s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_reset_sets_temp_pw_and_forces_change(client):
    _login_admin(client)
    # create a user, then reset their password
    client.post("/admin/users/new",
                data={"username": "yk5", "display_name": "T5",
                      "role": "viewer", "temp_password": "first123"})
    with Session(engine) as s:
        uid = s.exec(select(AppUser).where(AppUser.username == "yk5")).first().id
    r = client.post(f"/admin/users/{uid}/reset",
                    data={"temp_password": "reset456"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        u = s.get(AppUser, uid)
    assert verify_password("reset456", u.password_hash)
    assert u.must_change_pw is True


def test_reset_button_present_in_admin_page(client):
    _login_admin(client)
    client.post("/admin/users/new",
                data={"username": "yk6", "display_name": "T6",
                      "role": "viewer", "temp_password": "first123"})
    r = client.get("/admin/users")
    assert r.status_code == 200
    # a reset form should be rendered for the non-yk1 user
    assert "/reset" in r.text


def test_admin_cannot_see_existing_password_hash_as_plaintext(client):
    # Security guarantee: the page must NOT leak password hashes either.
    _login_admin(client)
    r = client.get("/admin/users")
    with Session(engine) as s:
        h = s.exec(select(AppUser).where(AppUser.username == "yk1")).first().password_hash
    assert h not in r.text
