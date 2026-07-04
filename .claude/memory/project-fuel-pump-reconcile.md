---
name: project-fuel-pump-reconcile
description: CLI tool reconciling pump fuel-report PDF ↔ FuelTxn for an LCB cycle; built TDD 2026-06-27 on branch feat/fuel-pump-reconcile (not merged).
metadata: 
  node_type: memory
  type: project
  originSessionId: 4f68d625-1a74-4663-983e-c3ddae9de9a1
---

**Built 2026-06-27** (branch `feat/fuel-pump-reconcile`, NOT merged yet). Read-only CLI at `ProjectYK_System/tools/fuel_pump_reconcile/`. Reconciles the **monthly pump fuel-report PDF** (เต็กย้ง เพิ่มทรัพย์ = Caltex AR report; ground truth, whole fleet, full month) against **FuelTxn** in app.db for one pay cycle.

**Why:** confirm system fuel (drives เหมา drivers' `fuel_cost_self` deduction) matches what the pump billed, before finalizing payroll. Replaces the data-starved LINE-message source of [[project-lcb-daily-fuel-crosscheck]].

**5 modules + TDD (15 tests pass):** `pdf_parser` (pypdf, regex `seq date plate station Diesel-type liter price amount balance`, skips วายเครูดบัตร/แสกน payment lines), `db_loader` (FuelTxn by source+cycle, resolves pay_mode from PayRun item), `matcher` (greedy plate+amount match, ±3-day drift — pump dates fill-day, system dates work-day; + `driver_impact()` aggregates เหมา/mixed only), `report` (HTML+MD to reports/), `run_reconcile.py` CLI.

**Run:**
```
python ProjectYK_System/tools/fuel_pump_reconcile/run_reconcile.py \
  --pdf "<May.pdf>" --pdf "<June.pdf>" \
  --cycle-start 2026-05-16 --cycle-end 2026-06-15 \
  --source-tag lcb_may-jun2026 --cycle-tag 2026-06
```
A cycle (16→15) spans 2 month PDFs. PDFs in `C:\Users\guole\Downloads\รายงานการเติมน้ำมันบริษัท วายเค <month> ...pdf` (June has versions (1)-(5); use latest). pypdf installed in app venv.

**Real run result (16/5–15/6):** pump LCB ฿638,917 vs system ฿686,535, **Δ −47,618 (−6.9%, system higher)**, 337 matched / 22 pump_only / 47 system_only. 8 เหมา/mixed flagged net-negative (system>pump).

**KEY interpretation (โอ must weigh, tool can't decide):** the net-negative is **NOT proven over-deduction**. Two causes mixed: (1) this PDF = ONE vendor (เต็กย้ง/Caltex); fills at other stations (ปตท. etc.) aren't in it → system legitimately has more. (2) per-driver split uses crude plate→dominant-owner, skewed by SHARED plates (พัฒิยะ/สันติพงษ์ share 71-8684). Report carries a Thai caveat saying so. Even drift=7 leaves ~40 unmatched → mostly station-coverage, not date-lag. **To prove fully would need all-vendor pump reports.** Payroll-material conclusion stands: เหมา totals reconcile within station/date noise; 3 mao tied exactly earlier.

**STILL OPEN:** branch not merged (awaiting โอ review); MVP web page deferred (CLI-first per โอ). Builds on [[project-lcb-jun-xlsx-reimport]] [[project-lcb-daily-fuel-crosscheck]].
