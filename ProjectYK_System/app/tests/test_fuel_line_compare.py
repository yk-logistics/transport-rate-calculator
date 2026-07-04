# -*- coding: utf-8 -*-
"""F4 (no-OCR): parse ข้อความแจ้งเติมกลุ่มปั๊ม + เทียบ FuelTxn + หน้า /fuel/line-compare."""
import os
import sqlite3
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
from models import AppUser, FuelTxn, LineGroupMap
from services.fuel_line_compare import parse_fill_text

D = date.today() - timedelta(days=2)
OLD = date.today() - timedelta(days=4)


def test_parse_caltex_and_ptt_formats():
    # format จริงจากกลุ่ม Caltex (4ก.ค.)
    o = parse_fill_text("71-8967 นายณัฐวุฒิ\nเติมดีเซล [20L]+B20 [80L]\nแจ้งเติมCaltex ศรีไทย ค่ะ")
    assert o == {"plate": "71-8967", "b7": 20, "b20": 80, "full_tank": False}
    # format จริงจากกลุ่ม ปตท.คลองเจ็ด
    o = parse_fill_text("71-0560 นายยา\nปตท. เติมดีเซล (20ลิตร) ค่ะ\nเติมดีเซลB20 (เต็มถัง) ค่ะ")
    assert o == {"plate": "71-0560", "b7": 20, "b20": 0, "full_tank": True}
    # ไม่ใช่คำสั่งเติม
    assert parse_fill_text("รบกวนสอบถามค่ะ คันนี้เข้าไปรับ BH หรือยังคะ 71-5041") is None
    assert parse_fill_text("เติมดีเซล 20 ลิตร") is None   # ไม่มีทะเบียน


@pytest.fixture()
def client(tmp_path, monkeypatch):
    p = tmp_path / "line_archive.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE line_group (group_id TEXT PRIMARY KEY, name TEXT, discord_channel_id TEXT, joined_at TEXT, active INT);
        CREATE TABLE line_user (user_id TEXT PRIMARY KEY, display_name TEXT, alias TEXT);
        CREATE TABLE line_message (id INTEGER PRIMARY KEY, line_message_id TEXT, group_id TEXT,
            user_id TEXT, msg_type TEXT, text TEXT, media_path TEXT, sent_at TEXT, received_at TEXT, discord_forwarded INT);
    """)
    con.execute("INSERT INTO line_group VALUES ('st1','ปั๊ม Caltex','','2026-06-01',1)")
    msgs = [
        # จับคู่ได้ (มี FuelTxn 20L + 80L วันเดียวกัน)
        (1, f"{OLD} 08:00", "71-8967 นายณัฐวุฒิ เติมดีเซล [20L]+B20 [80L] แจ้งเติมCaltex"),
        (2, f"{OLD} 08:01", "71-8967 นายณัฐวุฒิ เติมดีเซล [20L]+B20 [80L] แจ้งเติมCaltex"),  # โพสต์ซ้ำ → dedupe
        # ไลน์แจ้งแต่ระบบไม่มี (วันเก่ากว่า fuel_max)
        (3, f"{OLD} 10:00", "71-1111 นายเอ เติมB20 [60L] แจ้งเติมCaltex"),
        # ใหม่กว่าข้อมูลน้ำมันในระบบ → รอ import
        (4, f"{D} 09:00", "71-2222 นายบี เติมดีเซล [20L] แจ้งเติมCaltex"),
    ]
    for i, ts, t in msgs:
        con.execute("INSERT INTO line_message VALUES (?,?,'st1','u1','text',?,NULL,?,?,1)",
                    (i, f"m{i}", t, ts, ts))
    con.commit(); con.close()
    monkeypatch.setenv("YK_LINE_DB", str(p))

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(LineGroupMap(group_id="st1", label="ปั๊ม Caltex", kind="station", active=True))
        s.add(FuelTxn(site_code="LCB", txn_date=OLD, plate_no_raw="71-8967",
                      liter=20.0, amount=750.0, fuel_grade="B7"))
        s.add(FuelTxn(site_code="LCB", txn_date=OLD, plate_no_raw="71-8967",
                      liter=82.0, amount=2600.0, fuel_grade="B20"))   # 82 ≈ 80 (±5)
        # ระบบมีแต่ไลน์ไม่แจ้ง
        s.add(FuelTxn(site_code="LCB", txn_date=OLD, plate_no_raw="71-9999",
                      liter=100.0, amount=3200.0, fuel_grade="B20"))
        # แถวน้ำมันวันใหม่กว่า order ทุกตัว → order วัน OLD อยู่ในช่วงข้อมูลครบ
        # (ไม่โดนกันชนขอบ 1 วัน) — ส่วน order วัน D เท่ากับ max → รอ import
        s.add(FuelTxn(site_code="LCB", txn_date=D, plate_no_raw="71-8888",
                      liter=40.0, amount=1300.0, fuel_grade="B20"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_compare_buckets(client):
    r = client.get("/fuel/line-compare?days=10")
    assert r.status_code == 200
    b = r.text
    assert "71-1111" in b            # ไลน์แจ้ง ระบบไม่มี
    assert "71-9999" in b            # ระบบมี ไลน์ไม่แจ้ง
    assert "รอ import" in b and "71-2222" not in b.split("ไลน์แจ้งเติม แต่ไม่พบในระบบ")[1].split("ระบบมี")[0]
    # จับคู่: 71-8967 ต้องอยู่ในกลุ่ม matched (นับ 1 เดียว — dedupe โพสต์ซ้ำ)
    assert "จับคู่ได้ 1 รายการ" in b


def test_per_site_freshness():
    """LCB import ถึงแค่ 15 มิ.ย. แต่ AYU ถึง 25 — แจ้งเติม LCB วัน 20 ต้อง 'รอ import' ไม่ใช่ตกหล่น."""
    from services.fuel_line_compare import compare
    d_lcb_max, d_ayu_max = date(2026, 6, 15), date(2026, 6, 25)
    orders = [
        {"msg_id": 1, "date": date(2026, 6, 20), "plate": "71-9999",
         "b7": 20, "b20": 0, "full_tank": False, "text": "", "sent_at": "", "group_name": ""},
        {"msg_id": 2, "date": date(2026, 6, 20), "plate": "71-1111",
         "b7": 20, "b20": 0, "full_tank": False, "text": "", "sent_at": "", "group_name": ""},
    ]
    data = compare(orders, [],
                   plate_site={"71-9999": "LCB", "71-1111": "AYU"},
                   site_fuel_max={"LCB": d_lcb_max, "AYU": d_ayu_max})
    assert [o["plate"] for o in data["awaiting_import"]] == ["71-9999"]
    assert [o["plate"] for o in data["line_only"]] == ["71-1111"]


def test_no_station_groups_message(client):
    with Session(engine) as s:
        m = s.exec(select(LineGroupMap)).first()
        m.kind = "customer"; s.add(m); s.commit()
    r = client.get("/fuel/line-compare")
    assert "ยังไม่มีกลุ่มปั๊ม" in r.text
