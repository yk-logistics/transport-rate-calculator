# -*- coding: utf-8 -*-
"""E2 รายงานน้ำมันผิดปกติ: กติกา R1 เติมถี่ / R2 เกินถัง / R3 วันไม่มีงาน — read-only."""
import os
import tempfile
from datetime import date, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, DailyJob, FuelTxn, Vehicle
from services import fuel_anomaly as fa

D = date(2026, 6, 10)


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        v1 = Vehicle(plate_no="71-1111", truck_type="head", tank_liters=0)      # default 500
        v2 = Vehicle(plate_no="71-2222", truck_type="head", tank_liters=300)    # กรอกเอง
        s.add(v1); s.add(v2); s.commit()
        # v1: เติม 2 ครั้งวันเดียว (R1) + มีงานเดลี่วันนั้น (ไม่ติด R3)
        s.add(FuelTxn(txn_date=D, site_code="LCB", vehicle_id=v1.id, liter=200, amount=6000))
        s.add(FuelTxn(txn_date=D, site_code="LCB", vehicle_id=v1.id, liter=150, amount=4500))
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       plate_no_raw="71-1111", revenue_customer=100))
        # v2: เติมครั้งเดียว 350 > ถัง 300 (R2) + ไม่มีงานวันนั้น (R3)
        s.add(FuelTxn(txn_date=D + timedelta(days=1), site_code="LCB",
                      vehicle_id=v2.id, liter=350, amount=10500))
        # เติมปกติ — ไม่ธง
        s.add(FuelTxn(txn_date=D + timedelta(days=2), site_code="LCB",
                      vehicle_id=v1.id, liter=180, amount=5400))
        s.add(DailyJob(work_date=D + timedelta(days=2), site_code="AYU",
                       status_code="KAO", plate_no_raw="71-1111", revenue_customer=100))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_rules(client):
    with Session(engine) as s:
        data = fa.scan(s, D - timedelta(days=1), D + timedelta(days=3))
    assert data["n_fills"] == 4
    by_plate = {}
    for r in data["rows"]:
        by_plate.setdefault(r["plate"], []).append(r)
    # v1 วันแรก: 2 แถวติด R1 แต่ไม่ติด R3 (มีงานวันนั้น)
    v1_rows = [r for r in by_plate["71-1111"] if r["date"] == D]
    assert len(v1_rows) == 2
    assert all(any(f["code"] == "R1" for f in r["flags"]) for r in v1_rows)
    assert all(not any(f["code"] == "R3" for f in r["flags"]) for r in v1_rows)
    # v2: R2 (350>300 ถังที่กรอก) + R3 — เรียงแดงขึ้นก่อน
    v2_rows = by_plate["71-2222"]
    assert len(v2_rows) == 1
    codes = {f["code"] for f in v2_rows[0]["flags"]}
    assert codes == {"R2", "R3"}
    assert data["rows"][0]["plate"] == "71-2222"   # rose first
    # เติมปกติวันที่มีงาน (ข้ามไซท์ AYU ก็นับว่ามีงาน) — ไม่โผล่
    assert not [r for r in by_plate["71-1111"] if r["date"] == D + timedelta(days=2)]


def test_page_renders(client):
    r = client.get(f"/fuel/anomaly?d_from={D.isoformat()}&d_to={(D + timedelta(days=3)).isoformat()}")
    assert r.status_code == 200
    assert "ลิตรเกินถัง" in r.text and "71-2222" in r.text


def test_vehicle_form_saves_tank(client):
    with Session(engine) as s:
        vid = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-1111")).first().id
    client.post(f"/vehicles/{vid}/edit", data={
        "plate_no": "71-1111", "vehicle_kind": "truck", "truck_type": "head",
        "home_site_code": "LCB", "status": "active", "tank_liters": "450"})
    with Session(engine) as s:
        assert s.get(Vehicle, vid).tank_liters == 450.0
