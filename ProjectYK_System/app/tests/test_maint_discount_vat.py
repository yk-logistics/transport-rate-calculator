# -*- coding: utf-8 -*-
"""v50: ส่วนลด + VAT ต่อบรรทัด → ยอดบิลตรงกับ "ราคาสุทธิ" ในชีท RM History.

เคสจริง (LCB 71-6802 แถว 46): ฝาครอบรีเลย์ 690 − ส่วนลด 103.50 + VAT 41.06 = 627.56
"""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session

from db_config import engine
import main as appmod
from models import MaintPart, MaintRecord


@pytest.fixture()
def session():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        yield s


def _rec(s, **kw) -> MaintRecord:
    rec = MaintRecord(record_no=kw.pop("no", "M000001"), work_date=date(2021, 2, 18), **kw)
    s.add(rec); s.commit(); s.refresh(rec)
    return rec


def _line(s, rec_id, kind, qty, price, discount=0.0, vat=0.0):
    s.add(MaintPart(maint_record_id=rec_id, kind=kind, part_name_raw="x",
                    qty=qty, unit_price=price, total=qty * price,
                    discount=discount, vat=vat))
    s.commit()


def test_discount_and_vat_reach_record_total(session):
    rec = _rec(session)
    _line(session, rec.id, "part", 1, 690.0, discount=103.50, vat=41.06)
    appmod._recompute_maint_costs(session, rec)
    session.add(rec); session.commit()

    assert rec.parts_cost == 690.0        # ก่อนหักส่วนลด ก่อน VAT (ตรงช่อง "รวม")
    assert rec.discount == 103.50
    assert rec.vat == 41.06
    assert round(rec.total_cost, 2) == 627.56


def test_legacy_record_without_discount_unchanged(session):
    """บิลเดิม (บิลร้านยาง 4,100) ต้องได้ยอดเดิมทุกบาท — ห้าม regression."""
    rec = _rec(session, no="M000002")
    _line(session, rec.id, "service", 1, 1200.0)
    _line(session, rec.id, "labor", 1, 500.0)
    _line(session, rec.id, "part", 2, 200.0)
    _line(session, rec.id, "part", 8, 250.0)
    appmod._recompute_maint_costs(session, rec)

    assert rec.parts_cost == 2400.0 and rec.labor_cost == 500.0 and rec.other_cost == 1200.0
    assert rec.discount == 0.0 and rec.vat == 0.0
    assert rec.total_cost == 4100.0


def test_manual_costs_no_lines_keep_zero_discount(session):
    """บันทึกเก่าที่คีย์ยอดมือ ไม่มีบรรทัด → ห้ามแตะ discount/vat/total."""
    rec = _rec(session, no="M000003", parts_cost=1200.0, labor_cost=800.0, total_cost=2000.0)
    appmod._recompute_maint_costs(session, rec)
    assert rec.parts_cost == 1200.0 and rec.labor_cost == 800.0
    assert rec.discount == 0.0 and rec.vat == 0.0 and rec.total_cost == 2000.0


def test_migration_adds_columns_and_unique_index(session):
    with engine.begin() as conn:
        part_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(maintpart)")]
        rec_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(maintrecord)")]
        idx = [r[1] for r in conn.exec_driver_sql("PRAGMA index_list(maintrecord)")]
    assert "discount" in part_cols and "vat" in part_cols
    assert {"discount", "vat", "import_key"} <= set(rec_cols)
    assert "ux_maintrecord_import_key" in idx


def test_import_key_unique_but_blank_allowed(session):
    """บันทึกที่คนคีย์เอง (import_key='') มีได้หลายแถว; คีย์ที่ import ห้ามซ้ำ."""
    from sqlalchemy.exc import IntegrityError

    session.add(MaintRecord(record_no="M100", work_date=date(2024, 1, 1), import_key=""))
    session.add(MaintRecord(record_no="M101", work_date=date(2024, 1, 1), import_key=""))
    session.commit()
    session.add(MaintRecord(record_no="M102", work_date=date(2024, 1, 1), import_key="rm:lcb:abc"))
    session.commit()
    session.add(MaintRecord(record_no="M103", work_date=date(2024, 1, 1), import_key="rm:lcb:abc"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
