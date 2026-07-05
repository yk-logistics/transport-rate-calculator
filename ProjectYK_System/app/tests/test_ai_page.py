# -*- coding: utf-8 -*-
"""หน้า /ai ผู้ช่วยแชทถามระบบ (เฟส 3) — เฉพาะ admin, log ทุกครั้ง, AI พัง = ข้อความไม่ใช่ 500."""
import os
import tempfile

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
from models import AiChatLog, AppUser
from services import ai_assist


@pytest.fixture()
def clients():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
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


def test_admin_sees_page_office_denied(clients):
    c_admin, c_off = clients
    assert c_admin.get("/ai").status_code == 200
    assert c_off.get("/ai").status_code == 403
    assert c_off.post("/ai/ask", json={"q": "x", "model": "qwen"}).status_code == 403


def test_ask_qwen_answers_and_logs(clients, monkeypatch):
    c_admin, _ = clients
    seen = {}

    def fake(msgs, max_tokens=2000, temperature=0.3):
        seen["msgs"] = msgs
        return "AYU ตัดรอบ 26→25 ครับ"

    monkeypatch.setattr(ai_assist, "chat_qwen", fake)
    r = c_admin.post("/ai/ask", json={"q": "รอบจ่าย AYU ตัดวันไหน", "model": "qwen"})
    assert r.status_code == 200 and r.json() == {"ok": True, "answer": "AYU ตัดรอบ 26→25 ครับ"}
    assert seen["msgs"][0]["role"] == "system"
    assert "Project YK" in seen["msgs"][0]["content"]     # system prompt มีบริบทระบบ
    assert seen["msgs"][-1] == {"role": "user", "content": "รอบจ่าย AYU ตัดวันไหน"}
    with Session(engine) as s:
        log = s.exec(select(AiChatLog)).one()
    assert log.username == "yk1" and log.model == "qwen" and log.ok
    assert log.question == "รอบจ่าย AYU ตัดวันไหน" and "26" in log.answer


def test_history_passed_to_model(clients, monkeypatch):
    c_admin, _ = clients
    seen = {}
    monkeypatch.setattr(ai_assist, "chat_qwen",
                        lambda msgs, **kw: seen.update(msgs=msgs) or "ตอบ")
    hist = [{"role": "user", "content": "ถามแรก"}, {"role": "assistant", "content": "ตอบแรก"}]
    c_admin.post("/ai/ask", json={"q": "ต่อ", "model": "qwen", "history": hist})
    roles = [m["role"] for m in seen["msgs"]]
    assert roles == ["system", "user", "assistant", "user"]


def test_ai_failure_logged_not_500(clients, monkeypatch):
    c_admin, _ = clients

    def boom(msgs, **kw):
        raise RuntimeError("เรียก AI ไม่สำเร็จ (URLError) — ลองใหม่อีกครั้ง")

    monkeypatch.setattr(ai_assist, "chat_qwen", boom)
    r = c_admin.post("/ai/ask", json={"q": "ถาม", "model": "qwen"})
    assert r.status_code == 200
    j = r.json()
    assert not j["ok"] and "ไม่สำเร็จ" in j["answer"]
    with Session(engine) as s:
        log = s.exec(select(AiChatLog)).one()
    assert not log.ok


def test_claude_unavailable_friendly_message(clients, monkeypatch):
    c_admin, _ = clients
    monkeypatch.setattr(ai_assist, "_claude_exe", lambda: None)
    r = c_admin.post("/ai/ask", json={"q": "ถาม", "model": "claude"})
    j = r.json()
    assert not j["ok"] and "claude CLI" in j["answer"]


def test_claude_flattens_history_to_prompt(clients, monkeypatch):
    c_admin, _ = clients
    seen = {}
    monkeypatch.setattr(ai_assist, "chat_claude",
                        lambda prompt, cwd=None, timeout=180: seen.update(p=prompt) or "ตอบ")
    hist = [{"role": "user", "content": "ก่อนหน้า"}]
    c_admin.post("/ai/ask", json={"q": "ล่าสุด", "model": "claude", "history": hist})
    assert "Project YK" in seen["p"] and "โอ: ก่อนหน้า" in seen["p"]
    assert seen["p"].rstrip().endswith("โอ: ล่าสุด")
    with Session(engine) as s:
        assert s.exec(select(AiChatLog)).one().model == "claude"


def test_empty_question_rejected_no_log(clients):
    c_admin, _ = clients
    j = c_admin.post("/ai/ask", json={"q": "  ", "model": "qwen"}).json()
    assert not j["ok"]
    with Session(engine) as s:
        assert s.exec(select(AiChatLog)).first() is None
