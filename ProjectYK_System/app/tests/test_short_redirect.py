from datetime import datetime, timedelta
from sqlmodel import Session
from db_config import engine
from models import AccessLink
import services.access_link as al


def _link_with_code(code="Ab3x9Z", role="driver"):
    tok = al.make_token(role, 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, short_code=code, created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
    return tok


def test_short_code_redirects_to_check(client):
    tok = _link_with_code("Ab3x9Z")
    r = client.get("/c/Ab3x9Z", follow_redirects=False)
    assert r.status_code in (302, 303)
    loc = r.headers["location"]
    assert "/check?t=" in loc
    assert tok in loc


def test_unknown_short_code_404(client):
    r = client.get("/c/nope12", follow_redirects=False)
    assert r.status_code == 404
