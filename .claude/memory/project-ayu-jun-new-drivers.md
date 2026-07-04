---
name: project-ayu-jun-new-drivers
description: AYU มิ.ย. onboard 4 คนใหม่ (ปรีชา/พ้น/ธนา/สุธรรม) เข้า payrun18 — DONE+deployed
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (DB-only): สร้าง+ผูก 4 คนขับใหม่ AYU เข้า payrun#18 (ก่อนหน้านี้ unlinked รอโอ ตาม [[project-ayu-daily-import]]). ทั้งหมด pay_mode=**ayu_trip** (จ่ายตาม trip_fee_driver ที่คีย์), **ไม่หักเงินประกันตน** (custom_terms deposit_hold=true ทั้ง 4 — โอสั่ง คนใหม่ไม่หัก).

| คน | emp_id | raw name ในเดลี่ | rows | net |
|----|--------|------------------|------|-----|
| ปรีชา แก้วมณีโชติ | 165 | นายปรีชา แก้วมณีโชติ | 14 (17–25/6) | 4,569 |
| พ้น ทองเภา | 166 | นายพ้น ทองเภา | 1 (23/6) | 417 |
| ธนา ปาวรีย์ | 167 | **นายธันา ปาวรีย์** (คนคีย์คีย์ผิด!) | 1 (11/6) | 417 |
| สุธรรม สารนอก | 168 | นายสุธรรม สารนอก | 2 (17–18/6) | 1,717 |

**GOTCHA:**
- **ธนา คีย์ผิดเป็น "ธันา"** ในเดลี่ → หาเจอด้วยการ search ธันา (โอบอก); ผูกด้วย raw name="นายธันา ปาวรีย์"
- **สุธรรม ออกแล้ว** → end_date=2026-06-18 status=inactive; เดลี่ rev 8,500 แต่ tfd=0 → ใส่ tfd=**900/เที่ยว** (โอบอก "ค่าเที่ยวนครสวรรค์ 900") 2 วัน=1,800
- สร้าง employee ผ่าน **ORM Employee()** ไม่ใช่ raw INSERT (column NOT NULL เยอะ: code/nickname/phone/id_card... → ใช้ model default); code=`AYU-<ชื่อ>`
- compute เฉพาะ 4 คน in-place (สร้าง PayRunItem ใหม่) ไม่เรียก compute_pay_run ทั้งรอบ (เลี่ยง office wipe)
- absent days สูง (ธนา a=14 พ้น a=2) = implicit-absent จาก start_date เร็ว — **ayu_trip ไม่ prorate ตามวัน → ไม่กระทบเงิน** (display noise)

run18 24→**28 items**, net 208,997.59→**216,117.59** (Δ+7,120 รวมทุก step); net_guard รอบอื่นนิ่ง; live public 200.
**ค้าง: สดย่อยชื่อ ธนา/ปรีชา โอบอกมี แต่ยังไม่อยู่ใน DB (petty by requester=0)** — รอไฟล์/ลงทีหลัง. ยังมี unlinked AYU อื่นอีก (บุญนาม/มานพ/โกสินทร์/สมประสงค์/เสกสรร...) ที่โอยังไม่สั่ง onboard.
related: [[project-ayu-jun-payroll]], [[project-thach-deposit-2000-hold]] (deposit_hold), [[project-chatchawal-guarantee]]
