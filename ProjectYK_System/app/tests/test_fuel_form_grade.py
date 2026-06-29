from sqlmodel import Session, delete, select
from db_config import engine
from models import FuelTxn, AppUser
from auth import hash_password


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_post_fuel_new_saves_grade(client):
    _login_admin(client)
    resp = client.post("/fuel/new", data={
        "txn_date": "2026-06-03", "site_code": "LCB", "plate_no_raw": "ZZ-FF-1",
        "liter": "50", "amount": "1760", "fuel_grade": "B20",
    }, follow_redirects=False)
    assert resp.status_code == 303
    with Session(engine) as s:
        row = s.exec(select(FuelTxn).where(FuelTxn.plate_no_raw == "ZZ-FF-1")).first()
        assert row is not None
        assert row.fuel_grade == "B20"
        s.exec(delete(FuelTxn).where(FuelTxn.plate_no_raw == "ZZ-FF-1"))
        s.commit()


def test_fuel_row_json_includes_grade(client):
    # _fuel_row_json เป็น closure ใน fuel_list — ตรวจผ่าน GET /fuel ว่า rows_json มี key
    _login_admin(client)
    with Session(engine) as s:
        s.add(FuelTxn(txn_date=__import__("datetime").date(2026, 6, 3), site_code="LCB",
                      plate_no_raw="ZZ-FJ-1", liter=50, amount=1760, fuel_grade="B7",
                      source="test_ffjson"))
        s.commit()
    resp = client.get("/fuel?plate=ZZ-FJ-1")
    assert resp.status_code == 200
    assert "fuel_grade" in resp.text
    with Session(engine) as s:
        s.exec(delete(FuelTxn).where(FuelTxn.source == "test_ffjson"))
        s.commit()
