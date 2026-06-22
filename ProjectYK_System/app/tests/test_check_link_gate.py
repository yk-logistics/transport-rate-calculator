from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, AppUser
from auth import hash_password
import services.access_link as al


def _make_link(role="driver", hours=1):
    tok = al.make_token(role, ttl_seconds=hours * 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, created_by="test",
                         expires_at=datetime.utcnow() + timedelta(hours=hours)))
        s.commit()
    return tok


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_check_landing_rejects_missing_token(client):
    r = client.get("/check", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_check_landing_rejects_unknown_token(client):
    r = client.get("/check?t=not-a-real-token", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_check_landing_accepts_valid_token(client):
    tok = _make_link("mechanic")
    r = client.get(f"/check?t={tok}", follow_redirects=False)
    assert r.status_code == 200
    assert "ช่าง" in r.text  # role shown on landing


def test_revoked_link_rejected(client):
    tok = _make_link("driver")
    with Session(engine) as s:
        link = s.exec(select(AccessLink)).first()
        link.revoked = True
        s.add(link); s.commit()
    r = client.get(f"/check?t={tok}", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_admin_can_create_link(client):
    _login_admin(client)
    r = client.post("/admin/check-links", data={"role": "driver", "ttl_hours": "1"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        rows = s.exec(select(AccessLink)).all()
        assert len(rows) == 1
        assert rows[0].role == "driver"
