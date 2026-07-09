# -*- coding: utf-8 -*-
"""เฟส 4 LINE→todo: สแกนไลน์ → กล่องรอคัด (TodoSuggest) — AI เสนอ โอคัด.

กติกา: AI สร้างได้แค่แถว pending; TodoItem จริงเกิดตอนโอกด "รับเข้า" เท่านั้น
(ได้รูปชุดเดียวกันจากไลน์มาด้วย); dedupe ถาวรต่อข้อความ; เห็น/สแกนเฉพาะ admin.
"""
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
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
from auth import hash_password
from models import AppUser, TodoItem, TodoSuggest
from services import ai_assist, todo_scan

FAKE_JPG = b"\xff\xd8\xff" + b"x" * 200
NOW = datetime.now()


def _ts(minutes_ago: int) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _make_archive(tmp_path: Path) -> Path:
    """คลังปลอม: แจ้งซ่อม (มีรูปพ่วง 2 ใบ) + รายงานเสร็จแล้ว + ทักทาย + ข้อความเก่าเกิน."""
    db = tmp_path / "line_archive.db"
    media = tmp_path / "line_media"
    media.mkdir()
    for f in ("a.jpg", "b.jpg"):
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
    con.execute("INSERT INTO line_user VALUES ('u1','สันติพงษ์',NULL)")
    rows = [
        (1, 'm1', 'g1', 'u1', 'image', None, 'a.jpg', _ts(65)),
        (2, 'm2', 'g1', 'u1', 'image', None, 'b.jpg', _ts(64)),
        (3, 'm3', 'g1', 'u1', 'text', 'ยางหลังแตก 2 เส้น รถ 72-1219 ขอเปลี่ยนด่วนครับ', None, _ts(60)),
        (4, 'm4', 'g1', 'u1', 'text', 'ส่งตู้เสร็จแล้วครับ ขอบคุณครับ', None, _ts(30)),
        (5, 'm5', 'g1', 'u1', 'text', 'สวัสดีครับ', None, _ts(20)),
        (6, 'm6', 'g1', 'u1', 'text', 'เมื่อเดือนก่อนขอเบิกไส้กรอง', None,
         (NOW - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")),
        # ฟอร์แมตแจ้งเติมน้ำมัน (F4 ดูแยกแล้ว) + โพสต์ซ้ำข้ามกลุ่มของ msg 3
        (7, 'm7', 'g1', 'u1', 'text', 'แจ้งเติม Caltex ดีเซล 120 ลิตร รถ 72-1219', None, _ts(15)),
        (8, 'm8', 'g1', 'u1', 'text', 'ยางหลังแตก 2 เส้น รถ 72-1219 ขอเปลี่ยนด่วนครับ', None, _ts(10)),
    ]
    con.executemany("INSERT INTO line_message VALUES (?,?,?,?,?,?,?,?,NULL,0)", rows)
    con.commit()
    con.close()
    return db


@pytest.fixture()
def clients(tmp_path):
    os.environ["YK_LINE_DB"] = str(_make_archive(tmp_path))
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    # กัน auto-scan thread เด้งระหว่างเทสต์ — มาร์กว่าเพิ่งสแกนไป
    appmod.set_setting("todo_scan_last", datetime.utcnow().isoformat())
    with Session(engine) as s:
        admin = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        admin.must_change_pw = False
        s.add(admin)
        s.add(AppUser(username="off1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.commit()
    with TestClient(appmod.app) as c_admin, TestClient(appmod.app) as c_off:
        c_admin.post("/login", data={"username": "yk1", "password": "changeme1"})
        c_off.post("/login", data={"username": "off1", "password": "pw12345678"})
        yield c_admin, c_off
    os.environ.pop("YK_LINE_DB", None)


def _fake_classify(monkeypatch):
    """AI ปลอม: ชี้ msg 3 (แจ้งซ่อม) เป็นงาน — เก็บ listing ที่ AI เห็นไว้ตรวจ."""
    seen = {}

    def fake(messages, max_tokens=1000, temperature=0):
        seen["listing"] = messages[-1]["content"]
        return ('[{"id": 3, "summary": "เปลี่ยนยางหลัง 2 เส้น รถ 72-1219", '
                '"category": "แจ้งซ่อม"}]')

    monkeypatch.setattr(ai_assist, "chat_qwen", fake)
    return seen


def test_scan_creates_pending_and_dedupes(clients, monkeypatch):
    c_admin, _ = clients
    seen = _fake_classify(monkeypatch)
    r = c_admin.post("/todo/scan-line", follow_redirects=False)
    assert r.status_code == 303 and "scanned=1" in r.headers["location"]
    # prefilter หยาบ: msg 3 ต้องถึง AI; ทักทาย (ไม่มีคีย์เวิร์ด) / เก่าเกิน /
    # ฟอร์แมตแจ้งเติมน้ำมัน (7) / โพสต์ซ้ำข้ามกลุ่ม (8) ต้องไม่ถึง
    # (msg 4 "ขอบคุณ" ติดคีย์เวิร์ด "ขอ" มาด้วยได้ — AI เป็นคนคัดชั้นสุดท้าย)
    assert "[3]" in seen["listing"]
    assert "สวัสดี" not in seen["listing"] and "ไส้กรอง" not in seen["listing"]
    assert "[7]" not in seen["listing"] and "[8]" not in seen["listing"]
    with Session(engine) as s:
        sg = s.exec(select(TodoSuggest)).one()   # แถวเดียว
    assert sg.status == "pending" and sg.line_msg_id == 3
    assert sg.summary == "เปลี่ยนยางหลัง 2 เส้น รถ 72-1219" and sg.category == "แจ้งซ่อม"
    assert "ยางหลังแตก" in sg.text
    # สแกนซ้ำ — dedupe ไม่เพิ่มแถว
    c_admin.post("/todo/scan-line")
    with Session(engine) as s:
        assert len(s.exec(select(TodoSuggest)).all()) == 1


def test_suggest_box_admin_only(clients, monkeypatch):
    c_admin, c_off = clients
    _fake_classify(monkeypatch)
    c_admin.post("/todo/scan-line")
    assert "จากไลน์ รอคัด" in c_admin.get("/todo").text
    assert "จากไลน์ รอคัด" not in c_off.get("/todo").text
    assert c_off.post("/todo/scan-line").status_code == 403


def test_accept_creates_todo_with_media(clients, monkeypatch):
    c_admin, _ = clients
    _fake_classify(monkeypatch)
    c_admin.post("/todo/scan-line")
    with Session(engine) as s:
        sid = s.exec(select(TodoSuggest)).one().id
    r = c_admin.post(f"/todo/suggest/{sid}/accept", follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        sg = s.get(TodoSuggest, sid)
        t = s.get(TodoItem, sg.todo_id)
    assert sg.status == "accepted"
    assert t.username == "yk1" and t.category == "แจ้งซ่อม"
    assert "ยางหลังแตก" in t.text and "📱 ไลน์" in t.text
    assert len(t.media_json.split(",")) == 2   # รูป a+b (±20 นาที คนเดียวกัน) ตามมา
    # รับซ้ำไม่ได้ (ไม่ pending แล้ว)
    assert c_admin.post(f"/todo/suggest/{sid}/accept").status_code == 404


def test_dismiss_hides_from_box(clients, monkeypatch):
    c_admin, _ = clients
    _fake_classify(monkeypatch)
    c_admin.post("/todo/scan-line")
    with Session(engine) as s:
        sid = s.exec(select(TodoSuggest)).one().id
    c_admin.post(f"/todo/suggest/{sid}/dismiss")
    with Session(engine) as s:
        assert s.get(TodoSuggest, sid).status == "dismissed"
        assert s.exec(select(TodoItem)).first() is None   # ไม่เกิดงานจริง
    assert "เปลี่ยนยางหลัง" not in c_admin.get("/todo").text


def test_scan_error_shows_message(clients, monkeypatch):
    c_admin, _ = clients

    def boom(messages, **kw):
        raise RuntimeError("เรียก AI ไม่สำเร็จ (URLError) — ลองใหม่อีกครั้ง")

    monkeypatch.setattr(ai_assist, "chat_qwen", boom)
    monkeypatch.setattr(ai_assist, "claude_available", lambda: False)
    r = c_admin.post("/todo/scan-line", follow_redirects=True)
    assert r.status_code == 200 and "ไม่สำเร็จ" in r.text


def test_ai_bogus_ids_ignored(clients, monkeypatch):
    c_admin, _ = clients
    monkeypatch.setattr(ai_assist, "chat_qwen", lambda messages, **kw:
                        '[{"id": 999, "summary": "มั่ว", "category": "งาน"}]')
    c_admin.post("/todo/scan-line")
    with Session(engine) as s:
        assert s.exec(select(TodoSuggest)).first() is None


# ---- Qwen ล่ม (gateway ฟรี 9arm ตอบ content ว่างทั้งวัน 9ก.ค.) → ต้องมีทางรอด ----

def _qwen_down(monkeypatch):
    def boom(messages, **kw):
        raise RuntimeError("AI ไม่ได้ส่งคำตอบกลับมา — ลองใหม่อีกครั้ง")

    monkeypatch.setattr(ai_assist, "chat_qwen", boom)


def _add_line_msgs(n: int, start_id: int = 100) -> None:
    """เติมข้อความ 'เป็นงาน' n ข้อความในคลังไลน์ปลอม (ข้อความไม่ซ้ำ — ไม่โดน dedupe)."""
    con = sqlite3.connect(os.environ["YK_LINE_DB"])
    con.executemany("INSERT INTO line_message VALUES (?,?,?,?,?,?,?,?,NULL,0)", [
        (start_id + i, f"x{i}", 'g1', 'u1', 'text',
         f"ขอเปลี่ยนยางรถคันที่ {i} ด่วนครับ", None, _ts(50)) for i in range(n)])
    con.commit()
    con.close()


def test_qwen_down_falls_back_to_claude(clients, monkeypatch):
    """Qwen ล่ม = กล่องรอคัดต้องไม่ตาย — Claude (haiku) คัดแทน."""
    c_admin, _ = clients
    _qwen_down(monkeypatch)
    seen = {}

    def fake_claude(prompt, cwd=None, timeout=180, model=None):
        seen["prompt"] = prompt
        seen["model"] = model
        return ('[{"id": 3, "summary": "เปลี่ยนยางหลัง 2 เส้น รถ 72-1219", '
                '"category": "แจ้งซ่อม"}]')

    monkeypatch.setattr(ai_assist, "claude_available", lambda: True)
    monkeypatch.setattr(ai_assist, "chat_claude", fake_claude)

    r = c_admin.post("/todo/scan-line", follow_redirects=False)
    assert r.status_code == 303 and "scanned=1" in r.headers["location"]
    assert "[3]" in seen["prompt"]          # ก้อนเดิมถูกส่งต่อให้ Claude
    assert seen["model"] == "haiku"         # งานคัดกรองปริมาณเยอะ — ห้ามใช้รุ่นแพง
    with Session(engine) as s:
        sg = s.exec(select(TodoSuggest)).one()
    assert sg.line_msg_id == 3 and sg.category == "แจ้งซ่อม"


def test_claude_fallback_capped_per_run(clients, monkeypatch):
    """สำรอง Claude กินโควต้า Max ของโอ — จำกัดจำนวนก้อนต่อรอบ ก้อนที่เกินข้ามไป
    (ข้อความยังไม่ถูกจดว่าเสนอแล้ว → รอบหน้าได้สแกนใหม่)."""
    c_admin, _ = clients
    _add_line_msgs(30)                      # รวมของเดิม → 2 ก้อน (25/ก้อน)
    _qwen_down(monkeypatch)
    calls = []
    monkeypatch.setattr(todo_scan, "_MAX_CLAUDE_CHUNKS", 1)
    monkeypatch.setattr(ai_assist, "claude_available", lambda: True)
    monkeypatch.setattr(ai_assist, "chat_claude",
                        lambda prompt, **kw: calls.append(1) or "[]")

    res = todo_scan.scan()
    assert len(calls) == 1                  # ก้อนที่ 2 ไม่ยิง Claude ซ้ำ
    assert res["failed"] == 1 and res["added"] == 0
    with Session(engine) as s:
        assert s.exec(select(TodoSuggest)).first() is None


def test_invented_category_normalized(clients, monkeypatch):
    """วัดจริง 9ก.ค.: Claude แต่งหมวดเอง ('ฝากงาน'/'นัดหมาย') ทั้งที่สเปคมี 3 หมวด
    — ต้องยุบเป็น 'งาน' ไม่งั้นรายการหมวดบน /todo บานปลาย."""
    c_admin, _ = clients
    monkeypatch.setattr(ai_assist, "chat_qwen", lambda messages, **kw:
                        '[{"id": 3, "summary": "เปลี่ยนยาง", "category": "ฝากงาน"}]')
    c_admin.post("/todo/scan-line")
    with Session(engine) as s:
        assert s.exec(select(TodoSuggest)).one().category == "งาน"


def test_all_chunks_failed_raises(clients, monkeypatch):
    """AI ล่มทั้งคู่ = ต้องรู้ว่ายังไม่ได้สแกน (ไม่ใช่รายงานว่าเสร็จแล้วเจอ 0 งาน)."""
    c_admin, _ = clients
    _qwen_down(monkeypatch)
    monkeypatch.setattr(ai_assist, "claude_available", lambda: True)
    monkeypatch.setattr(ai_assist, "chat_claude", lambda prompt, **kw:
                        (_ for _ in ()).throw(RuntimeError("เรียก Claude ไม่สำเร็จ")))
    with pytest.raises(RuntimeError):
        todo_scan.scan()


# ---- auto-scan พังแล้วต้องลองใหม่ ไม่ใช่เงียบไป 20 ชม. ------------------------

class _SyncThread:
    """รัน target ทันทีตอน .start() — ให้เทสต์เห็นผล auto-scan โดยไม่ต้องรอ thread."""

    def __init__(self, target=None, daemon=None, **kw):
        self._target = target

    def start(self):
        self._target()


def test_failed_auto_scan_retries_within_hour(clients, monkeypatch):
    c_admin, _ = clients
    monkeypatch.setattr(appmod.threading, "Thread", _SyncThread)
    monkeypatch.setattr(ai_assist, "claude_available", lambda: False)
    calls = []

    def boom(messages, **kw):
        calls.append(1)
        raise RuntimeError("AI ไม่ได้ส่งคำตอบกลับมา — ลองใหม่อีกครั้ง")

    monkeypatch.setattr(ai_assist, "chat_qwen", boom)

    two_hours_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    # รอบก่อนสำเร็จ 2 ชม.ที่แล้ว → ยังไม่ถึงรอบวันถัดไป ไม่ต้องสแกน
    appmod.set_setting("todo_scan_last", two_hours_ago)
    appmod.set_setting("todo_scan_err", "")
    c_admin.get("/todo")
    assert calls == []

    # รอบก่อน "พัง" → ต้องลองใหม่ (1 ชม.) ไม่ใช่รอครบ 20 ชม.
    appmod.set_setting("todo_scan_last", two_hours_ago)
    appmod.set_setting("todo_scan_err", "AI ล่ม")
    c_admin.get("/todo")
    assert len(calls) == 1
    assert appmod.get_setting("todo_scan_err")     # ยังพัง → จดไว้

    # สแกนสำเร็จ → ล้างธงพัง กลับไปวันละครั้งตามเดิม
    monkeypatch.setattr(ai_assist, "chat_qwen", lambda messages, **kw: "[]")
    appmod.set_setting("todo_scan_last", two_hours_ago)
    c_admin.get("/todo")
    assert appmod.get_setting("todo_scan_err") == ""
    c_admin.get("/todo")
    assert len(calls) == 1                          # ไม่สแกนซ้ำเพราะยังไม่ถึงรอบ


def test_suggest_box_is_collapsible_and_closed_by_default(clients, monkeypatch):
    """โอสั่ง 9ก.ค.: กล่องรอคัดต้องพับเก็บได้เหมือนหัวข้อ "เสร็จแล้ว" (คลิกหัวข้อ = ขยาย/ซ่อน)."""
    c_admin, _ = clients
    _fake_classify(monkeypatch)
    c_admin.post("/todo/scan-line")
    body = c_admin.get("/todo").text
    box = body[body.index("จากไลน์ รอคัด") - 300:body.index("จากไลน์ รอคัด") + 100]
    assert "<details" in box and "<summary" in box
    assert "<details open" not in box          # ปิดไว้ก่อน ไม่บังโน้ตของโอ


def test_suggest_box_opens_when_there_is_news(clients, monkeypatch):
    """เพิ่งสแกนเสร็จ/สแกนพัง → กางให้เห็นเลย ไม่ต้องคลิกหา."""
    c_admin, _ = clients
    _fake_classify(monkeypatch)
    r = c_admin.post("/todo/scan-line", follow_redirects=True)
    assert "<details open" in r.text

    appmod.set_setting("todo_scan_last", datetime.utcnow().isoformat())
    appmod.set_setting("todo_scan_err", "AI ล่ม")
    assert "<details open" in c_admin.get("/todo").text


def test_saved_scan_error_shows_on_todo_page(clients):
    """โอต้องเห็นบนหน้า /todo ว่าสแกนล่าสุดพัง — ไม่ใช่ต้องไปเปิด log เอง."""
    c_admin, c_off = clients
    appmod.set_setting("todo_scan_last", datetime.utcnow().isoformat())
    appmod.set_setting("todo_scan_err", "AI ไม่ได้ส่งคำตอบกลับมา")
    assert "AI ไม่ได้ส่งคำตอบกลับมา" in c_admin.get("/todo").text
    assert "AI ไม่ได้ส่งคำตอบกลับมา" not in c_off.get("/todo").text
