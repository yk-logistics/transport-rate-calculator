"""สมุดโน้ต /todo — จดเร็ว/หมวด/ด่วน/กำหนด/ติ๊กเสร็จ/แยกของใครของมัน."""
import os, tempfile

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


def test_add_and_list(client):
    client.post("/todo/add", data={"text": "สั่งยางรถ 71-8967", "category": "อะไหล่",
                                   "priority": "1", "due_date": "2026-07-05"})
    b = client.get("/todo", follow_redirects=True).text
    assert "สั่งยางรถ 71-8967" in b
    assert "อะไหล่" in b
    assert "ด่วน" in b


def test_add_with_photo_saved_and_served(client):
    """บั๊กจริง 4ก.ค.: ปุ่มแนบรูปเดิมลบ <input> ทิ้งตอนเลือกไฟล์ (innerText ทับ parent)
    → รูปไม่เคยถูกส่ง; เทสต์นี้ยืนยันเส้นทาง server ทั้งสาย อัปโหลด→เซฟ→เปิดดู."""
    import io
    fake_jpg = b"\xff\xd8\xff" + b"y" * 300
    client.post("/todo/add", data={"text": "โน้ตมีรูป"},
                files=[("photos", ("a.jpg", io.BytesIO(fake_jpg), "image/jpeg")),
                       ("photos", ("b.png", io.BytesIO(fake_jpg), "image/png"))])
    with Session(engine) as s:
        t = s.exec(select(TodoItem).where(TodoItem.text == "โน้ตมีรูป")).first()
        assert t.media_json and len(t.media_json.split(",")) == 2
        names = t.media_json.split(",")
    b = client.get("/todo", follow_redirects=True).text
    assert f"/todo/media/{t.id}/{names[0]}" in b            # thumbnail โผล่ในหน้า
    r = client.get(f"/todo/media/{t.id}/{names[0]}")
    assert r.status_code == 200 and r.content == fake_jpg   # เปิดรูปได้จริง
    # นามสกุลนอก whitelist ต้องถูกข้าม (ไม่พัง)
    client.post("/todo/add", data={"text": "โน้ตไฟล์แปลก"},
                files=[("photos", ("x.exe", io.BytesIO(b"MZ" + b"z" * 200), "application/octet-stream"))])
    with Session(engine) as s:
        t2 = s.exec(select(TodoItem).where(TodoItem.text == "โน้ตไฟล์แปลก")).first()
        assert not t2.media_json


def test_toggle_done_and_reopen(client):
    client.post("/todo/add", data={"text": "งานทดสอบเสร็จ"})
    with Session(engine) as s:
        t = s.exec(select(TodoItem).where(TodoItem.text == "งานทดสอบเสร็จ")).first()
    client.post(f"/todo/{t.id}/toggle")
    with Session(engine) as s:
        assert s.get(TodoItem, t.id).status == "done"
    client.post(f"/todo/{t.id}/toggle")
    with Session(engine) as s:
        assert s.get(TodoItem, t.id).status == "open"


def test_search_and_category_filter(client):
    client.post("/todo/add", data={"text": "โทรหาลูกค้า KAO", "category": "ลูกค้า"})
    client.post("/todo/add", data={"text": "เช็คน้ำมันเครื่อง", "category": "ซ่อมบำรุง"})
    b = client.get("/todo?q=KAO", follow_redirects=True).text
    assert "โทรหาลูกค้า KAO" in b and "เช็คน้ำมันเครื่อง" not in b
    b = client.get("/todo?cat=ซ่อมบำรุง", follow_redirects=True).text
    assert "เช็คน้ำมันเครื่อง" in b and "โทรหาลูกค้า KAO" not in b


def test_per_user_isolation(client):
    """โน้ตของคนอื่น มองไม่เห็น/แก้ไม่ได้."""
    with Session(engine) as s:
        s.add(TodoItem(username="someone_else", text="โน้ตลับของคนอื่น"))
        s.commit()
        other = s.exec(select(TodoItem).where(TodoItem.username == "someone_else")).first()
    b = client.get("/todo", follow_redirects=True).text
    assert "โน้ตลับของคนอื่น" not in b
    client.post(f"/todo/{other.id}/delete")
    with Session(engine) as s:
        assert s.get(TodoItem, other.id) is not None  # ลบของคนอื่นไม่ได้


def test_all_roles_can_use():
    import permissions
    for role in ("admin", "office", "accountant", "viewer"):
        assert permissions.check(role, "/todo", "GET") == "edit"
