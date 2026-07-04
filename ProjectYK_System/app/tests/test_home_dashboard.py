# -*- coding: utf-8 -*-
"""P5.2 หน้าแรก / = การ์ดงานวันนี้ (โชว์ตามสิทธิ์; ไม่ล็อกอิน = เด้ง /login)."""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, DailyJob


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod._HOME_LINE_CACHE.update({"at": None, "inbox": None, "pod": None})
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        t = date.today()
        s.add(DailyJob(work_date=t, site_code="LCB", status_code="KLND",
                       revenue_customer=4900.0))
        s.add(DailyJob(work_date=t, site_code="LCB", status_code="รถจอด"))
        s.add(DailyJob(work_date=t.replace(day=1), site_code="LCB",
                       status_code="CY", revenue_customer=0.0))  # ราคาว่างเดือนนี้
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_anonymous_redirected_to_login():
    with TestClient(appmod.app) as c:
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 303 and "/login" in r.headers["location"]


def test_home_cards_render(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "งานวันนี้" in r.text
    assert "แถวงานราคาว่าง" in r.text
    assert "LCB" in r.text
    assert "แผนงาน MVP" in r.text        # admin เห็นการ์ดแผน
    assert "เงินหมุน 8 สัปดาห์" in r.text  # admin เห็น finance
