---
name: project-deposit-installment-number
description: "เงินประกันตน แสดง 'งวดที่ X/Y' ทุกหน้า (filter dep_install) — DONE+deployed 28มิ.ย."
metadata: 
  node_type: memory
  type: project
  originSessionId: e04b30d6-34c8-42d1-801a-fb9b2b989a0e
---

DONE + deployed live 28มิ.ย.2026: เพิ่มการแสดง **"งวดที่ X/Y"** ของเงินประกันตน ทุกหน้าที่เงินประกันโผล่ เพื่อให้ตรงกับชีต Excel "SSO" ที่โอใช้คู่กัน

**กฎ (single source of truth) — UPDATED 29มิ.ย.:** Jinja filter `dep_install` ใน `main.py` (const `DEPOSIT_INSTALL_UNIT=1000`) → **X = งวดที่กำลังหักรอบนี้** (ไม่ใช่งวดสะสม!). `deposit_balance` = ยอดจ่ายแล้วก่อนรอบนี้ = (งวดก่อน)×1000 → `X = balance//1000 + 1` (ถ้ายังผ่อนไม่หมด) หรือ `Y` (ถ้าจ่ายครบ, กัน overflow 11/10). `Y = deposit_target//1000`. คืน `''` ถ้า target<=0. **เดิม X=balance//1000=งวดสะสม โอบอกว่าผิด** (หักงวดแรกควรโชว์ 1/10 ไม่ใช่ 0/10) → แก้ +1. verified: bal 0→1/10, bal 9000→10/10, bal 10000(ครบ)→10/10. หน่วยงวด = 1,000 บาท/งวด ตรงชีต SSO (เพดาน 10,000=10งวด).

**ความหมายคอลัมน์ในชีต SSO (โอยืนยัน):** 9240 = เงินเดือนฐานไว้ลิงก์คิดประกันสังคม · 1000 = ยอดหักเงินประกันตน/งวด · 10 = จำนวนงวดทั้งหมด · เลข 0–10 = งวดล่าสุดที่หักเดือนนั้น. หน้า /deposits เก็บแค่ยอดสะสม(บาท) เดิมไม่มีเลขงวด → งานนี้เติมให้.

**หน้าที่แก้ (10 ไฟล์, แค่แสดงผล ไม่แตะ DB/engine/ยอดเงิน):**
- `main.py` — filter `dep_install` + const
- `templates/deposits_list.html` (หัวคอลัมน์ "งวดที่") + `deposits_row.html` (เซลล์) + `deposits_edit_row.html` (colspan 4→5)
- `templates/payroll_slip.html`, `payroll_print_all.html`, `payroll_employee_detail.html`, `payroll_detail.html`
- `services/payroll_export_pdf.py` — มี helper python แยก `_dep_install_str(emp)` (filter เป็น Jinja-only ใช้ใน PDF ไม่ได้)
- tests: `test_deposits.py` (+filter unit test + page assertion) → 26 ผ่าน

**GOTCHA ตัวแปร employee ต่างชื่อต่อ template:** slip ใช้ `employee` · payroll_detail ตารางรวมใช้ `e` · print_all ใช้ `r.employee` · deposits ใช้ `r.emp`. เช็คชื่อก่อนใส่ filter เสมอ.

**ข้อจำกัดที่บอกโอแล้ว:** เลขงวดคิดจากยอดสะสม**ปัจจุบัน** → สลิปย้อนหลังโชว์งวด ณ ตอนนี้ ไม่ใช่งวด ณ เดือนนั้น (เหมือนชีต SSO ที่ดูยอดล่าสุด). ถ้าโออยากให้สลิปเก่าโชว์งวดตามเดือนจริง ต้องคำนวณจากประวัติการหัก (PayRunItem.deposit_install สะสม) แทน — ยังไม่ทำ.

deploy = code-only ผ่าน Tailscale (scp 9 ไฟล์ ไม่ส่ง test/ไม่ส่ง app.db) → restart `YK_MVP_APP`. ดูวิธี restart+verify ที่ [[reference-mvp-server-deploy]]. หน้า /deposits เดิมดูที่ [[project-deposits-overview-page]]. การหักเงินประกันใน payroll: [[project-payroll-bank-print]].
