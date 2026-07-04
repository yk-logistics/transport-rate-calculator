---
name: project-cfo-cycle-vs-calendar
description: "DONE+deployed: /finance CFO P&L มีปุ่มสลับ เดือนปฏิทิน ↔ รอบจ่าย(ตามไซต์) — แก้อาการ 'ข้อมูลไม่เปลี่ยน' ที่เกิดเพราะ /daily เปลี่ยนเป็นรอบจ่าย"
metadata: 
  node_type: memory
  type: project
  originSessionId: cabcef69-ed3b-46a7-8c19-7b9bab9799b2
---

**RESOLVED 2026-06-27 (โอเลือก C = ปุ่มสลับ). Deployed live.**
Fix: `finance.monthly_pnl` รับ optional `period=(start,end,cycle_tag)` — ไม่ส่ง=เดือนปฏิทินเดิม (regression ยืนยัน June −10,236 / May +1,042,022 ไม่ขยับ), ส่ง=คิดทั้ง P&L ตามช่วงรอบ + payroll keyed by tag. `/finance?mode=calendar|cycle`; cycle ต้องมีไซต์ (ไม่มี→ถอยเป็นปฏิทิน+เตือน), default รอบ=รอบล่าสุดที่ครอบ max(work_date). helper `main._cycle_period_for_tag` (out-of-range tag→None→fallback ปฏิทิน). UI: dropdown ช่วง+รอบ, banner เปลี่ยนตามโหมด. cycle LCB=16/5–15/6 608 เที่ยว (ตรง /daily). **ยังเหลือ:** /finance/pnl + /finance/vehicles ยังเป็นปฏิทินล้วน (นอก scope งานนี้).

--- บันทึกการ debug เดิม (อ้างอิง) ---

**2026-06-27, OPEN — needs โอ's decision (money logic, did NOT change blind).**

Symptom (โอ): after /daily default became payroll-cycle (LCB 16/5–15/6), "หน้า CFO เหมือนข้อมูลไม่เปลี่ยน".

Diagnosis (debug-mantra, verified):
- `/finance` → `finance_svc.monthly_pnl(year, month, site)` windows REVENUE/fuel/petty/maint by **calendar month** (`month_bounds`), payroll by `pay_cycle_tag`. It has **no cycle concept** and default month = current calendar month.
- `/daily` now windows by **payroll cycle**. So the two pages measure different date ranges → look out of sync.
- Verified: calendar June 1–30 = 291 trips / rev 868k; LCB cycle 16/5–15/6 = 608 trips / rev 1.97M. Different windows. `monthly_pnl` itself works (June net −10k, May +1.04M — numbers DO move by month).
- Second real cause of "ไม่เปลี่ยน": **all data in DB is LCB**, so site dropdown ALL↔LCB gives identical output; BIGC/AYU = all zeros. Toggling site looks like "nothing changed".
- Data ends 15/6 (max work_date); today 27/6. So calendar June only has 1–15/6 (half month).

Why NOT fixed yet: aligning CFO to payroll cycle = a **business decision** (standard accounting P&L is usually calendar-month; payroll-cycle P&L is a different view). CLAUDE.md: don't guess on money. โอ was heading out.

Recommended fix to propose (when โอ confirms):
- Add site→payroll-cycle scoping to `/finance` mirroring `/daily` (reuse `_site_payroll_cycles`), OR add a toggle "เดือนปฏิทิน / รอบจ่าย" so CFO can switch. Keep `monthly_pnl` math; just feed it cycle start/end instead of `month_bounds` (needs a range-based variant since it currently takes year+month). Payroll cost already keys off `pay_cycle_tag` so that part aligns naturally.
- The dashboard banner (finance_dashboard.html:24–34) already warns calendar≠cycle — good anchor for the toggle.

See [[project-daily-grid-edit-ux]] (the /daily cycle change that triggered this).
