---
name: project-lcb-jun-xlsx-reimport
description: "LCB Jun cycle — โอ's edits live in LOCAL .xlsx not the Google Sheet; reimport from xlsx + recompute payrun#2. gsheet is now STALE."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4f68d625-1a74-4663-983e-c3ddae9de9a1
---

**2026-06-27:** โอ hand-edited the LOCAL Excel `Work/Salary/2026/6.Jun/LCB/วางบิล YK VOLVO.xlsx` (sheet renamed to **`Daily`**) for cycle 16/5–15/6 — filled missing 15/6+12/6 prices, added OT, corrected 21/5 KLND for นิพล+วิโรจน์ (7,377→4,918, INTENTIONAL, ratio=rev×0.60). 

**KEY GOTCHA:** these edits are in the **local .xlsx ONLY**, NOT the live Google Sheet. The existing `import_lcb_may_jun2026.py` reads gspread → would re-import STALE data and wipe โอ's edits. โอ confirmed **Excel local = source of truth** going forward. New importer `tools/import_lcb_may_jun2026_xlsx.py` (openpyxl, same column-NAME mapping via find(), same source tag `lcb_may-jun2026` + `--wipe-prior`). xlsx layout differs (driver=col5, trip=col29, OT=col32) but find() matches by header text so it's robust.

**Linking trap:** xlsx `driver_raw_name` is FIRST-NAME only ("วิโรจน์"); Employee.full_name is "นาย วิโรจน์ เหมสงวน" → `autolink_drivers.py` matches 0/608. Solution: built first-name→driver_id map from the PRE-reimport backup's already-correct linkage (18 drivers, 0 collisions, วิโรจน์→99 เหมสงวน NOT 39 เสมาทอง). Applied via direct UPDATE locked to that 18-roster map. (ว่าง)=6 rows stay null=0 pay.

**Result (payrun#2 still DRAFT):** recompute via compute_pay_run(recompute=True). Net total **259,888.20 → 287,090.88** (+27,203). Causes verified per-driver: mao drivers up (15/6+12/6 price fills → rev×60% fuel_share up), วิโรจน์ −829 (his 21/5 cut), trip drivers +OT/+special. Backups: `app.db.bak_before_xlsx_reimport_20260627_105540`, `app.db.bak_after_xlsx_reimport_recompute_20260627_105901`.

**Fuel:** ชีท↔ระบบ = ตรง 100% (17,104 L / 686,534.6 ฿, 0 anomaly, price 34.82–42.27 ฿/L). ชีท↔Caltex LINE = **not feasible full-cycle** — archive only covers 12–19 มิ.ย. (262 Caltex msgs in 12–15 window), other 27 days empty. Same data-starvation as [[project-lcb-daily-fuel-crosscheck]].

**2026-06-27 gap-fill + fuel xcheck:**
- โอ gave numbers for 5 unfilled cells: 13/6 นันทสิทธิ์ CJ ค่าเที่ยว=500 พิเศษ=100; 11/6 Nippon rev=5,074 ×4 คน (สุรเดช+สุภาพ=เหมา trip=3,044.40 each per โอ; ประจัก+อภิชาติ trip 350 already). Filled by DailyJob id (1065,1023,1030,1028,1032), not filter. Recompute: net **287,090.88 → 293,475.24** (สุรเดช +3,044, สุภาพ +2,740, นันทสิทธิ์ +600). Backups bak_before/after_gapfill_*.
- **PDF น้ำมัน = ground truth!** `Downloads/รายงานการเติมน้ำมันบริษัท วายเค มิถุนายน 25(2).pdf` = pump (เต็กย้ง เพิ่มทรัพย์/Caltex) full report, 17pp, **whole fleet** 1–22 มิ.ย. Parse via pypdf (installed in venv), regex `seq date plate station Diesel-type liter price amount balance`; skip วายเครูดบัตร/แสกน payment lines. 431 fuel rows.
- **Fuel xcheck result (1–15 มิ.ย. overlap):** LCB-plate PDF ฿305,160 vs DB ฿300,348 = **Δ +4,812 (1.6%)**. 11/18 drivers match EXACTLY incl all big เหมา (วิโรจน์/นิพล/ณัฐวุฒิ/สุรเดช). Apparent per-driver swaps (พัฒิยะ+4,495 / สันติพงษ์−4,495) were a **plate-attribution ARTIFACT** of my "dominant owner" estimate — they SHARE plate 71-8684 (สันติพงษ์'s 72-1219 was อุบัติเหตุ 1–9 มิ.ย.); system attributes per daily work-log = correct. Real residual = 6 plates totaling +4,812, biggest 71-8681 +3,038, likely cycle-boundary date diffs. **No payroll-material fuel error found.** Note: pump report dating did NOT shift-match (±1 day worse than 0).

**STILL OPEN:** payrun#2 not finalized (โอ verifying). All on DEV only — server not yet synced (full-file overwrite path per [[project-lcb-mixed-mode]] when ready). Builds on [[project-lcb-driver-extra-fees]] [[project-lcb-mixed-idle-days]] [[project-lcb-payroll-may-jun-2026]].
