"""ปุ่ม ➕ บนหน้า /line — ส่งข้อความ+รูปชุดเดียวกันเข้า /todo (เฟส 1 LINE→todo).

เคสจริง 4ก.ค.: สันติพงษ์ส่งรูปยาง 6 ใบ 7:09 แล้วพิมพ์ข้อความแจ้งซ่อม 7:14
— กดปุ่มที่ข้อความต้องได้รูปทั้งชุดตามมา โดยไม่ลากรูปนอกช่วงเวลา/ของคนอื่น.
"""
import os
import sqlite3
import tempfile
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
from models import AppUser, TodoItem

FAKE_JPG = b"\xff\xd8\xff" + b"x" * 200


def _make_archive(tmp_path: Path) -> Path:
    """คลังแชทปลอมโครงเดียวกับ archiver: รูป 2 ใบ (7:09) + ข้อความ (7:14) คนเดียวกัน
    + รูปนอกหน้าต่างเวลา + รูปของคนอื่นในนาทีเดียวกัน."""
    db = tmp_path / "line_archive.db"
    media = tmp_path / "line_media"
    media.mkdir()
    for f in ("a.jpg", "b.jpg", "far.jpg", "other.jpg"):
        (media / f).write_bytes(FAKE_JPG)
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE line_group(group_id TEXT PRIMARY KEY, name TEXT,
            discord_channel_id TEXT, joined_at TEXT, active INTEGER);
        CREATE TABLE line_user(user_id TEXT PRIMARY KEY, display_name TEXT, alias TEXT);
        CREATE TABLE line_message(id INTEGER PRIMARY KEY, line_message_id TEXT, group_id TEXT,
            user_id TEXT, msg_type TEXT, text TEXT, media_path TEXT, sent_at TEXT,
            received_at TEXT, discord_forwarded INTEGER);
    """)
    con.execute("INSERT INTO line_group VALUES ('g1','Y.K. หัวลาก LCB.',NULL,NULL,1)")
    con.execute("INSERT INTO line_user VALUES ('u1','YK LCB 72-1219 สันติพงษ์',NULL)")
    con.execute("INSERT INTO line_user VALUES ('u2','คนอื่น',NULL)")
    rows = [
        (1, 'm1', 'g1', 'u1', 'image', None, 'a.jpg', '2026-07-04 07:09:00'),
        (2, 'm2', 'g1', 'u1', 'image', None, 'b.jpg', '2026-07-04 07:09:30'),
        (3, 'm3', 'g1', 'u1', 'text', 'ยางหลังหมดและแตก 2 เส้น ขอเปลี่ยนครับ', None,
         '2026-07-04 07:14:00'),
        (4, 'm4', 'g1', 'u1', 'image', None, 'far.jpg', '2026-07-04 05:00:00'),
        (5, 'm5', 'g1', 'u2', 'image', None, 'other.jpg', '2026-07-04 07:10:00'),
    ]
    con.executemany("INSERT INTO line_message VALUES (?,?,?,?,?,?,?,?,NULL,0)", rows)
    con.commit()
    con.close()
    return db


@pytest.fixture()
def client(tmp_path):
    os.environ["YK_LINE_DB"] = str(_make_archive(tmp_path))
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c
    os.environ.pop("YK_LINE_DB", None)


def test_text_message_pulls_sibling_images(client):
    r = client.post("/line/3/to-todo", data={"q": "ยาง", "group": "g1", "page": "0"},
                    follow_redirects=False)
    assert r.status_code == 303 and "saved=" in r.headers["location"]
    with Session(engine) as s:
        t = s.exec(select(TodoItem)).first()
    assert "ยางหลังหมด" in t.text
    assert "Y.K. หัวลาก LCB." in t.text and "สันติพงษ์" in t.text
    assert t.category == "ไลน์"
    assert t.username == "yk1"
    names = t.media_json.split(",")
    assert len(names) == 2  # a+b เท่านั้น — far (นอก 20 นาที) / other (คนอื่น) ไม่มา
    r = client.get(f"/todo/media/{t.id}/{names[0]}")
    assert r.status_code == 200 and r.content == FAKE_JPG


def test_click_on_image_gets_same_bundle(client):
    client.post("/line/1/to-todo", data={})
    with Session(engine) as s:
        t = s.exec(select(TodoItem)).first()
    assert len(t.media_json.split(",")) == 2
    assert "📱 ไลน์" in t.text  # ไม่มีข้อความ → เหลือ header บอกที่มา


def test_saved_todo_shows_on_todo_page(client):
    client.post("/line/3/to-todo", data={})
    b = client.get("/todo", follow_redirects=True).text
    assert "ยางหลังหมด" in b


def test_missing_message_404(client):
    r = client.post("/line/999/to-todo", data={})
    assert r.status_code == 404
