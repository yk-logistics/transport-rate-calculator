# WORKFLOW BY TEAM

บันทึก workflow การทำงานจริงของทีม 7 คน (ต้นฉบับจากผู้ใช้ 22-04-2026)

---

## 1) ทีมจริง

| บทบาท | จำนวน | ขอบเขต |
|---|---|---|
| Operation A | 1 | AYU + BIGC (plan งาน, จัดรถ, รับใบงาน) |
| Operation B | 1 | LCB — plan งานในไลน์ + Notepad ส่วนตัว |
| Accounting | 2 | ใส่เอกสาร/ตัวเลขลง Daily + ทำวางบิล + เงินเดือน |
| Manager (ผู้ใช้) | 1 | ผู้จัดการ — ตรวจสอบ, ทำเงินเดือน, กำกับ |
| Owner (พ่อ) | 1 | ดู report สรุป, ตัดสินใจนโยบาย (เช่น ประกาศการันตี) |

---

## 2) วิธีทำงานปัจจุบัน (เหตุผลที่ต้องเปลี่ยน)

```
ลูกค้าส่งใบงาน
    ↓
Operation จัด plan ในใจ / Notepad / Line
    ↓
Operation คีย์ Daily Excel (บางไซต์)
    ↓
เอกสารจริงมาถึงบัญชี
    ↓
Accounting พิมพ์ Daily ซ้ำ / แก้ตัวเลข
    ↓
Accounting ทำวางบิล แยกไซต์
    ↓
ผู้จัดการรวม Daily ข้ามไซต์ ทำวางบิล (รถ BIGC ไปวิ่งแหลม)
    ↓
ผู้จัดการทำเงินเดือน (manual)
```

**ปัญหา:**
- พิมพ์ซ้ำ (Operation → Accounting)
- รถข้ามไซต์ ต้องรวม Daily ข้ามไฟล์
- เงินเดือนใช้ข้อมูลกระจัดกระจาย (Daily + สดย่อย + เงินเบิก + ประกันสังคม + ผ่อนอุบัติเหตุ)

---

## 3) Vision ของผู้ใช้ (target workflow)

```
ลูกค้าส่งใบงาน
    ↓
Operation เปิด Dispatch screen → สร้าง Job + จัดรถ + กด "แจ้งคนขับ" (ส่งไลน์อัตโนมัติ)
    ↓
งานนั้นกลายเป็น Daily row ทันที (เดลี่ = หางานต่อยอดจาก dispatch ไม่ต้องพิมพ์ซ้ำ)
    ↓
เอกสารจริงถึงบัญชี → Accounting แค่ "หยอดตัวเลข" ที่ขาด / แก้ค่าที่ต่างกับลูกค้า
    ↓
ระบบรวม Daily ข้ามไซต์ อัตโนมัติ → หน้า Billing เลือก cycle + ลูกค้า → export วางบิล
    ↓
หน้า Payroll ดึง Daily + Petty Cash + Deductions → คำนวณเงินเดือน + audit trail
```

**หลักการ**: ต้นทางคือ Dispatch, ทุกอย่างไหลจาก Dispatch → Daily → Billing + Payroll

---

## 4) Access pattern ปัจจุบัน

- **PC 100%** (Windows) ตอนอยู่ที่ออฟฟิศ
- **Google Sheet shared** สำหรับดูข้อมูลนอกออฟฟิศ
- **Line chat** สำหรับแจ้งคนขับ (LCB)

### อนาคตที่อยากได้
- มือถือ / แท็บเล็ต (responsive web) — ไม่ต้อง app native
- แจ้งคนขับผ่านไลน์ด้วยปุ่มเดียว (Line notify / Line OA webhook)

---

## 5) Device & Network

- Dev/test ตอนนี้: โน้ตบุ๊กผู้ใช้ (เครื่องนี้)
- Production: **PC Server** ที่สำนักงาน (ยังไม่ได้เซ็ตอัพ)
- Multi-site access: **Tailscale** (แทน Global IP + DDNS)
- One-click installer ที่ฝั่ง server เมื่อพร้อมย้าย

---

## 6) Principles ของระบบใหม่ (ข้อตกลงกับผู้ใช้)

1. **ไม่ซ้ำซ้อน** — พิมพ์ครั้งเดียว ส่งต่อทุก stage
2. **Dispatch = ต้นน้ำ** — Daily auto-generate จาก dispatched jobs
3. **บัญชีมาหยอดท้าย** — ไม่ให้บัญชีพิมพ์ซ้ำ
4. **ข้ามไซต์ได้** — รถ BIGC ไปวิ่งแหลม ต้องอยู่ใน Billing รอบนั้น ๆ ได้
5. **ทุกการคำนวณมี audit trail** — ใครเปลี่ยนอะไรเมื่อไหร่
6. **เงินเดือน/วางบิลล็อกได้** — ปิดรอบแล้วห้ามแก้ (ใช้ adjustment แทน)
7. **Single source of truth** = SQLite (dev) / PostgreSQL (prod) — Excel เป็น import/export เท่านั้น

---

## 7) Cross-site scenario (สำคัญ!)

**ผู้ใช้ยืนยัน**: รถบิ๊กซีบางคันไปวิ่งงานฝั่งแหลมได้

→ implication ใน data model:
- `vehicle.site_code` ไม่ควร fix (ใช้เป็น "home site" แทน)
- `daily_job.site_code` ต้องเป็นของงาน ไม่ใช่ของรถ
- `billing` รวมข้ามไซต์ได้ตาม customer ไม่ใช่ตาม vehicle site
- `payroll` ใช้ site_code ของ **คนขับ** (ไม่ใช่ของงาน) เพราะรอบจ่าย + กติกาการันตีอิงไซต์คนขับ
  - **⚠ ต้องยืนยัน**: ถ้าคนขับ AYU ไปวิ่งงานฝั่ง LCB — ค่าเที่ยวคิดแบบ AYU หรือ LCB?

---

## 8) Open questions

1. คนขับข้ามไซต์ — คิดค่าเที่ยวตามไซต์ของงาน หรือตามไซต์ของคนขับ?
2. `Operation A` และ `Operation B` ใช้ account แยกกันไหม? (permission แยกตามไซต์?)
3. Line notify — มี Line OA อยู่แล้วหรือเปล่า? หรือเริ่มใหม่?
