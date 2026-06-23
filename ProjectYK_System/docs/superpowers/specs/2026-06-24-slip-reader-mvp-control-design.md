# Slip-Reader — MVP On/Off Control (design)

Date: 2026-06-24 · Site: LCB only · Builds on `2026-06-18-lcb-slip-reader-review-design.md`

## Context / why
The LCB slip-reader is deployed on the server and runs every 20 min via the
`YK_SLIP_READER` scheduled task. But โอ is still in **testing** — he does NOT want it
reading real slips and spending API money yet, and he wants to control it himself from the
MVP web UI instead of editing files/tasks on the server. He also said: when he eventually
turns it on, he may turn it on *weeks later* and want it to read back over a chosen date
range; and once it's truly live, it should just continue from where it left off without him
re-entering a date each time.

**Goal:** an on/off switch + "check now" button + optional "read since <date>" field, all in
MVP. **Off must mean zero API spend.** Default state = **OFF** (โอ flips it on when ready).

## Key facts (verified in code)
- `/api/petty/ingest` (main.py:2873) is service-token auth, idempotent by
  `slip_line_message_id` → **re-running never double-posts**. The watermark below is only a
  cost optimisation, not the dedup mechanism.
- RBAC: routes under `/petty/*` and `/api/petty/*` inherit the `petty` menu
  (admin/office = edit, accountant/viewer = view) via `permissions.py` MENUS. New routes
  placed under those prefixes need no permission-matrix change.
- `/api/petty/` is in `PUBLIC_PREFIXES` (session-exempt; token checked in-handler) — the
  service-facing config endpoint goes here.
- New tables auto-create via `create_all` on startup; bump `SCHEMA_VERSION` (22 → 23) for
  the record. No manual ALTER needed.
- Reader is self-contained (`slip_reader/`), talks to MVP only over HTTP.

## Architecture

### 1. State store — `AppSetting` key/value table (MVP)
New `models.py` table `AppSetting(key PK, value TEXT, updated_at)`. A tiny generic
key/value store (first use; reusable later). Helpers `get_setting(key, default)` /
`set_setting(key, value)` in main.py.

Keys used:
| key | meaning |
|-----|---------|
| `slip_reader_enabled` | `"1"` / `"0"` — master switch. Default `"0"` (OFF). |
| `slip_reader_since` | ISO date `YYYY-MM-DD` the reader should read from (watermark / override). Default empty. |
| `slip_reader_last_run` | ISO datetime of the last reader poll (for status display). |
| `slip_reader_last_result` | short text e.g. `"pushed 3, skipped 1"` (status display). |

### 2. Control page — `GET/POST /petty/slip-control` (session UI, admin/office)
A small card page (`templates/slip_control.html`):
- **Status block:** enabled badge (เปิด/ปิด), `อ่านถึงวันที่` (since), `รอบล่าสุด` (last_run +
  last_result).
- **Toggle form:** POST `/petty/slip-control/toggle` → flips `slip_reader_enabled`.
- **Since form:** POST `/petty/slip-control/since` → sets `slip_reader_since` (date input,
  may be blank = continue from watermark). Shown as "อ่านย้อนตั้งแต่วันที่ (เว้นว่าง = อ่านต่อจากเดิม)".
- **Check-now form:** POST `/petty/slip-control/run-now` → sets a one-shot flag
  `slip_reader_run_now="1"`. (We do NOT shell out to the reader from the web process — the
  reader is on the server, runs as its own task. "Check now" just means "don't wait for the
  next 20-min tick": it raises a flag the reader honors immediately on its next poll, and the
  task is scheduled every few minutes so latency is small. Simpler + no cross-process exec.)

Link added to `base.html` nav next to สดย่อย, gated `{% if can_see(request, "/petty/review") %}`.

### 3. Service config endpoint — `GET /api/petty/slip-config` (service-token)
Returns JSON for the reader to read **before doing any API work**:
```json
{"enabled": true, "since": "2026-06-01", "run_now": true}
```
Token-gated exactly like ingest (401 on bad/no token). Reading `run_now=true` is consumed:
the reader, after a successful poll, calls `POST /api/petty/slip-config/ack-run` to clear
the one-shot flag (so "check now" fires once, not forever).

### 4. Reader change — `run_once.py` checks config first
At the top of `main()`:
1. GET `/api/petty/slip-config`. If `enabled` is false **and** `run_now` is false → print
   `DISABLED` and return 0 **before constructing the engine / any Anthropic call**. (This is
   the money guarantee: OFF = no `engine.read`, no API spend.)
2. Determine `since`: if config `since` is set, use it; else fall back to the existing
   2-day rolling window. (When โอ sets a since-date, that wins; when blank in live use, the
   rolling window keeps cost low. The watermark `slip_reader_since` is advanced by โอ or left
   blank — we keep it simple: no auto-advance in this phase; idempotency makes re-reads safe.)
3. After the run, POST a small status back: `slip_reader_last_run`, `slip_reader_last_result`,
   and ack `run_now`. (Reuse one endpoint `POST /api/petty/slip-config/report`.)

`config.py` gains `MVP_BASE_URL` (derive sibling endpoints from `MVP_INGEST_URL`).

### Error handling
- If the reader can't reach `/api/petty/slip-config` (MVP down): treat as **disabled** (fail
  safe — never spend API money when we can't confirm we're enabled). Print `CONFIG_UNREACHABLE`.
- Bad/missing token on any `/api/petty/*` → 401 (existing behavior).
- Web toggle/since/run-now are admin/office only (RBAC). Viewer/accountant can see status (GET)
  but POST is denied by the matrix.

## Testing
- **Unit (slip_reader/tests/):** new `test_run_gate.py` — mock the config endpoint;
  assert that `enabled=false, run_now=false` returns early and `engine.read` is never called
  (use a spy engine). Assert `since` override is passed through to `company_slips`.
- **MVP (app):** test `/api/petty/slip-config` returns 401 without token, correct JSON with
  token; toggle/since POST update settings; `run_now` clears on report.
- **End-to-end on server (manual, โอ asleep — I do it):** with enabled=0, run the task → must
  print `DISABLED`, create no rows, spend nothing. Flip enabled=1 + since=a test date via a
  direct setting write, run → rows appear. Then set back to **OFF** (default test posture) and
  confirm the public endpoint + page show OFF.

## Money / safety (unchanged)
Amount from slip only · all rows `pending_review` → human approve · idempotent · LCB only ·
never write Google Sheet · OFF = zero API spend (the whole point of this change).

## Out of scope (YAGNI)
- Per-interval scheduling from UI (โอ chose on/off only; 20-min tick stays in the task).
- Auto-advancing watermark (kept manual/blank this phase; idempotency covers re-reads).
- The `requester_raw="นาย"` name-prefix bug (separate fix, โอ to approve).
