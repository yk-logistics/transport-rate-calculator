# -*- coding: utf-8 -*-
"""หน้ารายการบันทึกซ่อม: โชว์รายการอะไหล่ในตาราง + ค้นหาจากชื่ออะไหล่ (โอสั่ง 10ก.ค.).

บิลที่ดึงจาก RM History มีช่องอาการว่าง — รายละเอียดจริงอยู่ใน MaintPart
โออยากรู้ "เปลี่ยนอะไหล่อะไรไปเมื่อไหร่" โดยไม่ต้องคลิกเข้าทีละใบ
"""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import AppUser, MaintPart, MaintRecord
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)

        r1 = MaintRecord(record_no="M000001", work_date=date(2026, 6, 28),
                         plate_raw="71-8005", kind="repair", status="done",
                         total_cost=4100.0)
        r2 = MaintRecord(record_no="M000002", work_date=date(2026, 5, 1),
                         plate_raw="71-0560", kind="repair", status="done",
                         work_done="เปลี่ยนแบตเตอรี่", total_cost=3200.0)
        s.add(r1); s.add(r2); s.commit(); s.refresh(r1); s.refresh(r2)
        for name in ("บริการนอกสถานที่", "ค่าแรงถอดประกอบ", "จุ๊บลมยางสลับกะทะ",
                     "น็อตล้อ อีซูซุ"):
            s.add(MaintPart(maint_record_id=r1.id, kind="part", part_name_raw=name,
                            qty=1, unit_price=100, total=100))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_list_shows_line_items_inline(client):
    body = client.get("/maint/records").text
    assert "จุ๊บลมยางสลับกะทะ" in body          # รายการโผล่ในตาราง ไม่ต้องคลิกเข้า
    assert "น็อตล้อ อีซูซุ" in body
    assert "เปลี่ยนแบตเตอรี่" in body             # ช่องอาการเดิมยังโชว์


def test_line_summary_capped_not_full_dump(client):
    """บิลบรรทัดเยอะๆ โชว์แค่ต้นๆ + ตัวนับ — กันหน้า 8 พันแถวบวมเป็นสิบ MB."""
    with Session(engine) as s:
        r = MaintRecord(record_no="M000003", work_date=date(2026, 4, 1),
                        plate_raw="71-9999", kind="repair", status="done")
        s.add(r); s.commit(); s.refresh(r)
        for i in range(12):
            s.add(MaintPart(maint_record_id=r.id, kind="part",
                            part_name_raw=f"อะไหล่ทดสอบ{i:02d}", qty=1,
                            unit_price=10, total=10))
        s.commit()
    body = client.get("/maint/records").text
    assert "อะไหล่ทดสอบ00" in body
    assert "อะไหล่ทดสอบ11" not in body            # เกิน 4 ตัวแรกถูกยุบ
    assert "+8 รายการ" in body


def test_search_by_part_name(client):
    body = client.get("/maint/records?q=น็อตล้อ").text
    assert "M000001" in body and "M000002" not in body
    assert "จำนวน: <strong>1</strong>" in body    # แถบสรุปนับตามผลค้นหา


def test_search_matches_work_done_too(client):
    body = client.get("/maint/records?q=แบตเตอรี่").text
    assert "M000002" in body and "M000001" not in body


def test_filter_form_submits_empty_fields_without_422(client):
    """ของจริง 10ก.ค.: กดปุ่ม 'กรอง' ฟอร์มส่งทุกช่องรวม vehicle_id ว่าง →
    เดิม FastAPI ตีกลับ 422 int_parsing ทั้งหน้า (บั๊กแฝง — ช่องค้นหาใหม่ทำให้เจอ)."""
    r = client.get("/maint/records?date_from=&date_to=&vehicle_id=&kind=&status=&q=น็อตล้อ")
    assert r.status_code == 200
    assert "M000001" in r.text and "M000002" not in r.text


def test_filter_vehicle_id_still_works_as_number(client):
    with Session(engine) as s:
        from models import Vehicle
        v = Vehicle(plate_no="71-8005", status="active")
        s.add(v); s.commit(); s.refresh(v)
        rec = s.exec(select(MaintRecord).where(MaintRecord.record_no == "M000001")).one()
        rec.vehicle_id = v.id
        s.add(rec); s.commit()
        vid = v.id
    r = client.get(f"/maint/records?vehicle_id={vid}")
    assert r.status_code == 200
    assert "M000001" in r.text and "M000002" not in r.text


def test_search_no_hit_shows_empty(client):
    body = client.get("/maint/records?q=ไม่มีทางเจอสิ่งนี้").text
    assert "M000001" not in body and "M000002" not in body
    assert "ไม่พบรายการ" in body
