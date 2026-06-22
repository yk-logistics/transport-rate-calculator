# Tire Inspection (Magic-Link) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let lowtech drivers (photo + condition) and mechanics (tread mm + tire jobs) record per-tire weekly inspections through expiring magic links — no login — building on the existing `Tire`/`TireEvent` model.

**Architecture:** New public route group `/check/*` gated by a signed, time-limited token (itsdangerous `URLSafeTimedSerializer`, already a dependency) instead of RBAC/login. Office generates links from an admin page. Driver flow writes per-tire `TireEvent(event_type="inspect")` rows with photos + a `condition_flag` and a blank tread (→ "awaiting mechanic"); mechanic flow fills tread mm on those rows and records mount/unmount/rotate/scrap jobs reusing the existing tire-event logic. Weekly fluid/equipment check reuses `DriverSubmission`.

**Tech Stack:** FastAPI + SQLModel, Jinja2 + HTMX + Tailwind (CDN), SQLite (dev) → PostgreSQL, itsdangerous for token signing, pytest + Starlette TestClient.

## Global Constraints

- Version pins (do NOT upgrade): `fastapi<0.115`, `starlette<0.40`.
- Schema migrations: no Alembic. Bump `main.py:SCHEMA_VERSION` AND add matching `_ensure_column(...)` calls in `_apply_additive_migrations()`. New tables are created by `SQLModel.metadata.create_all` automatically (no ALTER needed). Current `SCHEMA_VERSION = 20` → this plan moves it to **21**.
- New tables/columns must be additive — never drop or rewrite existing data.
- Tests live in `ProjectYK_System/app/tests/`. Run from `ProjectYK_System/app/` with the venv python so imports (`main`, `models`, `db_config`) resolve. The `client` fixture (conftest.py) builds a fresh throwaway SQLite schema + seed per test.
- Money rule: this feature does not touch payroll/billing, but it stores `mile`. Any handler that accepts a mile reading MUST warn (not block) when the new mile is less than the vehicle's last inspect mile.
- Driver/mechanic-facing copy is Thai. Position codes stay English in the DB; Thai labels are presentation-only via a mapping helper.
- Match existing route style in `main.py` (module-level `@app.get/post`, `with Session(engine) as s:`, `_parse_date/_parse_float/_parse_int`, `_gen_code`, `RedirectResponse(..., status_code=303)`).

## Run command (all tasks)

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/<file> -v
```

(On the dev machine the venv python is `.venv/Scripts/python.exe`. If a bare `pytest` is on PATH inside the venv, that works too.)

## File Structure

- `ProjectYK_System/app/models.py` — add `AccessLink` table; add fields to `TireEvent`; widen trailer position map; add Thai-label + outer/inner + role/condition constant tuples.
- `ProjectYK_System/app/services/access_link.py` — **new** — sign/verify magic-link tokens; thin wrapper over itsdangerous. Pure, no DB. One responsibility: token codec.
- `ProjectYK_System/app/services/tire_view.py` — **new** — presentation helpers: position→Thai label, outer/inner classification, required photo count, awaiting-mechanic query, distance-since-last. Pure functions + read queries. Keeps `main.py` thin.
- `ProjectYK_System/app/main.py` — migrations (`SCHEMA_VERSION`, `_ensure_column`); `PUBLIC_PREFIXES` add `/check`; admin gen-link route; `/check/*` route group (token gate, driver flow, mechanic flow).
- `ProjectYK_System/app/templates/` — new Jinja2 templates for gen-link (admin), check landing (name entry), driver tire grid, mechanic queue, tire-job form.
- `ProjectYK_System/app/tests/` — new test files per task.

---

### Task 1: `AccessLink` model + token codec

**Files:**
- Modify: `ProjectYK_System/app/models.py` (add `AccessLink` table near other Phase 4 tables; add `ACCESS_LINK_ROLES` tuple)
- Create: `ProjectYK_System/app/services/access_link.py`
- Test: `ProjectYK_System/app/tests/test_access_link.py`

**Interfaces:**
- Produces:
  - `class AccessLink(SQLModel, table=True)` with fields: `id: Optional[int]` (pk), `token: str` (index, unique), `role: str` (index, "driver"|"mechanic"), `created_by: str = ""`, `created_at: datetime`, `expires_at: datetime`, `revoked: bool = False` (index), `last_used_at: Optional[datetime] = None`, `use_count: int = 0`, `note: str = ""`.
  - `ACCESS_LINK_ROLES = (("driver","คนขับ"),("mechanic","ช่าง"))`
  - `access_link.make_token(role: str, ttl_seconds: int) -> str` — returns a signed token string encoding `{"role": role}`.
  - `access_link.read_token(token: str, max_age_seconds: int) -> dict | None` — returns the payload dict if signature valid and not older than `max_age_seconds`, else `None` (covers both bad signature and expiry).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_access_link.py
import time
from sqlmodel import Session
from db_config import engine
from models import AccessLink
from datetime import datetime, timedelta
import services.access_link as al


def test_make_and_read_token_roundtrip():
    tok = al.make_token("mechanic", ttl_seconds=3600)
    payload = al.read_token(tok, max_age_seconds=3600)
    assert payload is not None
    assert payload["role"] == "mechanic"


def test_read_token_rejects_expired():
    tok = al.make_token("driver", ttl_seconds=3600)
    # max_age 0 → anything older than 0s is rejected
    time.sleep(1)
    assert al.read_token(tok, max_age_seconds=0) is None


def test_read_token_rejects_tampered():
    tok = al.make_token("driver", ttl_seconds=3600)
    assert al.read_token(tok + "x", max_age_seconds=3600) is None


def test_accesslink_row_persists(client):
    with Session(engine) as s:
        link = AccessLink(
            token="abc.def.ghi", role="driver",
            created_by="yk1",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        s.add(link); s.commit(); s.refresh(link)
        assert link.id is not None
        assert link.revoked is False
        assert link.use_count == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_access_link.py -v`
Expected: FAIL — `ModuleNotFoundError: services.access_link` / `ImportError: AccessLink`.

- [ ] **Step 3: Add the model**

In `models.py`, after the `DriverSubmission` class (Phase 4 block), add:

```python
class AccessLink(SQLModel, table=True):
    """Signed, time-limited magic link for login-less data entry (driver | mechanic).

    The signed token is the source of truth for role + expiry; this row is for
    audit (who generated it, usage) and explicit revocation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    role: str = Field(default="driver", index=True)   # driver | mechanic
    created_by: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    revoked: bool = Field(default=False, index=True)
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    note: str = ""
```

And near the other constant tuples (e.g. after `REVIEW_STATUS`):

```python
ACCESS_LINK_ROLES = (
    ("driver",   "คนขับ"),
    ("mechanic", "ช่าง"),
)
```

- [ ] **Step 4: Add the token codec**

Create `ProjectYK_System/app/services/access_link.py`:

```python
"""Magic-link token codec. Signs a small payload (role) with the app session
secret so links can't be forged; expiry is enforced at read time via
itsdangerous max_age. No DB access here — pure sign/verify."""
import os

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

_SECRET = os.environ.get("YK_SESSION_SECRET", "dev-insecure-secret-change-me")
_SALT = "yk-access-link-v1"
_serializer = URLSafeTimedSerializer(_SECRET, salt=_SALT)


def make_token(role: str, ttl_seconds: int) -> str:
    # ttl_seconds is informational for the caller (used to set AccessLink.expires_at);
    # actual expiry is enforced in read_token via max_age_seconds.
    return _serializer.dumps({"role": role})


def read_token(token: str, max_age_seconds: int) -> dict | None:
    try:
        return _serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_access_link.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/services/access_link.py ProjectYK_System/app/tests/test_access_link.py
git commit -m "feat(tire-check): AccessLink model + signed magic-link token codec"
```

---

### Task 2: TireEvent fields + schema migration to v21

**Files:**
- Modify: `ProjectYK_System/app/models.py` (add fields to `TireEvent`)
- Modify: `ProjectYK_System/app/main.py` (`SCHEMA_VERSION` → 21; add `_ensure_column` calls)
- Test: `ProjectYK_System/app/tests/test_tire_event_schema.py`

**Interfaces:**
- Produces — new `TireEvent` columns:
  - `photo_paths: str = ""` — comma-separated relative paths (same convention as `DriverSubmission.photo_paths`)
  - `actor_name: str = ""` — name typed at link entry
  - `actor_role: str = ""` — "driver" | "mechanic" | "" (office)
  - `condition_flag: str = ""` — driver-reported before mechanic measures: "ok" | "near" | "problem" | ""
  - Constant `TIRE_CONDITION_FLAGS = (("ok","ปกติ"),("near","น่าจะใกล้หมด"),("problem","มีปัญหา (รั่ว/บวม/ฉีก)"))`
- Note: "awaiting mechanic" is **derived**, not a stored flag — an `inspect` event with `condition_flag != ""` and `tread_after_mm == 0`. (Implemented in Task 3.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tire_event_schema.py
from sqlmodel import Session
from db_config import engine
from models import TireEvent, Tire
from datetime import date


def test_tireevent_has_magiclink_fields(client):
    with Session(engine) as s:
        t = Tire(code="T9001", spec="11R22.5", status="in_use")
        s.add(t); s.commit(); s.refresh(t)
        ev = TireEvent(
            tire_id=t.id, event_date=date(2026, 6, 22), event_type="inspect",
            photo_paths="check/2026-06-22/abc.jpg,check/2026-06-22/def.jpg",
            actor_name="สมชาย", actor_role="driver",
            condition_flag="problem",
            tread_after_mm=0.0,
        )
        s.add(ev); s.commit(); s.refresh(ev)
        assert ev.id is not None
        assert ev.actor_role == "driver"
        assert ev.condition_flag == "problem"
        assert "abc.jpg" in ev.photo_paths
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_tire_event_schema.py -v`
Expected: FAIL — `TypeError`/`AttributeError` on unknown fields (the model has no `condition_flag`).

- [ ] **Step 3: Add the fields to TireEvent**

In `models.py`, inside `class TireEvent`, after `note: str = ""` add:

```python
    photo_paths: str = ""        # comma-separated relative paths (uploads root)
    actor_name: str = ""         # name typed at magic-link entry
    actor_role: str = ""         # driver | mechanic | "" (office)
    condition_flag: str = ""     # driver report: ok | near | problem | ""
```

Near the other tire constant tuples (after `TIRE_EVENT_TYPES`) add:

```python
TIRE_CONDITION_FLAGS = (
    ("ok",      "ปกติ"),
    ("near",    "น่าจะใกล้หมด"),
    ("problem", "มีปัญหา (รั่ว/บวม/ฉีก)"),
)
```

- [ ] **Step 4: Bump schema version + migration**

In `main.py`, set `SCHEMA_VERSION = 21`. In `_apply_additive_migrations()`, after the v20 petty-slip block, add:

```python
    # v20 → v21: TireEvent magic-link fields + AccessLink table (table via create_all).
    _ensure_column("tireevent", "photo_paths",    "TEXT", default="")
    _ensure_column("tireevent", "actor_name",     "TEXT", default="")
    _ensure_column("tireevent", "actor_role",     "TEXT", default="")
    _ensure_column("tireevent", "condition_flag", "TEXT", default="")
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_tire_event_schema.py -v`
Expected: PASS.

- [ ] **Step 6: Regression — full suite still green**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all existing tests still PASS (schema bump is additive).

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_tire_event_schema.py
git commit -m "feat(tire-check): TireEvent magic-link fields + schema v21"
```

---

### Task 3: Position labels, outer/inner, trailer 8-wheel map, view helpers

**Files:**
- Modify: `ProjectYK_System/app/models.py` (widen `TIRE_POSITIONS_BY_KIND["10WL"]` trailer entry to 8 wheels; add `TIRE_POSITION_TH` label map)
- Create: `ProjectYK_System/app/services/tire_view.py`
- Test: `ProjectYK_System/app/tests/test_tire_view.py`

**Interfaces:**
- Consumes: `models.TIRE_POSITIONS_BY_KIND`, `Tire`, `TireEvent`.
- Produces (in `services/tire_view.py`):
  - `th_label(pos: str) -> str` — Thai label for a position code; falls back to the raw code if unmapped.
  - `is_outer(pos: str) -> bool` — True for front singles (`FL`,`FR`) and any code ending in `O` (+ optional digit). Inner = ends in `I`.
  - `photo_count(pos: str) -> int` — 2 if outer, else 1.
  - `awaiting_mechanic(session) -> list[TireEvent]` — inspect events with `condition_flag != ""` and `tread_after_mm == 0`, newest first.
  - `distance_since_last(session, vehicle_id: int, current_mile: float) -> float` — `current_mile` minus the most recent prior inspect `mile` for that vehicle; 0 if none or negative.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tire_view.py
from sqlmodel import Session
from db_config import engine
from models import Tire, TireEvent
from datetime import date
import services.tire_view as tv
import models


def test_outer_inner_classification():
    assert tv.is_outer("FL") is True
    assert tv.is_outer("RRO1") is True
    assert tv.is_outer("RLI2") is False
    assert tv.is_outer("TRL_RO2") is True
    assert tv.is_outer("TRL_LI1") is False


def test_photo_count():
    assert tv.photo_count("RLO1") == 2
    assert tv.photo_count("RLI1") == 1


def test_th_label_known_and_fallback():
    assert tv.th_label("FL") == "ซ้ายหน้า"
    assert tv.th_label("ZZZ") == "ZZZ"


def test_trailer_has_eight_positions():
    assert len(models.TIRE_POSITIONS_BY_KIND["TRL8"]) == 8


def test_awaiting_mechanic_lists_only_unmeasured(client):
    with Session(engine) as s:
        t = Tire(code="T7001", spec="11R22.5", status="in_use")
        s.add(t); s.commit(); s.refresh(t)
        # driver report, no tread yet -> awaiting
        s.add(TireEvent(tire_id=t.id, event_date=date(2026,6,22),
                        event_type="inspect", condition_flag="ok", tread_after_mm=0.0))
        # already measured -> NOT awaiting
        s.add(TireEvent(tire_id=t.id, event_date=date(2026,6,22),
                        event_type="inspect", condition_flag="ok", tread_after_mm=7.5))
        s.commit()
        rows = tv.awaiting_mechanic(s)
        assert len(rows) == 1
        assert rows[0].tread_after_mm == 0.0


def test_distance_since_last(client):
    with Session(engine) as s:
        t = Tire(code="T7002", spec="11R22.5", status="in_use", current_vehicle_id=5)
        s.add(t); s.commit(); s.refresh(t)
        s.add(TireEvent(tire_id=t.id, event_date=date(2026,6,1),
                        event_type="inspect", to_vehicle_id=5, mile=100000.0))
        s.commit()
        assert tv.distance_since_last(s, 5, 103150.0) == 3150.0
        assert tv.distance_since_last(s, 5, 99000.0) == 0.0   # negative clamped
        assert tv.distance_since_last(s, 999, 5000.0) == 0.0  # no prior
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_tire_view.py -v`
Expected: FAIL — `services.tire_view` missing, `TRL8` key missing.

- [ ] **Step 3: Widen trailer map + add Thai labels**

In `models.py`, add an 8-wheel trailer entry and Thai label map. Append a new key (keep existing `10WL` untouched to avoid breaking the office setup grid):

```python
TIRE_POSITIONS_BY_KIND["TRL8"] = (
    "TRL_LO1", "TRL_LI1", "TRL_RI1", "TRL_RO1",   # เพลาหน้า: ซ้ายนอก ซ้ายใน ขวาใน ขวานอก
    "TRL_LO2", "TRL_LI2", "TRL_RI2", "TRL_RO2",   # เพลาหลัง
)

TIRE_POSITION_TH = {
    "FL": "ซ้ายหน้า", "FR": "ขวาหน้า",
    "RLO": "ซ้ายหลังนอก", "RLI": "ซ้ายหลังใน", "RRI": "ขวาหลังใน", "RRO": "ขวาหลังนอก",
    "RLO1": "ซ้ายหลังนอก (เพลาหน้า)", "RLI1": "ซ้ายหลังใน (เพลาหน้า)",
    "RRI1": "ขวาหลังใน (เพลาหน้า)", "RRO1": "ขวาหลังนอก (เพลาหน้า)",
    "RLO2": "ซ้ายหลังนอก (เพลาหลัง)", "RLI2": "ซ้ายหลังใน (เพลาหลัง)",
    "RRI2": "ขวาหลังใน (เพลาหลัง)", "RRO2": "ขวาหลังนอก (เพลาหลัง)",
    "TRL_LO1": "หาง ซ้ายนอก (เพลาหน้า)", "TRL_LI1": "หาง ซ้ายใน (เพลาหน้า)",
    "TRL_RI1": "หาง ขวาใน (เพลาหน้า)", "TRL_RO1": "หาง ขวานอก (เพลาหน้า)",
    "TRL_LO2": "หาง ซ้ายนอก (เพลาหลัง)", "TRL_LI2": "หาง ซ้ายใน (เพลาหลัง)",
    "TRL_RI2": "หาง ขวาใน (เพลาหลัง)", "TRL_RO2": "หาง ขวานอก (เพลาหลัง)",
}
```

- [ ] **Step 4: Add the view helpers**

Create `ProjectYK_System/app/services/tire_view.py`:

```python
"""Presentation + read helpers for the tire-check flows. No mutations."""
import re

from sqlmodel import Session, select

import models
from models import TireEvent


def th_label(pos: str) -> str:
    return models.TIRE_POSITION_TH.get((pos or "").upper(), pos)


def is_outer(pos: str) -> bool:
    p = (pos or "").upper()
    if p in ("FL", "FR"):
        return True
    # strip a trailing axle digit, then classify by O/I suffix
    base = re.sub(r"\d+$", "", p)
    if base.endswith("O"):
        return True
    if base.endswith("I"):
        return False
    return True  # singles / unknown default to outer (2 photos)


def photo_count(pos: str) -> int:
    return 2 if is_outer(pos) else 1


def awaiting_mechanic(session: Session) -> list[TireEvent]:
    rows = session.exec(
        select(TireEvent).where(
            TireEvent.event_type == "inspect",
            TireEvent.condition_flag != "",
            TireEvent.tread_after_mm == 0.0,
        ).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())
    ).all()
    return list(rows)


def distance_since_last(session: Session, vehicle_id: int, current_mile: float) -> float:
    prior = session.exec(
        select(TireEvent).where(
            TireEvent.event_type == "inspect",
            TireEvent.to_vehicle_id == vehicle_id,
            TireEvent.mile > 0,
        ).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())
    ).first()
    if not prior:
        return 0.0
    diff = current_mile - prior.mile
    return diff if diff > 0 else 0.0
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_tire_view.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/services/tire_view.py ProjectYK_System/app/tests/test_tire_view.py
git commit -m "feat(tire-check): Thai position labels, outer/inner, 8-wheel trailer, view helpers"
```

---

### Task 4: Admin gen-link route + token gate (public prefix)

**Files:**
- Modify: `ProjectYK_System/app/main.py` (add `/check` to `PUBLIC_PREFIXES`; add admin `GET/POST /admin/check-links`; add `_check_link_guard()` helper + `GET /check` landing)
- Create: `ProjectYK_System/app/templates/check_links_admin.html`, `ProjectYK_System/app/templates/check_landing.html`
- Test: `ProjectYK_System/app/tests/test_check_link_gate.py`

**Interfaces:**
- Consumes: `services.access_link` (`make_token`, `read_token`), `AccessLink`, `current_user`.
- Produces:
  - `LINK_MAX_AGE_DEFAULT = 3600` (module constant in main.py)
  - `_check_link_guard(request, session) -> AccessLink | None` — reads `?t=` (or path token), verifies signature+age via `read_token`, confirms the matching `AccessLink` row exists and is not revoked/expired; bumps `use_count`/`last_used_at`; returns the row or `None`.
  - Routes: `GET /admin/check-links` (admin form + list), `POST /admin/check-links` (create link, role + ttl hours), `GET /check?t=<token>` (landing → name entry, then redirects to `/check/driver` or `/check/mechanic`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_link_gate.py
from datetime import datetime, timedelta
from sqlmodel import Session
from db_config import engine
from models import AccessLink
import services.access_link as al


def _make_link(role="driver", hours=1):
    tok = al.make_token(role, ttl_seconds=hours * 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, created_by="test",
                         expires_at=datetime.utcnow() + timedelta(hours=hours)))
        s.commit()
    return tok


def test_check_landing_rejects_missing_token(client):
    r = client.get("/check", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_check_landing_rejects_unknown_token(client):
    r = client.get("/check?t=not-a-real-token", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_check_landing_accepts_valid_token(client):
    tok = _make_link("mechanic")
    r = client.get(f"/check?t={tok}", follow_redirects=False)
    assert r.status_code == 200
    assert "ช่าง" in r.text  # role shown on landing


def test_revoked_link_rejected(client):
    tok = _make_link("driver")
    with Session(engine) as s:
        link = s.exec(__import__("sqlmodel").select(AccessLink)).first()
        link.revoked = True
        s.add(link); s.commit()
    r = client.get(f"/check?t={tok}", follow_redirects=False)
    assert r.status_code in (400, 403)


def test_admin_can_create_link(client):
    # log in as seeded admin yk1 (must change pw first is fine for POST? -> use login helper)
    client.post("/login", data={"username": "yk1", "password": "changeme1"},
                follow_redirects=False)
    r = client.post("/admin/check-links", data={"role": "driver", "ttl_hours": "1"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        rows = s.exec(__import__("sqlmodel").select(AccessLink)).all()
        assert len(rows) == 1
        assert rows[0].role == "driver"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_link_gate.py -v`
Expected: FAIL — `/check` and `/admin/check-links` are 404 (or RBAC-redirected).

- [ ] **Step 3: Make `/check` public + add constant**

In `main.py`, add `/check` to `PUBLIC_PREFIXES` (the tuple near line 424):

```python
PUBLIC_PREFIXES = ("/login", "/logout", "/static/", "/uploads/", "/health", "/driver",
                   "/check", ...)   # keep existing entries; append "/check"
```

Add near other module constants:

```python
LINK_MAX_AGE_DEFAULT = 3600  # seconds; UI lets admin pick ttl in hours
```

- [ ] **Step 4: Add the guard helper + routes**

In `main.py` (tire section is fine), add:

```python
import services.access_link as access_link

def _check_link_guard(request: Request, session: Session):
    """Return the live AccessLink for a request's ?t= token, or None."""
    tok = request.query_params.get("t") or ""
    if not tok:
        return None
    payload = access_link.read_token(tok, max_age_seconds=7 * 24 * 3600)  # hard cap 7d
    if not payload:
        return None
    link = session.exec(select(AccessLink).where(AccessLink.token == tok)).first()
    if not link or link.revoked or link.expires_at < datetime.utcnow():
        return None
    link.use_count += 1
    link.last_used_at = datetime.utcnow()
    session.add(link); session.commit()
    return link


@app.get("/check", response_class=HTMLResponse)
def check_landing(request: Request):
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link:
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        role_th = dict(models.ACCESS_LINK_ROLES).get(link.role, link.role)
    return templates.TemplateResponse("check_landing.html", {
        "request": request, "token": request.query_params.get("t"),
        "role": link.role, "role_th": role_th,
    })


@app.get("/admin/check-links", response_class=HTMLResponse)
def admin_check_links(request: Request):
    u = current_user(request)
    with Session(engine) as s:
        links = s.exec(select(AccessLink).order_by(AccessLink.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse("check_links_admin.html", {
        "request": request, "links": links, "roles": models.ACCESS_LINK_ROLES, "user": u,
    })


@app.post("/admin/check-links")
async def admin_check_links_create(request: Request):
    u = current_user(request)
    form = await request.form()
    role = (form.get("role") or "driver").strip()
    ttl_hours = _parse_int(form.get("ttl_hours") or "1") or 1
    ttl_seconds = ttl_hours * 3600
    tok = access_link.make_token(role, ttl_seconds)
    with Session(engine) as s:
        s.add(AccessLink(
            token=tok, role=role, created_by=(u.username if u else ""),
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
        ))
        s.commit()
    return RedirectResponse("/admin/check-links", status_code=303)
```

Ensure `timedelta` is imported in `main.py` (add to the `from datetime import ...` line if absent).

- [ ] **Step 5: Add minimal templates**

Create `templates/check_landing.html` (extends nothing heavy — mirror existing driver templates; minimum needed for the test is that it renders `role_th`):

```html
<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ตรวจรถ</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-900 text-slate-100 p-5">
  <h1 class="text-lg font-bold mb-1">ตรวจรถ — บทบาท: {{ role_th }}</h1>
  <p class="text-sm text-slate-400 mb-4">พิมพ์ชื่อของคุณเพื่อเริ่ม</p>
  <form method="get" action="/check/{{ role }}">
    <input type="hidden" name="t" value="{{ token }}">
    <input name="actor_name" required placeholder="ชื่อ-สกุล"
           class="w-full p-3 rounded-lg bg-slate-800 border border-slate-600 mb-4">
    <button class="w-full p-3 rounded-lg bg-blue-600 font-bold">เริ่ม ▸</button>
  </form>
</body></html>
```

Create `templates/check_links_admin.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1 class="text-xl font-bold mb-3">สร้างลิงก์ตรวจรถ (Magic Link)</h1>
<form method="post" action="/admin/check-links" class="flex gap-2 items-end mb-5">
  <label>บทบาท
    <select name="role" class="border p-2 rounded">
      {% for code, th in roles %}<option value="{{ code }}">{{ th }}</option>{% endfor %}
    </select>
  </label>
  <label>อายุ (ชม.) <input name="ttl_hours" value="1" class="border p-2 rounded w-20"></label>
  <button class="bg-blue-600 text-white p-2 rounded">สร้างลิงก์</button>
</form>
<table class="w-full text-sm">
  <tr><th>บทบาท</th><th>หมดอายุ</th><th>ใช้</th><th>ลิงก์</th></tr>
  {% for l in links %}
  <tr class="{{ 'opacity-40' if l.revoked }}">
    <td>{{ l.role }}</td><td>{{ l.expires_at | dmy_hm }}</td><td>{{ l.use_count }}</td>
    <td><input class="border p-1 w-full text-xs" readonly value="/check?t={{ l.token }}"></td>
  </tr>
  {% endfor %}
</table>
{% endblock %}
```

(If `base.html` block name differs, match the real one — check an existing admin template like `account_password.html`.)

- [ ] **Step 6: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_link_gate.py -v`
Expected: PASS (5 tests). If `test_admin_can_create_link` fails on the login step, check the real login form field names in `tests/test_login.py` and align.

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/check_landing.html ProjectYK_System/app/templates/check_links_admin.html ProjectYK_System/app/tests/test_check_link_gate.py
git commit -m "feat(tire-check): admin gen-link + public /check token gate"
```

---

### Task 5: Driver flow — tire grid submit (photos + condition, no mm)

**Files:**
- Modify: `ProjectYK_System/app/main.py` (`GET /check/driver`, `POST /check/driver`)
- Create: `ProjectYK_System/app/templates/check_driver.html`
- Test: `ProjectYK_System/app/tests/test_check_driver.py`

**Interfaces:**
- Consumes: `_check_link_guard`, `services.tire_view` (`th_label`, `is_outer`, `photo_count`, `distance_since_last`), `Vehicle`, `Tire`, `TireEvent`, `_tire_positions_for_vehicle`, `driver_auth.save_photo`.
- Produces: one `TireEvent(event_type="inspect", actor_role="driver", condition_flag=<...>, tread_after_mm=0)` per submitted position, with `photo_paths` saved under a `check` kind. Mile recorded once per submit on each event's `mile`/`to_vehicle_id`. A mile-regression warning is surfaced (not blocking).
- Reuses `save_photo(emp_id, kind, bytes, ext)` with `emp_id=0` for link submissions (no employee). Photos land under `uploads/driver/0/<date>/check/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_driver.py
from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle, Tire, TireEvent
import services.access_link as al


def _driver_link():
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="driver", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-2345", vehicle_kind="head", truck_type="10W")
        s.add(v); s.commit(); s.refresh(v)
        vid = v.id
    return tok, vid


def test_driver_submit_creates_inspect_events_without_tread(client):
    tok, vid = _driver_link()
    data = {
        "t": tok, "actor_name": "สมชาย", "vehicle_id": str(vid), "mile": "103150",
        "cond_FL": "ok", "cond_FR": "problem",
    }
    r = client.post(f"/check/driver?t={tok}", data=data, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        evs = s.exec(select(TireEvent).where(TireEvent.event_type == "inspect")).all()
        assert len(evs) == 2
        assert all(e.actor_role == "driver" for e in evs)
        assert all(e.tread_after_mm == 0.0 for e in evs)   # mechanic fills later
        assert any(e.condition_flag == "problem" for e in evs)
        assert all(e.mile == 103150.0 for e in evs)


def test_driver_submit_rejected_without_valid_link(client):
    _tok, vid = _driver_link()
    r = client.post("/check/driver?t=bad", data={"vehicle_id": str(vid)},
                    follow_redirects=False)
    assert r.status_code in (400, 403)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_driver.py -v`
Expected: FAIL — `/check/driver` 404.

- [ ] **Step 3: Implement the routes**

In `main.py`:

```python
@app.get("/check/driver", response_class=HTMLResponse)
def check_driver_form(request: Request):
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "driver":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        vehicles = s.exec(select(Vehicle).where(Vehicle.status == "active").order_by(Vehicle.plate_no)).all()
        vid = _parse_int(request.query_params.get("vehicle_id") or "") or 0
        v = s.get(Vehicle, vid) if vid else None
        positions = _tire_positions_for_vehicle(v) if v else ()
        cells = [{"pos": p, "label": tire_view.th_label(p),
                  "photos": tire_view.photo_count(p), "outer": tire_view.is_outer(p)}
                 for p in positions]
    return templates.TemplateResponse("check_driver.html", {
        "request": request, "token": request.query_params.get("t"),
        "actor_name": request.query_params.get("actor_name", ""),
        "vehicles": vehicles, "vehicle": v, "cells": cells,
        "conditions": models.TIRE_CONDITION_FLAGS,
    })


@app.post("/check/driver")
async def check_driver_submit(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "driver":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)

        actor_name = (form.get("actor_name") or "").strip()
        vehicle_id = _parse_int(form.get("vehicle_id") or "") or 0
        mile = _parse_float(form.get("mile") or "0")
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise HTTPException(400, "เลือกทะเบียนรถก่อน")

        warn_mile = mile and mile < (tire_view.distance_since_last(s, vehicle_id, mile) and 0 or _last_inspect_mile(s, vehicle_id))
        positions = _tire_positions_for_vehicle(v)
        today = date.today()
        created = 0
        for pos in positions:
            cond = (form.get(f"cond_{pos}") or "").strip()
            if not cond:
                continue   # untouched position
            # save photos for this position (field name photo_<pos>, possibly multiple)
            paths = []
            for f in (form.getlist(f"photo_{pos}") if hasattr(form, "getlist") else []):
                if hasattr(f, "read"):
                    data = await f.read()
                    if data and len(data) > 100:
                        paths.append(drv.save_photo(0, "check", data, ext="jpg"))
            # find current tire at this position for tread baseline / link
            tire = s.exec(select(Tire).where(
                Tire.current_vehicle_id == vehicle_id, Tire.current_position == pos)).first()
            ev = TireEvent(
                tire_id=(tire.id if tire else 0),
                event_date=today, event_type="inspect",
                to_vehicle_id=vehicle_id, to_position=pos, mile=mile,
                tread_before_mm=(tire.tread_depth_mm if tire else 0.0),
                tread_after_mm=0.0,
                actor_name=actor_name, actor_role="driver",
                condition_flag=cond, photo_paths=",".join(paths),
            )
            s.add(ev); created += 1
        s.commit()
    return RedirectResponse(f"/check/driver?t={form.get('t')}&done={created}", status_code=303)


def _last_inspect_mile(session: Session, vehicle_id: int) -> float:
    row = session.exec(select(TireEvent).where(
        TireEvent.event_type == "inspect", TireEvent.to_vehicle_id == vehicle_id,
        TireEvent.mile > 0).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())).first()
    return row.mile if row else 0.0
```

> Simplify the `warn_mile` line during implementation — the intent is: `last = _last_inspect_mile(s, vehicle_id); warn_mile = bool(last and mile and mile < last)`. Pass `warn_mile` to the redirect/template as a query flag if you want to show it; the test does not require the warning UI, only that submission still succeeds.

- [ ] **Step 4: Add the template**

Create `templates/check_driver.html` — a vehicle dropdown (GET reloads grid with `?vehicle_id=`), then the top-view grid. Minimum for tests: POST form posting `t`, `actor_name`, `vehicle_id`, `mile`, and `cond_<pos>` selects per cell, plus `photo_<pos>` file inputs. Use the top-view layout from the approved mockup (`.superpowers/brainstorm/.../tire-topview.html`) as the visual reference. Keep Thai labels from `cells[].label`. The weekly fluid/equipment card (Task 7) will be appended to this template.

- [ ] **Step 5: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_driver.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/check_driver.html ProjectYK_System/app/tests/test_check_driver.py
git commit -m "feat(tire-check): driver tire-grid submit (photos + condition, awaiting mechanic)"
```

---

### Task 6: Mechanic flow — fill tread mm + tire jobs

**Files:**
- Modify: `ProjectYK_System/app/main.py` (`GET /check/mechanic` queue, `POST /check/mechanic/measure`, `POST /check/mechanic/job`)
- Create: `ProjectYK_System/app/templates/check_mechanic.html`
- Test: `ProjectYK_System/app/tests/test_check_mechanic.py`

**Interfaces:**
- Consumes: `_check_link_guard`, `tire_view.awaiting_mechanic`, `TireEvent`, `Tire`, the existing tire-job mutation logic from `maint_tire_event` (mount/unmount/rotate/scrap update `Tire` state).
- Produces:
  - `POST /check/mechanic/measure` — sets `tread_after_mm` (and `Tire.tread_depth_mm`) on an existing awaiting `inspect` event; records `actor_name`/`actor_role="mechanic"`; removes it from the queue.
  - `POST /check/mechanic/job` — creates a `TireEvent` for `rotate`/`unmount`/`mount`/`scrap` and updates `Tire` state, mirroring the office `maint_tire_event` behavior (extract shared logic into `_apply_tire_event(session, tire, event_type, ...)` and call it from both the office route and here).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_mechanic.py
from datetime import datetime, timedelta, date
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Tire, TireEvent
import services.access_link as al


def _mech_link():
    tok = al.make_token("mechanic", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="mechanic", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
    return tok


def _awaiting_event():
    with Session(engine) as s:
        t = Tire(code="T8001", spec="11R22.5", status="in_use",
                 current_vehicle_id=3, current_position="RLO1", tread_depth_mm=8.0)
        s.add(t); s.commit(); s.refresh(t)
        ev = TireEvent(tire_id=t.id, event_date=date(2026,6,22), event_type="inspect",
                       to_vehicle_id=3, to_position="RLO1", mile=103150,
                       actor_role="driver", condition_flag="near", tread_after_mm=0.0)
        s.add(ev); s.commit(); s.refresh(ev)
        return ev.id, t.id


def test_mechanic_measure_fills_tread_and_clears_queue(client):
    tok = _mech_link()
    ev_id, tire_id = _awaiting_event()
    r = client.post(f"/check/mechanic/measure?t={tok}",
                    data={"t": tok, "event_id": str(ev_id), "tread_mm": "6.3",
                          "actor_name": "ช่างต้น"}, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        ev = s.get(TireEvent, ev_id)
        assert ev.tread_after_mm == 6.3
        assert ev.actor_role == "mechanic"
        t = s.get(Tire, tire_id)
        assert t.tread_depth_mm == 6.3
        import services.tire_view as tv
        assert all(e.id != ev_id for e in tv.awaiting_mechanic(s))


def test_mechanic_scrap_job_updates_tire(client):
    tok = _mech_link()
    _ev_id, tire_id = _awaiting_event()
    r = client.post(f"/check/mechanic/job?t={tok}",
                    data={"t": tok, "tire_id": str(tire_id), "event_type": "scrap",
                          "actor_name": "ช่างต้น", "note": "ระเบิดข้างทาง"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        t = s.get(Tire, tire_id)
        assert t.status == "scrapped"
        ev = s.exec(select(TireEvent).where(TireEvent.tire_id == tire_id,
                    TireEvent.event_type == "scrap")).first()
        assert ev is not None
        assert ev.actor_role == "mechanic"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_mechanic.py -v`
Expected: FAIL — routes 404.

- [ ] **Step 3: Extract shared tire-event logic**

Refactor the body of the existing `@app.post("/maint/tires/{tire_id}/event")` (main.py ~6145) so the state-mutation core lives in a reusable function. Add:

```python
def _apply_tire_event(s: Session, t: Tire, *, event_type: str, event_date: date,
                      mile: float, to_vehicle_id: Optional[int] = None,
                      to_position: str = "", tread_before: float = 0.0,
                      tread_after: float = 0.0, note: str = "",
                      actor_name: str = "", actor_role: str = "",
                      photo_paths: str = "") -> TireEvent:
    ev = TireEvent(
        tire_id=t.id, event_date=event_date, event_type=event_type,
        from_vehicle_id=t.current_vehicle_id, from_position=t.current_position,
        mile=mile, tread_before_mm=tread_before or t.tread_depth_mm or 0.0,
        tread_after_mm=tread_after, note=note,
        actor_name=actor_name, actor_role=actor_role, photo_paths=photo_paths,
    )
    if event_type == "mount":
        # ... (move the existing mount block here, including auto-unmount of displaced tire)
        ...
    elif event_type == "unmount":
        t.current_vehicle_id = None; t.current_position = ""; t.status = "stored"
    elif event_type == "rotate":
        if not to_position:
            raise HTTPException(400, "rotate requires to_position")
        ev.to_vehicle_id = t.current_vehicle_id; ev.to_position = to_position
        t.current_position = to_position
    elif event_type == "scrap":
        t.status = "scrapped"; t.current_vehicle_id = None; t.current_position = ""
    elif event_type == "retread":
        t.retread_count += 1; t.status = "in_use"
    if tread_after:
        t.tread_depth_mm = tread_after
    s.add(ev); s.add(t)
    return ev
```

Then make the office route call `_apply_tire_event(...)` instead of its inline block (keep behavior identical — verify with `pytest tests/ -q`).

- [ ] **Step 4: Add the mechanic routes**

```python
@app.get("/check/mechanic", response_class=HTMLResponse)
def check_mechanic_form(request: Request):
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        queue = tire_view.awaiting_mechanic(s)
        tires = s.exec(select(Tire)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        rows = [{"ev": e, "label": tire_view.th_label(e.to_position or "")} for e in queue]
    return templates.TemplateResponse("check_mechanic.html", {
        "request": request, "token": request.query_params.get("t"),
        "queue": rows, "tires": tires, "vehicles": vehicles,
        "event_types": models.TIRE_EVENT_TYPES,
    })


@app.post("/check/mechanic/measure")
async def check_mechanic_measure(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        ev = s.get(TireEvent, _parse_int(form.get("event_id") or "") or 0)
        if not ev:
            raise HTTPException(404, "ไม่พบรายการ")
        ev.tread_after_mm = _parse_float(form.get("tread_mm") or "0")
        ev.actor_role = "mechanic"
        ev.actor_name = (form.get("actor_name") or "").strip() or ev.actor_name
        t = s.get(Tire, ev.tire_id) if ev.tire_id else None
        if t and ev.tread_after_mm:
            t.tread_depth_mm = ev.tread_after_mm; s.add(t)
        s.add(ev); s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}", status_code=303)


@app.post("/check/mechanic/job")
async def check_mechanic_job(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        t = s.get(Tire, _parse_int(form.get("tire_id") or "") or 0)
        if not t:
            raise HTTPException(404, "ไม่พบยาง")
        _apply_tire_event(
            s, t,
            event_type=(form.get("event_type") or "").strip(),
            event_date=_parse_date(form.get("event_date") or "") or date.today(),
            mile=_parse_float(form.get("mile") or "0"),
            to_vehicle_id=_parse_int(form.get("to_vehicle_id") or "") or None,
            to_position=(form.get("to_position") or "").strip().upper(),
            note=(form.get("note") or "").strip(),
            actor_name=(form.get("actor_name") or "").strip(),
            actor_role="mechanic",
        )
        s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}", status_code=303)
```

- [ ] **Step 5: Add the template**

Create `templates/check_mechanic.html` — section 1: queue list (each row shows Thai position label + condition + driver photos + a tread input using the lag/+0.5/+0.1 control from the approved mockup, posting to `/check/mechanic/measure`); section 2: tire-job form (tire select, event_type select, to_position, note, photo) posting to `/check/mechanic/job`. Carry `?t=` on every form.

- [ ] **Step 6: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_mechanic.py -v`
Expected: PASS (2 tests). Then regression: `pytest tests/ -q` (the office tire-event route must still behave identically after the refactor).

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/check_mechanic.html ProjectYK_System/app/tests/test_check_mechanic.py
git commit -m "feat(tire-check): mechanic queue (fill tread) + tire jobs via shared _apply_tire_event"
```

---

### Task 7: Weekly fluid/equipment check appended to driver flow

**Files:**
- Modify: `ProjectYK_System/app/main.py` (`POST /check/driver` — also create a `DriverSubmission(kind="vehicle_check")` when fluid items submitted)
- Modify: `ProjectYK_System/app/templates/check_driver.html` (append fluid/equipment card)
- Modify: `ProjectYK_System/app/models.py` (make `DriverSubmission.employee_id` nullable to allow link submissions without an employee)
- Modify: `ProjectYK_System/app/main.py` migration (`_ensure_column` not needed for nullable change on existing col; instead store actor in `data_json` — see step 3)
- Test: `ProjectYK_System/app/tests/test_check_weekly.py`

**Interfaces:**
- Consumes: `_check_link_guard`, `DriverSubmission`, `models.VEHICLE_CHECK_ITEMS`, `models.VEHICLE_CHECK_STATUS`.
- Produces: when the driver submits the weekly card, one `DriverSubmission(kind="vehicle_check", employee_id=None, plate_raw=..., data_json={items, actor_name, source:"check_link"})`, `review_status="flagged"` if any item is `fail`.

> Decision (resolves spec §10): keep `employee_id` but make it **nullable**; store `actor_name` inside `data_json` (no new column). This avoids touching the existing driver-PWA submission path.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_weekly.py
from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle, DriverSubmission
import services.access_link as al, json


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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_weekly.py -v`
Expected: FAIL — no submission created (and/or NOT NULL constraint on employee_id).

- [ ] **Step 3: Make employee_id nullable**

In `models.py`, change `DriverSubmission.employee_id`:

```python
    employee_id: Optional[int] = Field(default=None, foreign_key="employee.id", index=True)
```

(SQLite stores it nullable already for fresh tables via `create_all`; existing dev DBs keep working since the column already exists and we never insert NULL through the old path. No `_ensure_column` change required.)

- [ ] **Step 4: Append weekly handling to `/check/driver` POST**

Inside `check_driver_submit`, after the per-tire loop and before commit:

```python
        if form.get("weekly"):
            answers = {}
            any_fail = False
            for key, _ in models.VEHICLE_CHECK_ITEMS:
                val = (form.get(f"item_{key}") or "").strip()
                if not val:
                    continue
                answers[key] = val
                if val == "fail":
                    any_fail = True
            if answers:
                s.add(DriverSubmission(
                    employee_id=None, kind="vehicle_check",
                    vehicle_id=vehicle_id, plate_raw=(v.plate_no if v else ""),
                    data_json=_json.dumps(
                        {"items": answers, "actor_name": actor_name, "source": "check_link"},
                        ensure_ascii=False),
                    review_status="flagged" if any_fail else "pending",
                    device_info=request.headers.get("user-agent", "")[:200],
                ))
```

- [ ] **Step 5: Append the card to the template**

In `check_driver.html`, after the tire grid, add a `weekly` hidden marker + a row per `VEHICLE_CHECK_ITEMS` with a status select (`item_<key>`) using `VEHICLE_CHECK_STATUS`. (Pass `weekly_items=models.VEHICLE_CHECK_ITEMS` and `weekly_status=models.VEHICLE_CHECK_STATUS` from the GET handler context.)

- [ ] **Step 6: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_weekly.py -v`
Expected: PASS. Then regression: `pytest tests/ -q` (driver-PWA `/driver/check` path unchanged).

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/app/templates/check_driver.html ProjectYK_System/app/tests/test_check_weekly.py
git commit -m "feat(tire-check): weekly fluid/equipment check via magic link (nullable employee submission)"
```

---

### Task 8: Office view — inspection history per vehicle

**Files:**
- Modify: `ProjectYK_System/app/main.py` (extend `GET /maint/tires/by-vehicle/{id}` context OR add `GET /maint/tires/{tire_id}` events display) to surface inspect events with photos + actor + condition. Reuse the existing `tire_by_vehicle.html` / `tire_form.html` event tables.
- Test: `ProjectYK_System/app/tests/test_tire_history_view.py`

**Interfaces:**
- Consumes: existing `maint_tire_by_vehicle` route (already lists `events`), `TireEvent.photo_paths`/`actor_name`/`condition_flag`.
- Produces: no new route required if the existing event list already renders; this task ensures the new fields are shown and adds a regression test that an inspect event with photos appears for the office.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tire_history_view.py
from sqlmodel import Session
from db_config import engine
from models import Vehicle, Tire, TireEvent
from datetime import date


def test_office_by_vehicle_shows_inspect_actor(client):
    # log in as admin
    client.post("/login", data={"username": "yk1", "password": "changeme1"},
                follow_redirects=False)
    with Session(engine) as s:
        v = Vehicle(plate_no="71-7777", vehicle_kind="head", truck_type="6W", status="active")
        s.add(v); s.commit(); s.refresh(v)
        t = Tire(code="T6001", spec="11R22.5", status="in_use",
                 current_vehicle_id=v.id, current_position="FL", tread_depth_mm=6.0)
        s.add(t); s.commit(); s.refresh(t)
        s.add(TireEvent(tire_id=t.id, event_date=date(2026,6,22), event_type="inspect",
                        to_vehicle_id=v.id, to_position="FL", mile=50000,
                        actor_name="สมชาย", actor_role="driver", condition_flag="near",
                        tread_after_mm=6.0, photo_paths="check/2026-06-22/x.jpg"))
        s.commit()
        vid = v.id
    r = client.get(f"/maint/tires/by-vehicle/{vid}")
    assert r.status_code == 200
    assert "สมชาย" in r.text
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_tire_history_view.py -v`
Expected: FAIL — `สมชาย` not rendered (template doesn't show actor yet).

- [ ] **Step 3: Show new fields in the event table**

In `templates/tire_by_vehicle.html` (and `tire_form.html` if it has an event table), add columns/inline text for `ev.actor_name`, `ev.condition_flag`, and a thumbnail/link per `ev.photo_paths` entry (split on `,`; link to `/uploads/<path>`). Use the existing `dmy` filter for dates.

- [ ] **Step 4: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_tire_history_view.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/templates/tire_by_vehicle.html ProjectYK_System/app/templates/tire_form.html ProjectYK_System/app/tests/test_tire_history_view.py
git commit -m "feat(tire-check): office view shows inspect actor/condition/photos"
```

---

## Self-Review

**Spec coverage:**
- §3 magic link (no login, expiring, role-scoped, name entry, multi-use) → Tasks 1, 4. ✅
- §4 driver flow (top-view grid, photos by outer/inner, condition, no mm, weekly card, awaiting-mechanic) → Tasks 3, 5, 7. ✅
- §5 mechanic flow (queue fill mm + tire jobs in-link) → Task 6. ✅
- §6 data model (TireEvent fields, AccessLink, trailer 8-wheel, DriverSubmission nullable, derived queue) → Tasks 1, 2, 3, 7. ✅
- §7 Thai position labels + outer/inner rule → Task 3. ✅
- §8 mile-regression warning (non-blocking), distance-since-last → Tasks 3, 5. ✅
- §9 approved UI (top-view, tread control) → referenced as visual source in Tasks 5, 6 templates. ✅
- §10 open questions: employee_id nullable (Task 7), derived queue (Task 3), gen-link under admin (Task 4, behind `current_user`/RBAC matrix). ✅
- Office history view (implied by "เก็บรูปไว้โชว์ในระบบ") → Task 8. ✅

**Placeholder scan:** The `warn_mile` one-liner in Task 5 Step 3 is flagged with an explicit simplification note + exact intended code — not a placeholder. Template tasks (5, 6, 7, 8) describe required form fields/context explicitly and name the approved mockup as the visual source; no "TBD".

**Type consistency:** `_apply_tire_event` signature defined in Task 6 Step 3 is the only definition and is consumed only in Task 6. `_check_link_guard`, `make_token`/`read_token`, `tire_view.*` signatures match across Tasks 1, 3, 4, 5, 6. `condition_flag` values (`ok`/`near`/`problem`) consistent across Tasks 2, 3, 5. `kind="check"` for `save_photo` consistent in Task 5.

**Risk note for executor:** Tasks 5–8 modify the large monolith `main.py` and reuse office tire logic. Run the full suite (`pytest tests/ -q`) after Tasks 2, 6, and 7 specifically — those touch schema, refactor a shared handler, and change a shared model.
