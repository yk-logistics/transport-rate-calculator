# -*- coding: utf-8 -*-
"""F5 สรุปเช้ารายกลุ่ม /line/digest — DB จำลอง schema archiver (read-only)."""
import os, sqlite3, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser
from services import line_archive as la


@pytest.fixture()
def line_db(tmp_path, monkeypatch):
    p = tmp_path / "line_archive.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE line_group (group_id TEXT PRIMARY KEY, name TEXT, discord_channel_id TEXT, joined_at TEXT, active INT);
        CREATE TABLE line_user (user_id TEXT PRIMARY KEY, display_name TEXT, alias TEXT);
        CREATE TABLE line_message (id INTEGER PRIMARY KEY, line_message_id TEXT, group_id TEXT,
            user_id TEXT, msg_type TEXT, text TEXT, media_path TEXT, sent_at TEXT, received_at TEXT, discord_forwarded INT);
    """)
    con.execute("INSERT INTO line_group VALUES ('g1','กลุ่มคนขับแหลม','','2026-06-01',1)")
    con.execute("INSERT INTO line_group VALUES ('g2','ลูกค้า KAO','','2026-06-01',1)")
    con.execute("INSERT INTO line_group VALUES ('g3','กลุ่มปิดแล้ว','','2026-06-01',0)")
    con.execute("INSERT INTO line_user VALUES ('u1','สมชาย','ปกรณ์')")
    rows = [
        (1, 'm1', 'g1', 'u1', 'text', 'เช้านี้เข้า 3 ตู้', None, '2026-07-02 07:30', '2026-07-02 07:30', 1),
        (2, 'm2', 'g1', 'u1', 'image', '', 'x.jpg', '2026-07-02 12:00', '2026-07-02 12:00', 1),
        (3, 'm3', 'g1', 'u1', 'text', 'จบงานครับ', None, '2026-07-02 18:45', '2026-07-02 18:45', 1),
        (4, 'm4', 'g2', 'u1', 'text', 'เก่ามาก', None, '2026-06-20 10:00', '2026-06-20 10:00', 1),
    ]
    con.executemany("INSERT INTO line_message VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit(); con.close()
    monkeypatch.setenv("YK_LINE_DB", str(p))
    return p


@pytest.fixture()
def client(line_db):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_daily_digest_counts_and_first_last(line_db):
    d = la.daily_digest("2026-07-02", "2026-07-03")
    assert d["total_msg"] == 3 and d["total_media"] == 1
    g = d["groups"][0]
    assert g["name"] == "กลุ่มคนขับแหลม"
    assert g["first"]["text"].startswith("เช้านี้") and g["first"]["at"] == "07:30"
    assert g["last"]["text"] == "จบงานครับ" and g["last"]["at"] == "18:45"
    # เงียบ >3 วัน: g2 (20/6) ติด, g1 ไม่ติด, g3 ปิดแล้วไม่โผล่
    names = {s["name"] for s in d["silent"]}
    assert names == {"ลูกค้า KAO"}


def test_digest_page_renders(client):
    r = client.get("/line/digest?d=2026-07-02")
    assert r.status_code == 200
    assert "กลุ่มคนขับแหลม" in r.text
    assert "จบงานครับ" in r.text
    assert "ลูกค้า KAO" in r.text          # กล่องกลุ่มเงียบ
