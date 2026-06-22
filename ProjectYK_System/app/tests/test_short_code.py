from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink


def test_accesslink_short_code_persists_and_queryable(client):
    with Session(engine) as s:
        s.add(AccessLink(token="tok.aaa.bbb", role="driver", short_code="Ab3x9Z",
                         created_by="t", expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
        found = s.exec(select(AccessLink).where(AccessLink.short_code == "Ab3x9Z")).first()
        assert found is not None
        assert found.token == "tok.aaa.bbb"
        assert found.role == "driver"
