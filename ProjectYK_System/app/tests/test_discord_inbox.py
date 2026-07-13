"""ดึงจากช่อง Discord 📌01-inbox-โยนมาก่อน เข้า /todo อัตโนมัติ (13ก.ค.).

โอ forward ข้อความ/รูปจากที่ไหนก็ได้เข้าช่องนี้เอง → ระบบ poll แล้วสร้าง TodoItem
หมวด "inbox" ให้เลย (ของที่โยนเอง = ตั้งใจแล้ว ไม่ต้องผ่านกล่องรอคัด)
dedupe ด้วย watermark id ข้อความล่าสุดใน AppSetting.
"""
import os
import tempfile
from pathlib import Path

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"
os.environ["YK_DISCORD_TOKEN"] = "test-token"

import httpx
import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
from models import AppSetting, TodoItem
from services import discord_inbox as di

FAKE_JPG = b"\xff\xd8\xff" + b"x" * 200


def _msg(mid, content="", atts=(), author="kiwi", bot=False, snapshots=()):
    return {
        "id": str(mid), "content": content,
        "timestamp": "2026-07-12T08:38:00.000000+00:00",
        "author": {"username": author, "bot": bot},
        "attachments": [
            {"filename": fn, "size": len(FAKE_JPG), "content_type": "image/jpeg",
             "url": f"https://cdn.test/{mid}/{fn}"} for fn in atts],
        "message_snapshots": [
            {"message": {"content": sc, "attachments": []}} for sc in snapshots],
    }


def _client(store):
    """Discord ปลอม: คืนข้อความ id > after เรียงใหม่→เก่า (เหมือนของจริง) + เสิร์ฟไฟล์รูป."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cdn.test":
            return httpx.Response(200, content=FAKE_JPG)
        assert "/messages" in request.url.path
        after = int(request.url.params.get("after", 0))
        limit = int(request.url.params.get("limit", 50))
        rows = [m for m in store["messages"] if int(m["id"]) > after]
        rows.sort(key=lambda m: -int(m["id"]))
        return httpx.Response(200, json=rows[:limit])
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(di, "MEDIA_DIR", tmp_path / "_todo_media")
    yield


def _todos():
    with Session(engine) as s:
        return s.exec(select(TodoItem).order_by(TodoItem.id)).all()


def test_available_requires_token(monkeypatch, tmp_path):
    assert di.available() is True
    monkeypatch.delenv("YK_DISCORD_TOKEN")
    monkeypatch.delenv("YK_DISCORD_TOKEN_FILE", raising=False)
    assert di.available() is False          # ไม่มี fallback อัตโนมัติ — dev/test ปิดโดยปริยาย
    envf = tmp_path / "bot.env"
    envf.write_text("LINE_CHANNEL_SECRET=x\nDISCORD_BOT_TOKEN=tok-from-env-file\n",
                    encoding="utf-8")
    monkeypatch.setenv("YK_DISCORD_TOKEN_FILE", str(envf))
    assert di._token() == "tok-from-env-file"


def test_pull_creates_todo_with_text_and_media(tmp_path):
    store = {"messages": [_msg(101, "เปลี่ยนยางหน้า 71-5042", atts=("a.jpg", "b.jpg"))]}
    r = di.pull("oh", http=_client(store))
    assert r["added"] == 1
    items = _todos()
    assert len(items) == 1
    t = items[0]
    assert t.username == "oh"
    assert t.category == "inbox"
    assert "เปลี่ยนยางหน้า 71-5042" in t.text
    assert "kiwi" in t.text                      # header บอกที่มา
    assert "2026-07-12 15:38" in t.text          # เวลาไทย (+7 จาก UTC)
    names = [m for m in t.media_json.split(",") if m]
    assert len(names) == 2
    for n in names:
        assert (tmp_path / "_todo_media" / str(t.id) / n).read_bytes() == FAKE_JPG


def test_watermark_dedupes_and_picks_up_new(tmp_path):
    store = {"messages": [_msg(101, "งานแรก")]}
    c = _client(store)
    assert di.pull("oh", http=c)["added"] == 1
    assert di.pull("oh", http=c)["added"] == 0          # ไม่ดึงซ้ำ
    store["messages"].append(_msg(102, "งานสอง"))
    assert di.pull("oh", http=c)["added"] == 1          # ได้เฉพาะตัวใหม่
    texts = [t.text for t in _todos()]
    assert len(texts) == 2 and "งานสอง" in texts[1]


def test_forwarded_message_uses_snapshot_text():
    store = {"messages": [_msg(103, "", snapshots=("ข้อความที่ forward มา",))]}
    r = di.pull("oh", http=_client(store))
    assert r["added"] == 1
    assert "ข้อความที่ forward มา" in _todos()[0].text


def test_bot_and_empty_messages_skipped_but_watermark_moves():
    store = {"messages": [
        _msg(104, "จากบอท", bot=True),
        _msg(105, ""),                       # ว่างเปล่า (เช่น sticker)
    ]}
    c = _client(store)
    assert di.pull("oh", http=c)["added"] == 0
    assert not _todos()
    with Session(engine) as s:
        wm = s.get(AppSetting, "discord_inbox_last_id")
    assert wm and wm.value == "105"          # watermark ขยับ ไม่วนดึงซ้ำ
    store["messages"].append(_msg(106, "งานจริง"))
    assert di.pull("oh", http=c)["added"] == 1
