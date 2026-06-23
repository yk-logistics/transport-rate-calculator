"""Slip-reader on/off control: service config endpoint + setting persistence."""
from sqlmodel import Session, select
from db_config import engine
from models import AppUser
from auth import hash_password
import main as appmod

TOKEN = "test-ingest-token"


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1"); u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_control_page_renders_and_toggle_persists(client):
    _login_admin(client)
    r = client.get("/petty/slip-control")
    assert r.status_code == 200 and "ระบบอ่านสลิป" in r.text
    # default OFF
    assert appmod.get_setting(appmod.SLIP_ENABLED_KEY, "0") == "0"
    # toggle ON
    client.post("/petty/slip-control/toggle", data={"enable": "1"})
    assert appmod.get_setting(appmod.SLIP_ENABLED_KEY) == "1"
    # set since-date
    client.post("/petty/slip-control/since", data={"since": "2026-06-01"})
    assert appmod.get_setting(appmod.SLIP_SINCE_KEY) == "2026-06-01"
    # blank since clears it
    client.post("/petty/slip-control/since", data={"since": ""})
    assert appmod.get_setting(appmod.SLIP_SINCE_KEY) == ""
    # run-now flag
    client.post("/petty/slip-control/run-now")
    assert appmod.get_setting(appmod.SLIP_RUNNOW_KEY) == "1"


def test_slip_config_requires_token(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    assert client.get("/api/petty/slip-config").status_code == 401
    assert client.get("/api/petty/slip-config",
                      headers={"X-Service-Token": "wrong"}).status_code == 401


def test_slip_config_default_is_disabled(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    r = client.get("/api/petty/slip-config", headers={"X-Service-Token": TOKEN})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False and body["since"] == "" and body["run_now"] is False


def test_setting_helpers_roundtrip(client):
    # get/set_setting upsert behavior (client fixture gives a fresh db)
    assert appmod.get_setting("x", "def") == "def"
    appmod.set_setting("x", "1")
    assert appmod.get_setting("x") == "1"
    appmod.set_setting("x", "2")
    assert appmod.get_setting("x") == "2"


def test_config_reflects_settings(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    appmod.set_setting(appmod.SLIP_ENABLED_KEY, "1")
    appmod.set_setting(appmod.SLIP_SINCE_KEY, "2026-06-01")
    appmod.set_setting(appmod.SLIP_RUNNOW_KEY, "1")
    r = client.get("/api/petty/slip-config", headers={"X-Service-Token": TOKEN})
    body = r.json()
    assert body["enabled"] is True and body["since"] == "2026-06-01" and body["run_now"] is True


def test_report_acks_run_now(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    appmod.set_setting(appmod.SLIP_RUNNOW_KEY, "1")
    r = client.post("/api/petty/slip-config/report",
                    json={"result": "pushed 3 of 5", "ack_run_now": True},
                    headers={"X-Service-Token": TOKEN})
    assert r.status_code == 200
    assert appmod.get_setting(appmod.SLIP_RUNNOW_KEY) == "0"          # acked
    assert appmod.get_setting(appmod.SLIP_LASTRESULT_KEY) == "pushed 3 of 5"
