---
name: project-lcb-payroll-may-jun-2026
description: LCB payroll 16/5–15/6 (tag 2026-06) — import DONE + draft payrun #2 computed; remaining = petty/เบิก deductions + ปกรณ์/วราวุฒิ mode decision + finalize
metadata: 
  node_type: memory
  type: project
  originSessionId: 6182d152-ce07-4450-aa05-40ab887fdf30
---

**Status 2026-06-18: import + draft payrun DONE on Dev** (cycle_tag confirmed `2026-06`, LCB 16→15 verified in code).

**Done this session:**
- Imported เดลี่แหลม tab `Daily 16.05.69 - 15.06.69` straight via gspread (แบบ1) → **609 DailyJob rows**, source tag `lcb_may-jun2026`. Script: `ProjectYK_System/tools/import_lcb_may_jun2026.py` (sibling of import_lcb_jan2026.py; reusable mapping verified vs header). `เงินเบิก`/`ค่าเสียเวลา` columns intentionally NOT imported (โอ: those live in สดย่อย/petty).
- Linked driver_id on 603 daily + 385 fuel rows to the 18 existing LCB employees (only `(ว่าง)` placeholder = 6 parked rows left null, 0 pay). Reactivated emp 84 พัฒิยะ + emp 85 รัฐภูมิ (status active; โอ confirmed still working).
- Created **draft PayRun id=2** (status=draft, NOT finalized), 18 drivers, **net total 566,145.32**. เหมาน้ำมัน gross=0 issue from พ.ค. did NOT recur (fixed by linking); no net-negative.
- Fixed cosmetic note bug in `services/payroll.py` (lcb_trip branch ~line 812): mid-month hires (e.g. วราวุฒิ start 23/5) now show "ยังไม่เริ่มงาน Nวัน" instead of mislabeled "ลา/ขาด". Money unchanged. Base IS correctly prorated by days-present (base in base_salary_earned + care in care_allowance_earned — two fields, sum = prorated 12,240).
- Backups before each write: `app.db.bak_before_lcb_may-jun_import_*`, `app.db.bak_before_lcb_link_*`.

**Status 2026-06-24: เงินเบิก IMPORTED + recomputed. Net จ่ายจริง 395,719.38** (still draft).
- Source = `Work/Salary/2026/6.Jun/LCB/สรุปเงินเบิกแหลม  16-05-15-06.xlsx`, sheet **สดย่อย col O** ("พขร.เบิก หัก"). โอ confirmed: deduct EVERYTHING in col O as หมิว entered (เงินเบิก + เบิกค้างรอบก่อน "ไม่ได้หักรอบ5" + รับตู้/เข้าท่า/ค่าน้ำ + ค่าผ่อนอุบัติเหตุ500). NOT the สรุป col I (col O > col I by ~21k because col O carries prior-cycle unpaid advances; col I omits them).
- Importer: `tools/import_lcb_jun2026_petty.py` (source tag `lcb_jun2026_petty_O`, one consolidated PettyCashTxn/driver, deduct_from_driver=True, pending, tag 2026-06). Re-runnable. **Matching LOCKED to payrun#2's 18 driver_ids** — caught วิโรจน์ collision: เหมสงวน[99] is the real LCB driver, เสมาทอง[39] is a different person; naive first-name match grabbed 39. Always lock to payrun roster.
- Recompute via `compute_pay_run(s, pr, recompute=True)` (standard engine path = the in-app button). 18 rows, petty 170,788.58.
- **วันชัย พิมพยอม (2,000)** in sheet but NOT in payrun#2 → SKIPPED, deduct next cycle (note it).
- **พัฒิยะ (emp84)**: net 8,792 < เบิก 10,270 → โอ said deduct full, allow net NEGATIVE -1,478 (driver owes the overage).
- Backups: `app.db.bak_before_lcb_jun_petty_import_*`, `app.db.bak_before_jun_recompute_*`.
- Accident installment system EMPTY (0 rows) → the 500-baht อุบัติเหตุ lines in col O are NOT double-deducted.

**Status 2026-06-24 (later): ปกรณ์+วราวุฒิ SWITCHED to lcb_mao** (โอ confirmed after seeing numbers). Both now เหมา: pay_mode=lcb_mao, drivers pay own fuel (~38k each). net dropped ~69k→~20k each (ปกรณ์ 19,518 / วราวุฒิ 22,050). Backup `app.db.bak_before_mao_switch_*`. Recomputed via compute_pay_run.
- **NEW payrun#2 total: net จ่ายจริง 298,275.60** (was 395,719 before mao switch). 18 คน: 8 mao / 10 trip. เบิก unchanged 170,788.58. พัฒิยะ still -1,478.

**Remaining before finalize (NEXT):**
1. PayRun #2 still **draft** — โอ has NOT said finalize yet (last session he paused). All numbers settled; just needs his go.
3. (Unrelated) Old LCB พ.ค. trips (508 rows source `reimport_lcb_daily`, 16/4-15/5) — โอ considered deleting but said "ขอคิดดูก่อน". They do NOT interfere with มิ.ย. (separate dates). Don't delete without re-confirm; deleting breaks payrun#1 recompute.
4. Prior-cycle leftover: 67 petty rows tagged 2026-05 (~93,121) still pending — belongs to LCB 2026-05, separate.

**โอ wanted to do this "in the system" not in sheets** — no own Excel/PDF for this cycle exists yet (Salary/2026 only goes to 5.May), so DON'T look for ground truth to compare; this IS the first authoritative run.

**All on Dev only — NOT server.** Server (app.yklogistics.uk) has its own fresh DB, no gspread/git; pushing to it is a separate decision later. See [[reference-mvp-server-deploy]] [[project-daily-lcb-sheet]] [[reference-google-sheets-access]] [[project-audit-lcb-may2026]].
