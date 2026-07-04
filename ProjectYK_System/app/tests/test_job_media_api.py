# -*- coding: utf-8 -*-
"""คลิกขวา "ดูรูปงานนี้": /api/daily/{id}/media รวมรูปไลน์ (JobMedia) + มือถือคนขับ."""
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
from models import AppUser, DailyJob, DriverSubmission, JobMedia


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(DailyJob(work_date=date(2026, 7, 3), site_code="LCB",
                       status_code="KLND", revenue_customer=100))
        s.commit()
        jid = s.exec(select(DailyJob)).first().id
        s.add(JobMedia(line_message_pk=42, daily_job_id=jid, status="linked", by_user="yk1"))
        s.add(JobMedia(line_message_pk=43, daily_job_id=jid, status="skipped"))  # ข้าม — ไม่โผล่
        s.add(DriverSubmission(employee_id=None, kind="container_photo", daily_job_id=jid,
                               photo_paths="d/1.jpg,d/2.jpg"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_media_api_merges_sources(client):
    with Session(engine) as s:
        jid = s.exec(select(DailyJob)).first().id
    j = client.get(f"/api/daily/{jid}/media").json()
    srcs = [i["src"] for i in j["items"]]
    assert "/line/media/42" in srcs                 # จากไลน์ (linked)
    assert "/line/media/43" not in srcs             # skipped ไม่โผล่
    assert "/uploads/d/1.jpg" in srcs and "/uploads/d/2.jpg" in srcs
    kinds = {i["kind"] for i in j["items"]}
    assert "ไลน์" in kinds and "รูปตู้ 4 ด้าน" in kinds


def test_media_api_empty(client):
    assert client.get("/api/daily/999999/media").json()["items"] == []
