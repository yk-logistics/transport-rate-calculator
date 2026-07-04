---
name: project-lcb-jun-payroll-audit-fixes
description: LCB Jun-2026 payrun
metadata: 
  node_type: memory
  type: project
  originSessionId: 753a7f01-eac1-414e-8a78-baab59aa8d42
---

**2026-06-28:** AI-audited LCB payrun #2 (มิ.ย., draft, net 257,497.09, 18 drivers) vs ground-truth Excel in `Work/Salary/2026/6.Jun/LCB/`. Report saved there as `ตรวจสอบเงินเดือน_มิย_โดยAI.md`. Five findings + โอ decisions:

**1. INCOME TAX — too high, fix the formula (โอ: ควรหักภาษี แต่ยอดน้อยลง).** Engine `_compute_income_tax_withholding` (payroll.py:457-533) projects annual income as `gross_THIS_month × remaining_months` — extrapolates ONE high month (June เหมา gross ~90k) ×6 → over-states → withholds 15,539 total across 8 mao drivers (วิโรจน์ 3,370 … รัฐภูมิ 346). **โอ wants YTD-average method:** projected_annual = `actual_YTD_gross_incl_current + (YTD_avg_per_month × remaining_months)`, where avg = YTD_gross/months_elapsed (real months in DB). Minus tax already withheld YTD, spread over remaining cycles. **PLUS add ประกันสังคม as ลดหย่อน** (currently only 50%-expense-cap-100k + 60k personal allowance). Result with this method ≈ **4,150 total** (วิโรจน์ 1,253, วราวุฒิ 1,792 high only because few months of data → self-corrects). YTD gross history DOES exist: COPY-LOCK runs stored gross=net so Jan–May is usable (ปกรณ์ 6mo, วิโรจน์ only 2mo since late start). **Also โอ wants: a ภาษี page + show เงินสะสม/ภาษีสะสมทั้งปี on the slip.**

**2. SSO base mismatch.** Engine imputes 9,000 SS base for lcb_mao when Employee.social_security_base<=0 (payroll.py:1129-1139). But ground-truth sheet `บันทึกประจำเดือน หัวลาก.xlsm`/SSO col C = real base (C=0 means not submitting). **พิชิต(93)** C=0 but sys deducts 407; **สุภาพ(100)** DB base=9240 but sheet C=0, sys deducts 462 → both should be 0 (set their Employee.social_security_base=0). เนื้อ/ชยุต already 0 OK. **โอ: new hires count SS by start-date − leave (proration)** = already what engine does, so วราวุฒิ(101) prorated 358 is fine (he's new 23/5, not in sheet yet). Deposit (ประกันตน, SSO col F) all CORRECT.

**3. Fuel duplicate.** 2 dup FuelTxn pairs (same date/plate/liter/amount, diff daily_job_id): นิพล(97) 27/5 71-6802 60L=2,473.20 ×2 (นิพล=mao → over-charged 2,473 IF single real fill); ประจัก(89) 23/5 30L=1,266 ×2 (trip, no $ impact). **โอ: if truly dup, remove.** Verify against pump source first. (System fuel total 686,534.60/17,104L matches prior pump-PDF verification; Caltex sheet is only a subset.)

**4. Trip/special/OT deltas Excel≠system (~6,347 total).** **โอ: ยึด Excel เป็นหลัก** → sync AD(ค่าเที่ยว)/AF(พิเศษ)/AG(OT) from `วางบิล YK VOLVO.xlsx` sheet `Daily`. NOTE: for the 4 biggest-delta drivers (ปกรณ์+2899, ณัฐวุฒิ+2899, นิพล−1200, สุภาพ−1200) they're all **lcb_mao** → AD doesn't add to pay directly (gross from revenue×60% via fuel_share_income; revenue_customer already matches sheet col U). Real pay impact is on TRIP drivers' พิเศษ/OT (เนื้อ+300, สุวิทย์+700, ประจัก+600 etc.) ≈ +2,850 total.

**5. วันชัย(81)** resigned 1/5 (inactive), correctly excluded from June run, but has 2,000 เบิก in JUN26 uncollected. **โอ: carry to next cycle, deduct next round** (เขาพึ่งกลับมาทำงาน). วราวุฒิ(101) also missing bank account_no in DB → can't pay by transfer until added.

Builds on [[project-lcb-jun-xlsx-reimport]] [[project-multisite-payroll-onboard]] [[project-lcb-may-lock-pdf]]. Tax fix is the priority money item. All still DEV/draft — not finalized, not deployed.

---

**IMPLEMENTED 2026-06-28 (branch `fix/lcb-income-tax-ytd-method`, 4 commits, all tests pass, DRAFT — not finalized/deployed):**

1. **Tax engine fixed in TWO steps.** (a) YTD-average projection (not single-month ×remaining) + ประกันสังคม ลดหย่อน → 15,539→4,150. (b) **โอ then said tax base for เหมาน้ำมัน = รายได้หลังหักน้ำมัน "เฉพาะคนเหมาน้ำมัน"** → changed taxable income to `(gross − fuel_cost_self)` for current+YTD. fuel_cost_self=0 for trip/office so auto mode-correct. Result: **tax → 0 all 8 (real post-fuel income < 150k threshold)**, net 273,036. (`_compute_income_tax_withholding` now uses `_real_income()` helper + `avg_monthly_income`.) 5 unit tests in `tests/test_income_tax_ytd.py`.
2. **SSO**: added `custom_terms {"ss_exempt": true}` flag (mirrors tax_exempt) that skips the 9,000 impute + zeroes SS. Applied to พิชิต(93)+สุภาพ(100) → −869, net 273,905.
3. **Fuel "dup" = NOT a dup.** Pump PDF (`Downloads/รายงานการเติมน้ำมัน...พฤษภาคม 2569.pdf`) shows นิพล 71-6802 really filled 60L on BOTH 26/5 AND 27/5 (system has one mis-dated to 27/5, same cycle → no $ impact). ประจัก same (22/5 twin fills). **Removing would UNDER-charge — left as-is.** Always check pump source before deleting "dups".
4. **Excel sync (ยึด Excel)**: synced พิเศษ(AF) 100→200/day + นันทสิทธิ์ trip −350 for trip/mixed drivers only (35 special + 1 trip rows, +2,950). **Skipped AD for mao drivers** — mao gross from revenue×60%, ignores trip_fee_driver (writing it would mislead). Final net **276,854.75**.
5. วันชัย(81) 2,000 เบิก → carry to next cycle (โอ). วราวุฒิ(101) still no bank account_no.

**UI**: slip (`payroll_print_all.html`) shows รายได้สะสม/ภาษีสะสมทั้งปี per driver; new page `/payroll/{id}/tax` (`payroll_tax.html`) + button on payroll detail. helper `_ytd_income_tax_by_emp`.

**Net progression**: 257,497 (audit) → 273,036 (tax→0) → 273,905 (sso) → **276,855 (excel sync)**. All DB changes backed up (`app.db.bak_before_taxfix_*`, `_ss_exempt_*`, `_excel_sync_*`). **CAUTION: branch flipped repeatedly mid-session (parallel deposits work on `feat/deposits-active-filter`); verify branch before each git op. My 4 commits are clean on fix/lcb-income-tax-ytd-method.** NOT YET: finalize payrun, deploy to server, merge to main.

**DEPLOYED to server 2026-06-28** (via Tailscale, payrun stays DRAFT per โอ — เขาขอตรวจรายละเอียดในระบบก่อนแล้วค่อย finalize เอง). Code (5 files: main.py, payroll.py, 3 templates) scp'd + DB swapped (backup→stop task→scp app.db→restart). VERIFIED LIVE: server LCB มิ.ย. tax=0 net=276,854.75; `/payroll/2/tax` new route = 303 (not 404) → new code confirmed serving (not stale). MVP pid 1652 (global pythoncore python, port 8010). **GOTCHA hit:** my stop-script kill-filter `.venv` matched YK_LINE_ARCHIVER (also runs main.py from a .venv) and killed it — it auto-recovered via YK_LINE_HEALTHPOLL task (back on 8020). Lesson: the MVP isn't killed by the filter at all (it's the SCHEDULED TASK stop that frees 8010); narrow future filters to `YK_MVP` path only, don't use bare `.venv`. Also saw a stray pid running `.\.venv\Scripts\python.exe main.py` not owning 8010 (harmless leftover). Server DB backup: app.db.bak_before_taxfix_deploy_20260628_093649.

**SLIP option 1 + MERGED TO MAIN + RE-DEPLOYED (2026-06-28 ~10:05):** โอ decided slip should NOT show ยอดสะสมทั้งปี (คนขับไม่เข้าใจคำว่า "สะสม") — show only this-period (incl this-period tax if any). YTD totals live ONLY on the /payroll/{id}/tax page (for โอ/บัญชี). Removed the สะสม block from slip; slip-test now asserts สะสม NOT present.
**CLOBBER INCIDENT:** the parallel deposits workstream ran `deploy_mvp_to_server.sh` at 09:45 from main (which lacked my tax commits) → OVERWROTE server payroll.py/main.py with OLD code (engine reverted, but DB kept tax=0 → fragile inconsistent state). Root cause: my tax commits were on `fix/lcb-income-tax-ytd-method`, NOT main. **FIX: merged my branch into main (clean, no conflicts — merge f387ab6) so future main deploys include the tax fix**, then re-scp'd 5 files + narrow restart. Verified server now: payroll.py has _real_income/avg_monthly_income/ss_exempt, OLD formula gone, tax route live, DB tax=0/net=276,854.75. **Restart lesson applied:** kill by port-8010 owner + `YK_MVP`-path filter ONLY (the earlier `.venv` filter killed the LINE archiver — it self-recovered but avoid). LESSON: on this repo, deploy money code only AFTER merging to main, else parallel main-deploys clobber it.

**SLIP 2 เวอร์ชัน + เดลี่รายวัน + โน้ตคืนประกันตน (2026-06-28, DONE+deployed, branch feat/payroll-slip-boss-driver → merged main → server):**
- `/payroll/{id}/print` = สลิปคนขับ (default); `?for=boss` = สลิปผู้บริหาร. param อ่านจาก request.query_params['for'] (เลี่ยง keyword `for`).
- **กฎความลับ KB (สำคัญ):** คนขับห้ามเห็น KB(ใต้โต๊ะ) + ค่าขนส่งวางบิลจริง. เหมาเห็นแค่ราคากลาง=`price_override ?? revenue_customer`. เที่ยวเห็นแค่ค่าเที่ยว(trip_fee). boss เห็นครบ 3 (ค่าขนส่งจริง+ราคากลาง+KB). helper `_slip_daily_rows()` ใส่ logic confidentiality. 4 tests ยืนยัน 333/110 ไม่หลุดสลิปคนขับ.
- เดลี่รายวันในสลิป: ตาราง วันที่/งาน/ปลายทาง/เบอร์ตู้/ราคา(ตาม audience)/น้ำมัน(ถ้าเหมา).
- `_auto_transfer_note`: เพิ่ม "คืนประกันตน {deposit_balance}" ให้คนลาออก (resigned) ที่ deposit_balance>0 (นอกจาก "ออก"/"เหมาน้ำมัน" เดิม). 2 tests.
- DB ไม่แตะ (display only). deploy = scp main.py+template + narrow restart (kill port-8010 owner + YK_MVP path; archiver ไม่โดน). 16 payroll/tax tests ผ่าน. **สลิปคนขับยังไม่โชว์ยอดสะสม (option 1 เดิม) ยังคงอยู่.**

**ปุ่มพิมพ์ผู้บริหาร (2026-06-28, DONE+deployed):** หน้า /payroll/{id} มี 2 ปุ่มพิมพ์ — "🖨 พิมพ์ (คนขับ)" (น้ำเงิน, ซ่อน KB) + "🔒 พิมพ์ (ผู้บริหาร)" (แดง, ?for=boss, เห็น KB; title เตือนอย่าแจกคนขับ). branch feat/boss-print-button → merged main → deployed (template only). ทั้งหมดงานสลิป/ภาษี/audit ของ LCB มิ.ย. เสร็จครบ + ขึ้น server แล้ว; payrun ยัง DRAFT รอ โอ ตรวจ+finalize เอง.

**ทะเบียนรถในเดลี่สลิป (2026-06-28, DONE+deployed):** เพิ่มคอลัมน์ "ทะเบียน" (plate_no_raw) ในตารางรายการวิ่งงานรายวันของสลิป (ถัดจากวันที่) ทั้งคนขับ+ผู้บริหาร. branch feat/slip-plate → merged main → deployed.

**เซฟ PDF (2026-06-28, DONE+deployed):** หน้าพิมพ์มีปุ่ม "💾 เซฟ PDF" (=window.print() → ผู้ใช้เลือก Save as PDF + โฟลเดอร์เองใน dialog; เบราว์เซอร์เลือกโฟลเดอร์อัตโนมัติไม่ได้ = ข้อจำกัด security, แนะนำตั้ง "ถามที่จัดเก็บทุกครั้ง"). <title> = `เงินเดือน_{site}_{cycle}_{คนขับ/ผู้บริหาร}` → กลายเป็นชื่อไฟล์ตอนเซฟ PDF. โอเปิดเว็บจากเครื่อง Dev → เซฟลง Dev ได้เลย. branch feat/slip-save-pdf → merged main → deployed.
