"""Daily grid exposes ALL sheet columns: company-reserve fees (lift/yard/clean/
shore/port_entry/weighing/mflow) as read-only, plus new ref fields
(phone/shared_vehicle/receive_inv_no/bl_booking/fuel_date/gps_rate) editable.
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import DailyJob, DailyJobFee, AppUser


@pytest.fixture()
def seeded():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()  # runs additive migrations → v30 columns
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        job = DailyJob(site_code="LCB", work_date=date(2026, 6, 1),
                       driver_raw_name="ทดสอบ", plate_no_raw="72-0420",
                       revenue_customer=5000, trip_fee_driver=350,
                       phone="081-2345678", shared_vehicle="71-8888",
                       receive_inv_no="RC-1", bl_booking="BL-9",
                       fuel_date=date(2026, 6, 1), gps_rate=12.5)
        s.add(job); s.commit(); s.refresh(job)
        # company-reserve fees + a driver fee
        for ft, amt in [("lift", 300), ("yard", 80), ("clean", 50), ("shore", 40),
                        ("port_entry", 110), ("ค่าชั่งน้ำหนัก", 25), ("mflow", 15),
                        ("special", 100)]:
            s.add(DailyJobFee(daily_job_id=job.id, fee_type=ft, amount=amt))
        s.commit()
        jid = job.id
    return jid


def test_grid_data_has_company_fees_and_ref_fields(seeded):
    res = appmod.daily_grid_data(site="LCB", d_from="2026-06-01", d_to="2026-06-01", limit=0)
    it = {r["id"]: r for r in res["items"]}[seeded]
    # company reserve fees
    assert it["fee_lift"] == 300
    assert it["fee_yard"] == 80
    assert it["fee_clean"] == 50
    assert it["fee_shore"] == 40
    assert it["fee_port_entry"] == 110
    assert it["fee_weighing"] == 25      # ค่าชั่งน้ำหนัก aliased
    assert it["fee_mflow"] == 15
    # driver fee still separate + correct
    assert it["fee_special"] == 100
    # new ref fields
    assert it["phone"] == "081-2345678"
    assert it["shared_vehicle"] == "71-8888"
    assert it["receive_inv_no"] == "RC-1"
    assert it["bl_booking"] == "BL-9"
    assert it["fuel_date"] == "2026-06-01"
    assert it["gps_rate"] == 12.5


def test_grid_save_roundtrips_new_editable_fields(seeded):
    with _client() as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        r = c.post("/api/daily/grid-save", json={"rows": [{
            "id": seeded, "phone": "099-9", "gps_rate": "20", "fuel_date": "2026-06-05",
            "shared_vehicle": "71-7777", "receive_inv_no": "RC-2", "bl_booking": "BL-2",
        }]})
        assert r.status_code == 200
        assert r.json()["ok"] is True
    with Session(engine) as s:
        row = s.get(DailyJob, seeded)
        assert row.phone == "099-9"
        assert row.gps_rate == 20
        assert row.fuel_date == date(2026, 6, 5)
        assert row.shared_vehicle == "71-7777"


def _client():
    from starlette.testclient import TestClient
    return TestClient(appmod.app)
