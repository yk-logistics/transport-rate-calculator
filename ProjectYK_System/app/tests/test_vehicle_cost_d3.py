# -*- coding: utf-8 -*-
"""D3 ต้นทุน/กำไรต่อคัน: ค่าเที่ยวคนขับ + งวดรถ + match ทะเบียนข้อความ + เรียงแย่สุดก่อน."""
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
from models import AppUser, DailyJob, DebtAccount, FuelTxn, Vehicle
from services import finance as fin


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _seed(s):
    v1 = Vehicle(plate_no="71-8967", site_code="LCB", truck_type="head")
    v2 = Vehicle(plate_no="71-6803", site_code="LCB", truck_type="head")
    s.add(v1); s.add(v2); s.commit()
    # คันแรก: ผูก id ตรง + กำไรดี
    s.add(DailyJob(work_date=date(2026, 6, 5), site_code="LCB", status_code="KLND",
                   head_vehicle_id=v1.id, plate_no_raw="71-8967",
                   revenue_customer=10000.0, trip_fee_driver=600.0))
    # คันสอง: ไม่มี head_vehicle_id — ต้อง match จากทะเบียนข้อความ (gotcha B4)
    s.add(DailyJob(work_date=date(2026, 6, 6), site_code="LCB", status_code="CY",
                   head_vehicle_id=None, plate_no_raw="71-6803",
                   revenue_customer=5000.0, trip_fee_driver=3000.0))
    s.add(FuelTxn(txn_date=date(2026, 6, 6), vehicle_id=v2.id, amount=2500.0, liter=70.0))
    # งวดรถผูกทะเบียนคันสอง → ขาดทุน
    s.add(DebtAccount(name="ไฟแนนซ์ 71-6803", kind="finance", plate="71-6803",
                      due_day=25, monthly_payment=18000.0, active=True))
    s.commit()
    return v1.id, v2.id


def test_net_margin_and_plate_text_match(client):
    with Session(engine) as s:
        vid1, vid2 = _seed(s)
        rows = fin.cost_per_vehicle(s, 2026, 6)
    by = {r["vehicle_id"]: r for r in rows}
    assert by[vid2]["trips"] == 1          # match ด้วยทะเบียนข้อความ
    assert by[vid2]["cost_driver"] == 3000.0
    assert by[vid2]["cost_install"] == 18000.0
    assert by[vid2]["net_margin"] == 5000.0 - 2500.0 - 3000.0 - 18000.0
    assert by[vid1]["net_margin"] == 10000.0 - 600.0
    # เรียงแย่สุดขึ้นก่อน
    assert rows[0]["vehicle_id"] == vid2
    # gross_margin ความหมายเดิม (ไม่หักค่าเที่ยว/งวด) — dashboard ใช้อยู่
    assert by[vid1]["gross_margin"] == 10000.0


def test_vehicles_page_renders_with_spark(client):
    with Session(engine) as s:
        _seed(s)
    r = client.get("/finance/vehicles?month=2026-06")
    assert r.status_code == 200
    assert "กำไรสุทธิ/คัน" in r.text
    assert "งวดรถ" in r.text
    assert "<svg" in r.text                 # sparkline 6 เดือน
    assert "71-6803" in r.text
