# LCB OT + รับตู้แทน เข้าเป็นรายได้คนขับ + แสดงคอลัมน์พิเศษ/OT/รับตู้แทน

วันที่: 2026-06-25
สถานะ: design — รออนุมัติจากโอ
ประเภท: **งานเงิน** (กระทบ net pay) → ต้อง preflight + recompute + ตรวจย้อนกลับ

## ที่มา

โอขอเพิ่มคอลัมน์รายได้คนขับในตารางเดลี่ของ #86: พิเศษ / OT / รับตู้แทน
ตรวจ DB แล้วพบว่า:
- **พิเศษ 100/เที่ยว** — engine บวกอยู่แล้ว (`n_trip × 100` → other_income, เฉพาะวันเที่ยว) → **แค่แสดงคอลัมน์**
- **OT + รับตู้แทน** — เก็บใน `DailyJobFee` (child table) แต่ engine **ไม่เคยบวกให้ใครเลย**
  → โอยืนยัน: บวกเข้า net pay จริง **ทุก mode LCB** (trip/mao/mixed)

## ขอบเขต fee (โอยืนยัน)

| กลุ่มแสดง | fee_type ที่นับรวม (case-insensitive) |
|----------|-----------------------------------------|
| OT | `OT`, `ot`, `ค่าล่วงเวลา` |
| รับตู้แทน | `pickup_return`, `รับตู้แทน` |
| พิเศษ (โบนัส) | ไม่ใช่ fee — คือ `n_trip × 100` เดิมใน engine |

> **สำคัญ:** fee `special`/`ค่าพิเศษ` ใน DailyJobFee = ค่าพิเศษที่บิลลูกค้า (อยู่ใน
> revenue แล้ว) **ไม่ใช่** โบนัส 100/เที่ยว — ห้ามนับซ้ำ ห้ามแตะ

## ผลกระทบเงิน (blast radius — วัดจาก DB ปัจจุบัน)

OT+รับตู้แทน รวมทั้งระบบ (ยังไม่เคยจ่าย):
- lcb_trip: 46 fee = 6,100฿
- lcb_mao: 13 fee = 2,600฿
- lcb_mixed: 5 fee = 500฿ (**ไม่รวม #86** ที่ไม่มี fee นี้รอบนี้)

→ emp #86 รอบนี้ net **ไม่เปลี่ยน** (ไม่มี OT/รับตู้แทน) — การเปลี่ยนแปลงเงินจริง
อยู่ที่คนอื่นใน LCB

## การแก้ engine (services/payroll.py)

1. helper ใหม่ `_sum_driver_fees(session, emp_id, start, end, fee_types, site_code)`
   — join DailyJobFee↔DailyJob, filter `lower(fee_type) in fee_types`, คืน sum
   (ตามแพทเทิร์น `_sum_trip_fees`)
2. ค่าคงที่: `LCB_OT_FEE_TYPES = {"ot","ค่าล่วงเวลา"}`,
   `LCB_PICKUP_RETURN_FEE_TYPES = {"pickup_return","รับตู้แทน"}`
3. ในทั้ง 3 บล็อก `lcb_trip` / `lcb_mao` / `lcb_mixed`:
   `calc.other_income += ot_sum + pickup_return_sum` และต่อท้าย note
   (`+ OT x,xxx + รับตู้แทน x,xxx`)
4. ไม่แตะ mode อื่น (bigc/ayu/...)

> เก็บใน `other_income` เพราะ gross_total รวม other_income อยู่แล้ว (บรรทัด 190)
> และ slip มีบรรทัด "รายได้อื่น" รองรับ → ไม่ต้องเพิ่ม field ใน PayRunItem

## การแสดงผล (display)

### detail (payroll_employee_detail.html, lcb_mixed)
เพิ่ม 3 คอลัมน์ในตารางเดลี่เดียวเรียงวันที่: **พิเศษ · OT · รับตู้แทน**
- พิเศษ: แถวเที่ยวโชว์ `100`, แถวเหมา/จอด ว่าง
- OT / รับตู้แทน: ดึงจาก DailyJobFee ของแถวนั้น (helper ส่ง map daily_job_id→{ot,pickup})
- คอลัมน์ "ได้" เดิม = ค่าหลัก (เหมา×60% / ค่าเที่ยว) คงไว้

### slip (payroll_slip.html) — ทุก LCB
"รายได้อื่น" แสดงอยู่แล้ว (other_income) → จะรวม OT+รับตู้แทน+พิเศษเข้าไปอัตโนมัติ
หลัง recompute ไม่ต้องแก้ slip template

## helper map สำหรับ display

`fees_by_day(daily_jobs, session)` → `{daily_job_id: {"ot": x, "pickup_return": y}}`
ใช้ใน detail handler เท่านั้น (slip ใช้ตัวเลขรวมจาก other_income)

## การตรวจย้อนกลับ (preflight — ก่อน recompute)

1. สคริปต์ read-only: list ทุก PayRunItem ที่ other_income จะเปลี่ยน +
   เทียบ before/after (เฉพาะ OT/รับตู้แทน sum) ต่อคน ต่อรอบ
2. ยืนยันยอดรวมตรงกับ blast-radius (trip 6,100 / mao 2,600 / mixed 500)
3. ยืนยัน special/ค่าพิเศษ ไม่ถูกนับ (count = 0 ใน fee filter)
4. recompute เฉพาะรอบที่กระทบ → diff net per emp → โอดูก่อน finalize
5. รอบที่ finalized แล้ว **ห้าม recompute** (guardrail เดิม) — รายงานแยก

## YAGNI / ไม่ทำ
- ไม่เพิ่ม field ใน PayRunItem (ใช้ other_income)
- ไม่แตะ mode ที่ไม่ใช่ LCB
- ไม่แตะ fee special/lift/yard/port_entry/clean (เป็น revenue ลูกค้า)
- ไม่ recompute/ขึ้น server จนกว่าโอจะเห็น preflight diff และสั่ง go
