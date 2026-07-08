"""Tire 'stop the bleed' feature — bill entry + lifecycle/cost report.

Covers design spec 2026-07-08 success criteria 2–5:
  - new model fields (tire_type, removal_reason, reason_code) + constants
  - bill entry route creates Tire+mount event+MaintRecord+MaintPart, unmounts old
  - lifecycle report aggregates cost by reason and compares retread vs new
  - missing odometer must not break the report (km column blank for that tire)
"""
from datetime import date

from sqlmodel import Session, select

from db_config import engine
import models
from models import Tire, TireEvent, Vehicle, MaintRecord, MaintPart, AppUser
from auth import hash_password
import services.tire_view as tv


def _login_admin(client):
    """Office pages require auth; log in as yk1 with a deterministic password."""
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})


# ---------------------------------------------------------------------------
# Constants & schema
# ---------------------------------------------------------------------------

def test_tire_type_constants_exist():
    codes = {c for c, _ in models.TIRE_TYPES}
    assert {"new", "retread", "used"} <= codes


def test_removal_reason_constants_exist():
    codes = {c for c, _ in models.TIRE_REMOVAL_REASONS}
    # the four the user explicitly named + the retread-send workflow
    assert {"burst", "wire", "worn", "retread_send"} <= codes


def test_tire_has_type_and_removal_reason_fields(client):
    with Session(engine) as s:
        t = Tire(code="TT001", spec="11R22.5", status="new",
                 tire_type="retread", removal_reason="")
        s.add(t); s.commit(); s.refresh(t)
        assert t.tire_type == "retread"
        assert t.removal_reason == ""


def test_tireevent_has_reason_code_field(client):
    with Session(engine) as s:
        t = Tire(code="TT002", spec="11R22.5", status="in_use")
        s.add(t); s.commit(); s.refresh(t)
        ev = TireEvent(tire_id=t.id, event_date=date(2026, 7, 1),
                       event_type="unmount", reason_code="burst")
        s.add(ev); s.commit(); s.refresh(ev)
        assert ev.reason_code == "burst"


# ---------------------------------------------------------------------------
# Lifecycle report (services.tire_view.tire_lifecycle_report)
# ---------------------------------------------------------------------------

def _mount(s, tire, veh_id, pos, d, mile):
    s.add(TireEvent(tire_id=tire.id, event_date=d, event_type="mount",
                    to_vehicle_id=veh_id, to_position=pos, mile=mile))


def _remove(s, tire, veh_id, pos, d, mile, reason):
    s.add(TireEvent(tire_id=tire.id, event_date=d, event_type="scrap",
                    from_vehicle_id=veh_id, from_position=pos, mile=mile,
                    reason_code=reason))


def test_lifecycle_compares_new_vs_retread_by_days_and_km(client):
    """A 'new' tyre lasting 300 days/60000km vs a 'retread' lasting 100 days/20000km."""
    with Session(engine) as s:
        v = Vehicle(plate_no="70-1000", truck_type="10W"); s.add(v); s.commit(); s.refresh(v)

        new = Tire(code="TN01", tire_type="new", status="scrapped", purchase_price=9000.0)
        rt = Tire(code="TR01", tire_type="retread", status="scrapped", purchase_price=3000.0)
        s.add(new); s.add(rt); s.commit(); s.refresh(new); s.refresh(rt)

        _mount(s, new, v.id, "FL", date(2025, 1, 1), 100000.0)
        _remove(s, new, v.id, "FL", date(2025, 10, 28), 160000.0, "worn")  # 300 days, 60000 km
        _mount(s, rt, v.id, "FR", date(2025, 1, 1), 100000.0)
        _remove(s, rt, v.id, "FR", date(2025, 4, 11), 120000.0, "worn")    # 100 days, 20000 km
        s.commit()

        rep = tv.tire_lifecycle_report(s)
        by_type = {r["tire_type"]: r for r in rep["by_type"]}

        assert by_type["new"]["count"] == 1
        assert by_type["new"]["avg_days"] == 300
        assert by_type["new"]["avg_km"] == 60000
        # baht per 1000km = 9000 / (60000/1000) = 150
        assert round(by_type["new"]["baht_per_1000km"], 2) == 150.0
        # baht per month = 9000 / (300/30) = 900
        assert round(by_type["new"]["baht_per_month"], 2) == 900.0

        assert by_type["retread"]["avg_days"] == 100
        assert by_type["retread"]["avg_km"] == 20000
        assert round(by_type["retread"]["baht_per_1000km"], 2) == 150.0  # 3000/(20000/1000)


def test_lifecycle_missing_mile_still_counts_days(client):
    """A tyre removed without an odometer reading contributes to avg_days but not avg_km."""
    with Session(engine) as s:
        v = Vehicle(plate_no="70-1001", truck_type="10W"); s.add(v); s.commit(); s.refresh(v)
        t = Tire(code="TN02", tire_type="new", status="scrapped", purchase_price=8000.0)
        s.add(t); s.commit(); s.refresh(t)
        _mount(s, t, v.id, "FL", date(2025, 1, 1), 0.0)     # no mile
        _remove(s, t, v.id, "FL", date(2025, 4, 1), 0.0, "burst")  # 90 days, no mile
        s.commit()

        rep = tv.tire_lifecycle_report(s)
        by_type = {r["tire_type"]: r for r in rep["by_type"]}
        assert by_type["new"]["avg_days"] == 90
        assert by_type["new"]["km_sample"] == 0      # no tyre had both miles
        assert by_type["new"]["avg_km"] is None      # cannot compute -> None, not crash


def test_lifecycle_reason_breakdown(client):
    with Session(engine) as s:
        v = Vehicle(plate_no="70-1002", truck_type="10W"); s.add(v); s.commit(); s.refresh(v)
        a = Tire(code="TA1", tire_type="new", status="scrapped", purchase_price=9000.0)
        b = Tire(code="TB1", tire_type="new", status="scrapped", purchase_price=9000.0)
        c = Tire(code="TC1", tire_type="new", status="scrapped", purchase_price=5000.0)
        for t in (a, b, c):
            s.add(t)
        s.commit()
        for t in (a, b, c):
            s.refresh(t)
        _mount(s, a, v.id, "FL", date(2025, 1, 1), 0.0); _remove(s, a, v.id, "FL", date(2025, 2, 1), 0.0, "burst")
        _mount(s, b, v.id, "FR", date(2025, 1, 1), 0.0); _remove(s, b, v.id, "FR", date(2025, 2, 1), 0.0, "burst")
        _mount(s, c, v.id, "RLO1", date(2025, 1, 1), 0.0); _remove(s, c, v.id, "RLO1", date(2025, 2, 1), 0.0, "worn")
        s.commit()

        rep = tv.tire_lifecycle_report(s)
        by_reason = {r["reason_code"]: r for r in rep["by_reason"]}
        assert by_reason["burst"]["count"] == 2
        assert by_reason["burst"]["cost"] == 18000.0
        assert by_reason["worn"]["count"] == 1
        # ordered most-frequent first
        assert rep["by_reason"][0]["reason_code"] == "burst"


# ---------------------------------------------------------------------------
# Bill entry route (POST /maint/tires/bill)
# ---------------------------------------------------------------------------

def test_bill_entry_creates_tire_event_maint_and_part(client):
    _login_admin(client)
    with Session(engine) as s:
        v = Vehicle(plate_no="70-2000", truck_type="10W"); s.add(v); s.commit(); s.refresh(v)
        vid = v.id

    form = {
        "vehicle_id": str(vid),
        "work_date": "2026-07-08",
        "mechanic_name": "ช่างA",
        "paid_by": "cash",
        "receipt_ref": "R-001",
        # no mile on purpose
        "row_count": "2",
        "pos_0": "FL", "type_0": "new", "brand_0": "Bridgestone", "model_0": "R150",
        "price_0": "9000", "reason_0": "burst",
        "pos_1": "FR", "type_1": "retread", "brand_1": "หล่อ", "model_1": "X",
        "price_1": "3000", "reason_1": "worn",
    }
    r = client.post("/maint/tires/bill", data=form, follow_redirects=False)
    assert r.status_code in (302, 303)

    with Session(engine) as s:
        tires = s.exec(select(Tire).where(Tire.current_vehicle_id == vid)).all()
        assert len(tires) == 2
        types = sorted(t.tire_type for t in tires)
        assert types == ["new", "retread"]

        recs = s.exec(select(MaintRecord).where(MaintRecord.vehicle_id == vid)).all()
        assert len(recs) == 1
        rec = recs[0]
        assert rec.kind == "tire_change"
        assert round(rec.parts_cost, 2) == 12000.0
        assert round(rec.total_cost, 2) == 12000.0

        parts = s.exec(select(MaintPart).where(MaintPart.maint_record_id == rec.id)).all()
        assert len(parts) == 2
        assert all(p.tire_id is not None for p in parts)

        # mount events carry the reason of the replacement
        evs = s.exec(select(TireEvent).where(TireEvent.event_type == "mount")).all()
        assert len(evs) == 2


def test_bill_entry_unmounts_existing_tire_at_position(client):
    _login_admin(client)
    with Session(engine) as s:
        v = Vehicle(plate_no="70-2001", truck_type="10W"); s.add(v); s.commit(); s.refresh(v)
        vid = v.id
        old = Tire(code="TOLD", tire_type="new", status="in_use",
                   current_vehicle_id=vid, current_position="FL")
        s.add(old); s.commit(); s.refresh(old)
        old_id = old.id

    form = {
        "vehicle_id": str(vid), "work_date": "2026-07-08", "paid_by": "cash",
        "row_count": "1",
        "pos_0": "FL", "type_0": "new", "brand_0": "B", "model_0": "R",
        "price_0": "9000", "reason_0": "worn",
    }
    r = client.post("/maint/tires/bill", data=form, follow_redirects=False)
    assert r.status_code in (302, 303)

    with Session(engine) as s:
        old = s.get(Tire, old_id)
        # displaced: no longer mounted, carries removal reason
        assert old.current_position == ""
        assert old.status in ("stored", "scrapped")
        assert old.removal_reason == "worn"
        # a new tyre now sits at FL
        at_fl = s.exec(select(Tire).where(
            Tire.current_vehicle_id == vid, Tire.current_position == "FL")).all()
        assert len(at_fl) == 1
        assert at_fl[0].id != old_id


def test_displaced_old_tyre_unmount_event_carries_reason(client):
    """The old tyre's unmount event (history) must record why it came off,
    so its lifecycle reason is auditable from the event trail, not only the Tire."""
    _login_admin(client)
    with Session(engine) as s:
        v = Vehicle(plate_no="70-2002", truck_type="10W"); s.add(v); s.commit(); s.refresh(v)
        vid = v.id
        old = Tire(code="TOLD2", tire_type="new", status="in_use",
                   current_vehicle_id=vid, current_position="FL", purchase_price=9000.0)
        s.add(old); s.commit(); s.refresh(old)
        old_id = old.id

    form = {
        "vehicle_id": str(vid), "work_date": "2026-07-08", "paid_by": "cash",
        "row_count": "1",
        "pos_0": "FL", "type_0": "retread", "brand_0": "หล่อ", "model_0": "X",
        "price_0": "3000", "reason_0": "burst",
    }
    client.post("/maint/tires/bill", data=form, follow_redirects=False)

    with Session(engine) as s:
        unmount = s.exec(select(TireEvent).where(
            TireEvent.tire_id == old_id,
            TireEvent.event_type == "unmount",
        ).order_by(TireEvent.id.desc())).first()
        assert unmount is not None
        assert unmount.reason_code == "burst"


def test_report_page_renders(client):
    _login_admin(client)
    # must resolve to the report route itself (not fall through to /tires/{id})
    r = client.get("/maint/tires/report", follow_redirects=False)
    assert r.status_code == 200
    assert "รายงานความคุ้มยาง" in r.text


def test_bill_page_renders(client):
    _login_admin(client)
    with Session(engine) as s:
        v = Vehicle(plate_no="70-3000", truck_type="10W"); s.add(v); s.commit()
    r = client.get("/maint/tires/bill", follow_redirects=False)
    assert r.status_code == 200
    assert "คีย์บิลยาง" in r.text
