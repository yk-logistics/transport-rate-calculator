# LCB Slip-Reader → Review-in-MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI reads LCB transfer slips from the archived LINE group, drafts petty-cash entries, and a human approves them in an MVP web page before they post — LCB only, MVP DB only, sheet untouched.

**Architecture:** Two runtimes. (1) MVP (`ProjectYK_System/app/`) gains a schema migration, an idempotent ingest endpoint, and a `/petty/review` approval page. (2) A new server-side `slip_reader/` service reads `line_archive.db` read-only, OCRs slips via a swappable engine (Claude API default), enriches with the day's work-plan, and pushes drafts to the MVP ingest endpoint. The MVP side is built and tested first; the server side pushes into it.

**Tech Stack:** FastAPI + SQLModel + Jinja2/HTMX (MVP, existing); Python + httpx + Anthropic Messages API (slip_reader, new). Tests: pytest via `app/conftest.py` `client` fixture.

## Global Constraints

- Pin floors (verbatim): `fastapi<0.115`, `starlette<0.40` — do not upgrade.
- Schema migrations: no Alembic. Bump `main.py:SCHEMA_VERSION` (currently 19 → 20) and add an `ALTER TABLE` block in `lifespan()` guarded by version check. Update both together.
- Money rules: amount comes from the slip only; never guessed from text. Every entry passes `status="pending_review"` → human approve → `posted`. No auto-post. Idempotent by `slip_line_message_id`. `site_code="LCB"` on every row. Do NOT write the Google Sheet in this phase.
- Tests run from `ProjectYK_System/app/`: `.venv\Scripts\python.exe -m pytest tests/<file> -v`. The `client` fixture drops+recreates schema and seeds admin `yk1` per test. Admin login pattern: `_login_admin(client)` (force-set hash `adminpass1`, then `POST /login`).
- UTF-8 rule for any Windows console output: scripts that print Thai must wrap stdout (`io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`) or set `PYTHONUTF8=1`.
- Server access: `ssh yklog@100.97.150.114` (PowerShell remote). archiver DB at `C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db`; archiver venv python at `C:\Users\yklog\YK_LINE_ARCHIVER\.venv\Scripts\python.exe`.

---

## File Structure

**MVP (`ProjectYK_System/app/`):**
- Modify `models.py` — add 3 columns to `PettyCashTxn`; add `pending_review` to `PETTY_TXN_STATUS`.
- Modify `main.py` — bump `SCHEMA_VERSION`; add migration block; add ingest endpoint + review routes.
- Create `templates/petty_review.html` — approval page.
- Create `tests/test_petty_ingest.py`, `tests/test_petty_review.py`.

**slip_reader service (`ProjectYK_System/slip_reader/`, new):**
- Create `engine.py` — `SlipEngine` protocol + `ClaudeSlipEngine`.
- Create `slip_source.py` — read archive, find unprocessed company slips.
- Create `plan_context.py` — parse the day's work-plan text.
- Create `entry_builder.py` — assemble draft from readout + plan.
- Create `mvp_push.py` — POST to ingest endpoint.
- Create `run_once.py` — wire the pipeline for one pass.
- Create `config.py` — engine selection, MVP URL, service token.
- Create `tests/test_plan_context.py`, `tests/test_entry_builder.py`, `tests/test_slip_engine_contract.py`.

---

## Task 1: PettyCashTxn schema — provenance columns + pending status

**Files:**
- Modify: `ProjectYK_System/app/models.py:218-258` (PettyCashTxn), `:1227-1231` (PETTY_TXN_STATUS)
- Modify: `ProjectYK_System/app/main.py:88` (SCHEMA_VERSION), lifespan migration block
- Test: `ProjectYK_System/app/tests/test_petty_schema.py`

**Interfaces:**
- Produces: `PettyCashTxn` with new fields `slip_line_message_id: str`, `slip_media_path: str`, `slip_ref_code: str` (all default `""`); status value `"pending_review"`.

- [ ] **Step 1: Write the failing test**

Create `ProjectYK_System/app/tests/test_petty_schema.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_petty_schema.py -v` (from `app/`)
Expected: FAIL — `TypeError: 'slip_line_message_id' is an invalid keyword argument` (field not yet on model).

- [ ] **Step 3: Add the fields and status**

In `models.py`, inside `PettyCashTxn` after `parsed_payload_json` (line ~255):
```python
    parsed_payload_json: str = ""

    # provenance for LINE-slip-sourced entries (phase: lcb-slip-reader)
    slip_line_message_id: str = Field(default="", index=True)
    slip_media_path: str = ""
    slip_ref_code: str = ""
```
In `PETTY_TXN_STATUS` (line ~1227), add one row:
```python
PETTY_TXN_STATUS = (
    ("draft",          "ร่าง"),
    ("pending_review", "รอ AI อ่าน—รออนุมัติ"),
    ("posted",         "บันทึกแล้ว"),
    ("locked",         "ปิดรอบแล้ว (แก้ไม่ได้)"),
)
```

- [ ] **Step 4: Bump SCHEMA_VERSION + add migration block**

In `main.py`, change `SCHEMA_VERSION = 19` → `SCHEMA_VERSION = 20`.
In the `lifespan()` migration ladder (the block doing version-gated `ALTER TABLE`), add after the v19 handling:
```python
        if current.version < 20:
            for col in ("slip_line_message_id", "slip_media_path", "slip_ref_code"):
                try:
                    s.exec(text(f"ALTER TABLE pettycashtxn ADD COLUMN {col} TEXT DEFAULT ''"))
                except Exception:
                    pass  # column already exists (fresh create_all)
```
(Match the exact idiom already used in the file — find an existing `if current.version < N:` block and copy its shape, including how `text(...)` is imported/called there.)

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_petty_schema.py -v`
Expected: PASS.

- [ ] **Step 6: Run full suite to confirm no regression**

Run: `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: all pass (same count as before + 1).

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_petty_schema.py
git commit -m "feat(petty): slip provenance fields + pending_review status (schema v20)"
```

---

## Task 2: Ingest endpoint — drafts in, idempotent

**Files:**
- Modify: `ProjectYK_System/app/main.py` (add route near other petty/api routes)
- Test: `ProjectYK_System/app/tests/test_petty_ingest.py`

**Interfaces:**
- Consumes: `PettyCashTxn` model from Task 1.
- Produces: `POST /api/petty/ingest` accepting JSON
  `{slip_line_message_id, site_code, txn_date (YYYY-MM-DD), amount, direction, category, requester_raw, memo, slip_media_path, slip_ref_code, parsed_confidence, parsed_payload_json}`.
  Auth via header `X-Service-Token` matching env `YK_SLIP_INGEST_TOKEN`. Returns
  `{"status":"created","id":N}` or `{"status":"duplicate","id":N}` (same `slip_line_message_id` already present). Always creates with `status="pending_review"`, `source="line_slip"`.

- [ ] **Step 1: Write the failing tests**

Create `ProjectYK_System/app/tests/test_petty_ingest.py`:
```python
import os
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
    p.update(over); return p

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_petty_ingest.py -v`
Expected: FAIL — 404 (route missing).

- [ ] **Step 3: Implement the endpoint**

In `main.py`, add (near other petty routes; reuse the existing session dependency
pattern — find how other endpoints get a `Session`, e.g. `with Session(engine) as s:`):
```python
from pydantic import BaseModel  # if not already imported

class PettyIngestIn(BaseModel):
    slip_line_message_id: str
    site_code: str
    txn_date: str
    amount: float
    direction: str = "out"
    category: str = "other"
    requester_raw: str = ""
    memo: str = ""
    slip_media_path: str = ""
    slip_ref_code: str = ""
    parsed_confidence: float = 0.0
    parsed_payload_json: str = ""

@app.post("/api/petty/ingest")
def petty_ingest(body: PettyIngestIn, request: Request):
    expected = os.environ.get("YK_SLIP_INGEST_TOKEN", "")
    if not expected or request.headers.get("X-Service-Token") != expected:
        raise HTTPException(status_code=401, detail="bad service token")
    from datetime import date as _date
    with Session(engine) as s:
        existing = s.exec(select(PettyCashTxn).where(
            PettyCashTxn.slip_line_message_id == body.slip_line_message_id
        )).first()
        if existing:
            return {"status": "duplicate", "id": existing.id}
        t = PettyCashTxn(
            txn_date=_date.fromisoformat(body.txn_date),
            site_code=body.site_code, direction=body.direction,
            amount=body.amount, category=body.category,
            requester_raw=body.requester_raw, memo=body.memo,
            status="pending_review", source="line_slip",
            slip_line_message_id=body.slip_line_message_id,
            slip_media_path=body.slip_media_path, slip_ref_code=body.slip_ref_code,
            parsed_confidence=body.parsed_confidence,
            parsed_payload_json=body.parsed_payload_json,
        )
        s.add(t); s.commit(); s.refresh(t)
        return {"status": "created", "id": t.id}
```
Ensure `Request`, `HTTPException`, `os`, `select`, `Session`, `engine`, `PettyCashTxn` are imported (most already are; add what's missing).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_petty_ingest.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Verify the ingest route is exempt from login redirect**

The RBAC middleware may redirect unauthenticated requests to `/login`. Confirm
`/api/petty/ingest` is reachable with only the service token (the test already
asserts 200/401, not a redirect). If the test sees a 302/307 to `/login`, add
`/api/petty/` to the middleware's public-path allowlist (search `main.py` for the
existing allowlist, e.g. where `/health` or `/login` is exempted) and re-run.

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_petty_ingest.py
git commit -m "feat(petty): idempotent /api/petty/ingest for slip-sourced drafts"
```

---

## Task 3: Review page — list, approve, reject

**Files:**
- Modify: `ProjectYK_System/app/main.py` (3 routes)
- Create: `ProjectYK_System/app/templates/petty_review.html`
- Test: `ProjectYK_System/app/tests/test_petty_review.py`

**Interfaces:**
- Consumes: `PettyCashTxn` (Task 1), entries created by Task 2.
- Produces: `GET /petty/review` (admin/office only; lists LCB `pending_review`),
  `POST /petty/review/{id}/approve` (optional form fields `amount`, `requester_raw`,
  `category`, `memo` override before posting; sets `status="posted"`),
  `POST /petty/review/{id}/reject` (sets `status="draft"`). Both redirect back to
  `/petty/review`.

- [ ] **Step 1: Write the failing tests**

Create `ProjectYK_System/app/tests/test_petty_review.py`:
```python
from sqlmodel import Session, select
from db_config import engine
from models import PettyCashTxn, AppUser
from auth import hash_password
from datetime import date

def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1"); u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client

def _mk_pending(msg_id="618000000000000020", amount=1280.0):
    with Session(engine) as s:
        t = PettyCashTxn(txn_date=date(2026,6,16), site_code="LCB", amount=amount,
                         direction="out", category="other", requester_raw="ปกรณ์",
                         memo="ปกรณ์ คืนตู้", status="pending_review",
                         source="line_slip", slip_line_message_id=msg_id)
        s.add(t); s.commit(); s.refresh(t); return t.id

def test_review_lists_pending(client):
    _login_admin(client); _mk_pending()
    r = client.get("/petty/review")
    assert r.status_code == 200 and "ปกรณ์" in r.text

def test_approve_posts_entry(client):
    _login_admin(client); pid = _mk_pending(msg_id="618000000000000021")
    r = client.post(f"/petty/review/{pid}/approve", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        assert s.get(PettyCashTxn, pid).status == "posted"

def test_approve_with_override(client):
    _login_admin(client); pid = _mk_pending(msg_id="618000000000000022", amount=100.0)
    client.post(f"/petty/review/{pid}/approve",
                data={"amount": "107", "category": "loading"}, follow_redirects=False)
    with Session(engine) as s:
        t = s.get(PettyCashTxn, pid)
        assert t.amount == 107.0 and t.category == "loading" and t.status == "posted"

def test_reject_sets_draft(client):
    _login_admin(client); pid = _mk_pending(msg_id="618000000000000023")
    client.post(f"/petty/review/{pid}/reject", data={}, follow_redirects=False)
    with Session(engine) as s:
        assert s.get(PettyCashTxn, pid).status == "draft"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_petty_review.py -v`
Expected: FAIL — 404 on `/petty/review`.

- [ ] **Step 3: Create the template**

Create `ProjectYK_System/app/templates/petty_review.html` (follow an existing
template's `{% extends %}` base — open `templates/employees.html` or similar to copy
the base layout/block names):
```html
{% extends "base.html" %}
{% block content %}
<h1 class="text-xl font-bold mb-4">รออนุมัติ — สดย่อย LCB (จากสลิป LINE)</h1>
<table class="w-full text-sm border">
  <thead><tr class="bg-gray-100">
    <th>วันที่</th><th>คนขับ</th><th>ยอด</th><th>รายการ</th>
    <th>มั่นใจ</th><th>สลิป</th><th></th></tr></thead>
  <tbody>
  {% for t in rows %}
    <tr class="border-t">
      <td>{{ t.txn_date | dmy }}</td>
      <td>{{ t.requester_raw }}</td>
      <td class="text-right">{{ "%.2f"|format(t.amount) }}</td>
      <td>{{ t.memo }}</td>
      <td>{{ "%.0f"|format(t.parsed_confidence * 100) }}%</td>
      <td>{% if t.slip_media_path %}มี{% else %}-{% endif %}</td>
      <td>
        <form method="post" action="/petty/review/{{ t.id }}/approve" class="inline">
          <input name="amount" value="{{ t.amount }}" size="7">
          <button class="text-green-700">อนุมัติ</button>
        </form>
        <form method="post" action="/petty/review/{{ t.id }}/reject" class="inline">
          <button class="text-red-600">ทิ้ง</button>
        </form>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="7" class="text-center p-4 text-gray-500">ไม่มีรายการรออนุมัติ</td></tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Implement the routes**

In `main.py` (copy the admin-guard dependency used by `/admin/users` so only
admin/office roles reach these):
```python
@app.get("/petty/review", response_class=HTMLResponse)
def petty_review(request: Request):
    # reuse the same auth guard pattern as /admin/users (admin/office)
    with Session(engine) as s:
        rows = s.exec(select(PettyCashTxn).where(
            PettyCashTxn.status == "pending_review",
            PettyCashTxn.site_code == "LCB"
        ).order_by(PettyCashTxn.txn_date, PettyCashTxn.id)).all()
    return templates.TemplateResponse("petty_review.html",
                                      {"request": request, "rows": rows})

@app.post("/petty/review/{pid}/approve")
async def petty_review_approve(pid: int, request: Request):
    form = await request.form()
    with Session(engine) as s:
        t = s.get(PettyCashTxn, pid)
        if t and t.status == "pending_review":
            if form.get("amount"): t.amount = float(form["amount"])
            if form.get("requester_raw"): t.requester_raw = form["requester_raw"]
            if form.get("category"): t.category = form["category"]
            if form.get("memo"): t.memo = form["memo"]
            t.status = "posted"
            s.add(t); s.commit()
    return RedirectResponse("/petty/review", status_code=303)

@app.post("/petty/review/{pid}/reject")
def petty_review_reject(pid: int):
    with Session(engine) as s:
        t = s.get(PettyCashTxn, pid)
        if t and t.status == "pending_review":
            t.status = "draft"; s.add(t); s.commit()
    return RedirectResponse("/petty/review", status_code=303)
```
Ensure `RedirectResponse`, `HTMLResponse`, `templates` are imported/defined (they
are already used elsewhere in `main.py`).

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_petty_review.py -v`
Expected: PASS (4 tests). If the list test 404s on the template base name, fix the
`{% extends %}` to match the real base template filename.

- [ ] **Step 6: Run full suite**

Run: `.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/petty_review.html ProjectYK_System/app/tests/test_petty_review.py
git commit -m "feat(petty): /petty/review approve/reject page for slip drafts"
```

---

## Task 4: Slip engine — protocol + Claude implementation

**Files:**
- Create: `ProjectYK_System/slip_reader/__init__.py`, `engine.py`, `config.py`
- Test: `ProjectYK_System/slip_reader/tests/test_slip_engine_contract.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass
  class SlipReadout:
      is_slip: bool
      amount: float | None
      recipient_name: str        # from "ไปยัง" / memo
      memo: str                  # บันทึกช่วยจำ
      ref_code: str
      slip_time: str             # "HH:MM" or ""
      direction: str             # "out" | "in"
  class SlipEngine(Protocol):
      def read(self, image_bytes: bytes) -> SlipReadout: ...
  def get_engine(name: str) -> SlipEngine   # "claude" -> ClaudeSlipEngine
  ```
- `ClaudeSlipEngine` calls the Anthropic Messages API (model id `claude-haiku-4-5-20251001`) with the image + a JSON-only extraction prompt, parses the JSON into `SlipReadout`.

- [ ] **Step 1: Write the contract test (no network)**

Create `ProjectYK_System/slip_reader/tests/test_slip_engine_contract.py`:
```python
from slip_reader.engine import SlipReadout, get_engine, ClaudeSlipEngine

class FakeEngine:
    def read(self, image_bytes):
        return SlipReadout(is_slip=True, amount=428.0, recipient_name="วิโรจน์",
                           memo="วิโรจน์ รับตู้ดรอป", ref_code="REF", slip_time="08:54",
                           direction="out")

def test_readout_shape():
    r = FakeEngine().read(b"")
    assert r.is_slip and r.amount == 428.0 and r.direction in ("out", "in")

def test_get_engine_returns_claude():
    e = get_engine("claude")
    assert isinstance(e, ClaudeSlipEngine)
```

- [ ] **Step 2: Run to verify it fails**

Run (from repo root): `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_slip_engine_contract.py -v`
Expected: FAIL — module `slip_reader.engine` not found.

- [ ] **Step 3: Implement engine.py + config.py**

Create `ProjectYK_System/slip_reader/__init__.py` (empty).
Create `ProjectYK_System/slip_reader/config.py`:
```python
import os
SLIP_ENGINE = os.environ.get("SLIP_ENGINE", "claude")
MVP_INGEST_URL = os.environ.get("MVP_INGEST_URL", "http://127.0.0.1:8010/api/petty/ingest")
SLIP_INGEST_TOKEN = os.environ.get("YK_SLIP_INGEST_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("SLIP_CLAUDE_MODEL", "claude-haiku-4-5")
```
Create `ProjectYK_System/slip_reader/engine.py`:
```python
from __future__ import annotations
import base64, json
from dataclasses import dataclass
from typing import Protocol, Optional
from . import config

@dataclass
class SlipReadout:
    is_slip: bool
    amount: Optional[float]
    recipient_name: str
    memo: str
    ref_code: str
    slip_time: str
    direction: str

class SlipEngine(Protocol):
    def read(self, image_bytes: bytes) -> SlipReadout: ...

_PROMPT = (
    "You are reading a Thai bank transfer slip image. Return ONLY JSON with keys: "
    "is_slip (true if this is a bank transfer/bill-pay slip, false for job orders, "
    "work plans, or summary tables), amount (number or null), recipient_name "
    "(from 'ไปยัง' or memo, Thai), memo (บันทึกช่วยจำ text), ref_code "
    "(รหัสอ้างอิง), slip_time ('HH:MM' or ''), direction ('out' normally; 'in' if "
    "money is received into petty cash). No prose, JSON only."
)

class ClaudeSlipEngine:
    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._model = config.CLAUDE_MODEL

    # JSON schema constrains the response — no ```json fences to strip, no
    # free-form parsing. Haiku 4.5 supports structured outputs.
    _SCHEMA = {
        "type": "object",
        "properties": {
            "is_slip": {"type": "boolean"},
            "amount": {"type": ["number", "null"]},
            "recipient_name": {"type": "string"},
            "memo": {"type": "string"},
            "ref_code": {"type": "string"},
            "slip_time": {"type": "string"},
            "direction": {"type": "string", "enum": ["out", "in"]},
        },
        "required": ["is_slip", "amount", "recipient_name", "memo",
                     "ref_code", "slip_time", "direction"],
        "additionalProperties": False,
    }

    def read(self, image_bytes: bytes) -> SlipReadout:
        b64 = base64.standard_b64encode(image_bytes).decode()
        msg = self._client.messages.create(
            model=self._model, max_tokens=400,
            output_config={"format": {"type": "json_schema", "schema": self._SCHEMA}},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": _PROMPT},
            ]}],
        )
        # A safety refusal returns stop_reason="refusal" with no usable content.
        # Treat as "not a readable slip" — caller will skip (no guessed amount).
        if msg.stop_reason == "refusal":
            return SlipReadout(False, None, "", "", "", "", "out")
        text = next((b.text for b in msg.content if b.type == "text"), "").strip()
        d = json.loads(text)  # output_config guarantees valid JSON, no fences
        return SlipReadout(
            is_slip=bool(d.get("is_slip")),
            amount=(float(d["amount"]) if d.get("amount") not in (None, "") else None),
            recipient_name=d.get("recipient_name", "") or "",
            memo=d.get("memo", "") or "", ref_code=d.get("ref_code", "") or "",
            slip_time=d.get("slip_time", "") or "",
            direction=d.get("direction", "out") or "out",
        )

def get_engine(name: str = None) -> SlipEngine:
    name = name or config.SLIP_ENGINE
    if name == "claude":
        return ClaudeSlipEngine()
    raise ValueError(f"unknown slip engine: {name}")
```

- [ ] **Step 4: Add anthropic to a slip_reader requirements file**

Create `ProjectYK_System/slip_reader/requirements.txt`:
```
anthropic>=0.40
httpx
```
Install into the existing venv: `ProjectYK_System/app/.venv/Scripts/pip.exe install -r ProjectYK_System/slip_reader/requirements.txt`

- [ ] **Step 5: Run contract test to verify it passes**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_slip_engine_contract.py -v`
Expected: PASS (note: `get_engine("claude")` constructs the client but does not call the API — no network, no key needed; if `anthropic.Anthropic()` requires a key at construction, pass a dummy via `config.ANTHROPIC_API_KEY` env in the test).

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/slip_reader/
git commit -m "feat(slip-reader): SlipEngine protocol + ClaudeSlipEngine (swappable)"
```

---

## Task 5: plan_context — parse the day's work-plan

**Files:**
- Create: `ProjectYK_System/slip_reader/plan_context.py`
- Test: `ProjectYK_System/slip_reader/tests/test_plan_context.py`

**Interfaces:**
- Produces:
  ```python
  def parse_plan(plan_text: str) -> dict[str, list[dict]]
      # {driver_name: [{"job","agent","return_yard","plate_head","date"}]}
  def plan_lookup(plans_text_by_time: list[tuple[str,str]], day: str) -> dict
      # picks the LATEST plan message whose body targets `day` (DD.MM.YY), parses it
  ```

- [ ] **Step 1: Write the failing test**

Create `ProjectYK_System/slip_reader/tests/test_plan_context.py`:
```python
from slip_reader.plan_context import parse_plan, plan_lookup

PLAN = """@All **16.06.26** งาน13วิ่ง13
***********************************
KAO2 [DC2]

Job. 26-0914 Agent. YANG MING
รับตู้หนักKERRY [หลังเที่ยงคืน-15.06.26] เปิดคาโอDC อมตะ คืนลานUNIWISE
- นายปกรณ์ ศรีบุญเรือง 063-379-3511
หัว72-1220 หาง72-2952
Con.[40]
"""

def test_parse_plan_extracts_driver_job():
    d = parse_plan(PLAN)
    assert "ปกรณ์" in " ".join(d.keys()) or any("ปกรณ์" in k for k in d)
    key = [k for k in d if "ปกรณ์" in k][0]
    entry = d[key][0]
    assert entry["return_yard"] == "UNIWISE"
    assert entry["agent"].startswith("YANG")

def test_plan_lookup_picks_latest_for_day():
    older = ("2026-06-15 16:57", PLAN.replace("UNIWISE", "OLDYARD"))
    newer = ("2026-06-15 22:06", PLAN)
    d = plan_lookup([older, newer], "16.06.26")
    key = [k for k in d if "ปกรณ์" in k][0]
    assert d[key][0]["return_yard"] == "UNIWISE"  # newer wins
```

- [ ] **Step 2: Run to verify it fails**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_plan_context.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement plan_context.py**

Create `ProjectYK_System/slip_reader/plan_context.py`:
```python
from __future__ import annotations
import re

_DRIVER = re.compile(r"-\s*นาย([^\d\n]+?)\s+\d{3}-\d{3}-\d{4}")
_AGENT = re.compile(r"Agent\.\s*([A-Z][A-Z0-9 ]+)")
_YARD = re.compile(r"คืนลาน([^\s\[\]]+)")
_JOB = re.compile(r"Job\.\s*([0-9\-]+)")
_HEAD = re.compile(r"หัว\s*([0-9\-]+)")

def parse_plan(plan_text: str) -> dict:
    """Split into job blocks by 'Job.'; attach driver(s) found in each block."""
    out: dict[str, list[dict]] = {}
    blocks = re.split(r"(?=Job\.)", plan_text)
    for b in blocks:
        if "Job." not in b:
            continue
        job = (_JOB.search(b) or [None, ""])[1] if _JOB.search(b) else ""
        agent = (_AGENT.search(b).group(1).strip() if _AGENT.search(b) else "")
        yard = (_YARD.search(b).group(1).strip() if _YARD.search(b) else "")
        head = (_HEAD.search(b).group(1).strip() if _HEAD.search(b) else "")
        for m in _DRIVER.finditer(b):
            full = m.group(1).strip()
            first = full.split()[0] if full.split() else full
            out.setdefault(first, []).append(
                {"job": job, "agent": agent, "return_yard": yard, "plate_head": head})
    return out

def plan_lookup(plans_text_by_time, day: str) -> dict:
    """plans_text_by_time: list[(sent_at_str, text)]. Pick the LATEST whose body
    contains the target day token (e.g. '16.06.26'), parse it."""
    candidates = [(t, txt) for (t, txt) in plans_text_by_time if day in txt]
    if not candidates:
        return {}
    candidates.sort(key=lambda x: x[0])
    return parse_plan(candidates[-1][1])
```

- [ ] **Step 4: Run to verify it passes**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_plan_context.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/slip_reader/plan_context.py ProjectYK_System/slip_reader/tests/test_plan_context.py
git commit -m "feat(slip-reader): plan_context — parse daily work-plan, latest-wins"
```

---

## Task 6: entry_builder — assemble draft from readout + plan

**Files:**
- Create: `ProjectYK_System/slip_reader/entry_builder.py`
- Test: `ProjectYK_System/slip_reader/tests/test_entry_builder.py`

**Interfaces:**
- Consumes: `SlipReadout` (Task 4), `parse_plan` output (Task 5).
- Produces:
  ```python
  def build_entry(readout: SlipReadout, *, day: str, plan: dict,
                  slip_line_message_id: str, slip_media_path: str) -> dict | None
      # returns the /api/petty/ingest JSON payload, or None if not a usable slip
  ```
  Rules: if `not readout.is_slip` or `readout.amount is None` → return None.
  `category` mapped from memo keywords (คืนตู้/รับตู้/เข้าท่า → "other";
  เบิก → "driver_advance"; m flow/mflow/ทาง → "toll"; ล้าง → "loading").
  `direction` from readout. `memo` enriched: if the driver's plan entry exists,
  append `" / {agent} {return_yard}"`. `parsed_confidence`: 0.9 if driver found in
  plan, 0.6 if not. `requester_raw` = readout.recipient_name (first name token).

- [ ] **Step 1: Write the failing tests**

Create `ProjectYK_System/slip_reader/tests/test_entry_builder.py`:
```python
from slip_reader.engine import SlipReadout
from slip_reader.entry_builder import build_entry

def _ro(**o):
    base = dict(is_slip=True, amount=1280.0, recipient_name="ปกรณ์",
                memo="ปกรณ์ คืนตู้", ref_code="REF", slip_time="13:53", direction="out")
    base.update(o); return SlipReadout(**base)

PLAN = {"ปกรณ์": [{"job":"26-0914","agent":"YANG MING","return_yard":"UNIWISE","plate_head":"72-1220"}]}

def test_build_basic_payload():
    p = build_entry(_ro(), day="16.06.26", plan=PLAN,
                    slip_line_message_id="618x", slip_media_path="a.jpg")
    assert p["amount"] == 1280.0 and p["site_code"] == "LCB"
    assert p["slip_line_message_id"] == "618x"
    assert p["requester_raw"] == "ปกรณ์"

def test_plan_enriches_memo_and_confidence():
    p = build_entry(_ro(), day="16.06.26", plan=PLAN,
                    slip_line_message_id="618y", slip_media_path="")
    assert "UNIWISE" in p["memo"] and p["parsed_confidence"] == 0.9

def test_no_plan_match_lower_confidence():
    p = build_entry(_ro(recipient_name="ใครก็ไม่รู้", memo="คืนตู้"),
                    day="16.06.26", plan=PLAN, slip_line_message_id="z", slip_media_path="")
    assert p["parsed_confidence"] == 0.6

def test_advance_category_from_memo():
    p = build_entry(_ro(memo="ประจัก เบิก"), day="16.06.26", plan=PLAN,
                    slip_line_message_id="w", slip_media_path="")
    assert p["category"] == "driver_advance"

def test_non_slip_returns_none():
    assert build_entry(_ro(is_slip=False), day="16.06.26", plan={},
                       slip_line_message_id="q", slip_media_path="") is None

def test_no_amount_returns_none():
    assert build_entry(_ro(amount=None), day="16.06.26", plan={},
                       slip_line_message_id="q", slip_media_path="") is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_entry_builder.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement entry_builder.py**

Create `ProjectYK_System/slip_reader/entry_builder.py`:
```python
from __future__ import annotations
import json
from .engine import SlipReadout

def _category(memo: str) -> str:
    m = memo or ""
    if "เบิก" in m: return "driver_advance"
    if "m flow" in m.lower() or "mflow" in m.lower() or "ทาง" in m: return "toll"
    if "ล้าง" in m: return "loading"
    return "other"  # คืนตู้/รับตู้/เข้าท่า ฯลฯ

def _ddmmyy_to_iso(day: str) -> str:
    # "16.06.26" -> "2026-06-16"
    dd, mm, yy = day.split(".")
    return f"20{yy}-{mm}-{dd}"

def build_entry(readout: SlipReadout, *, day: str, plan: dict,
                slip_line_message_id: str, slip_media_path: str):
    if not readout.is_slip or readout.amount is None:
        return None
    name = (readout.recipient_name or "").strip()
    first = name.split()[0] if name.split() else name
    plan_entry = None
    for k, lst in (plan or {}).items():
        if k and (k in name or name in k) and lst:
            plan_entry = lst[0]; break
    memo = readout.memo or ""
    if plan_entry:
        extra = " ".join(x for x in (plan_entry.get("agent",""),
                                     plan_entry.get("return_yard","")) if x).strip()
        if extra:
            memo = f"{memo} / {extra}".strip(" /")
    return {
        "slip_line_message_id": slip_line_message_id,
        "site_code": "LCB",
        "txn_date": _ddmmyy_to_iso(day),
        "amount": float(readout.amount),
        "direction": readout.direction or "out",
        "category": _category(readout.memo),
        "requester_raw": first,
        "memo": memo,
        "slip_media_path": slip_media_path,
        "slip_ref_code": readout.ref_code or "",
        "parsed_confidence": 0.9 if plan_entry else 0.6,
        "parsed_payload_json": json.dumps(readout.__dict__, ensure_ascii=False),
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_entry_builder.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/slip_reader/entry_builder.py ProjectYK_System/slip_reader/tests/test_entry_builder.py
git commit -m "feat(slip-reader): entry_builder — readout+plan -> ingest payload"
```

---

## Task 7: slip_source + mvp_push + run_once — wire the pipeline

**Files:**
- Create: `ProjectYK_System/slip_reader/slip_source.py`, `mvp_push.py`, `run_once.py`
- Test: `ProjectYK_System/slip_reader/tests/test_mvp_push.py`

**Interfaces:**
- Consumes: `build_entry` payloads (Task 6), `get_engine` (Task 4), `plan_lookup` (Task 5).
- Produces:
  ```python
  # slip_source.py
  def company_slips(db_path, group_like="หัวลาก LCB", since=None) -> list[dict]
      # [{message_id, sent_at, media_abspath, day_ddmmyy}], company-side images only
  def day_plans(db_path, group_like, day_ddmmyy) -> list[tuple[str,str]]
  # mvp_push.py
  def push(payload: dict) -> dict      # POST ingest, returns server JSON
  # run_once.py
  def main() -> int                    # one pass; returns count pushed
  ```

- [ ] **Step 1: Write the failing test for mvp_push (mock HTTP)**

Create `ProjectYK_System/slip_reader/tests/test_mvp_push.py`:
```python
import slip_reader.mvp_push as mp

def test_push_sends_token_and_returns_json(monkeypatch):
    captured = {}
    class FakeResp:
        status_code = 200
        def json(self): return {"status": "created", "id": 1}
    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url; captured["headers"] = headers; captured["json"] = json
        return FakeResp()
    monkeypatch.setattr(mp.httpx, "post", fake_post)
    monkeypatch.setattr(mp.config, "SLIP_INGEST_TOKEN", "tok")
    out = mp.push({"slip_line_message_id": "1", "amount": 100.0})
    assert out["status"] == "created"
    assert captured["headers"]["X-Service-Token"] == "tok"
```

- [ ] **Step 2: Run to verify it fails**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_mvp_push.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement mvp_push.py**

```python
from __future__ import annotations
import httpx
from . import config

def push(payload: dict) -> dict:
    r = httpx.post(config.MVP_INGEST_URL, json=payload,
                   headers={"X-Service-Token": config.SLIP_INGEST_TOKEN},
                   timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ingest failed {r.status_code}: {r.text[:200]}")
    return r.json()
```

- [ ] **Step 4: Run mvp_push test to pass**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/test_mvp_push.py -v`
Expected: PASS.

- [ ] **Step 5: Implement slip_source.py**

```python
from __future__ import annotations
import os, sqlite3, re

_DAY = re.compile(r"(\d{2})-(\d{2})-(\d{2})")  # fallback; we derive day from sent_at
COMPANY = ["Miew", "Khao", "Luktan", "ตาล", "หมิว"]

def _media_root(db_path):
    return os.path.join(os.path.dirname(db_path), "line_media")

def company_slips(db_path, group_like="หัวลาก LCB", since=None):
    con = sqlite3.connect(db_path)
    gid = con.execute("select group_id from line_group where name like ?",
                      (f"%{group_like}%",)).fetchone()
    if not gid: return []
    gid = gid[0]
    q = ("select m.line_message_id, m.sent_at, m.media_path, "
         "coalesce(u.alias,u.display_name) who "
         "from line_message m left join line_user u on u.user_id=m.user_id "
         "where m.group_id=? and m.msg_type='image' and m.media_path is not null")
    args = [gid]
    if since:
        q += " and m.sent_at >= ?"; args.append(since)
    q += " order by m.sent_at"
    out = []
    for mid, sent, media, who in con.execute(q, args):
        if not who or not any(c in who for c in COMPANY):
            continue
        dd = sent[8:10]; mm = sent[5:7]; yy = sent[2:4]
        out.append({"message_id": mid, "sent_at": sent,
                    "media_abspath": os.path.join(_media_root(db_path), media),
                    "day_ddmmyy": f"{dd}.{mm}.{yy}"})
    return out

def day_plans(db_path, group_like, day_ddmmyy):
    con = sqlite3.connect(db_path)
    gid = con.execute("select group_id from line_group where name like ?",
                      (f"%{group_like}%",)).fetchone()[0]
    rows = con.execute(
        "select sent_at, text from line_message where group_id=? and msg_type='text' "
        "and text is not null and length(text)>200 order by sent_at", (gid,)).fetchall()
    return [(s, t) for (s, t) in rows if day_ddmmyy in t]
```

- [ ] **Step 6: Implement run_once.py**

```python
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from . import config, slip_source, mvp_push
from .engine import get_engine
from .plan_context import parse_plan
from .entry_builder import build_entry

DB = r"C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db"
GROUP = "หัวลาก LCB"

def main(since=None) -> int:
    engine = get_engine(config.SLIP_ENGINE)
    slips = slip_source.company_slips(DB, GROUP, since=since)
    plan_cache = {}
    pushed = 0
    for s in slips:
        day = s["day_ddmmyy"]
        if day not in plan_cache:
            texts = slip_source.day_plans(DB, GROUP, day)
            texts.sort(key=lambda x: x[0])
            plan_cache[day] = parse_plan(texts[-1][1]) if texts else {}
        try:
            with open(s["media_abspath"], "rb") as f:
                readout = engine.read(f.read())
        except Exception as e:
            print("READ_FAIL", s["message_id"], e); continue
        payload = build_entry(readout, day=day, plan=plan_cache[day],
                              slip_line_message_id=s["message_id"],
                              slip_media_path=s["media_abspath"])
        if not payload:
            print("SKIP non-slip/no-amount", s["message_id"]); continue
        res = mvp_push.push(payload)
        print(res["status"], res.get("id"), payload["requester_raw"], payload["amount"])
        if res["status"] == "created":
            pushed += 1
    print("PUSHED", pushed, "of", len(slips))
    return pushed

if __name__ == "__main__":
    main(since=sys.argv[1] if len(sys.argv) > 1 else None)
```

- [ ] **Step 7: Add a smoke test for slip_source against a tiny fixture DB**

Append to `tests/test_mvp_push.py` (or new `tests/test_slip_source.py`):
```python
import sqlite3, os
from slip_reader.slip_source import company_slips

def test_company_slips_filters_company_side(tmp_path):
    db = tmp_path / "line_archive.db"
    con = sqlite3.connect(db)
    con.executescript("""
      create table line_group(group_id text, name text);
      create table line_user(user_id text, display_name text, alias text);
      create table line_message(line_message_id text, group_id text, user_id text,
        msg_type text, text text, media_path text, sent_at text);
      insert into line_group values('G','Y.K. หัวลาก LCB. ');
      insert into line_user values('u1','Miew','Miew');
      insert into line_user values('u2','นิพล','นิพล');
      insert into line_message values('m1','G','u1','image','', 'G\\2026-06\\a.jpg','2026-06-16 11:00:00');
      insert into line_message values('m2','G','u2','image','', 'G\\2026-06\\b.jpg','2026-06-16 11:01:00');
    """)
    con.commit()
    rows = company_slips(str(db), "หัวลาก LCB")
    assert len(rows) == 1 and rows[0]["message_id"] == "m1"
    assert rows[0]["day_ddmmyy"] == "16.06.26"
```

- [ ] **Step 8: Run all slip_reader tests**

Run: `ProjectYK_System/app/.venv/Scripts/python.exe -m pytest ProjectYK_System/slip_reader/tests/ -v`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add ProjectYK_System/slip_reader/slip_source.py ProjectYK_System/slip_reader/mvp_push.py ProjectYK_System/slip_reader/run_once.py ProjectYK_System/slip_reader/tests/
git commit -m "feat(slip-reader): slip_source + mvp_push + run_once pipeline"
```

---

## Task 8: End-to-end dry-run against real proof slips (local, no server write)

**Files:**
- Create: `ProjectYK_System/slip_reader/dry_run_report.py`
- (uses existing `reports/lcb_slips_0615/` from the proof phase)

**Interfaces:**
- Consumes: everything above. Produces a local Markdown report comparing engine
  readouts on the saved proof slips against the known proof results — no MVP write.

- [ ] **Step 1: Write the dry-run script**

Create `ProjectYK_System/slip_reader/dry_run_report.py`:
```python
from __future__ import annotations
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from .engine import get_engine

SLIP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "lcb_slips_0615")

def main():
    engine = get_engine()
    out = io.open(os.path.join(os.path.dirname(SLIP_DIR), "..", "reports",
                  "slip_reader_dryrun.md"), "w", encoding="utf-8")
    out.write("# Slip-reader dry-run (real proof slips)\n\n")
    out.write("| file | is_slip | amount | recipient | memo | time |\n|---|---|---|---|---|---|\n")
    for f in sorted(glob.glob(os.path.join(SLIP_DIR, "*.jpg"))):
        with open(f, "rb") as fh:
            r = engine.read(fh.read())
        out.write(f"| {os.path.basename(f)} | {r.is_slip} | {r.amount} | "
                  f"{r.recipient_name} | {r.memo} | {r.slip_time} |\n")
    out.close()
    print("wrote reports/slip_reader_dryrun.md")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the dry-run (requires ANTHROPIC_API_KEY)**

Run (from repo root, key set):
`ANTHROPIC_API_KEY=... ProjectYK_System/app/.venv/Scripts/python.exe -m slip_reader.dry_run_report` (run from inside `ProjectYK_System/` so `slip_reader` is importable, or add it to PYTHONPATH).
Expected: writes `reports/slip_reader_dryrun.md` with one row per slip.

- [ ] **Step 3: Verify against proof ground truth**

Open `reports/slip_reader_dryrun.md` and compare the amounts/recipients to
`reports/lcb_petty_ai_accuracy_2026-06-18.md` (e.g. วิโรจน์ 428, ปกรณ์ 1,544.44,
the 3 driver-summary tables → is_slip=False). Confirm the engine matches the
manually-verified proof. Document any mismatch.

- [ ] **Step 4: Commit the dry-run tooling (not the API output if it has account data)**

```bash
git add ProjectYK_System/slip_reader/dry_run_report.py
# do NOT commit reports/slip_reader_dryrun.md if it contains recipient account names
git commit -m "feat(slip-reader): local dry-run report against proof slips"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 = §3 model + status; Task 2 = §4 `mvp_push`/ingest + §5 idempotency; Task 3 = §4 review routes + §7 human-approve gate; Task 4 = §4 engine interface (swappable); Task 5 = §4 `plan_context`; Task 6 = §4 `entry_builder` + plan enrichment; Task 7 = §4 `slip_source` + §5 data flow; Task 8 = §8 testing/preflight against proof. §9 YAGNI items are explicitly excluded (no sheet write, LCB only, no plan UI).
- **Money rules:** amount-from-slip-only (entry_builder returns None without amount, Task 6), human approve (Task 3), idempotency (Task 2 + slip_source dedup by message_id), LCB-only (`site_code="LCB"` hardcoded in build_entry), sheet untouched (no sheet code anywhere).
- **Type consistency:** `SlipReadout` fields used identically in Tasks 4/6/7; `build_entry` payload keys match `PettyIngestIn` (Task 2) and `company_slips` dict keys feed `run_once` (Task 7).
- **Deferred-but-known risk:** RBAC guard exact import for `/petty/review` (Task 3 Step 4) and middleware allowlist for `/api/petty/ingest` (Task 2 Step 5) must be matched to the real `main.py` idioms during implementation — both steps say to copy the existing pattern rather than invent one.
