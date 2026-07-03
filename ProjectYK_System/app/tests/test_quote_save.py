"""B2 เซฟใบเสนอราคา: เครื่องคิด /quote sync ผ่านโปรโตคอล Drive-sync เดิมของไฟล์
(POST {action:'save', payload:{records}} / GET ?action=load) → ตาราง Quotation
+ หน้า /quote/list ค้นหา + แก้สถานะ/ราคาต่อรอง (QuotationAudit insert-only)
"""
import json, os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, Quotation, QuotationAudit


def _rec(rid, customer, job, km=100.0, price=5500.0, toll=250.0):
    return {
        "id": rid, "customerName": customer, "jobName": job,
        "tags": "", "note": "โน้ต" + rid, "savedAt": "2026-07-03T10:00:00.000Z",
        "snapshot": {
            "fieldValues": {
                "tollCost": str(toll), "customerPrice": "0",
                "mapsOriginPreset": "13.065831297727314,100.88241036968732",
                "mapsDestinationLink": "https://maps.app.goo.gl/x" + rid,
            },
            "routeSegments": [{"name": "ไป-กลับ", "distance": km}],
            "summary": {"totalDistance": km, "totalCost": 4000.0,
                        "totalCostWithFinance": 4100.0,
                        "suggested15AfterFinance": price,
                        "marginAfterFinancePct": 15.0},
        },
    }


def _sync(client, records):
    return client.post("/quote/sync", content=json.dumps(
        {"action": "save", "secret": "", "payload": {"records": records}}),
        headers={"Content-Type": "text/plain;charset=utf-8"})


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


def test_sync_save_maps_fields(client):
    r = _sync(client, [_rec("job_1", "KAO", "โรงงานบางปะกง", km=120.5),
                       _rec("job_2", "NHL", "ลานตู้")])
    assert r.status_code == 200 and r.json()["ok"] is True
    with Session(engine) as s:
        q = {x.record_id: x for x in s.exec(select(Quotation)).all()}
        assert set(q) == {"job_1", "job_2"}
        a = q["job_1"]
        assert a.customer_name == "KAO" and a.factory_name == "โรงงานบางปะกง"
        assert a.km_round == 120.5 and a.toll_cost == 250.0
        assert a.price_offered == 5500.0 and a.origin_site == "LCB"
        assert a.location_url.startswith("https://maps.app.goo.gl/")
        assert a.status == "draft"


def test_sync_load_roundtrip(client):
    recs = [_rec("job_1", "KAO", "โรงงาน")]
    _sync(client, recs)
    r = client.get("/quote/sync?action=load&secret=")
    got = r.json()["records"]
    assert got == recs  # โหลดกลับเครื่องคิดได้ค่าเดิมครบ (เกณฑ์ผ่าน B2)


def test_resync_updates_and_archives_missing(client):
    _sync(client, [_rec("job_1", "KAO", "โรงงาน"), _rec("job_2", "NHL", "ลาน")])
    _sync(client, [_rec("job_1", "KAO", "โรงงานใหม่", km=200.0)])  # job_2 หายไป
    with Session(engine) as s:
        q = {x.record_id: x for x in s.exec(select(Quotation)).all()}
        assert q["job_1"].factory_name == "โรงงานใหม่" and q["job_1"].km_round == 200.0
        assert q["job_2"].status == "archived"
    got = client.get("/quote/sync?action=load").json()["records"]
    assert [g["id"] for g in got] == ["job_1"]


def test_list_page_and_search(client):
    _sync(client, [_rec("job_1", "KAO", "โรงงานบางปะกง"), _rec("job_2", "NHL", "ลานตู้")])
    b = client.get("/quote/list").text
    assert "KAO" in b and "NHL" in b
    b = client.get("/quote/list?q=บางปะกง").text
    assert "KAO" in b and "NHL" not in b


def test_status_price_agreed_audit_two_rows(client):
    _sync(client, [_rec("job_1", "KAO", "โรงงาน")])
    with Session(engine) as s:
        qid = s.exec(select(Quotation)).first().id
    client.post(f"/quote/{qid}/status",
                data={"status": "negotiating", "price_agreed": "5300"})
    client.post(f"/quote/{qid}/status",
                data={"status": "agreed", "price_agreed": "5200"})
    with Session(engine) as s:
        qq = s.get(Quotation, qid)
        assert qq.status == "agreed" and qq.price_agreed == 5200.0
        audits = s.exec(select(QuotationAudit).where(
            QuotationAudit.quotation_id == qid)).all()
        price_changes = [a for a in audits if a.field_name == "price_agreed"]
        assert len(price_changes) == 2  # แก้ราคา 2 ครั้ง = ประวัติ 2 แถว
    b = client.get(f"/quote/{qid}").text
    assert "5,200" in b and "ประวัติ" in b


def test_quote_page_injects_sync_bootstrap(client):
    b = client.get("/quote").text
    assert "yk-quote-sync-bootstrap" in b and "/quote/sync" in b


def test_quote_admin_only():
    import permissions
    assert permissions.check("admin", "/quote/sync", "POST") == "edit"
    for role in ("office", "accountant", "viewer"):
        assert permissions.check(role, "/quote/sync", "GET") == "deny"
