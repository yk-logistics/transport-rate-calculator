---
name: project-daily-grid-edit-ux
description: "/daily grid got Undo/Redo, Fullscreen, pagination, and an edit-log (DailyJobAudit) — DONE+deployed 2026-06-26"
metadata: 
  node_type: memory
  type: project
  originSessionId: 861f199b-b8da-4a59-9259-2c834a013a0e
---

/daily already served `daily_grid.html` (Tabulator) with inline edit + manual "Save Grid" + dirty-highlight + missing filter — but โอ never noticed. Added (DONE + live at app.yklogistics.uk 2026-06-26):

- **Edit log:** `DailyJobAudit` model (models.py, mirrors DispatchPlanAudit) — SCHEMA_VERSION 23→24, created by `create_all` (no manual ALTER). `daily_grid_save` snapshots old values, writes one audit row per changed field (changed_by = current_user.username, action=edit). `GET /api/daily/{id}/audit` + per-row "ประวัติ" button → modal.
- **Undo/Redo** of unsaved cell edits (Ctrl+Z / Ctrl+Shift+Z + toolbar buttons); client-only stack in cellEdited, `replayingHistory` guard. Only BEFORE Save (after save → use the log).
- **Fullscreen** button (Fullscreen API on `.yk-grid-fs-target`).
- **Pagination** 100/page + toggle "แสดงทั้งหมด" — fixes โอ's "ตารางเริ่ม 25/5 ไม่ใช่ 16/5" which was just the default `limit=400` newest-first cap, NOT missing data (all 1117 rows present).
- Save button made prominent (💾).

**UPDATE 2026-06-27 (deployed):** the `limit=400` newest-first cap caused a NEW confusion — filtering a column header (e.g. status_code='DHL Overflow', 111 rows total) showed only 7 because client-side header-filter only sees the loaded 400 (which reached back only to 26 May). Fix evolved through 2 commits:
1. Added "โหลดทั้งหมด (ไม่จำกัด)" checkbox → `limit=0` = server returns ALL matching rows (no cap). But still required a manual tick → bad UX.
2. First tried MONTH-scoping (calendar month) — but โอ rejected: "เดลี่ควรเป็นตามรอบเงินเดือนแต่ละไซต์สิ ถ้าแหลมฉบัง 16-15". Calendar month is WRONG for ops because pay cycles differ per site (LCB 16→15, AYU 26→25, BIGC 1→end).
3. **FINAL (deployed 2026-06-27): default range = PAYROLL CYCLE per site.** `/daily` takes `cycle=YYYY-MM` (tag=month cycle ends). New helper `_site_payroll_cycles(site, today, n=12)` → list of cycles newest-first, reusing existing `_month_bounds(year,month)` + `_shift_year_month`. Resolution in `daily_list`: **anchor = max(work_date) in DB, NOT today** (so default cycle covers the latest DATA, not an empty future cycle — data here ends 15/6 while today is 27/6). If site selected → cycle dropdown shows that site's cycles, default = cycle covering anchor; if no site → default ~2 calendar months ending at anchor's month. "ทุกรอบ"(cycle=all) = no date limit. Manual d_from/d_to overrides cycle; cycle dropdown `disabled` until a site is picked. Site change reloads (server regenerates cycle list). AJAX still built from server-resolved dates (Jinja `|tojson`). Verified: LCB 16/5–15/6=608, LCB 16/4–15/5=508, all-cycles+DHL=111, no-site=829. **Removed** the `month`/`avail_months`/`_month_range_str` from step-2 (superseded). Avoid 2nd `_month_bounds` def — name collision at main.py:~7017.

Backups: `app.db.bak_before_dailyaudit_*` (dev + server). audit is INSERT-only, didn't touch existing data. Ctrl+Enter batch-apply path does NOT push undo (only single-cell edits do — acceptable). Spec: `docs/superpowers/specs/2026-06-26-daily-grid-edit-ux-design.md`. Deploy = copy main.py+models.py+daily_grid.html, restart → schema auto-bumps via create_all on lifespan (verified schema_version=24 on server). See [[reference-mvp-deploy-restart-gotcha]], [[project-merge-daily-grid]].
