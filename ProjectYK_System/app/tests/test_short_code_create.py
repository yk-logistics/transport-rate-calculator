from sqlmodel import Session, select
from db_config import engine
from models import AppUser, AccessLink
from auth import hash_password


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_create_link_assigns_short_code(client):
    _login_admin(client)
    client.post("/admin/check-links", data={"role": "driver", "ttl_hours": "1"},
                follow_redirects=False)
    with Session(engine) as s:
        link = s.exec(select(AccessLink)).first()
        assert link.short_code != ""
        assert 4 <= len(link.short_code) <= 10


def test_admin_page_shows_short_link_and_copy(client):
    _login_admin(client)
    client.post("/admin/check-links", data={"role": "mechanic", "ttl_hours": "2"},
                follow_redirects=False)
    r = client.get("/admin/check-links")
    assert r.status_code == 200
    assert "/c/" in r.text
    assert "คัดลอก" in r.text   # copy button label
