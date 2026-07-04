# -*- coding: utf-8 -*-
"""E1 Driver PWA: เช็คอิน 3 จุด + รูปตู้ 4 ด้าน + ปิดงาน — ผ่าน DriverSession จริง."""
import io
import json
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
from models import DailyJob, DriverSubmission, Employee
from services import driver_auth as drv

FAKE_JPG = b"\xff\xd8\xff" + b"x" * 200  # >100 bytes ผ่านเกณฑ์ len


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        emp = Employee(code="D001", full_name="คนขับ ทดสอบ", home_site_code="LCB",
                       phone="0812345678", pin_hash=drv.hash_pin("123456"))
        s.add(emp); s.commit()
        s.add(DailyJob(work_date=date.today(), site_code="LCB", status_code="KLND",
                       driver_id=emp.id, container_no="TESU1111111",
                       destination="CONTINENTAL", revenue_customer=100))
        s.commit()
    with TestClient(appmod.app) as c:
        r = c.post("/driver/login", data={"phone": "0812345678", "pin": "123456"},
                   follow_redirects=False)
        assert "/driver" in r.headers["location"]
        yield c


def _job_id():
    with Session(engine) as s:
        return s.exec(select(DailyJob)).first().id


def test_home_shows_e1_tiles(client):
    b = client.get("/driver").text
    assert "เช็คอิน" in b and "รูปตู้ 4 ด้าน" in b and "ปิดงาน" in b


def test_checkin_records_point_gps_job(client):
    r = client.post("/driver/checkin", data={
        "point": "pickup", "daily_job_id": str(_job_id()),
        "gps_lat": "13.08", "gps_lng": "100.89", "gps_acc": "12", "note": "รอคิว"},
        files={"photos": ("a.jpg", io.BytesIO(FAKE_JPG), "image/jpeg")},
        follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        sub = s.exec(select(DriverSubmission).where(
            DriverSubmission.kind == "checkin")).first()
        assert sub and sub.daily_job_id == _job_id()
        assert sub.gps_lat == 13.08
        assert json.loads(sub.data_json)["point"] == "pickup"
        assert sub.photo_paths


def test_checkin_rejects_bad_point(client):
    r = client.post("/driver/checkin", data={"point": "มั่ว"})
    assert r.status_code == 400


def test_container_4_sides_vs_incomplete(client):
    files = {f"photo_{s}": (f"{s}.jpg", io.BytesIO(FAKE_JPG), "image/jpeg")
             for s in ("front", "back", "left", "right")}
    client.post("/driver/container", data={
        "daily_job_id": str(_job_id()), "container_no": "TESU1111111"}, files=files)
    with Session(engine) as s:
        sub = s.exec(select(DriverSubmission).where(
            DriverSubmission.kind == "container_photo")).first()
        d = json.loads(sub.data_json)
        assert d["complete_4_sides"] is True and len(d["sides"]) == 4
        assert sub.review_status == "pending"
    # ส่งด้านเดียว = flagged ให้ออฟฟิศเห็น
    client.post("/driver/container", data={"container_no": "X"},
                files={"photo_front": ("f.jpg", io.BytesIO(FAKE_JPG), "image/jpeg")})
    with Session(engine) as s:
        subs = s.exec(select(DriverSubmission).where(
            DriverSubmission.kind == "container_photo")).all()
        assert subs[-1].review_status == "flagged"


def test_container_requires_at_least_one_photo(client):
    assert client.post("/driver/container", data={"container_no": "X"}).status_code == 400


def test_done_records(client):
    client.post("/driver/done", data={
        "daily_job_id": str(_job_id()), "note": "ส่งเสร็จ",
        "gps_lat": "13.1", "gps_lng": "100.9", "gps_acc": "8"})
    with Session(engine) as s:
        sub = s.exec(select(DriverSubmission).where(
            DriverSubmission.kind == "job_done")).first()
        assert sub and sub.daily_job_id == _job_id()
        assert json.loads(sub.data_json)["note"] == "ส่งเสร็จ"


def test_requires_driver_session():
    with TestClient(appmod.app) as anon:
        for path in ("/driver/checkin", "/driver/container", "/driver/done"):
            r = anon.get(path, follow_redirects=False)
            assert r.status_code == 303 and "/driver/login" in r.headers["location"]
