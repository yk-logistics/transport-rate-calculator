# Project YK — One Platform (Phase 1.1)

เว็บแอปสำหรับใช้งาน **Daily + Master Data** ครอบคลุม 3 ไซต์ (AYU / BIGC / LCB)
จากนั้นจะค่อย ๆ ต่อ Dispatch / Billing / Petty Cash / Payroll / Maintenance

## วิธีรัน (ครั้งแรก)

1. ติดตั้ง **Python 3.10+** จาก https://www.python.org/downloads/
   - ตอนติดตั้งให้ติ๊ก **"Add Python to PATH"**
2. ดับเบิลคลิกไฟล์ **`start.bat`**
   - ครั้งแรกจะสร้าง `.venv` และติดตั้งแพ็กเกจ (~1-2 นาที)
   - หลังจากนั้นเบราว์เซอร์จะเปิดที่ http://localhost:8000/daily เอง
3. แนะนำลำดับลองใช้:
   1. **คนขับ** → "+ เพิ่มคนขับ" (กรอก pay contract)
   2. **รถ** → "+ เพิ่มรถ"
   3. **ลูกค้า** → "+ เพิ่มลูกค้า"
   4. **Daily** → "+ เพิ่มงาน" (dropdown เลือกคน/รถ/ลูกค้าได้แล้ว)

## โครงสร้างไฟล์

```
app/
  main.py              FastAPI + routes (Employee/Vehicle/Customer/DailyJob CRUD)
  models.py            SQLModel tables (11 ตาราง) + enums/choices
  templates/
    base.html              layout + nav
    daily_grid.html        หน้า Daily รวม (แก้แบบ Excel + คอลัมน์ดิบ/ชื่อจริง) เสิร์ฟที่ /daily
    daily_form.html        ฟอร์มงาน (new + edit ใช้ร่วมกัน)
    employees_list.html    คนขับ
    employee_form.html     ฟอร์มคนขับ + pay contract
    vehicles_list.html     รถ
    vehicle_form.html      ฟอร์มรถ (head/tail/truck)
    customers_list.html    ลูกค้า
    customer_form.html     ฟอร์มลูกค้า
  requirements.txt
  start.bat
  app.db               SQLite สร้างอัตโนมัติ (schema v2)
```

## ตาราง SQLite (schema v2)

**Master Data**: Employee, Vehicle, Customer, PayCycle (seed 3 ไซต์)
**Daily core**: DailyJob, DailyJobFee (ตารางพร้อม — UI รอ Phase 1.1.5)
**Payroll support** (ตารางพร้อม — UI รอ): LeaveRecord, AccidentCase, AccidentInstallment, DriverDeposit
**Billing ref**: BigcBranch (ตารางว่าง รอ import Excel จากผู้ใช้)
**Meta**: SchemaInfo (version tracking)

## Routes หลัก

- `/health` — สถานะ + schema version
- `/daily`, `/daily/new`, `/daily/{id}/edit`, `/daily/{id}/delete`
- `/employees`, `/employees/new`, `/employees/{id}/edit`, `/employees/{id}/delete`
- `/vehicles`, `/vehicles/new`, `/vehicles/{id}/edit`, `/vehicles/{id}/delete`
- `/customers`, `/customers/new`, `/customers/{id}/edit`, `/customers/{id}/delete`

## Pay Mode ที่รองรับ (Employee)

| Mode | ใช้กับ | ฟิลด์สำคัญ |
|---|---|---|
| `bigc_standard` | BIGC พขร.ทั่วไป | base_salary=9000, ค่าเที่ยวต่องาน, ค่าเรทน้ำมัน 16 บาท/ลิตรที่เหลือ |
| `lcb_trip` | LCB รายเที่ยว | base_salary=9240 + care_allowance=3000 + ค่าเที่ยวต่องาน |
| `lcb_mao` | LCB เหมาน้ำมัน | gross_share_rate=0.60 (รับ 60% ของค่าขนส่ง + ใส่รายการ "ไม่แบ่ง" ใน custom_terms) |
| `ayu_trip` | AYU รายเที่ยว | ค่าเที่ยวเท่านั้น + has_guarantee (6ล้อ=12000 / 10ล้อ=15000 เต็มเดือน) |
| `ayu_mao` | AYU เหมาน้ำมัน | gross_share_rate=0.55-0.60 ต่อคน (flexible) |

## Pay Cycles (seed อัตโนมัติ)

- **AYU**: 26 → 25 ของเดือนถัดไป · จ่ายสิ้นเดือน
- **BIGC**: 1 → สิ้นเดือน · จ่ายวันที่ 1 ของเดือนถัดไป (ค้าง 1 เดือน)
- **LCB**: 16 → 15 ของเดือนถัดไป · จ่ายวันที่ 1

## Schema Migration / Reset

ตอนนี้ยังใช้ SQLModel `create_all` เท่านั้น (ไม่มี alembic)
ถ้าจะอัปเกรดเพิ่มคอลัมน์: **ลบ `app.db` แล้วรันใหม่** — ระบบจะสร้างตารางใหม่และ seed pay_cycles ให้
ก่อนลบให้คัดลอกเก็บไว้ก่อนเป็นสำรองทุกครั้ง

## แผนถัดไป (Phase 1.1.5 + 1.2)

1. เพิ่ม UI `daily_job_fees` (ค่าย่อย LCB: lift/yard/clean/shore/port/weighing/special/ot/pickup_return/mflow)
2. หน้า `/leaves`, `/accidents`, `/deposits`, `/pay-cycles`
3. ฟอร์ม import BIGC branches จาก Excel (รอไฟล์ผู้ใช้)
4. สคริปต์ `tools/import_daily_{ayu,bigc,lcb}.py` — import จาก `ProjectYK_System/Daily.xlsx`
5. หน้า Dispatch → auto-fill Daily
