# -*- coding: utf-8 -*-
"""F2 กล่องงานเข้า /line/inbox: pattern scorer + mark กลุ่มลูกค้า + รับ/ปัด candidate."""
import os, sqlite3, tempfile
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
from models import AppUser, LineGroupMap, LineJobSeen
from services import line_inbox as li


def _iso(days_ago=0, hm="08:00"):
    return f"{(date.today() - timedelta(days=days_ago)).isoformat()} {hm}"


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
    con.execute("INSERT INTO line_group VALUES ('g1','ลูกค้า KLND','','2026-06-01',1)")
    con.execute("INSERT INTO line_group VALUES ('g2','กลุ่มภายใน','','2026-06-01',1)")
    con.execute("INSERT INTO line_user VALUES ('u1','ประสาน','KLND')")
    msgs = [
        (1, 'g1', 'พรุ่งนี้เข้าโหลด CNC2 เวลา 08:00 ตู้ TEXU1234567 กับ FFAU7388082'),
        (2, 'g1', 'ขอบคุณครับ 🙏'),
        (3, 'g1', 'ส่งตู้วันที่ 6/7 ครับ 2 คัน'),
        (4, 'g2', 'พรุ่งนี้เข้าโหลด TEXU9999999'),  # กลุ่มไม่ใช่ลูกค้า — ไม่โผล่
    ]
    for i, gid, text in msgs:
        con.execute("INSERT INTO line_message VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (i, f"m{i}", gid, 'u1', 'text', text, None, _iso(1), _iso(1), 1))
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
        u.must_change_pw = False; s.add(u)
        s.add(LineGroupMap(group_id="g1", label="ลูกค้า KLND", kind="customer",
                           customer_name="KLND", site_code="LCB", active=True))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_score_message_patterns():
    assert li.score_message("พรุ่งนี้เข้าโหลด 08:00 TEXU1234567")["containers"] == ["TEXU1234567"]
    assert li.score_message("ส่งตู้วันที่ 6/7 ครับ") is not None      # keyword + วันที่
    assert li.score_message("ขอบคุณครับ") is None                     # คุยเฉยๆ
    assert li.score_message("เข้า 3 ตู้") is None                     # weak kw ไม่มีวันเวลา
    assert li.score_message("texu 1234567 นะ".upper()) is not None    # ตู้มีช่องว่าง


def test_guess_work_date():
    assert li._guess_work_date("พรุ่งนี้เข้าโหลด", "2026-07-03 20:00") == "2026-07-04"
    assert li._guess_work_date("ส่งตู้วันที่ 6/7", "2026-07-03 20:00") == "2026-07-06"
    assert li._guess_work_date("บิลเลขที่ 12/9999", "2026-07-03 20:00") == ""
    assert li._guess_work_date("ไม่มีวัน", "2026-07-03 20:00") == ""


def test_inbox_lists_only_customer_groups(client):
    r = client.get("/line/inbox")
    assert r.status_code == 200
    assert "TEXU1234567" in r.text          # จากกลุ่มลูกค้า g1
    assert "TEXU9999999" not in r.text      # กลุ่มภายใน g2 ไม่สแกน
    assert "ขอบคุณครับ" not in r.text        # ไม่ใช่ candidate


def test_dismiss_hides_message(client):
    client.post("/line/inbox/mark", data={"msg_id": 1, "action": "dismiss"})
    assert "TEXU1234567" not in client.get("/line/inbox").text
    with Session(engine) as s:
        seen = s.exec(select(LineJobSeen)).all()
        assert len(seen) == 1 and seen[0].status == "dismissed"


def test_accept_redirects_to_planner_prefilled(client):
    r = client.post("/line/inbox/mark",
                    data={"msg_id": 3, "action": "accept", "site": "LCB",
                          "work_date": "2026-07-06"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/dispatch/planner/new?site=LCB&plan_date=2026-07-06"
    with Session(engine) as s:
        seen = s.exec(select(LineJobSeen).where(
            LineJobSeen.line_message_pk == 3)).first()
        assert seen and seen.status == "accepted" and seen.by_user == "yk1"


def test_group_map_upsert(client):
    client.post("/line/inbox/map", data={
        "group_id": "g2", "label": "กลุ่มภายใน", "kind": "internal"})
    with Session(engine) as s:
        m = s.exec(select(LineGroupMap).where(LineGroupMap.group_id == "g2")).first()
        assert m and m.kind == "internal"
