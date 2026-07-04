# -*- coding: utf-8 -*-
"""D1 เติมราคาเร็ว: เสนอเรทจาก RateCard เฉพาะแถวราคาว่าง — คนกดรับ, ไม่ทับราคา, audit."""
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
from models import AppUser, DailyJob, DailyJobAudit, RateCard

D = date(2026, 7, 2)


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(RateCard(kind="revenue_customer", site_code="LCB", destination="CNC2",
                       rate_value=4900.0, source="manual", priority=1, status="active"))
        # แถวราคาว่าง match เรท
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       destination="CNC2", revenue_customer=0.0))
        # แถวราคาว่าง ไม่ match (ปลายทางอื่น)
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       destination="ไม่มีเรท", revenue_customer=0.0))
        # แถวมีราคาแล้ว — ต้องไม่โผล่
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="CY",
                       destination="CNC2", revenue_customer=5000.0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _job(dest):
    with Session(engine) as s:
        return s.exec(select(DailyJob).where(DailyJob.destination == dest)).first()


def test_page_lists_only_empty_price_rows(client):
    r = client.get("/billing/fill-prices?site=LCB&month=2026-07")
    assert r.status_code == 200
    assert "4,900" in r.text                 # เรทเสนอของแถว match
    assert "ไม่มีเรท" in r.text               # แถวไม่ match ก็โผล่ (ลิงก์ไป grid)
    assert "5,000" not in r.text             # แถวมีราคาแล้วไม่โผล่


def test_apply_writes_price_and_audit_once(client):
    jid = _job("CNC2").id
    r = client.post("/api/billing/fill-price", json={"job_id": jid})
    assert r.status_code == 200 and r.json()["value"] == 4900.0
    with Session(engine) as s:
        j = s.get(DailyJob, jid)
        assert j.revenue_customer == 4900.0
        a = s.exec(select(DailyJobAudit).where(
            DailyJobAudit.daily_job_id == jid)).all()
        assert len(a) == 1 and a[0].action == "rate_apply"
        card = s.exec(select(RateCard)).first()
        assert card.use_count == 1
    # กดซ้ำ = 409 ไม่ทับ
    assert client.post("/api/billing/fill-price", json={"job_id": jid}).status_code == 409


def test_apply_no_match_409(client):
    jid = _job("ไม่มีเรท").id
    r = client.post("/api/billing/fill-price", json={"job_id": jid})
    assert r.status_code == 409
    with Session(engine) as s:
        assert s.get(DailyJob, jid).revenue_customer == 0.0
