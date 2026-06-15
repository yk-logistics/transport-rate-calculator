from sqlmodel import Session, select
from db_config import engine
from models import AppUser


def test_yk1_admin_seeded_on_boot(client):
    # client fixture booted the app -> lifespan ran -> yk1 created
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
    assert u is not None
    assert u.role == "admin"
    assert u.must_change_pw is True
    assert u.password_hash and u.password_hash != ""
