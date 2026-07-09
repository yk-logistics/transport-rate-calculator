# -*- coding: utf-8 -*-
"""📷 อ่านบิลจากรูป → ร่างรายการ (v49) — AI เสนอ คนกดยืนยันถึงบันทึก.

เคสจริง: บิลร้านประเสริฐทรัพย์การยาง (โอส่ง 9ก.ค.) — บริการ 1,200 + ค่าแรง 500
+ ลูกยาง 2×200 + น็อต 8×250 = 4,100
"""
import io
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
from models import AppUser, MaintPart, MaintRecord
from services import ai_assist, bill_ocr

FAKE_JPG = b"\xff\xd8\xff" + b"x" * 300

BILL_JSON = """```json
{"vendor": "ร้านประเสริฐทรัพย์การยาง", "work_date": "2026-06-28", "plate": "71-8005",
 "total": 4100,
 "lines": [
   {"kind": "service", "name": "บริการนอกสถานที่", "qty": 1, "unit_price": 1200, "amount": 1200},
   {"kind": "ค่าแรง", "name": "ค่าแรงถอดประกอบ", "qty": 1, "unit_price": 500, "amount": 500},
   {"kind": "part", "name": "ลูกยางสลับกะทะ", "qty": 2, "unit_price": 200, "amount": 400},
   {"kind": "part", "name": "น็อต", "qty": 8, "unit_price": 250, "amount": null}
 ]}
```"""


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


def _new_record(client) -> int:
    client.post("/maint/records/new", data={"work_date": "2026-06-28", "kind": "tire_change",
                                            "status": "done", "plate_raw": "71-8005",
                                            "paid_by": "cash"})
    with Session(engine) as s:
        return s.exec(select(MaintRecord).order_by(MaintRecord.id.desc())).first().id


# ---- service: แกะคำตอบ AI --------------------------------------------------

def test_read_bill_parses_fence_and_normalizes(monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw: BILL_JSON)
    d = bill_ocr.read_bill(r"C:\x\bill.jpg")
    assert d["vendor"] == "ร้านประเสริฐทรัพย์การยาง"
    assert d["plate"] == "71-8005" and d["work_date"] == "2026-06-28"
    assert [ln["kind"] for ln in d["lines"]] == ["service", "labor", "part", "part"]
    assert d["lines"][3]["amount"] == 2000.0     # amount ว่าง → qty × หน่วยละ
    assert d["sum_lines"] == 4100.0
    assert d["total"] == 4100.0 and d["mismatch"] is False


def test_read_bill_flags_total_mismatch(monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw:
                        '{"total": 5000, "lines": [{"kind":"part","name":"น็อต","qty":8,'
                        '"unit_price":250,"amount":2000}]}')
    d = bill_ocr.read_bill("x.jpg")
    assert d["sum_lines"] == 2000.0 and d["mismatch"] is True   # ต้องเตือน ไม่ใช่แก้เอง


def test_read_bill_ignores_prose_around_json(monkeypatch):
    """วัดจริง 9ก.ค.: Sonnet พ่วงคำอธิบายไทยหน้า JSON เมื่อรูปแปลกจากที่สั่ง."""
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw:
                        "รูปนี้เป็นบิลร้านยางครับ ผมแกะให้แล้ว:\n\n" + BILL_JSON +
                        "\n\nถ้าต้องการเพิ่มเติมบอกได้")
    d = bill_ocr.read_bill("x.jpg")
    assert d["sum_lines"] == 4100.0


def test_read_bill_not_a_bill_says_so(monkeypatch):
    """รูปที่ไม่ใช่บิล (ใบเสร็จไปรษณีย์/ฟอร์ม DHL — เจอจริงในคลังไลน์) ต้องบอกตรงๆ
    ไม่ใช่โทษคนถ่ายว่า 'ถ่ายไม่ชัด'."""
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw:
                        '{"is_bill": false, "note": "ใบส่งของ DHL", "lines": []}')
    with pytest.raises(RuntimeError, match="ไม่ใช่บิล"):
        bill_ocr.read_bill("x.jpg")


def test_read_bill_no_lines_raises(monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw: '{"lines": []}')
    with pytest.raises(RuntimeError, match="ไม่พบรายการ"):
        bill_ocr.read_bill("x.jpg")


def test_read_bill_garbage_raises(monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw: "อ่านไม่ออกครับ")
    with pytest.raises(RuntimeError):
        bill_ocr.read_bill("x.jpg")


# ---- route: อัปโหลด → ร่าง → ยืนยัน ----------------------------------------

def test_upload_shows_draft_without_saving(client, monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw: BILL_JSON)
    rec_id = _new_record(client)
    r = client.post(f"/maint/records/{rec_id}/read-bill",
                    files={"photo": ("bill.jpg", io.BytesIO(FAKE_JPG), "image/jpeg")})
    assert r.status_code == 200
    assert "ลูกยางสลับกะทะ" in r.text and "บริการนอกสถานที่" in r.text
    with Session(engine) as s:                       # ยังไม่เขียนบรรทัดจริง
        assert s.exec(select(MaintPart)).first() is None
        assert s.get(MaintRecord, rec_id).total_cost == 0.0


def test_confirm_draft_creates_lines_and_totals(client):
    """ฟอร์มร่างส่งฟิลด์ซ้ำชื่อกัน 4 แถว — จับคู่ตามลำดับ (เหมือน HTML form จริง)."""
    rec_id = _new_record(client)
    r = client.post(f"/maint/records/{rec_id}/parts/bulk-add", data={
        "kind": ["service", "labor", "part", "part"],
        "name": ["บริการนอกสถานที่", "ค่าแรงถอดประกอบ", "ลูกยางสลับกะทะ", "น็อต"],
        "qty": ["1", "1", "2", "8"],
        "unit_price": ["1200", "500", "200", "250"],
    }, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        rec = s.get(MaintRecord, rec_id)
        lines = s.exec(select(MaintPart)).all()
    assert len(lines) == 4
    assert rec.parts_cost == 2400.0 and rec.labor_cost == 500.0 and rec.other_cost == 1200.0
    assert rec.total_cost == 4100.0


def test_bulk_add_skips_empty_rows(client):
    """แถวที่ถูกลบชื่อออก (คนไม่เอาบรรทัดนั้น) ต้องไม่ถูกบันทึก."""
    rec_id = _new_record(client)
    client.post(f"/maint/records/{rec_id}/parts/bulk-add", data={
        "kind": ["part", "part"],
        "name": ["น็อต", ""],
        "qty": ["8", "1"],
        "unit_price": ["250", "999"],
    })
    with Session(engine) as s:
        assert len(s.exec(select(MaintPart)).all()) == 1
        assert s.get(MaintRecord, rec_id).parts_cost == 2000.0


def test_upload_saves_with_safe_extension(client, monkeypatch):
    """ชื่อไฟล์มาจากผู้ใช้ — นามสกุลแปลกต้องไม่ตกค้างใน uploads/."""
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw: BILL_JSON)
    rec_id = _new_record(client)
    client.post(f"/maint/records/{rec_id}/read-bill",
                files={"photo": ("bill.exe", io.BytesIO(FAKE_JPG), "image/jpeg")})
    saved = list((appmod._uploads_dir / "maint" / str(rec_id)).iterdir())
    assert saved and all(f.suffix == ".jpg" for f in saved)


def test_upload_rejects_non_image(client):
    rec_id = _new_record(client)
    r = client.post(f"/maint/records/{rec_id}/read-bill",
                    files={"photo": ("bill.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    assert r.status_code == 200 and "รูปภาพ" in r.text
    with Session(engine) as s:
        assert s.exec(select(MaintPart)).first() is None


def test_ocr_failure_shows_message_not_500(client, monkeypatch):
    monkeypatch.setattr(ai_assist, "chat_claude", lambda p, **kw:
                        (_ for _ in ()).throw(RuntimeError("Claude ใช้เวลานานเกินไป")))
    rec_id = _new_record(client)
    r = client.post(f"/maint/records/{rec_id}/read-bill",
                    files={"photo": ("bill.jpg", io.BytesIO(FAKE_JPG), "image/jpeg")})
    assert r.status_code == 200 and "นานเกินไป" in r.text
