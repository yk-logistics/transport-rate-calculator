"""revenue_breakdown: CFO drill-down ไซต์→ลูกค้า→รถ. revenue = revenue_customer.
ลูกค้า = status_code, รถ = plate_no_raw. ผลรวมต้องไม่ตกหล่น/นับซ้ำ.
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import DailyJob, AppUser
from services.finance import revenue_breakdown

START, END = date(2026, 6, 1), date(2026, 6, 30)


@pytest.fixture()
def seeded():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()  # seed yk1 user for route test
    with Session(engine) as s:
        # LCB: KLND (รถ A 1000 + รถ B 500), CJ (รถ A 300)
        s.add(DailyJob(site_code="LCB", work_date=date(2026,6,2), status_code="KLND", plate_no_raw="72-0001", revenue_customer=1000))
        s.add(DailyJob(site_code="LCB", work_date=date(2026,6,3), status_code="KLND", plate_no_raw="72-0002", revenue_customer=500))
        s.add(DailyJob(site_code="LCB", work_date=date(2026,6,4), status_code="CJ",   plate_no_raw="72-0001", revenue_customer=300))
        # LCB: รถจอด ไม่มีราคา (นับ trip แต่ rows_no_price)
        s.add(DailyJob(site_code="LCB", work_date=date(2026,6,5), status_code="รถจอด", plate_no_raw="72-0001", revenue_customer=0))
        # นอกช่วง — ต้องไม่ถูกนับ
        s.add(DailyJob(site_code="LCB", work_date=date(2026,5,1), status_code="KLND", plate_no_raw="72-0001", revenue_customer=9999))
        s.commit()
    yield


def test_totals_no_leak(seeded):
    r = revenue_breakdown(Session(engine), START, END)
    # 1000+500+300+0 = 1800 (9999 นอกช่วงไม่นับ)
    assert r["totals"]["revenue"] == 1800
    assert r["totals"]["trips"] == 4
    assert r["totals"]["rows_no_price"] == 1


def test_nesting_and_sort(seeded):
    r = revenue_breakdown(Session(engine), START, END)
    sites = r["sites"]
    assert len(sites) == 1 and sites[0]["site"] == "LCB"
    lcb = sites[0]
    assert lcb["revenue"] == 1800
    assert lcb["rows_priced"] == 3 and lcb["rows_no_price"] == 1
    custs = {c["customer"]: c for c in lcb["customers"]}
    # KLND=1500, CJ=300, รถจอด=0 ; เรียงมาก→น้อย
    assert lcb["customers"][0]["customer"] == "KLND"
    assert custs["KLND"]["revenue"] == 1500
    assert custs["CJ"]["revenue"] == 300
    # รถใน KLND: A=1000, B=500
    veh = {v["plate"]: v for v in custs["KLND"]["vehicles"]}
    assert veh["72-0001"]["revenue"] == 1000
    assert veh["72-0002"]["revenue"] == 500
    # percentages
    assert custs["KLND"]["pct_of_site"] == round(1500/1800*100, 1)
    assert veh["72-0001"]["pct_of_customer"] == round(1000/1500*100, 1)


def test_site_filter(seeded):
    r = revenue_breakdown(Session(engine), START, END, site="BIGC")
    assert r["sites"] == []
    assert r["totals"]["revenue"] == 0


def test_route_renders(seeded):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        r = c.get("/finance/revenue?from=2026-06-01&to=2026-06-30", follow_redirects=True)
        assert r.status_code == 200
        b = r.text
        assert "KLND" in b           # customer drill-down shows
        assert "72-0001" in b        # vehicle row shows
        assert "เฉพาะ LCB" in b      # coverage banner (no other sites)
