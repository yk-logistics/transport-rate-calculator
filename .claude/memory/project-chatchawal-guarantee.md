---
name: project-chatchawal-guarantee
description: "ชัชวาล AYU การันตี 15,000/เดือน prorate ตามวันลา + top-up — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (DB-only): ชัชวาล(emp142 AYU ayu_trip) ตั้งการันตีขั้นต่ำ **15,000/เดือน**; ค่าเที่ยวจริงรอบ มิ.ย. = 10,100 (น้อยกว่าการันตี) → เติม top-up ให้ถึง.

**engine มีสูตรอยู่แล้ว** (ayu_trip): ถ้า `has_guarantee` + `guarantee_monthly_amount>0` → `prorated = (amount/days_in_month) × eligible_days` (eligible = days_worked + days_company_no_work, **ไม่รวมลา/ขาด**); ถ้า trip_fee_total < prorated → guarantee_topup = ส่วนต่าง.

ลา 18/6 = 1 วัน → prorate (15000/31)×30 = **14,516.13**; top-up = 14,516.13−10,100 = **4,416.13**; gross→14,516.13; net 650→**5,080.13** (SS 450→436 ตาม gross). run18 204,567.46→**208,997.59**; net_guard --allow 18 OK.

**GOTCHA วันลา AYU คีย์ใน destination='ลา' (ช่องส่งสินค้า) เหมือน BIGC** ([[project-bigc-holiday-anuloom]]): `_count_work_days` **ไม่ scan destination** สำหรับ token "ลา" (กัน false-positive ชื่อสถานที่ เช่น เซเว่นลาดกระบัง) → leave ไม่ถูกตรวจ. แก้ = data fix `leave_status='ลา'` บนแถวนั้น (row id 4970) → token scan เจอ → leave=1 worked=30. ตรวจ ลา เฉพาะ 18/6 (อีก 3 "ลา" = ลาดกระบัง มี revenue ตัดออกถูก).

ตั้ง: has_guarantee=true, guarantee_monthly_amount=15000 (Employee). recompute 142 in-place (inline calc_one_employee→28 fields). deploy DB WAL-safe. related: [[project-ayu-jun-payroll]], [[project-bigc-holiday-anuloom]]
