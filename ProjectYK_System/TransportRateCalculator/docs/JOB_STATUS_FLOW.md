# JOB STATUS FLOW

เอกสารกำหนดสถานะงานมาตรฐาน และเงื่อนไขเปลี่ยนสถานะ

## 1) Main Flow

1. `draft`
2. `planned`
3. `dispatched`
4. `in_progress`
5. `completed`
6. `billable_review`
7. `ready_to_invoice`
8. `invoiced`
9. `paid` หรือ `partial_paid` หรือ `overdue`
10. `closed`

## 2) ความหมายแต่ละสถานะ

- `draft` - รับงานแล้วแต่ยังไม่จัดรถ/คนขับ
- `planned` - จัดรถ/คนขับแล้ว รอวันวิ่ง
- `dispatched` - แจ้งงานเรียบร้อย (รวมข้อความไลน์)
- `in_progress` - งานกำลังวิ่งจริง
- `completed` - งานจบและบันทึกข้อมูลรายวันครบ
- `billable_review` - ตรวจเอกสารและเงื่อนไขวางบิล
- `ready_to_invoice` - พร้อมออกเอกสารวางบิล
- `invoiced` - ออกใบวางบิลแล้ว
- `partial_paid` - จ่ายเข้าบางส่วน
- `paid` - ปิดยอดวางบิลครบ
- `overdue` - เกินกำหนดชำระ
- `closed` - ปิดงานในรอบบัญชีแล้ว

## 3) State Transition Rules

- `draft -> planned`
  - ต้องมี site, วันที่งาน, ลูกค้า, จุดรับ-ส่ง อย่างน้อย
  - ผู้ทำได้: Dispatcher

- `planned -> dispatched`
  - ต้องเลือกคนขับ/รถแล้ว
  - ระบบสร้างข้อความแจ้งงานสำเร็จ
  - ผู้ทำได้: Dispatcher

- `dispatched -> in_progress`
  - เริ่มวันงานจริง
  - ผู้ทำได้: Dispatcher/Daily Operator

- `in_progress -> completed`
  - กรอกข้อมูล daily ขั้นต่ำครบ:
    - วันที่
    - คนขับ
    - รถ
    - ประเภทงาน
    - ค่ารายได้/ค่าเที่ยว หรือเหตุผลที่ว่าง
  - ผู้ทำได้: Daily Operator

- `completed -> billable_review`
  - ตรวจเอกสารหน้างานและความครบถ้วนเรียบร้อย
  - ผู้ทำได้: Billing Operator

- `billable_review -> ready_to_invoice`
  - ผ่าน validation วางบิลตาม profile ลูกค้า
  - ผู้ทำได้: Billing Operator

- `ready_to_invoice -> invoiced`
  - สร้างเอกสารวางบิลสำเร็จ
  - ผู้ทำได้: Billing Operator

- `invoiced -> partial_paid/paid/overdue`
  - ตามการรับเงินจริงและวันครบกำหนด
  - ผู้ทำได้: Accounting

- `paid -> closed`
  - ปิดรอบบัญชีและ lock ข้อมูล
  - ผู้ทำได้: Accounting (หรือ Owner override)

## 4) Non-billable Branch

หลัง `completed` ถ้ารายการวางบิลไม่ได้:
- สถานะย่อย `non_billable_approved`
- ต้องระบุเหตุผล:
  - ลูกค้าไม่รับวางบิล
  - งานยกเลิก
  - ค่าเสียหายภายใน
- ส่งต้นทุนเข้าฝั่ง accounting โดยตรง

## 5) Validation Gate ก่อนออกวางบิล

- ชื่องานต้อง match กับ customer profile
- เอกสารแนบครบตามลูกค้า
- จำนวนเงินไม่ว่าง
- รายการผิดปกติ (เช่น revenue = 0 แต่ marked billable) ต้องอนุมัติพิเศษ

## 6) Lock Policy

- เมื่อ payroll run/status = approved หรือ accounting month close แล้ว:
  - daily/billing lines ที่เกี่ยวข้องต้อง lock
  - ถ้าจะแก้ ต้องทำ adjustment document เท่านั้น

## 7) Audit Log Requirements

ทุกการเปลี่ยนสถานะต้องเก็บ:
- from_status
- to_status
- changed_by
- changed_at
- reason/comment

