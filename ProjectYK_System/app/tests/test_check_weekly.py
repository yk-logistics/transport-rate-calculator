import json
from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle, DriverSubmission
import services.access_link as al


def _driver_link_with_vehicle():
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="driver", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-9999", vehicle_kind="head", truck_type="6W")
        s.add(v); s.commit(); s.refresh(v)
        return tok, v.id


def test_weekly_check_creates_submission_with_actor(client):
    tok, vid = _driver_link_with_vehicle()
    data = {"t": tok, "actor_name": "สมหญิง", "vehicle_id": str(vid), "mile": "50000",
            "weekly": "1", "item_oil_level": "ok", "item_coolant": "fail"}
    r = client.post(f"/check/driver?t={tok}", data=data, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        sub = s.exec(select(DriverSubmission).where(
            DriverSubmission.kind == "vehicle_check")).first()
        assert sub is not None
        assert sub.employee_id is None
        payload = json.loads(sub.data_json)
        assert payload["actor_name"] == "สมหญิง"
        assert sub.review_status == "flagged"   # coolant=fail
