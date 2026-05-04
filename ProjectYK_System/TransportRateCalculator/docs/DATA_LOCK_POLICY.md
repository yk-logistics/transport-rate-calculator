# DATA LOCK POLICY

เอกสารนี้กำหนดนโยบายการแก้ข้อมูลหลังอนุมัติ/ปิดรอบ เพื่อลดการเพี้ยนของตัวเลขข้ามโมดูล

## 1) หลักการ

- หลังอนุมัติรอบเงินเดือนหรือปิดบัญชี ข้อมูลต้นทางต้อง lock
- ไม่แก้ทับข้อมูลโดยตรงย้อนหลัง ให้ใช้ adjustment document
- ทุก adjustment ต้องมีเหตุผลและผู้อนุมัติ

## 2) Lock Trigger

ข้อมูลที่เกี่ยวข้องกับรอบจะ lock เมื่อเกิดอย่างใดอย่างหนึ่ง:

1. `payroll_runs.status = approved`
2. `payroll_runs.status = locked`
3. accounting month close ของรอบนั้นสำเร็จ

## 3) ตารางที่ lock

- `daily_jobs` (เฉพาะรอบที่ปิด)
- `fuel_txns` (เฉพาะรอบที่ปิด)
- `advance_txns` (เฉพาะรอบที่ปิด)
- `billing_docs` / `billing_lines` ที่ออกเอกสารแล้ว
- `payroll_lines` ของ run ที่อนุมัติแล้ว

## 4) สิ่งที่ยังแก้ได้แม้ lock

- หมายเหตุเอกสารที่ไม่กระทบตัวเงิน
- attachment metadata (เช่น tag)
- reference ภายในที่ไม่กระทบผลคำนวณ

## 5) Adjustment Mechanism

ถ้าต้องแก้ตัวเงินหลัง lock:

1. สร้างเอกสาร `adjustment_request`
2. ระบุ:
   - table/ref_id เดิม
   - ค่าเดิม/ค่าใหม่
   - เหตุผล
   - รอบที่กระทบ
3. ผู้อนุมัติ (Accounting lead หรือ Owner)
4. ระบบสร้าง `adjustment entry` แยก ไม่แก้ทับ row เดิม

## 6) Reconciliation Rule

- ทุก adjustment ที่กระทบ payroll ต้องปรากฏในรอบถัดไปหรือในเอกสาร correction
- ทุก adjustment ที่กระทบ billing ต้องมีเอกสารประกอบ (debit/credit note ตามใช้งานจริง)

## 7) Permission Matrix (lock related)

- Dispatcher / Daily / Billing operator:
  - แก้ไขข้อมูลได้ก่อน lock เท่านั้น
- Payroll officer:
  - approve payroll run และ lock รอบ
- Accounting:
  - month close และอนุมัติ adjustment ฝั่งการเงิน
- Owner:
  - override เฉพาะกรณีจำเป็น พร้อมเหตุผลบังคับ
- Admin IT:
  - ไม่มีสิทธิ์แก้ค่าทางธุรกิจโดยตรง

## 8) Audit Requirements

ต้องเก็บ:
- action_type (create/update/lock/unlock/adjust)
- actor
- timestamp
- before_value / after_value
- reason
- approval_ref

## 9) Emergency Unlock (exception)

ทำได้เฉพาะ:
- Owner หรือผู้ได้รับมอบหมาย
- ต้องระบุ incident id
- ต้องมี log และแจ้งผู้เกี่ยวข้อง
- หลัง unlock ต้อง relock ภายในช่วงเวลาที่กำหนด

