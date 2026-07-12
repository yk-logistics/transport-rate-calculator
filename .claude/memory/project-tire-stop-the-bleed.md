---
name: project-tire-stop-the-bleed
description: "ระบบยาง \"หยุดเลือด\" — คีย์บิลเร็ว + รายงานความคุ้ม หล่อ vs แท้ (8ก.ค.)"
metadata: 
  node_type: memory
  type: project
  originSessionId: fee8b57c-9433-4ad4-b3e4-67335153e356
---

ค่ายาง ~2 แสน/เดือนไม่มีระบบติดตาม → 8ก.ค. เติม 3 ชิ้นบน schema ยางเดิม (มีครบตั้งแต่ v8/v10 แต่ 0 แถว — เครื่องมือพร้อมแต่ไม่มีใครกรอก). commit 43a8a57 + **deploy เขียว production** (surgical scp 6 ไฟล์, migration schema=48 รันจริง, backup app.db.bak_before_tire_v48_20260708_200045). spec: docs/superpowers/specs/2026-07-08-tire-tracking-stop-the-bleed-design.md

**ทำอะไร (schema v48 ALTER additive):**
- `Tire.tire_type` (new/retread/used = แท้/หล่อ/มือสอง) + `Tire.removal_reason`; `TireEvent.reason_code`
- `/maint/tires/bill` — ธุรการคีย์บิลร้านยาง 1 ใบ → สร้าง Tire+mount event+MaintRecord(kind=tire_change)+MaintPart ครบ; ยางเก่าถูก unmount พร้อม reason_code; **เลขไมล์ไม่บังคับ**; อัปเดต Vehicle.current_mile เมื่อกรอก
- `/maint/tires/report` — ค่ายางเดือนนี้+เทียบเดือนก่อน · เหตุที่เปลี่ยน · รายคัน · **ตารางเทียบหล่อ vs แท้ (บาท/เดือน·บาท/1,000กม.)** จากยางครบวงจร (ติดตั้ง→ถอด)
- logic aggregate แยก unit: `services/tire_view.tire_lifecycle_report()`
- ปุ่มเข้า 2 หน้าใน /maint dashboard

**กติกาหน้างาน (โอเคาะ brainstorm):** คนกรอก=ธุรการคีย์ทีหลังจากคอม (ไม่ทำ PWA ช่าง/OCR); เลขไมล์มีบ้างไม่มีบ้าง → คิดได้ทั้งกิโล+เดือน ระบบไม่พังเมื่อไมล์ว่าง

**GOTCHA (สำคัญ):**
- route bill/report ต้องประกาศ **ก่อน** `/maint/tires/{tire_id}` ใน main.py ไม่งั้น starlette จับ literal เป็น tire_id ([[reference-branch-switch-during-session]] คนละเรื่อง แต่ pattern literal-before-{id} เดียวกับ /quote/deal ใน [[project-deal-checker]])
- ยางเก่าตอนถูกแทนที่: unmount **ชัดเจน** พร้อม reason_code (ไม่พึ่ง auto-unmount ใน `_apply_tire_event` mount branch ที่สร้าง event แต่ไม่ใส่เหตุ) — self-review เจอ
- ตารางหล่อ/แท้ **ว่างจนกว่ามียางครบวงจร** (ติดตั้ง→ถอด) 2-3 เส้น = ปกติ ไม่ใช่บั๊ก; เดือนแรกเห็นแค่ค่าใช้จ่าย+เหตุ

**ค้างรอโอ:** ลองคีย์บิลจริง 1-2 ใบ + ยังไม่มี "ตรวจเช็คยาง 100% ลงระบบ" (โออยากได้แต่รอบนี้โฟกัสหยุดเลือดก่อน — ตัวเลือกที่โอเลือก); การเทียบหล่อ/แท้จะแม่นเมื่อสะสมข้อมูล 2-3 เดือน

**อัปเดต 11 ก.ค. 2026:**
- **ยาง 2 เส้นแรกของระบบลงแล้ว**: T0001/T0002 WESTLAKE AZ599 (FL/FR 71-8000 บิลไทร์มาร์ท 256933 30/9/68 ไมล์ 736,101) — ลงย้อนหลังผูก M005828 เดิม **ไม่บวกเงินซ้ำ** (เงินอยู่จากชีท RM แล้ว: 5,300×2+ถ่วง 600+ตั้งศูนย์ 800=12,000); เลขยาง T0002 ลายมือกำกวม (P5T/P58 1594399) จดใน notes; รูปบิลผูกใน TireEvent.photo_paths
- **v52 คีย์บิลยางรายเส้น (af14823, deploy เขียว):** แต่ละแถวเลือกรถปลายทาง (default คันหลัก) หรือ 📦 STOCK → **แยก MaintRecord ตามคันปลายทาง ค่าใช้จ่ายเข้าคันใครคันมัน**; สต๊อก=ใบ vehicle_id=None (plate_raw="สต๊อกยาง") mount ทีหลังที่ /maint/tires/{id}/event; ค่าแรง/ค่าอื่นเข้าคันหลักเสมอ (labor-only สร้างใบคันหลักให้); เทสต์รวม 14 ตัว
- BR = ร้านบอสรับเบอร์ (บิลยางเยอะ); ใบบริการไทร์มาร์ทมีตำแหน่ง/ยี่ห้อ/เบอร์ยางละเอียด — โอสั่งเจอไทร์มาร์ทให้ลงระบบยางรายเส้นเสมอ

**verify:** TDD 13 เทสต์ tests/test_tire_bill_report.py; ชุดเต็ม 558 ผ่าน; e2e HTTP + migration บนสำเนา app.db. ไม่แตะ payroll/finance/daily/billing/cycle (ค่ายาง=MaintRecord kind=tire_change ตามทางเดิม)
