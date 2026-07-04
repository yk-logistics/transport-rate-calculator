---
name: project-ayu-deposit-installments
description: AYU เงินประกันตน มิ.ย. แก้ทั้งรอบ (ครบ/กำลังหัก) + โชว์งวด X/Y บนสลิป + print 31 สลิป — DONE+deployed
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย.: แก้เงินประกันตน (deposit) AYU run18 ตาม ground truth โอ. เดิมเกือบทุกคน bal=0 tgt=0 → engine หัก 1,000 (tgt=0 default→10,000) ผิด.

**ครบแล้ว (bal=tgt → dep=0, net +1,000):** ติ๋ว131/ทองสุข132/นิวัติ139/เรวัตร140 = 10,000 (10/10); **เสรี144 = 30,000 unit 2,000 (15/15)** (เหมือนธัชชนพล หักครั้งละ 2,000×15); เรืองฤทธิ์133 = ตั้ง bal 10,000 (ไม่อยู่ run18, **รอคืนเงินประกันเดือนนี้**).
**กำลังหัก งวด X (bal=(X−1)×1,000, dep=1,000):** สุริยันต์134 2/10, สมปอง135 2/10, สิทธิชัย136 1/10, สมัย137 4/10, วัชร์นล141 10/10 (เดือนหน้าครบหยุดหัก), ชัชวาล142 3/10.
run18 → **246,193.34** (Δ+5,000 = 5 คนครบหยุดหัก); net_guard นิ่ง.

**CODE FIX (deploy):** (1) `payroll_export_pdf._dep_install_str` เดิม bal/1000 ตายตัว → ใช้ logic web (หน่วยต่อคน+paid+1+hold) เสรีโชว์ 15/15 ถูก. (2) `_slip_body.html` เพิ่มบรรทัด **"เงินประกันครบแล้ว งวด X/Y — ไม่หัก"** เมื่อ bal>=tgt (เดิมซ่อนบรรทัด deposit เมื่อไม่หัก → คนไม่เห็นว่าครบ). main c807360.

**PRINT 31 สลิป:** `tools/export_ayu_slips.py <run> <dir>` render รายคน (Chrome headless web layout) → `Work\Salary\2026\6.Jun\AYU\สลิป_แก้ไขใหม่\`. โชว์งวด X/Y ครบ.

**FALSE ALARM x2 (โอถาม ปกรณ์ + ณัฐวุฒิ):** **26/5 "มีงานวิ่งแต่ไม่มีค่าเที่ยว" = ปกติ ไม่ใช่บั๊ก** สำหรับคน **lcb_mao (เหมาน้ำมัน)** — จ่าย = gross×60%−น้ำมัน ไม่ใช่ค่าเที่ยวต่อเที่ยว (tfd=0 ปกติ). ปกรณ์92 26/5 rev 4,831 นับใน run2 gross 121,538×60%; ณัฐวุฒิ98 26/5 rev 4,831 นับใน run2 gross 131,677×60%. **ค่าเที่ยว(tfd)=เฉพาะ lcb_trip; mao ไม่มี tfd ถูกแล้ว**. **UPDATE: โอยืนกรานให้ใส่ค่าเที่ยว 60% job 718/719 (อยากให้โชว์บนสลิป — ช่องค่าเที่ยวว่างเพราะ tfd=0)** → fill tfd=4,831×0.6=**2,898.60** (display); recompute พิสูจน์ **net UNCHANGED** (ปกรณ์ 23,734.40/ณัฐวุฒิ 19,948.50 — mao อ่าน revenue ไม่ใช่ tfd, รายได้นับใน 60% แล้วจริง). net_guard run2 only. **บทเรียน: mao ใส่ tfh ได้เพื่อโชว์บนสลิป แต่ไม่กระทบ net (อย่าให้ net เพิ่ม=ซ้ำ).** (โอถาม deposit ณัฐวุฒิ แต่จริงๆหมายถึงค่าเที่ยว 26/5 = เคสเดียวกับปกรณ์). related: [[project-deposit-installment-number]], [[project-thach-deposit-2000-hold]], [[feedback-slip-fuel-must-reconcile]]
