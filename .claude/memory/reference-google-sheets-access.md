---
name: reference-google-sheets-access
description: "How Claude reads/edits โอ's Google Sheets (service account + gspread); the Daily LCB sheet id + validation gotcha"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6182d152-ce07-4450-aa05-40ab887fdf30
---

Claude can read AND edit โอ's Google Sheets via a service account (not OAuth/browser).

**Setup (done 2026-06-17):**
- Service account key: `noble-history-446303-e4-c36409a0122c.json` at repo root — gitignored (`noble-history-*.json` + `*service*account*.json` patterns added). NEVER commit; it can edit any sheet shared to it.
- Service account email: `yk-sheets-editor@noble-history-446303-e4.iam.gserviceaccount.com` — share a sheet to this email as **Editor** to grant access.
- GCP project `907583740329`: **Google Sheets API** enabled. Drive API NOT enabled → must open by key (`gc.open_by_key(ID)`), not by name (`gc.open('title')`).
- Lib: `gspread` installed in `ProjectYK_System/app/.venv`.
- Run with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` or Thai prints crash (cp1252).

**Gotchas learned:**
- Sheets API limit ~60 reads/min/user → batch reads, sleep ~30s after a 429. Don't fetch metadata per-tab in a tight loop.
- An .xlsx uploaded to Drive (URL has `rtpof=true`) is NOT a real Google Sheet — API errors "must not be an Office file". User must do File→Save as Google Sheets, then re-share the NEW file (permissions don't carry over).
- To read formulas (not computed values): `ws.get(rng, value_render_option='FORMULA')`. Data validation rules live in `fetch_sheet_metadata` under `dataValidation`.

**"Daily LCB" sheet (เดลี่แหลม / เดลี่แหลมฉบัง):** see [[project-daily-lcb-sheet]].
