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
    # เข้ารถแล้วต้องกลับหน้ากล่องบิลต่อ (คัดใบถัดไปรัวๆ) — โอขอ 11 ก.ค.
    assert r.headers["location"] == f"/maint/bills?ok=record:{rec.id}"
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


def test_new_record_form_links_to_inbox_for_admin_only(clients):
    """โอเปิดหน้า 'สร้างใหม่' แล้วหาปุ่มไม่เจอ (10ก.ค.) — ต้องมีทางลัดไปกล่องบิล."""
    c_admin, c_off = clients
    assert 'href="/maint/bills"' in c_admin.get("/maint/records/new").text
    assert 'href="/maint/bills"' not in c_off.get("/maint/records/new").text


# ---------------------------------------------------------------------------
# v52: ทะเบียนรายบรรทัด — เส้นไหนคันไหนคีย์ในกล่องเลย (โอขอ 11 ก.ค. 2026)
# ---------------------------------------------------------------------------

def test_to_record_per_line_plate_splits_records(clients, monkeypatch):
    """แถวที่กรอกทะเบียนของตัวเอง แยกไปใบซ่อมของคันนั้น; แถวว่างตามทะเบียนหลัก."""
    c_admin, _ = clients
    with Session(engine) as s:
        s.add(Vehicle(plate_no="71-8006", status="active")); s.commit()
    row = _ready_row(c_admin, monkeypatch)
    r = c_admin.post(f"/maint/bills/{row.id}/to-record", data={
        "plate_raw": "71-8005", "work_date": "2026-06-28",
        "vendor_name": "ร้านประเสริฐทรัพย์การยาง",
        "kind": ["service", "part"],
        "name": ["บริการนอกสถานที่", "น็อตล้อ อีซูซุ"],
        "qty": ["1", "8"], "unit_price": ["1200", "250"],
        "line_plate": ["", "71-8006"],
    }, follow_redirects=False)
    assert r.status_code == 303

    with Session(engine) as s:
        recs = s.exec(select(MaintRecord).order_by(MaintRecord.id)).all()
        assert len(recs) == 2
        by_plate = {rec.plate_raw: rec for rec in recs}
        assert set(by_plate) == {"71-8005", "71-8006"}
        assert by_plate["71-8005"].total_cost == 1200.0
        assert by_plate["71-8006"].total_cost == 2000.0
        assert all(rec.vehicle_id is not None for rec in recs)
        for rec in recs:
            lines = s.exec(select(MaintPart).where(
                MaintPart.maint_record_id == rec.id)).all()
            assert len(lines) == 1
        ids = ",".join(str(rec.id) for rec in recs)
    assert r.headers["location"] == f"/maint/bills?ok=record:{ids}"
    row2 = _rows()[0]
    assert row2.status == "done" and row2.done_action == f"record:{ids}"


def test_to_record_plate_suffix_resolves_vehicle(clients, monkeypatch):
    """โอสอน: ทะเบียนในบิลมักเขียนแค่เลขท้าย เช่น 8005 = 71-8005 —
    ถ้าเลขท้ายชี้รถได้คันเดียว ให้จับคู่และเก็บทะเบียนเต็ม."""
    c_admin, _ = clients
    row = _ready_row(c_admin, monkeypatch)
    r = c_admin.post(f"/maint/bills/{row.id}/to-record", data={
        "plate_raw": "8005", "work_date": "2026-06-28",
        "kind": ["part"], "name": ["น็อตล้อ"], "qty": ["1"], "unit_price": ["250"],
    }, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        rec = s.exec(select(MaintRecord)).one()
        assert rec.plate_raw == "71-8005"
        assert rec.vehicle_id is not None


def test_dismiss_all_failed(clients, monkeypatch):
    """ปุ่มทิ้งทั้งหมดที่อ่านไม่ผ่าน — ทิ้งเฉพาะ failed ไม่แตะ ready/pending."""
    c_admin, _ = clients
    _upload(c_admin, n=3)
    rows = _rows()
    with Session(engine) as s:
        a, b, c = (s.get(BillInbox, r.id) for r in rows)
        a.status, a.error = "failed", "ไม่ใช่บิล"
        b.status, b.error = "failed", "อ่านไม่ออก"
        c.status = "ready"
        for x in (a, b, c):
            s.add(x)
        s.commit()
        cid = c.id
    r = c_admin.post("/maint/bills/dismiss-failed", follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        st = {row.id: row.status for row in s.exec(select(BillInbox)).all()}
    assert list(st.values()).count("dismissed") == 2
    assert st[cid] == "ready"


# ---------------------------------------------------------------------------
# v53 UX: หน้ารายการซ่อมโชว์รูปบิลต้นฉบับจากกล่อง + ฟอร์มซ่อมรับทะเบียนเลขท้าย
# ---------------------------------------------------------------------------

def test_record_page_links_source_bill_photo(clients, monkeypatch):
    """คัดใบเข้ารถแล้ว → หน้ารายการซ่อมต้องมีลิงก์รูปบิลต้นฉบับ."""
    c_admin, _ = clients
    row = _ready_row(c_admin, monkeypatch)
    c_admin.post(f"/maint/bills/{row.id}/to-record", data={
        "plate_raw": "71-8005", "work_date": "2026-06-28",
        "kind": ["part"], "name": ["น็อตล้อ"], "qty": ["8"], "unit_price": ["250"],
    })
    with Session(engine) as s:
        rec = s.exec(select(MaintRecord)).one()
        photo = s.get(BillInbox, row.id).photo_path
    page = c_admin.get(f"/maint/records/{rec.id}").text
    assert f"/uploads/{photo}" in page


def test_maint_form_resolves_plate_suffix(clients):
    """ฟอร์มบันทึกซ่อม: พิมพ์เลขท้าย 8005 → ผูกรถ 71-8005 (กฎเดียวกับกล่องบิล)."""
    c_admin, _ = clients
    r = c_admin.post("/maint/records/new", data={
        "work_date": "2026-07-12", "kind": "repair", "status": "done",
        "plate_raw": "8005", "mile_snapshot": "0",
    }, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        rec = s.exec(select(MaintRecord).order_by(MaintRecord.id.desc())).first()
        v = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-8005")).one()
    assert rec.vehicle_id == v.id
    assert rec.plate_raw == "71-8005"


def test_home_shows_bill_inbox_card_for_admin(clients, monkeypatch):
    """หน้าแรกโชว์การ์ดกล่องบิล (จำนวน ready) เฉพาะคนที่มีสิทธิ์กล่องบิล."""
    c_admin, c_off = clients
    _ready_row(c_admin, monkeypatch)
    home = c_admin.get("/").text
    assert "กล่องบิลรอคัด" in home
    # office (bill_ocr_mode=admin) ไม่เห็นการ์ด
    assert "กล่องบิลรอคัด" not in c_off.get("/").text


def test_inbox_page_shows_today_progress(clients, monkeypatch):
    """หัวกล่องบิลโชว์ 'คัดแล้ววันนี้ X ใบ' — นับ done+dismissed ที่อัปเดตวันนี้."""
    c_admin, _ = clients
    row = _ready_row(c_admin, monkeypatch)
    c_admin.post(f"/maint/bills/{row.id}/dismiss")
    page = c_admin.get("/maint/bills").text
    assert "คัดแล้ววันนี้" in page and "1 ใบ" in page


def test_nav_badge_when_bills_ready(clients, monkeypatch):
    """เมนู 'หน้างาน' มีจุดแดงเมื่อกล่องบิลมีของ ready (cache 60 วิ)."""
    c_admin, _ = clients
    import main as m
    m._NAV_BADGE_CACHE["at"] = None          # ล้าง cache ข้ามเทสต์
    _ready_row(c_admin, monkeypatch)
    m._NAV_BADGE_CACHE["at"] = None
    assert "yk-nav-dot" in c_admin.get("/maint").text


def test_fuel_form_resolves_plate_suffix(clients):
    """ฟอร์มน้ำมัน: พิมพ์เลขท้าย 8005 (ไม่เลือกจาก dropdown) → ผูก 71-8005 ให้เอง."""
    from models import FuelTxn
    c_admin, _ = clients
    r = c_admin.post("/fuel/new", data={
        "txn_date": "2026-07-12", "site_code": "LCB", "plate_no_raw": "8005",
        "liter": "100", "amount": "3200",
    }, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        t = s.exec(select(FuelTxn).order_by(FuelTxn.id.desc())).first()
        v = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-8005")).one()
    assert t.plate_no_raw == "71-8005" and t.vehicle_id == v.id
