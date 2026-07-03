# -*- coding: utf-8 -*-
"""P3 เมนูคลิกขวา: /api/ctxmenu/{type} — registry ฝั่ง server + กรองสิทธิ์ต่อ item."""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from auth import hash_password
from models import AppUser


@pytest.fixture()
def clients():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        admin = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        admin.must_change_pw = False
        s.add(admin)
        s.add(AppUser(username="off1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.commit()
    with TestClient(appmod.app) as c_admin, TestClient(appmod.app) as c_off:
        c_admin.post("/login", data={"username": "yk1", "password": "changeme1"})
        c_off.post("/login", data={"username": "off1", "password": "pw12345678"})
        yield c_admin, c_off


def _labels(resp):
    return [i["label"] for i in resp.json()["items"]]


def test_admin_sees_all_daily_items(clients):
    c_admin, _ = clients
    r = c_admin.get("/api/ctxmenu/daily-cell")
    assert r.status_code == 200
    labels = _labels(r)
    assert any("ประวัติ" in x for x in labels)
    assert any("ใบเสนอราคา" in x for x in labels)   # perm /quote — admin เท่านั้น
    # perm key ห้ามหลุดไป client
    assert all("perm" not in i for i in r.json()["items"])


def test_office_items_filtered_by_permission(clients):
    _, c_off = clients
    labels = _labels(c_off.get("/api/ctxmenu/daily-cell"))
    assert any("ประวัติ" in x for x in labels)           # ไม่มี perm = เห็น
    assert not any("ใบเสนอราคา" in x for x in labels)    # /quote: office = deny
    assert any("แชทไลน์" in x for x in labels)           # /line: office = view


def test_unknown_type_404(clients):
    c_admin, _ = clients
    assert c_admin.get("/api/ctxmenu/no-such-type").status_code == 404


def test_all_registry_types_resolve(clients):
    c_admin, _ = clients
    for t in appmod.CTX_MENUS:
        r = c_admin.get(f"/api/ctxmenu/{t}")
        assert r.status_code == 200 and r.json()["items"], t


def test_no_money_actions_in_menus():
    """กติกา P3: เมนูมีแค่ copy/link/call — ไม่มี kind ที่ยิง POST/แก้เงินตรง."""
    for t, items in appmod.CTX_MENUS.items():
        for it in items:
            assert it["kind"] in ("copy", "link", "call"), (t, it)
