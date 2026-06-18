from sqlmodel import Session, select
from db_config import engine
from models import PettyCashTxn

TOKEN = "test-ingest-token"


def _payload(**over):
    p = dict(slip_line_message_id="618000000000000010", site_code="LCB",
             txn_date="2026-06-16", amount=1280.0, direction="out",
             category="other", requester_raw="ปกรณ์", memo="ปกรณ์ คืนตู้",
             slip_media_path="Cabc\\2026-06\\x.jpg", slip_ref_code="REF123",
             parsed_confidence=0.9, parsed_payload_json="{}")
    p.update(over)
    return p


def test_ingest_creates_pending_entry(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    r = client.post("/api/petty/ingest", json=_payload(),
                    headers={"X-Service-Token": TOKEN})
    assert r.status_code == 200 and r.json()["status"] == "created"
    with Session(engine) as s:
        row = s.exec(select(PettyCashTxn).where(
            PettyCashTxn.slip_line_message_id == "618000000000000010")).first()
    assert row.status == "pending_review" and row.source == "line_slip"
    assert row.site_code == "LCB" and row.amount == 1280.0


def test_ingest_is_idempotent(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    h = {"X-Service-Token": TOKEN}
    r1 = client.post("/api/petty/ingest", json=_payload(), headers=h)
    r2 = client.post("/api/petty/ingest", json=_payload(), headers=h)
    assert r2.json()["status"] == "duplicate" and r2.json()["id"] == r1.json()["id"]
    with Session(engine) as s:
        n = len(s.exec(select(PettyCashTxn).where(
            PettyCashTxn.slip_line_message_id == "618000000000000010")).all())
    assert n == 1


def test_ingest_rejects_bad_token(client, monkeypatch):
    monkeypatch.setenv("YK_SLIP_INGEST_TOKEN", TOKEN)
    r = client.post("/api/petty/ingest", json=_payload(),
                    headers={"X-Service-Token": "wrong"})
    assert r.status_code == 401
