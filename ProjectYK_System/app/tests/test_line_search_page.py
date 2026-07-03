"""หน้า /line (F1) — ค้นคลังแชท read-only; เทสต์ด้วย DB จำลอง schema เดียวกับ archiver."""
import os, sqlite3, tempfile
from pathlib import Path

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
    con.execute("INSERT INTO line_user VALUES ('u1','สมชาย','ปกรณ์')")
    media = tmp_path / "line_media"; media.mkdir()
    (media / "img1.jpg").write_bytes(b"fakejpg")
    con.execute("INSERT INTO line_message VALUES (1,'m1','g1','u1','text','เติมน้ำมัน 71-8967 เต็มถัง',NULL,'2026-07-01 08:00','2026-07-01 08:00',1)")
    con.execute(f"INSERT INTO line_message VALUES (2,'m2','g1','u1','image','','{(media / 'img1.jpg').as_posix()}','2026-07-02 09:00','2026-07-02 09:00',1)")
    con.execute("INSERT INTO line_message VALUES (3,'m3','g2','u1','text','พรุ่งนี้เข้าโหลด 2 ตู้',NULL,'2026-06-20 10:00','2026-06-20 10:00',1)")
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


def test_groups_sorted_by_activity(client):
    b = client.get("/line", follow_redirects=True).text
    assert "กลุ่มคนขับแหลม" in b and "ลูกค้า KAO" in b
    # กลุ่มคนขับ (ล่าสุด 2/7) ต้องมาก่อนกลุ่ม KAO (20/6)
    assert b.index("กลุ่มคนขับแหลม") < b.index("ลูกค้า KAO")


def test_search_finds_across_groups(client):
    b = client.get("/line?q=71-8967", follow_redirects=True).text
    assert "เติมน้ำมัน 71-8967" in b
    b = client.get("/line?q=ไม่มีคำนี้แน่", follow_redirects=True).text
    assert "ไม่พบข้อความ" in b


def test_media_served_and_scoped(client):
    r = client.get("/line/media/2", follow_redirects=True)
    assert r.status_code == 200 and r.content == b"fakejpg"
    assert client.get("/line/media/1", follow_redirects=True).status_code == 404  # ไม่มีไฟล์
    assert client.get("/line/media/999", follow_redirects=True).status_code == 404


def test_line_permissions():
    import permissions
    assert permissions.check("admin", "/line", "GET") == "edit"
    assert permissions.check("office", "/line", "GET") == "view"
    assert permissions.check("viewer", "/line", "GET") == "deny"
