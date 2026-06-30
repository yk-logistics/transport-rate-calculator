import pytest
from sqlmodel import Session
from db_config import engine
from models import AppUser
from auth import hash_password


def _make_user(username, role):
    from sqlmodel import select
    with Session(engine) as s:
        if s.exec(select(AppUser).where(AppUser.username == username)).first():
            return
        s.add(AppUser(username=username, password_hash=hash_password("pw123456"),
                      display_name=username, role=role, status="active",
                      must_change_pw=False))
        s.commit()


@pytest.fixture()
def office_client(client):
    _make_user("office1", "office")
    client.post("/login", data={"username": "office1", "password": "pw123456"})
    return client


def test_unauthenticated_redirects_to_login(client):
    r = client.get("/daily", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")


def test_unauthenticated_api_returns_401_json(client):
    # /api/* must answer 401 JSON (not redirect to login HTML) so AJAX saves
    # surface a clear "session expired" message instead of failing silently.
    r = client.post("/api/daily/grid-save", json={"rows": [{"id": 1, "remark": "x"}]},
                    follow_redirects=False)
    assert r.status_code == 401
    assert r.headers.get("content-type", "").startswith("application/json")
    assert r.json().get("error") == "auth_required"


def test_office_denied_payroll(office_client):
    r = office_client.get("/payroll", follow_redirects=False)
    assert r.status_code == 403


def test_office_denied_finance(office_client):
    r = office_client.get("/finance", follow_redirects=False)
    assert r.status_code == 403


def test_office_allowed_daily(office_client):
    r = office_client.get("/daily", follow_redirects=False)
    assert r.status_code == 200


def test_office_cannot_post_to_master(office_client):
    # /employees is view-only for office; a write must be blocked
    r = office_client.post("/employees/new", data={}, follow_redirects=False)
    assert r.status_code == 403
