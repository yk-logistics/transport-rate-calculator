from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AppUser, AccessLink
from auth import hash_password
import services.access_link as al


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def _make_link(code="Rv0001"):
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        link = AccessLink(token=tok, role="driver", short_code=code, created_by="t",
                          expires_at=datetime.utcnow() + timedelta(hours=1))
        s.add(link); s.commit(); s.refresh(link)
        return link.id, tok


def test_admin_can_revoke_link(client):
    _login_admin(client)
    lid, _tok = _make_link()
    r = client.post(f"/admin/check-links/{lid}/revoke", follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        link = s.get(AccessLink, lid)
        assert link.revoked is True


def test_revoked_link_no_longer_opens(client):
    _login_admin(client)
    lid, tok = _make_link("Rv0002")
    client.post(f"/admin/check-links/{lid}/revoke", follow_redirects=False)
    # short URL still resolves the row, but /check rejects a revoked link
    r = client.get(f"/check?t={tok}", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_revoke_button_in_admin_page(client):
    _login_admin(client)
    _make_link("Rv0003")
    r = client.get("/admin/check-links")
    assert r.status_code == 200
    assert "/revoke" in r.text
    assert "ปิดใช้งาน" in r.text
