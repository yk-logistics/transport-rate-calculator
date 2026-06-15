import pytest
from sqlmodel import Session
from db_config import engine
from models import AppUser
from auth import hash_password


@pytest.fixture()
def office_client(client):
    with Session(engine) as s:
        s.add(AppUser(username="offm", password_hash=hash_password("pw123456"),
                      display_name="offm", role="office", status="active",
                      must_change_pw=False))
        s.commit()
    client.post("/login", data={"username": "offm", "password": "pw123456"})
    return client


def test_office_nav_hides_payroll_and_finance(office_client):
    r = office_client.get("/daily")
    assert r.status_code == 200
    assert 'href="/payroll"' not in r.text
    assert 'href="/finance"' not in r.text
