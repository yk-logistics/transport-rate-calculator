"""B3 ราคาไหลเข้าเดลี่/บิล: ใบเสนอ status=agreed → เสนอราคาให้แถวเดลี่ที่
ลูกค้า+ปลายทางตรง (เสนอ ไม่ auto-ทับ — คนคีย์กดรับต่อแถว จึงเขียน + ลง audit)
+ หน้า /billing เตือนแถวราคา≠ใบเสนอ. ห้ามแตะ engine เงินเดือน/trip_fee_driver.
"""
import os, tempfile
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
from models import AppUser, DailyJob, DailyJobAudit, Quotation

D = date(2026, 7, 10)
MONTH = "2026-07"


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Quotation(record_id="job_a", customer_name="KAO",
                        factory_name="โรงงานบางปะกง", status="agreed",
                        price_agreed=5200.0, price_offered=5500.0, raw_json="{}"))
        # ใบยัง draft — ต้องไม่ถูกเสนอ
        s.add(Quotation(record_id="job_b", customer_name="NHL",
                        factory_name="ลานตู้", status="draft",
                        price_offered=4000.0, raw_json="{}"))
        # j1: ตรงลูกค้า+ปลายทาง + ราคาว่าง → ต้องถูกเสนอ
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KAO",
                       plate_no_raw="70-0001", doc_no="J1",
                       destination="โรงงานบางปะกง อ.บางปะกง"))
        # j2: ลูกค้าตรง ปลายทางไม่ตรง → ไม่เสนอ
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KAO",
                       plate_no_raw="70-0002", doc_no="J2", destination="ท่าเรือ"))
        # j3: ปลายทางตรง ลูกค้าไม่ตรง → ไม่เสนอ
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="CJ",
                       plate_no_raw="70-0003", doc_no="J3",
                       destination="โรงงานบางปะกง"))
        # j4: ตรงทั้งคู่แต่มีราคาแล้ว (5,000 ≠ 5,200) → ไม่เสนอทับ แต่ /billing ต้องเตือน
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KAO",
                       plate_no_raw="70-0004", doc_no="J4",
                       destination="โรงงานบางปะกง", revenue_customer=5000.0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _ids(s):
    return {j.doc_no: j for j in s.exec(select(DailyJob)).all()}


def test_suggest_matches_customer_and_destination(client):
    r = client.get(f"/api/daily-jobs/quote-suggest?site=LCB&d_from=2026-07-01&d_to=2026-07-31")
    items = r.json()["items"]
    assert len(items) == 1
    it = items[0]
    assert it["price"] == 5200.0 and it["customer"] == "KAO"
    with Session(engine) as s:
        assert it["job_id"] == _ids(s)["J1"].id


def test_apply_writes_price_with_audit_not_touching_driver_fee(client):
    with Session(engine) as s:
        j1 = _ids(s)["J1"]
        q = s.exec(select(Quotation).where(Quotation.status == "agreed")).first()
    r = client.post("/api/daily-jobs/apply-quote",
                    json={"job_id": j1.id, "quote_id": q.id})
    assert r.status_code == 200 and r.json()["ok"] is True
    with Session(engine) as s:
        j1b = s.get(DailyJob, j1.id)
        assert j1b.revenue_customer == 5200.0
        assert j1b.trip_fee_driver == 0.0          # เงินคนขับห้ามขยับ
        audits = s.exec(select(DailyJobAudit).where(
            DailyJobAudit.daily_job_id == j1.id)).all()
        assert len(audits) == 1
        a = audits[0]
        assert a.action == "quote_apply" and a.field_name == "revenue_customer"
        assert a.old_value in ("0.0", "0") and a.new_value == "5200.0"


def test_apply_refuses_overwrite_and_mismatch_pair(client):
    with Session(engine) as s:
        j4 = _ids(s)["J4"]
        j2 = _ids(s)["J2"]
        q = s.exec(select(Quotation).where(Quotation.status == "agreed")).first()
    # แถวมีราคาแล้ว → ห้ามทับ
    r = client.post("/api/daily-jobs/apply-quote",
                    json={"job_id": j4.id, "quote_id": q.id})
    assert r.status_code == 409
    # แถวที่ match ไม่ผ่าน (ปลายทางไม่ตรง) → ปฏิเสธแม้ราคาว่าง
    r = client.post("/api/daily-jobs/apply-quote",
                    json={"job_id": j2.id, "quote_id": q.id})
    assert r.status_code == 409
    with Session(engine) as s:
        assert _ids(s)["J4"].revenue_customer == 5000.0
        assert _ids(s)["J2"].revenue_customer == 0.0


def test_billing_warns_price_mismatch(client):
    b = client.get(f"/billing?site=LCB&month={MONTH}").text
    # j4 ราคา 5,000 ≠ ใบเสนอ 5,200 → เตือนใต้ลูกค้า KAO (นอกจาก ราคาว่าง/ไม่มีเลขใบงาน)
    assert 'data-pricediff="1"' in b
    assert "ราคาไม่ตรงใบเสนอ" in b


def test_draft_quote_never_suggested(client):
    with Session(engine) as s:
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="NHL",
                       plate_no_raw="70-0009", doc_no="J9", destination="ลานตู้"))
        s.commit()
    items = client.get(
        f"/api/daily-jobs/quote-suggest?site=LCB&d_from=2026-07-01&d_to=2026-07-31"
    ).json()["items"]
    assert all(i["customer"] != "NHL" for i in items)
