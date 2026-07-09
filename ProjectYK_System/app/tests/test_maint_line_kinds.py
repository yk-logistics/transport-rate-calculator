# -*- coding: utf-8 -*-
"""บันทึกซ่อม: คีย์บิลเป็นรายการๆ พร้อมหมวดต่อบรรทัด (อะไหล่ / ค่าแรง / บริการ).

เคสจริง — บิลร้านประเสริฐทรัพย์การยาง 28/6/69 รถ 71-8005 (โอส่งรูป 9ก.ค.):
    1 × บริการนอกสถานที่   1,200 = 1,200   (บริการ)
    1 × ค่าแรง               500 =   500   (ค่าแรง)
    2 × ลูกยางสลับกะทะ       200 =   400   (อะไหล่)
    8 × น็อต                 250 = 2,000   (อะไหล่)
                                   -------
                            รวม    4,100

กฎเงิน: หมวดไหน "ไม่มีบรรทัดเลย" ต้องใช้ยอดที่คีย์มือไว้ตามเดิม — ห้ามล้างเป็น 0
(บันทึกเก่ามีแต่บรรทัดอะไหล่ + ค่าแรงคีย์มือ).
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
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, MaintPart, MaintRecord


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


def _new_record(client, **manual_costs) -> int:
    """สร้างบันทึกซ่อมผ่านฟอร์ม; manual_costs = ยอดที่คีย์มือไว้ "สมัยก่อน v49"
    (ตั้งตรงใน DB เพราะฟอร์มไม่มีช่องให้กรอกแล้ว)."""
    client.post("/maint/records/new", data={
        "work_date": "2026-06-28", "kind": "tire_change", "status": "done",
        "plate_raw": "71-8005", "paid_by": "cash"})
    with Session(engine) as s:
        rec = s.exec(select(MaintRecord).order_by(MaintRecord.id.desc())).first()
        if manual_costs:
            for k, v in manual_costs.items():
                setattr(rec, k, float(v))
            rec.total_cost = rec.parts_cost + rec.labor_cost + rec.other_cost
            s.add(rec); s.commit(); s.refresh(rec)
        return rec.id


def _add_line(client, rec_id, name, qty, price, kind):
    return client.post(f"/maint/records/{rec_id}/parts/add",
                       data={"part_name_raw": name, "qty": str(qty),
                             "unit_price": str(price), "kind": kind})


def _rec(rec_id) -> MaintRecord:
    with Session(engine) as s:
        return s.get(MaintRecord, rec_id)


def test_real_bill_71_8005_sums_by_kind(client):
    rec_id = _new_record(client)
    _add_line(client, rec_id, "บริการนอกสถานที่", 1, 1200, "service")
    _add_line(client, rec_id, "ค่าแรง", 1, 500, "labor")
    _add_line(client, rec_id, "ลูกยางสลับกะทะ", 2, 200, "part")
    _add_line(client, rec_id, "น็อต", 8, 250, "part")

    r = _rec(rec_id)
    assert r.parts_cost == 2400.0      # 400 + 2000 (เฉพาะบรรทัดอะไหล่)
    assert r.labor_cost == 500.0
    assert r.other_cost == 1200.0      # บริการ → ช่อง "ค่าอื่นๆ"
    assert r.total_cost == 4100.0      # ตรงกับยอดรวมในบิล


def test_manual_cost_kept_when_no_line_of_that_kind(client):
    """บันทึกเก่า: ค่าแรงคีย์มือ 900 + เพิ่มบรรทัดอะไหล่ → ค่าแรงต้องไม่ถูกล้างเป็น 0."""
    rec_id = _new_record(client, labor_cost=900)
    _add_line(client, rec_id, "ผ้าเบรก", 2, 300, "part")

    r = _rec(rec_id)
    assert r.labor_cost == 900.0
    assert r.parts_cost == 600.0
    assert r.total_cost == 1500.0


def test_manual_parts_cost_kept_when_only_labor_line(client):
    """คีย์ค่าอะไหล่มือ 1,000 แล้วเพิ่มบรรทัด 'ค่าแรง' → ค่าอะไหล่ต้องไม่หาย."""
    rec_id = _new_record(client, parts_cost=1000)
    _add_line(client, rec_id, "ค่าแรงถอดประกอบ", 1, 500, "labor")

    r = _rec(rec_id)
    assert r.parts_cost == 1000.0
    assert r.labor_cost == 500.0


def test_delete_last_labor_line_zeroes_labor(client):
    rec_id = _new_record(client)
    _add_line(client, rec_id, "ค่าแรง", 1, 500, "labor")
    _add_line(client, rec_id, "น็อต", 8, 250, "part")
    with Session(engine) as s:
        labor_line = s.exec(select(MaintPart).where(MaintPart.kind == "labor")).one()
        lid = labor_line.id

    client.post(f"/maint/records/{rec_id}/parts/{lid}/delete")
    r = _rec(rec_id)
    assert r.labor_cost == 0.0
    assert r.parts_cost == 2000.0
    assert r.total_cost == 2000.0


def test_line_kind_defaults_to_part(client):
    """ฟอร์มเก่า/สคริปต์ที่ไม่ส่ง kind (เช่น หน้าคีย์บิลยาง) ต้องได้ 'อะไหล่' ตามเดิม."""
    rec_id = _new_record(client)
    client.post(f"/maint/records/{rec_id}/parts/add",
                data={"part_name_raw": "ยางนอก", "qty": "1", "unit_price": "5000"})
    with Session(engine) as s:
        assert s.exec(select(MaintPart)).one().kind == "part"
    assert _rec(rec_id).parts_cost == 5000.0


def test_header_form_has_no_manual_cost_inputs(client):
    """v49: เลิกกรอกยอดซ้ำ 2 ที่ — ยอดมาจากรายการอย่างเดียว (ช่องกรอกมือหายไป)."""
    rec_id = _new_record(client)
    body = client.get(f"/maint/records/{rec_id}").text
    assert 'name="parts_cost"' not in body
    assert 'name="labor_cost"' not in body
    assert 'name="other_cost"' not in body


def test_saving_header_does_not_wipe_line_totals(client):
    """เคยเป็นกับดัก: แก้หัวบิล (วันที่/หมายเหตุ) แล้ว save → ยอดที่มาจากรายการต้องไม่หาย."""
    rec_id = _new_record(client)
    _add_line(client, rec_id, "น็อต", 8, 250, "part")
    _add_line(client, rec_id, "ค่าแรง", 1, 500, "labor")

    client.post(f"/maint/records/{rec_id}", data={
        "work_date": "2026-06-29", "kind": "tire_change", "status": "done",
        "plate_raw": "71-8005", "paid_by": "cash", "notes": "แก้วันที่"})

    r = _rec(rec_id)
    assert r.parts_cost == 2000.0 and r.labor_cost == 500.0 and r.total_cost == 2500.0
    assert r.notes == "แก้วันที่"


def test_saving_header_keeps_legacy_manual_costs(client):
    """บันทึกเก่า (ยอดคีย์มือ ไม่มีบรรทัด) — save หัวบิลแล้วยอดต้องไม่ถูกล้างเป็น 0."""
    rec_id = _new_record(client, parts_cost=1200, labor_cost=800)
    client.post(f"/maint/records/{rec_id}", data={
        "work_date": "2026-06-28", "kind": "repair", "status": "done",
        "plate_raw": "71-8005", "paid_by": "cash"})
    r = _rec(rec_id)
    assert r.parts_cost == 1200.0 and r.labor_cost == 800.0 and r.total_cost == 2000.0


def test_form_has_kind_selector_and_shows_line_kind(client):
    rec_id = _new_record(client)
    _add_line(client, rec_id, "บริการนอกสถานที่", 1, 1200, "service")
    body = client.get(f"/maint/records/{rec_id}").text
    assert 'name="kind"' in body                    # ช่องเลือกหมวดตอนคีย์
    assert 'value="labor"' in body and 'value="service"' in body
    assert "บริการนอกสถานที่" in body               # บรรทัดที่คีย์ไว้โผล่ในตาราง
