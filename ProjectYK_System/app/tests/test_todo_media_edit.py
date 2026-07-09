# -*- coding: utf-8 -*-
"""หน้าโน้ต /todo: แก้ไขโน้ตแล้ว เพิ่ม/ลบรูป ได้ (โอสั่ง 9ก.ค.).

เดิม: แนบรูปได้เฉพาะตอนสร้างใหม่ · ลบรูปไม่ได้เลย · ช่องแก้ข้อความเป็น input
บรรทัดเดียว → โน้ตจากไลน์ (หลายบรรทัด + บรรทัดที่มา "📱 ไลน์...") พังตอนแก้
"""
import io
import os
import shutil
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
from models import AppUser, TodoItem

JPG = b"\xff\xd8\xff" + b"a" * 100
PNG = b"\x89PNG\r\n" + b"b" * 100


@pytest.fixture()
def clients():
    shutil.rmtree(appmod._TODO_MEDIA, ignore_errors=True)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    appmod.set_setting("todo_scan_last", "2999-01-01T00:00:00")   # กัน auto-scan
    with Session(engine) as s:
        admin = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        admin.must_change_pw = False
        s.add(admin)
        s.add(AppUser(username="off1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.commit()
    with TestClient(appmod.app) as c, TestClient(appmod.app) as c2:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        c2.post("/login", data={"username": "off1", "password": "pw12345678"})
        yield c, c2


def _add_note(client, text="เปลี่ยนยาง 71-8005", photos=None) -> int:
    files = photos or []
    client.post("/todo/add", data={"text": text, "category": "งาน", "priority": "0"},
                files=files)
    with Session(engine) as s:
        return s.exec(select(TodoItem).order_by(TodoItem.id.desc())).first().id


def _media(item_id) -> list[str]:
    with Session(engine) as s:
        t = s.get(TodoItem, item_id)
    return [m for m in (t.media_json or "").split(",") if m]


def _file(name, blob):
    return ("photos", (name, io.BytesIO(blob), "image/jpeg"))


def test_edit_can_add_photo_to_existing_note(clients):
    c, _ = clients
    nid = _add_note(c)
    assert _media(nid) == []

    c.post(f"/todo/{nid}/update", data={"text": "เปลี่ยนยาง 71-8005", "priority": "0"},
           files=[_file("a.jpg", JPG)])
    names = _media(nid)
    assert len(names) == 1
    assert (appmod._TODO_MEDIA / str(nid) / names[0]).read_bytes() == JPG
    assert c.get(f"/todo/media/{nid}/{names[0]}").status_code == 200


def test_edit_can_remove_photo(clients):
    c, _ = clients
    nid = _add_note(c, photos=[_file("a.jpg", JPG), _file("b.png", PNG)])
    names = _media(nid)
    assert len(names) == 2
    gone, kept = names[0], names[1]

    c.post(f"/todo/{nid}/update", data={"text": "แก้แล้ว", "priority": "0",
                                        "remove_media": gone})
    assert _media(nid) == [kept]
    assert not (appmod._TODO_MEDIA / str(nid) / gone).exists()      # ลบไฟล์จริง
    assert (appmod._TODO_MEDIA / str(nid) / kept).exists()


def test_new_photo_after_remove_does_not_overwrite(clients):
    """ลบรูปที่ 1 แล้วเพิ่มรูปใหม่ ต้องไม่ทับชื่อไฟล์ของรูปที่ 2."""
    c, _ = clients
    nid = _add_note(c, photos=[_file("a.jpg", JPG), _file("b.jpg", PNG)])
    first, second = _media(nid)

    c.post(f"/todo/{nid}/update", data={"text": "x", "priority": "0", "remove_media": first},
           files=[_file("c.jpg", b"\xff\xd8\xffccc")])
    names = _media(nid)
    assert second in names and len(names) == 2
    assert (appmod._TODO_MEDIA / str(nid) / second).read_bytes() == PNG   # ของเดิมไม่โดนทับ


def test_remove_media_cannot_escape_folder(clients):
    """ชื่อไฟล์มาจากฟอร์ม — ต้องลบได้เฉพาะรูปของโน้ตนั้นจริงๆ."""
    c, _ = clients
    nid = _add_note(c, photos=[_file("a.jpg", JPG)])
    keep = _media(nid)[0]
    victim = appmod._TODO_MEDIA / "victim.txt"
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_text("ห้ามหาย")

    c.post(f"/todo/{nid}/update", data={"text": "x", "priority": "0",
                                        "remove_media": "../victim.txt"})
    assert victim.exists()
    assert _media(nid) == [keep]


def test_multiline_note_survives_edit(clients):
    """โน้ตจากไลน์มีหลายบรรทัด — แก้แล้วบรรทัดที่มาต้องไม่หาย (textarea ไม่ใช่ input)."""
    c, _ = clients
    body = "ยางหลังแตก 2 เส้น\nขอเปลี่ยนด่วน\n\n📱 ไลน์ · Y.K. หัวลาก LCB."
    nid = _add_note(c, text=body)
    c.post(f"/todo/{nid}/update", data={"text": body + "\nสั่งของแล้ว", "priority": "0"})
    with Session(engine) as s:
        t = s.get(TodoItem, nid)
    assert "📱 ไลน์" in t.text and t.text.count("\n") == 4
    assert 'name="text"' in c.get("/todo").text and "<textarea" in c.get("/todo").text


def test_other_user_cannot_touch_photos(clients):
    c, c2 = clients
    nid = _add_note(c, photos=[_file("a.jpg", JPG)])
    name = _media(nid)[0]

    c2.post(f"/todo/{nid}/update", data={"text": "แอบแก้", "priority": "0",
                                         "remove_media": name},
            files=[_file("evil.jpg", JPG)])
    assert _media(nid) == [name]
    assert (appmod._TODO_MEDIA / str(nid) / name).exists()
    assert c2.get(f"/todo/media/{nid}/{name}").status_code == 404


def test_non_image_upload_ignored(clients):
    c, _ = clients
    nid = _add_note(c)
    c.post(f"/todo/{nid}/update", data={"text": "x", "priority": "0"},
           files=[("photos", ("bill.pdf", io.BytesIO(b"%PDF"), "application/pdf"))])
    assert _media(nid) == []
