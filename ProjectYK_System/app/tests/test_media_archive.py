# -*- coding: utf-8 -*-
"""G2: ย้ายรูปเก่าลงแผ่น External — copy → hash → ลบ → จด MediaArchive + ป้ายบน /line."""
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
from models import AppUser, MediaArchive

OLD = "2024-01-05"          # เก่ากว่า 2 ปี = ครบกำหนดย้าย
RECENT = (date.today() - timedelta(days=3)).isoformat()
N_OLD = 100


@pytest.fixture()
def world(tmp_path, monkeypatch):
    """archive db: รูปเก่า 100 + รูปใหม่ 2 + แผ่นปลอม (dir) ผ่าน YK_EXT_TEST_TARGET."""
    p = tmp_path / "line_archive.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE line_group (group_id TEXT PRIMARY KEY, name TEXT, discord_channel_id TEXT, joined_at TEXT, active INT);
        CREATE TABLE line_user (user_id TEXT PRIMARY KEY, display_name TEXT, alias TEXT);
        CREATE TABLE line_message (id INTEGER PRIMARY KEY, line_message_id TEXT, group_id TEXT,
            user_id TEXT, msg_type TEXT, text TEXT, media_path TEXT, sent_at TEXT, received_at TEXT, discord_forwarded INT);
    """)
    con.execute("INSERT INTO line_group VALUES ('g1','ลูกค้า','','2024-01-01',1)")
    media = tmp_path / "line_media"; media.mkdir()
    for i in range(1, N_OLD + 1):
        f = media / f"old_{i}.jpg"
        f.write_bytes(b"OLD" + bytes(str(i), "ascii") * 20)
        con.execute("INSERT INTO line_message VALUES (?,?,'g1','u1','image','',?,?,?,1)",
                    (i, f"m{i}", str(f), f"{OLD} 10:00", f"{OLD} 10:00"))
    for i in (900, 901):
        f = media / f"new_{i}.jpg"
        f.write_bytes(b"NEW" * 30)
        con.execute("INSERT INTO line_message VALUES (?,?,'g1','u1','image','',?,?,?,1)",
                    (i, f"m{i}", str(f), f"{RECENT} 09:00", f"{RECENT} 09:00"))
    con.commit(); con.close()
    monkeypatch.setenv("YK_LINE_DB", str(p))

    drive = tmp_path / "extdrive"; drive.mkdir()
    monkeypatch.setenv("YK_EXT_TEST_TARGET", str(drive))
    return {"media": media, "drive": drive, "tmp": tmp_path}


@pytest.fixture()
def client(world):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _run_move(world, mode="due"):
    appmod._MEDIA_ARCH.update({"running": True, "ok": None, "log": "", "ts": None})
    appmod._media_archive_worker(str(world["drive"]), mode, "yk1")
    return appmod._MEDIA_ARCH


def test_move_due_hash_verified_then_delete(client, world):
    st = _run_move(world)
    assert st["ok"] is True, st["log"]
    with Session(engine) as s:
        rows = s.exec(select(MediaArchive)).all()
    assert len(rows) == N_OLD
    assert all(r.disk_label == "EXT-01" and len(r.sha256) == 64 for r in rows)
    # ต้นทางรูปเก่าหาย / รูปใหม่ยังอยู่ / ปลายทางครบ
    assert not list(world["media"].glob("old_*.jpg"))
    assert len(list(world["media"].glob("new_*.jpg"))) == 2
    dest = world["drive"] / "YK_MEDIA" / "2024" / "01"
    assert len(list(dest.glob("*.jpg"))) == N_OLD
    assert (world["drive"] / "YK_ARCHIVE.txt").read_text(encoding="utf-8").find("EXT-01") > 0
    # ย้ายซ้ำ = ไม่มีอะไรให้ย้าย (idempotent)
    st = _run_move(world)
    assert st["ok"] is True and "0 ไฟล์" in st["log"]


def test_serve_from_disk_and_placeholder_when_unplugged(client, world):
    _run_move(world)
    r = client.get("/line/media/1")
    assert r.status_code == 200 and r.content.startswith(b"OLD")
    # ดึงแผ่นออก (ย้าย dir หนี) → ป้าย SVG ไม่พัง
    unplugged = world["tmp"] / "gone"
    world["drive"].rename(unplugged)
    r = client.get("/line/media/1")
    assert r.status_code == 200
    assert "image/svg" in r.headers["content-type"] and "EXT-01" in r.text
    unplugged.rename(world["drive"])  # เสียบกลับ → เปิดได้เหมือนเดิม
    assert client.get("/line/media/1").content.startswith(b"OLD")


def test_oldest_month_mode_moves_only_that_month(client, world):
    st = _run_move(world, mode="oldest-month")
    assert st["ok"] is True and "2024-01" in st["log"]
    with Session(engine) as s:
        assert len(s.exec(select(MediaArchive)).all()) == N_OLD
    assert len(list(world["media"].glob("new_*.jpg"))) == 2  # เดือนล่าสุดไม่ถูกแตะ


def test_health_page_shows_card(client, world):
    r = client.get("/admin/server-health")
    assert r.status_code == 200
    assert "ย้ายรูปเก่าลงแผ่น External (G2)" in r.text
    assert "ครบกำหนดแล้ว" in r.text          # มีไฟล์เก่า 100 ไฟล์ครบกำหนด
