# -*- coding: utf-8 -*-
"""เขียนประวัติซ่อมลง DB — dry-run เป็นค่าเริ่มต้น, ยิงซ้ำไม่เกิดซ้ำ,
จับคู่รถไม่ได้ = ไม่เขียน, rollback แตะเฉพาะแถวที่ import."""
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
from models import MaintPart, MaintRecord, Vehicle, Vendor
from services import rm_history as rm
from services import rm_history_import as rmi

SHEET_ID = "SHEETLCB"


def _parsed(plate="71-6802"):
    p = rm.ParsedTab(plate=plate, header_row=6, sheet_net_total=638.26)
    b = rm.Bill(work_date=date(2021, 2, 18), mile=12029.0,
                vendor="Isuzu บางปะอิน", sheet_row=11)
    b.lines = [{"kind": "part", "name": "ฝาครอบรีเลย์", "qty": 1.0, "unit_price": 690.0,
                "total": 690.0, "discount": 103.50, "vat": 41.06, "net": 627.56}]
    p.bills = [b]
    return p


@pytest.fixture()
def session():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        s.add(Vehicle(plate_no="71-6802", site_code="LCB"))
        s.commit()
        yield s


def test_dry_run_writes_nothing(session):
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=True)
    assert stats["bills"] == 1 and stats["lines"] == 1
    assert session.exec(select(MaintRecord)).first() is None
    assert session.exec(select(Vendor)).first() is None


def test_apply_creates_record_lines_and_vendor(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    rec = session.exec(select(MaintRecord)).one()
    line = session.exec(select(MaintPart)).one()
    vendor = session.exec(select(Vendor)).one()

    assert rec.vehicle_id is not None and rec.plate_raw == "71-6802"
    assert rec.mile_snapshot == 12029.0 and rec.vendor_id == vendor.id
    assert rec.import_key.startswith("rm:lcb:")
    assert round(rec.total_cost, 2) == 627.56 and rec.discount == 103.50
    assert line.kind == "part" and line.vat == 41.06


def test_second_run_is_idempotent(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    assert stats["skipped_dup"] == 1
    assert len(session.exec(select(MaintRecord)).all()) == 1
    assert len(session.exec(select(MaintPart)).all()) == 1


def test_unmatched_plate_writes_nothing(session):
    p = _parsed(plate="99-9999")
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "99-9999", p, dry_run=False)
    assert stats["skipped_tab"] == 1 and stats["bills"] == 0
    assert session.exec(select(MaintRecord)).first() is None


def test_non_vehicle_tab_writes_nothing(session):
    p = rm.ParsedTab(plate=None, header_row=0)
    stats = rmi.import_tab(session, "lcb", SHEET_ID, "หน้ารวม", p, dry_run=False)
    assert stats["skipped_tab"] == 1
    assert session.exec(select(MaintRecord)).first() is None


def test_rollback_only_touches_imported_rows(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    hand = MaintRecord(record_no="M999999", work_date=date(2026, 1, 1), import_key="")
    session.add(hand); session.commit()

    n = rmi.rollback_file(session, "lcb", dry_run=True)
    assert n == 1 and len(session.exec(select(MaintRecord)).all()) == 2

    n = rmi.rollback_file(session, "lcb", dry_run=False)
    assert n == 1
    rows = session.exec(select(MaintRecord)).all()
    assert len(rows) == 1 and rows[0].record_no == "M999999"   # บันทึกที่คนคีย์เองรอด
    assert session.exec(select(MaintPart)).first() is None


def test_rollback_of_other_file_does_not_touch_this_one(session):
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", _parsed(), dry_run=False)
    assert rmi.rollback_file(session, "bigc", dry_run=False) == 0
    assert len(session.exec(select(MaintRecord)).all()) == 1


def test_blank_net_line_still_counted(session):
    """โอเคาะ 9ก.ค.: ชีทไม่กรอกช่องสุทธิ → นับจาก รวม−ส่วนลด+VAT."""
    p = _parsed()
    p.bills[0].lines = [{"kind": "service", "name": "อัดจาระบีทุกจุด", "qty": 1.0,
                         "unit_price": 180.0, "total": 180.0, "discount": 0.0,
                         "vat": 0.0, "net": 0.0}]
    rmi.import_tab(session, "lcb", SHEET_ID, "71-6802", p, dry_run=False)
    rec = session.exec(select(MaintRecord)).one()
    assert rec.other_cost == 180.0 and rec.total_cost == 180.0
