from sqlmodel import Session
from db_config import engine
from models import PettyCashTxn
from datetime import date


def test_pettycashtxn_has_slip_provenance_fields(client):
    # client fixture created the schema; insert a row using the new fields
    with Session(engine) as s:
        t = PettyCashTxn(
            txn_date=date(2026, 6, 16), site_code="LCB",
            amount=1280.0, status="pending_review", source="line_slip",
            slip_line_message_id="618000000000000001",
            slip_media_path="Cabc\\2026-06\\618000000000000001.jpg",
            slip_ref_code="202606160OcVl6K2",
        )
        s.add(t); s.commit(); s.refresh(t)
        assert t.id is not None
        assert t.slip_line_message_id == "618000000000000001"
        assert t.status == "pending_review"
