# -*- coding: utf-8 -*-
"""กันบั๊กตระกูล "กดกรองแล้ว 422": ฟอร์ม GET ส่ง select ค่าว่างชนพารามิเตอร์ int.

โอเจอที่ /maint/records 10ก.ค. → audit ทั้งระบบพบอีกหน้าเดียว: /maint/inspections
(หน้าอื่น: /billing, /admin/submissions รับ str อยู่แล้ว; ฟอร์ม POST แกะ form เอง)
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import AppUser, Vehicle
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Vehicle(plate_no="71-8005", status="active"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_inspection_filter_all_empty_is_200(client):
    """URL แบบเดียวกับที่ปุ่ม 'กรอง' ส่งจริงเมื่อไม่เลือกอะไรเลย."""
    r = client.get("/maint/inspections?date_from=&date_to=&vehicle_id=&overall_status=")
    assert r.status_code == 200


def test_inspection_filter_by_vehicle_number_still_works(client):
    with Session(engine) as s:
        vid = s.exec(select(Vehicle)).first().id
    r = client.get(f"/maint/inspections?vehicle_id={vid}")
    assert r.status_code == 200
