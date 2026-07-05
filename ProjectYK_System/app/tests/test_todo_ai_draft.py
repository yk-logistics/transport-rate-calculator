"""ปุ่ม ✨ AI เรียบเรียงบนหน้า /todo (เฟส 2 LINE→todo).

กติกา: AI คืน draft เป็น fragment เท่านั้น — DB ไม่เปลี่ยนจนกว่าโอกด "ใช้ตามนี้"
(ยิง /todo/{id}/update ตัวเดิม); AI พัง = โชว์ข้อความ ไม่ใช่ 500.
"""
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
from models import AppUser, TodoItem
from services import ai_assist


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


def _add(client, text="สั่งยาง 71-8967 ดว่น"):
    client.post("/todo/add", data={"text": text})
    with Session(engine) as s:
        return s.exec(select(TodoItem).order_by(TodoItem.id.desc())).first().id


def test_draft_fragment_shows_ai_text_without_saving(client, monkeypatch):
    seen = {}

    def fake(text, cats):
        seen["text"], seen["cats"] = text, cats
        return {"text": "สั่งยาง 71-8967 ด่วน", "category": "แจ้งซ่อม"}

    monkeypatch.setattr(ai_assist, "rewrite_todo", fake)
    tid = _add(client)
    r = client.post(f"/todo/{tid}/ai-draft")
    assert r.status_code == 200
    assert "สั่งยาง 71-8967 ด่วน" in r.text and "แจ้งซ่อม" in r.text
    assert f'action="/todo/{tid}/update"' in r.text
    assert seen["text"] == "สั่งยาง 71-8967 ดว่น"  # ส่งข้อความเดิมให้ AI
    with Session(engine) as s:  # draft เท่านั้น — DB ยังเป็นข้อความเดิม
        assert s.get(TodoItem, tid).text == "สั่งยาง 71-8967 ดว่น"


def test_accept_draft_saves_via_update(client, monkeypatch):
    monkeypatch.setattr(ai_assist, "rewrite_todo",
                        lambda text, cats: {"text": "เรียบเรียงแล้ว", "category": "งาน"})
    tid = _add(client)
    client.post(f"/todo/{tid}/ai-draft")
    client.post(f"/todo/{tid}/update",
                data={"text": "เรียบเรียงแล้ว", "category": "งาน", "priority": "0", "due_date": ""})
    with Session(engine) as s:
        t = s.get(TodoItem, tid)
    assert t.text == "เรียบเรียงแล้ว" and t.category == "งาน"


def test_ai_failure_shows_message_not_500(client, monkeypatch):
    def boom(text, cats):
        raise RuntimeError("ยังไม่ได้ตั้งคีย์ AI (YK_QWEN_KEY) — แจ้งแอดมิน")

    monkeypatch.setattr(ai_assist, "rewrite_todo", boom)
    tid = _add(client)
    r = client.post(f"/todo/{tid}/ai-draft")
    assert r.status_code == 200 and "ยังไม่ได้ตั้งคีย์ AI" in r.text
    with Session(engine) as s:
        assert s.get(TodoItem, tid).text == "สั่งยาง 71-8967 ดว่น"


def test_other_users_item_404(client):
    with Session(engine) as s:
        other = TodoItem(username="someone_else", text="ของคนอื่น")
        s.add(other); s.commit(); s.refresh(other)
        oid = other.id
    r = client.post(f"/todo/{oid}/ai-draft")
    assert r.status_code == 404


def test_todo_page_has_ai_button(client, monkeypatch):
    tid = _add(client)
    b = client.get("/todo").text
    assert f'hx-post="/todo/{tid}/ai-draft"' in b and f'id="aid-{tid}"' in b


def test_rewrite_todo_keeps_source_lines_and_parses_fenced_json(monkeypatch):
    """unit: service ต้องแกะ JSON ในรั้ว ``` ได้ + เติมบรรทัดที่มา 📱 คืนถ้า AI ทำหาย."""
    class FakeResp:
        def read(self):
            import json
            return json.dumps({"choices": [{"message": {"content":
                '```json\n{"text": "ยางหลังแตก 2 เส้น ขอเปลี่ยน", "category": "แจ้งซ่อม"}\n```'}}]}).encode()

        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setenv("YK_QWEN_KEY", "k")
    monkeypatch.setattr(ai_assist.urllib.request, "urlopen", lambda req, timeout: FakeResp())
    src = "ยางหลังแตก2เส้นขอเปลียน\n\n📱 ไลน์ Y.K. หัวลาก LCB. — สันติพงษ์ 2026-07-04 07:14"
    d = ai_assist.rewrite_todo(src, ["แจ้งซ่อม"])
    assert d["category"] == "แจ้งซ่อม"
    assert "ขอเปลี่ยน" in d["text"]
    assert "📱 ไลน์ Y.K. หัวลาก LCB." in d["text"]  # บรรทัดที่มาต้องไม่หาย


def test_rewrite_todo_no_key_raises_thai_message(monkeypatch):
    monkeypatch.delenv("YK_QWEN_KEY", raising=False)
    monkeypatch.delenv("YK_QWEN_KEY_FILE", raising=False)
    with pytest.raises(RuntimeError, match="YK_QWEN_KEY"):
        ai_assist.rewrite_todo("x", [])
