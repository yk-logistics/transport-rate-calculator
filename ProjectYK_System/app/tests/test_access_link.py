import time
from sqlmodel import Session
from db_config import engine
from models import AccessLink
from datetime import datetime, timedelta
import services.access_link as al


def test_make_and_read_token_roundtrip():
    tok = al.make_token("mechanic", ttl_seconds=3600)
    payload = al.read_token(tok, max_age_seconds=3600)
    assert payload is not None
    assert payload["role"] == "mechanic"


def test_read_token_rejects_expired():
    tok = al.make_token("driver", ttl_seconds=3600)
    # max_age 0 -> anything older than 0s is rejected
    time.sleep(1)
    assert al.read_token(tok, max_age_seconds=0) is None


def test_read_token_rejects_tampered():
    tok = al.make_token("driver", ttl_seconds=3600)
    assert al.read_token(tok + "x", max_age_seconds=3600) is None


def test_accesslink_row_persists(client):
    with Session(engine) as s:
        link = AccessLink(
            token="abc.def.ghi", role="driver",
            created_by="yk1",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        s.add(link); s.commit(); s.refresh(link)
        assert link.id is not None
        assert link.revoked is False
        assert link.use_count == 0
