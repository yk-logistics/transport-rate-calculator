# -*- coding: utf-8 -*-
"""สวิตช์คุมปุ่ม 📷 อ่านบิล — โอสั่ง 9ก.ค.: กินโควต้า Max ของโอ ต้องล็อกไว้ใช้เอง.

`bill_ocr_mode` (AppSetting, ตั้งที่หน้า /ai):
  admin (ค่าเริ่มต้น) = เฉพาะแอดมิน · all = ทุกคนที่เข้าหน้าบันทึกซ่อม · off = ปิดทั้งระบบ
กันไม่ให้เห็นปุ่ม **และ** กันยิง route ตรงๆ (ซ่อนปุ่มอย่างเดียวไม่ใช่การกัน).
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
from models import AppUser, MaintPart, MaintRecord
from services import ai_assist

FAKE_JPG = b"\xff\xd8\xff" + b"x" * 300
BILL_JSON = ('{"lines": [{"kind": "part", "name": "น็อต", "qty": 8, '
             '"unit_price": 250, "amount": 2000}], "total": 2000}')


@pytest.fixture()
def clients(monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw: BILL_JSON)
    shutil.rmtree(appmod._uploads_dir / "maint", ignore_errors=True)  # rec_id ซ้ำข้ามเทสต์
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


def _new_record(client) -> int:
    client.post("/maint/records/new", data={"work_date": "2026-06-28", "kind": "repair",
                                            "status": "done", "plate_raw": "71-8005",
                                            "paid_by": "cash"})
    with Session(engine) as s:
        return s.exec(select(MaintRecord).order_by(MaintRecord.id.desc())).first().id


def _upload(client, rec_id):
    return client.post(f"/maint/records/{rec_id}/read-bill",
                       files={"photo": ("bill.jpg", io.BytesIO(FAKE_JPG), "image/jpeg")})


def test_default_admin_only(clients):
    c_admin, c_off = clients
    rec_id = _new_record(c_admin)

    form = f'action="/maint/records/{rec_id}/read-bill"'
    assert form in c_admin.get(f"/maint/records/{rec_id}").text
    assert form not in c_off.get(f"/maint/records/{rec_id}").text
    assert _upload(c_admin, rec_id).status_code == 200
    assert _upload(c_off, rec_id).status_code == 403       # ยิง route ตรงก็ไม่ได้


def test_mode_off_blocks_everyone(clients):
    c_admin, _ = clients
    rec_id = _new_record(c_admin)
    appmod.set_setting("bill_ocr_mode", "off")

    assert f'action="/maint/records/{rec_id}/read-bill"' not in c_admin.get(f"/maint/records/{rec_id}").text
    assert _upload(c_admin, rec_id).status_code == 403


def test_mode_all_lets_office_use_it(clients):
    c_admin, c_off = clients
    rec_id = _new_record(c_admin)
    appmod.set_setting("bill_ocr_mode", "all")

    assert f'action="/maint/records/{rec_id}/read-bill"' in c_off.get(f"/maint/records/{rec_id}").text
    assert _upload(c_off, rec_id).status_code == 200


def test_blocked_upload_saves_nothing(clients):
    """ถูกกันแล้วต้องไม่มีไฟล์รูปตกค้าง/ไม่มีบรรทัดเกิด (กันเปลืองโควต้า+ที่เก็บ)."""
    c_admin, c_off = clients
    rec_id = _new_record(c_admin)
    _upload(c_off, rec_id)
    assert not (appmod._uploads_dir / "maint" / str(rec_id)).exists()
    with Session(engine) as s:
        assert s.exec(select(MaintPart)).first() is None


def test_admin_can_switch_mode_from_ai_page(clients):
    c_admin, _ = clients
    r = c_admin.post("/ai/settings", data={"draft_provider": "auto", "bill_ocr_mode": "off"},
                     follow_redirects=False)
    assert r.status_code == 303
    assert appmod.get_setting("bill_ocr_mode") == "off"
    assert "อ่านบิลจากรูป" in c_admin.get("/ai").text     # มีสวิตช์ให้เห็นบนหน้า /ai


def test_bad_mode_value_ignored(clients):
    c_admin, _ = clients
    appmod.set_setting("bill_ocr_mode", "admin")
    c_admin.post("/ai/settings", data={"draft_provider": "auto", "bill_ocr_mode": "ทุกคนเลย"})
    assert appmod.get_setting("bill_ocr_mode") == "admin"
