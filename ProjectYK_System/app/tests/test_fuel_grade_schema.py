from sqlmodel import Session
from db_config import engine
from models import FuelTxn
from datetime import date
import sqlalchemy as sa


def test_fueltxn_has_fuel_grade_column(client):
    # client fixture creates schema and calls init_db(); just verify the column exists
    insp = sa.inspect(engine)
    cols = {c["name"] for c in insp.get_columns("fueltxn")}
    assert "fuel_grade" in cols


def test_fueltxn_fuel_grade_roundtrip(client):
    with Session(engine) as s:
        row = FuelTxn(txn_date=date(2026, 6, 1), site_code="LCB",
                      plate_no_raw="ZZ-TEST-GRADE", liter=50, amount=1760,
                      fuel_grade="B20", source="test")
        s.add(row)
        s.commit()
        rid = row.id
    with Session(engine) as s:
        got = s.get(FuelTxn, rid)
        assert got.fuel_grade == "B20"
        s.delete(got)
        s.commit()


def test_fuel_grade_defaults_blank(client):
    with Session(engine) as s:
        row = FuelTxn(txn_date=date(2026, 6, 1), site_code="LCB",
                      plate_no_raw="ZZ-TEST-DEFAULT", liter=10, amount=350,
                      source="test")
        s.add(row)
        s.commit()
        rid = row.id
    with Session(engine) as s:
        got = s.get(FuelTxn, rid)
        assert got.fuel_grade == ""
        s.delete(got)
        s.commit()
