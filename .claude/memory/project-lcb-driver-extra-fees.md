---
name: project-lcb-driver-extra-fees
description: "LCB driver-pay change (พิเศษ from sheet not 100/trip, +OT +รับตู้แทน) — preflight done, STOPPED at a money fork before recompute"
metadata: 
  node_type: memory
  type: project
  originSessionId: 861f199b-b8da-4a59-9259-2c834a013a0e
---

Task: make LCB driver income read 4 sheet cols AL–AO — ค่าเที่ยวพขร.(=trip_fee_driver, already right), รับตู้แทน, OT, พิเศษ. โอ-confirmed: **พิเศษ = manual sheet number, STOP using engine's auto 100/trip**; add OT + รับตู้แทน to all 3 LCB modes; runs not-finalized only; P–V (ยกตู้/ผ่านลาน/คลีน/ชอร์/เข้าท่า/ชั่งน้ำหนัก) = สำรองจ่าย, NOT driver pay. Spec: `docs/superpowers/specs/2026-06-25-lcb-driver-extra-fees-from-sheet-design.md`. Preflight tool: `tools/preflight_lcb_driver_fees.py` (read-only).

**DONE + DEPLOYED 2026-06-25.** โอ confirmed **คนเหมาไม่ได้พิเศษ** → zeroing mao พิเศษ is correct, not underpay. Engine `services/payroll.py`: new `_sum_lcb_driver_extra_fees(session,emp_id,start,end,site_code)` sums special/ot/pickup_return from DailyJobFee; lcb_trip & lcb_mixed add all three, lcb_mao adds only OT+pickup (no พิเศษ); old 100/trip formula + `_count_trips` removed. detail template: removed flat "+100".

**Recompute scope decision (important):** only **run 2 (June, draft)** recomputed — both local and server. **Run 1 (May, draft) deliberately LEFT untouched**: a full recompute of run1 swung net +661k because run1 held STALE May-27 items with the old "Gross revenue 0.00 × 60%" bug (revenue not yet filled → huge negatives like −84k). That correction is real but is NOT what โอ asked for, so I restored run1 from backup (`app.db.bak_before_lcb_extrafees_*`) to its prior stored state. **If โอ wants run1 refreshed too, that's a separate decision** — its numbers will jump massively (and probably become correct). Server run1 was NOT recomputed either.

emp86 run2: net 16,335, other_income 1,200 (was พิเศษ 2,200 via 100/trip → now 1,200 manual; net −100 after tax). Live verified at app.yklogistics.uk. Preflight tool kept: `tools/preflight_lcb_driver_fees.py`. Display single-table from [[project-lcb-mixed-mode]].
