---
name: project-lcb-jun-audit-round2
description: "2nd full audit of LCB payrun#2 (มิ.ย. 16/5-15/6, draft net 268,457.69) — what's confirmed-correct + the one real open item (26/5 2,000 rows DB vs Excel)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9cbd7456-99c5-4547-b7e4-19b56411726b
---

**2026-06-29:** โอ asked for a fresh full correctness audit of LCB cycle 16/5–15/6 (PayRun **id=2**, draft, live net **268,457.69**, 18 drivers; whole run recomputed today 04:10). Covered all 8: daily↔pay, petty, deposit งวด, SSO, วันหยุด/ลา/เริ่มงาน/รถจอด, fuel หัก/ไม่หัก. Ran via bill-checker subagent, then **I verified the money-material findings against engine code** before reporting (key — the agent didn't know the codebase).

**CONFIRMED CORRECT (told โอ "ผ่าน"):**
- Petty: all 18 match สดย่อยวังน้อย.xlsx exactly. วันชัย(81) 2,000 carry stays in 2026-05, NOT deducted in มิ.ย. (correct).
- Deposit ประกันตน: all 18 deducted exactly 1,000 this cycle, งวด numbers match บันทึกประจำเดือน หัวลาก.xlsm, no over/under deduction (วราวุฒิ 1/10 first).
- SSO: พิชิต(93)+สุภาพ(100)=0 correct (ss_exempt). Others 462 or correctly prorated (วราวุฒิ 358, พัฒิยะ 328). ชยุต(95)+เนื้อ(87)=0 because Employee.social_security_base=0 (matches sheet; data-quality nit only — no explicit ss_exempt flag).
- รถจอด/mixed: พชร+สุรเดช idle days included in mao divisor (note "รวมจอดช่วงเหมา"). Not dropped.
- Fuel ไม่หัก: only **3 entries** exclude_from_driver=1 (วราวุฒิ 1 first-tank 3,920; สุภาพ 2 first-tank 8,288.20) — small, as โอ expected. 7 trip drivers all fuel_cost_self=0 correct.

**FALSE ALARMS the subagent raised — DO NOT re-flag (engine works as designed):**
- รัฐภูมิ −330 / ปกรณ์ −880 "revenue lower than DB" = **KB deduction**, NOT a bug. Engine mao gross = `_sum_gross_revenue` → `driver_calc_price(r)` = (price_override ?? revenue_customer) − **kb_amount** ([[project-kb-driver-calc-price]]). Verified: รัฐภูมิ KB=330, ปกรณ์ KB=880, พิชิต KB=220 — deltas == KB exactly. Excel ค่าขนส่ง = raw rev (no KB) because KB is system-only/ใต้โต๊ะ. **Lesson: any mao "revenue < raw daily sum" delta — check kb_amount first.**
- สุรเดช mao "doesn't reconcile" = mixed-mode `_classify_lcb_days` split working (note "เหมา 8วัน", fuel_share 33,324×0.6=19,994.4 checks out). Not a bug.

**RESOLVED 2026-06-29 — the 26/5 2,000 rows were งานยกเลิก (โอ did วางบิล manually, never paid driver):**
- นิพล(97) row id=716 + สุภาพ(100) id=715, work_date 26/5, were `status=KAO, rev=2,000, trip=1,200, ตู้="ยกเลิก", pickup="คาโอDC อมตะ"`. โอ: "ตัดออก" + wants driver to see it as **a normal รถจอด idle day, NOT a cancelled job**.
- **GOTCHA: option "price_override=0" alone does NOT hide it from the driver** — the slip (`build_payroll_slip_context`) passes ALL daily_jobs to the template, so the row would still show "KAO · คาโอDC อมตะ · ตู้ ยกเลิก · 0฿" = looks like worked-for-nothing. To make it read as plain idle: set `revenue_customer=0, price_override=0, trip_fee_driver=0, status_code='รถจอด'`, clear origin/pickup/destination/container_no, and stash original detail in `remark`.
- Applied to both rows + recomputed payrun#2. **Net 268,457.69 → 266,057.69 (−2,400; only นิพล −1,200 + สุภาพ −1,200, other 16 unchanged — regression clean).** Backup `app.db.bak_before_cancel_kao_26may_20260629_173342`.
- **DEPLOYED to server 2026-06-29** (โอ said go; payrun stays DRAFT). Before deploy, proved no clobber of the parallel session: diffed local vs server payrun nets — server matched local on all 17 other runs incl AYU#18=205,892.10 (the other session's work, already on server), only LCB#2 differed (local newer). Verified live: server LCB#2=266,057.69, AYU#18=205,892.10 intact, 8020 archiver up, public 200.
- **DEPLOY GOTCHA (new):** `deploy_mvp.sh --with-db` FAILED at the DB scp ("dest open Failure") because it copies app.db at step 2b BEFORE stopping the app → Windows file lock (running app holds app.db open). Server DB was NOT corrupted (open-for-write failed outright, wrote nothing; backup was already made). Fix = manual order: Stop-ScheduledTask YK_MVP_APP → kill 8010 owner *only if cmdline matches YK_MVP* (spares 8020 archiver) → confirm db unlocked → scp app.db → verify byte-size == local → Start-ScheduledTask. The `--with-db` path of the script needs reordering (stop before DB copy). Used [[reference-deploy-mvp-selfverify]] tool but its --with-db step is broken for a live app.
- Lesson: any 2,000 KAO row at คาโอ with ตู้="ยกเลิก" = cancelled job, manual-billed, driver not paid → exclude from driver calc + render as รถจอด.

**Oatside / DHL Overflow ราคากลาง = 5,500 CONFIRMED:** 19 "DHL Overflow" rows this cycle (all เนื้อ id 87) every one `price_override=5,500`, real billing rev 7,264–7,456 (fuel-linked). System splits correctly ([[project-dhl-overflow-rate]]). เนื้อ is lcb_trip so 5,500 is slip/CFO display only, not his pay base. (2 JGL rows also =5,500 but different customer, coincidental.)

**Minor flags reported (low):** สุวิทย์(90) fueled นิพล's plate 71-6802 28/5 (2,353.20) — สุวิทย์ trip so no impact on him; if it should be นิพล(mao) it'd reduce นิพล. Likely shared-plate/cross-fuel (normal per [[project-lcb-fuel-crosscheck-domain-rules]]). อภิชาติ SSO 448 vs sheet 446.6 = 1.40 rounding. 6 "(ว่าง)" รถจอด rows plate 71-8684 rev=0 (no money impact). xlsm "LCB" tab header still says old cycle label (16เม.ย.–15พ.ค.) but data is มิ.ย. cycle.

Builds on [[project-lcb-jun-payroll-audit-fixes]] [[project-lcb-jun-xlsx-reimport]] [[project-lcb-deposit-sso-resync]] [[project-kb-driver-calc-price]]. Payrun still DRAFT.
