---
name: project-lcb-mixed-mode
description: "LCB lcb_mixed per-day เหมา/เที่ยว pay mode — design APPROVED, implementing on branch (TDD). Spec at docs/superpowers/specs/2026-06-24-lcb-mixed-mao-trip-design.md"
metadata: 
  node_type: memory
  type: project
  originSessionId: 14188e73-c52b-42bd-9264-dc15f80835e0
---

**Goal:** new LCB pay_mode `lcb_mixed` for drivers who run บางวันเหมา บางวันเที่ยว in one cycle (เคส A = เปลี่ยนระบบกลางรอบยาวๆ; เคส B = ย้ายรถกระทันหันบางวัน → จ่ายเที่ยววันนั้น). Real cases this cycle: **พชร emp86, สุรเดช emp91** (currently lcb_trip). Possibly สุภาพ emp100 too.

**Design (โอ-approved 2026-06-24):**
- 1 PayRunItem/คน (NOT 2 lines). engine classifies each DailyJob day per-day.
- **Rule: ratio = trip_fee_driver/revenue_customer.** rev>0 & ratio≈0.60(±0.05) → mao day; rev>0 & low (~0.07) → trip day; rev=0 → ambiguous/skip (no money). Verified vs sheet: ratio=60.0% EXACT matches พี่ตาล's blue-text days every working day. Blue color = SECONDARY signal only (พี่ตาล may forget). โอ: ratio first, ask if ambiguous.
- mao part: Σrev(mao days)×0.60 − Σfuel(mao days self). trip part: Σtrip_fee(trip days) + พิเศษ100×เที่ยว(trip days only).
- **base+care (9240+3000): prorate by TRIP days only** (mao days have no base). โอ confirmed.
- SS/tax/petty/deposit/accident: computed ONCE for whole person (1 item), unchanged path.
- Slip: 1 ใบ, แสดงแยกส่วนเหมา/เที่ยว (โอ picked this over 2-line). Uses existing fields fuel_share_income vs trip_fee_total → no schema change.
- generic (future drivers), MUST NOT change other 16 drivers' numbers (regression: net identical).
- NO per-day mode column in DailyJob (ratio is enough, YAGNI).

**Implementation approach:** branch (not main — money engine). TDD. Units: `_classify_lcb_days()`, fuel-for-day-subset, `lcb_mixed` branch in calc_one_employee (services/payroll.py ~line 824 near lcb_mao), slip template. Tests: classify unit + พชร/สุรเดช real-data calc vs โอ hand-calc + regression 16 ครู unchanged + read-only preview before write.

**Context this builds on:** [[project-lcb-payroll-may-jun-2026]] — payrun#2 (2026-06) draft, 18 คน, petty deducted (net 298,275 after ปกรณ์/วราวุฒิ→mao). พชร/สุรเดช still lcb_trip pending this feature. NOT finalized.
