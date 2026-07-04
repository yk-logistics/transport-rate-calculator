---
name: project-fuel-move-0556-0560
description: "น้ำมัน 23/6 คีย์ผิด 71-0556(เรวัตร)→71-0560(วัชร์นล) — โยก 4,400, เรวัตร net +4,400 — DONE+deployed +gsheet"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย.: คนคีย์ใส่น้ำมัน 23/6 ผิดทะเบียน — **71-0556 (เรวัตร140) ไม่มีเติมจริง → ย้ายไป 71-0560 (วัชร์นล141)**. 2 บิล FuelTxn id1823(750)+id1824(3,650)=**4,400**.

**ผล:** เรวัตร = **ayu_mao (หักน้ำมัน)** → fuel 49,661.03→45,261.03, net 11,143.81→**15,543.81 (+4,400)**. วัชร์นล = **ayu_trip (ไม่หักน้ำมัน)** → net 6,880 ไม่ขยับ (รับบิลไว้แต่ไม่กระทบเงิน). run18 235,343→**239,743**; net_guard รอบอื่นนิ่ง; live public 200.

ย้าย: UPDATE FuelTxn driver_id 140→141, plate 0556→0560, daily_job_id→job วัชร์นล 23/6 (5094); recompute 2 คน. **+อัปเดต gsheet** (1F5eJ.../Jun26 r753,r754: plate→71-0560 name→วัชร์นล +note) ให้ชีต↔ระบบตรง (โอสั่ง "เช็ค gsheet + อัปเดตระบบ"). GOTCHA: 0556/0560=ทะเบียนรถ ไม่ใช่คนขับ — ต้องดูว่ารถวันนั้นใครขับ (daily) ก่อนย้าย. related: [[project-ayu-mao-pertrip-pay]], [[project-rewat-handover-fuel-jun]], [[reference-google-sheets-access]]
