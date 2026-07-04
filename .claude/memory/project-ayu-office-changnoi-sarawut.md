---
name: project-ayu-office-changnoi-sarawut
description: "AYU office: ช่างน้อย รายวัน 500×30 + ศราวุธ ฐาน 9000 ลา 2 (วันละ 300) — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (DB-only) payrun#18: พนง.บริษัท AYU 2 คน, **ไม่ส่ง SS** (custom_terms ss_exempt=true → engine SS=0):
- **ช่างน้อย (สร้างใหม่ emp169, office_monthly)**: รายวัน 500/วัน, รอบ**ปฏิทิน 1–30/6 = 30 วัน**, ลาไม่จ่าย, ไม่มีลา → net **15,000** (500×30). base_salary=15000.
- **ศราวุธ (emp124, office_monthly เดิม)**: ฐาน 9,000, รอบ 26→25, **ลา 2 วัน หาร÷30 (วันละ 300)** → 9000−600 = net **8,400** (โอยืนยัน ÷30 ไม่ใช่ ÷31=8,419). base_salary set 9000. เดิม net 3,400 (ลอกยอด stale).

**GOTCHA divisor:** office engine หาร `days_in_month = period_days` (run18 = 31 วัน). โอ**คิดวันลา÷30** (ศราวุธ) และ ช่างน้อย**รอบ 1–30 ไม่ใช่ 26→25** → ไม่ตรง engine. แก้แบบ office "ลอกยอด" = **set base_salary_earned/gross/net ตรงๆ บน PayRunItem** (pattern เดียวกับ office อีก 11 คนที่ลอกยอด net จ่ายจริง เพราะ engine คิด base office ไม่ได้).

**+1,000 office:** office AYU อีก 11 คน net=ฐาน+1,000 (คืนประกัน/โบนัสรอบก่อน [[project-office-no-deposit]]) — **ช่างน้อย/ศราวุธ ไม่บวก** (โอยืนยัน net=8,400/15,000 เป๊ะ).

run18 28→**29 items** (ช่างน้อยเพิ่ม 1), net 216,117.59→**236,117.59** (Δ+20,000=ศราวุธ+5,000+ช่างน้อย 15,000); net_guard รอบอื่นนิ่ง; live public 200. related: [[project-ayu-jun-payroll]], [[project-office-no-deposit]], [[project-ayu-jun-new-drivers]]
