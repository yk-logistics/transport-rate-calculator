# -*- coding: utf-8 -*-
"""📥 กล่องบิลรอคัด (v51) — อัปโหลดรูปบิลเป็นกอง → OCR คิวเบื้องหลัง → คัดเข้ารถ/Stock.

กฎยืน: AI เขียนได้แค่ร่างใน BillInbox — MaintRecord/StockTxn เกิดตอนโอกดยืนยัน
คิวอยู่ใน DB (restart แล้วอ่านต่อ) · สวิตช์ bill_ocr_mode เดิมคุมทั้งฟีเจอร์
สเปค: docs/superpowers/specs/2026-07-10-bill-inbox-ocr-queue-design.md
"""
import io
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from auth import hash_password
from models import AppUser, BillInbox, MaintPart, MaintRecord, Part, StockTxn, Vehicle
from services import bill_ocr
from starlette.testclient import TestClient

JPG = b"\xff\xd8\xff" + b"x" * 200

DRAFT = {"vendor": "ร้านประเสริฐทรัพย์การยาง", "work_date": "2026-06-28",
         "plate": "71-8005", "total": 4100.0, "sum_lines": 4100.0, "mismatch": False,
         "lines": [
             {"kind": "service", "name": "บริการนอกสถานที่", "qty": 1.0, "unit_price": 1200.0, "amount": 1200.0},
             {"kind": "part", "name": "น็อตล้อ อีซูซุ", "qty": 8.0, "unit_price": 250.0, "amount": 2000.0},
         ]}


@pytest.fixture()
def clients(monkeypatch):
    monkeypatch.setattr(appmod, "_bill_inbox_kick", lambda: None)   # คุมจังหวะ worker เอง
    shutil.rmtree(appmod._uploads_dir / "bill_inbox", ignore_errors=True)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        admin = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        admin.must_change_pw = False; s.add(admin)
        s.add(AppUser(username="off1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.add(Vehicle(plate_no="71-8005", status="active"))
        s.commit()
    with TestClient(appmod.app) as c_admin, TestClient(appmod.app) as c_off:
        c_admin.post("/login", data={"username": "yk1", "password": "changeme1"})
        c_off.post("/login", data={"username": "off1", "password": "pw12345678"})
        yield c_admin, c_off


def _upload(client, n=1):
    files = [("photos", (f"b{i}.jpg", io.BytesIO(JPG), "image/jpeg")) for i in range(n)]
    return client.post("/maint/bills/upload", files=files, follow_redirects=False)


def _rows():
    with Session(engine) as s:
        return s.exec(select(BillInbox).order_by(BillInbox.id)).all()


# ---- อัปโหลด = ตั้งคิวทันที ไม่เรียก AI ----------------------------------------

def test_upload_queues_rows_without_calling_ai(clients, monkeypatch):
    c_admin, _ = clients
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: (_ for _ in ()).throw(
        AssertionError("ห้ามเรียก AI ตอนอัปโหลด")))
    r = _upload(c_admin, n=3)
    assert r.status_code == 303
    rows = _rows()
    assert len(rows) == 3 and all(x.status == "pending" for x in rows)
    for x in rows:
        assert (appmod._uploads_dir / x.photo_path).exists()
        assert x.photo_path.endswith(".jpg")
    with Session(engine) as s:                      # ไม่มีบิลจริงเกิด
        assert s.exec(select(MaintRecord)).first() is None


def test_upload_gate_office_403_and_off_403(clients):
    c_admin, c_off = clients
    assert _upload(c_off).status_code == 403
    assert c_off.get("/maint/bills").status_code == 403
    appmod.set_setting("bill_ocr_mode", "off")
    assert _upload(c_admin).status_code == 403
    assert _rows() == []


# ---- worker: pending → ready/failed + restart-safe ----------------------------

def test_worker_pass_reads_pending_to_ready(clients, monkeypatch):
    c_admin, _ = clients
    _upload(c_admin, n=2)
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: DRAFT)
    appmod._bill_inbox_pass()
    rows = _rows()
    assert [x.status for x in rows] == ["ready", "ready"]
    assert json.loads(rows[0].ocr_json)["plate"] == "71-8005"


def test_worker_failure_marks_failed_with_reason_and_retry(clients, monkeypatch):
    c_admin, _ = clients
    _upload(c_admin)
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: (_ for _ in ()).throw(
        RuntimeError("รูปนี้ไม่ใช่บิลที่มีรายการราคา")))
    appmod._bill_inbox_pass()
    row = _rows()[0]
    assert row.status == "failed" and "ไม่ใช่บิล" in row.error

    r = c_admin.post(f"/maint/bills/{row.id}/retry", follow_redirects=False)
    assert r.status_code == 303
    assert _rows()[0].status == "pending"


def test_stale_reading_requeued(clients, monkeypatch):
    """แอปดับกลางคัน (แถวค้าง reading) → pass ถัดไปตีกลับเป็น pending แล้วอ่านต่อ."""
    c_admin, _ = clients
    _upload(c_admin)
    with Session(engine) as s:
        row = s.exec(select(BillInbox)).one()
        row.status = "reading"
        row.updated_at = datetime.utcnow() - timedelta(minutes=15)
        s.add(row); s.commit()
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: DRAFT)
    appmod._bill_inbox_pass()
    assert _rows()[0].status == "ready"


def test_worker_respects_off_switch(clients, monkeypatch):
    c_admin, _ = clients
    _upload(c_admin)
    appmod.set_setting("bill_ocr_mode", "off")
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: (_ for _ in ()).throw(
        AssertionError("ปิดสวิตช์แล้วห้ามอ่าน")))
    appmod._bill_inbox_pass()
    assert _rows()[0].status == "pending"


# ---- คัดออกจากกล่อง: เข้ารถ / เข้า Stock / ทิ้ง --------------------------------

def _ready_row(client, monkeypatch):
    _upload(client)
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: DRAFT)
    appmod._bill_inbox_pass()
    return _rows()[0]


def test_to_record_creates_bill_and_marks_done(clients, monkeypatch):
    c_admin, _ = clients
    row = _ready_row(c_admin, monkeypatch)
    r = c_admin.post(f"/maint/bills/{row.id}/to-record", data={
        "plate_raw": "71-8005", "work_date": "2026-06-28",
        "vendor_name": "ร้านประเสริฐทรัพย์การยาง",
        "kind": ["service", "part"],
        "name": ["บริการนอกสถานที่", "น็อตล้อ อีซูซุ"],
        "qty": ["1", "8"], "unit_price": ["1200", "250"],
    }, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        rec = s.exec(select(MaintRecord)).one()
        lines = s.exec(select(MaintPart)).all()
    assert rec.vehicle_id is not None and rec.total_cost == 3200.0
    assert rec.other_cost == 1200.0 and rec.parts_cost == 2000.0
    assert len(lines) == 2
    row2 = _rows()[0]
    assert row2.status == "done" and row2.done_action == f"record:{rec.id}"
    # กดซ้ำไม่ได้ — ใบนี้จบแล้ว
    assert c_admin.post(f"/maint/bills/{row.id}/to-record", data={
        "plate_raw": "71-8005", "work_date": "2026-06-28",
        "kind": ["part"], "name": ["x"], "qty": ["1"], "unit_price": ["1"],
    }).status_code == 404


def test_to_stock_creates_parts_and_stockin_no_maintrecord(clients, monkeypatch):
    c_admin, _ = clients
    row = _ready_row(c_admin, monkeypatch)
    r = c_admin.post(f"/maint/bills/{row.id}/to-stock", data={
        "work_date": "2026-06-28",
        "name": ["น็อตล้อ อีซูซุ", "จุ๊บลมยาง"],
        "qty": ["8", "2"], "unit_price": ["250", "200"],
    }, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        parts = s.exec(select(Part).order_by(Part.id)).all()
        txns = s.exec(select(StockTxn)).all()
        assert s.exec(select(MaintRecord)).first() is None
    assert [p.name for p in parts] == ["น็อตล้อ อีซูซุ", "จุ๊บลมยาง"]
    assert all(t.direction == "in" for t in txns) and len(txns) == 2
    assert txns[0].qty == 8.0 and txns[0].unit_price == 250.0
    assert _rows()[0].status == "done" and _rows()[0].done_action == "stock"

    # เข้า Stock ซ้ำด้วยชื่อเดิม → ไม่สร้าง Part ซ้ำ
    row2 = _ready_row(c_admin, monkeypatch)
    c_admin.post(f"/maint/bills/{row2.id}/to-stock", data={
        "work_date": "2026-06-28", "name": ["น็อตล้อ อีซูซุ"],
        "qty": ["4"], "unit_price": ["250"]})
    with Session(engine) as s:
        assert len(s.exec(select(Part)).all()) == 2


def test_dismiss_keeps_photo_for_audit(clients, monkeypatch):
    c_admin, _ = clients
    row = _ready_row(c_admin, monkeypatch)
    c_admin.post(f"/maint/bills/{row.id}/dismiss")
    row2 = _rows()[0]
    assert row2.status == "dismissed"
    assert (appmod._uploads_dir / row2.photo_path).exists()   # รูปไม่ถูกลบ


def test_bills_page_shows_queue_and_ready_draft(clients, monkeypatch):
    c_admin, _ = clients
    _upload(c_admin, n=2)
    monkeypatch.setattr(bill_ocr, "read_bill", lambda p: DRAFT)
    appmod._bill_inbox_pass()
    body = c_admin.get("/maint/bills").text
    assert "น็อตล้อ อีซูซุ" in body                 # ร่างโผล่
    assert 'value="71-8005"' in body                # ทะเบียนที่ OCR อ่านได้ prefill
    assert "to-stock" in body and "to-record" in body
