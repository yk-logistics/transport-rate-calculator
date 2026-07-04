---
name: project-payroll-bank-print
description: "หน้าพิมพ์เงินเดือนรวม (/payroll/{run}/print: สรุป+โอนเงิน+สลิป) + เลขบัญชีคนขับใน DB; schema v27. DONE+deployed 2026-06-27."
metadata: 
  node_type: memory
  type: project
  originSessionId: dd159b75-a9ad-4971-90f9-dbb17a444943
---

**DONE + deployed server 2026-06-27 (branch feat/payroll-bank-print → main).**

**Schema v27:** `Employee.bank_name` + `Employee.account_no` (เลขบัญชีโอนเงินเดือน), `PayRunItem.transfer_note` (หมายเหตุหน้าโอนเงิน แก้มือ). ทุก field default "" → ไม่กระทบ engine (regression: payrun#2 total เท่าเดิม 256,942.96).

**หน้าใหม่ `/payroll/{run}/print`** (`templates/payroll_print_all.html`, standalone ไม่ extends base.html → พิมพ์สะอาด): 3 บล็อก `page-break-after:always` ตามลำดับโอเลือก: (1) สรุปทุกคน (2) โอนเงิน (3) สลิปรายคน (18 สลิป/รอบ). ทุกบล็อก**น้ำมันลบก่อนรายได้สุทธิ** (gross−fuel; deduction−fuel). ปุ่ม window.print(). หน้าโอนเงิน: ลำดับ|ชื่อ|ธนาคาร เลขบัญชี|จำนวนโอน(net ติดลบได้)|หมายเหตุ.

**หมายเหตุโอนเงิน = auto + แก้มือ** (โอเลือกทั้งสอง). `_auto_transfer_note(emp,item,period_end)` ใน main.py: status inactive/resigned หรือ end_date≤period_end → "ออก"; pay_mode mao/mixed/ayu_mao → "เหมาน้ำมัน". transfer_note ที่กรอกมือ override auto. POST `/payroll/{run}/employee/{emp}/transfer-note` (ไม่ recompute, locked เมื่อ finalized).

**ปุ่ม:** "🖨 พิมพ์ทั้งหมด" (เปิด /print แท็บใหม่) ข้างปุ่ม "ส่งออก PDF" เดิม (เก็บ export ไฟล์ไว้ด้วย ตามที่โอบอก). ช่องกรอกธนาคาร/บัญชีในหน้าแก้ไขพนักงาน (`employee_form.html` + employees_save route).

**Backfill บัญชี (2026-06-27):** เลขบัญชีจากภาพ Excel sheet "BANK" คอลัมน์ G สีแดง (เลขล่าสุด) — hard-code dict 21 คน by id (ปลอดภัย ไม่ filter ชื่อ), backup app.db.bak_before_bank_backfill_*. ธนาคาร: ไทยพาณิชย์/กสิกร(ไทย)/กรุงศรี/กรุงไทย. **วราวุฒิ(id101) ยังไม่มีบัญชีในภาพ** → โอกรอกผ่าน UI เอง. โอยังไม่ได้ส่งไฟล์ Excel จริง (ใช้เลขจากภาพ).

**Deploy:** code (main+models+3 templates) scp + **app.db full-file overwrite** (bank backfill อยู่ใน DB). restart by port-owner ([[reference-mvp-deploy-restart-gotcha]]). verified: login 200, schema 27, 21 บัญชี, print page render 18 สลิป + เลขบัญชีจริง + auto-note. ดู [[project-fuel-exclude-from-driver]] (รายได้หลังหักน้ำมันในสลิป/หน้ารวม), [[project-dhl-overflow-rate]].

**บัญชี source เดียว (DB) ทั้ง 2 ปุ่ม — แก้แล้ว 2026-06-27:** เดิม export PDF เก่า (`payroll_export_pdf.py`, ปุ่ม "ส่งออก PDF") ดึงบัญชีจาก `merged_bank_terms` → custom_terms JSON (คนละที่กับ DB ใหม่). แก้ `merged_bank_terms` (services/payroll_slip.py) ให้**เช็ค Employee.account_no/bank_name (DB) ก่อน — ชนะ custom_terms**. fallback JSON/custom_terms ยังอยู่ถ้า DB ว่าง (BIGC seed ยังทำงาน). ผล: ปุ่ม PDF เก่า + ปุ่มพิมพ์ใหม่ใช้เลขบัญชีชุดเดียวกัน, แก้ในหน้าแก้ไขพนักงานที่เดียวมีผลทั้งคู่. deployed (code-only). 14 payroll/slip/bank tests ผ่าน.
