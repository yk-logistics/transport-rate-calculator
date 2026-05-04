# CUSTOMER BILLING PROFILE TEMPLATE

เอกสารแม่แบบสำหรับเก็บเงื่อนไขการวางบิลรายลูกค้า

---

## 1) Customer Header

- `customer_code`:
- `customer_name`:
- `site_scope`: AYU / BigC / LCB / ALL
- `billing_cycle`: รายสัปดาห์ / ราย 15 วัน / รายเดือน / อื่นๆ
- `credit_days`:
- `tax_type`: VAT included / VAT excluded / no VAT
- `active`: true/false

## 2) Invoice Format Rules

- `invoice_template_type`: standard / custom
- `invoice_no_pattern`: เช่น `LCB-YYYYMM-####`
- `line_grouping_rule`:
  - by_date
  - by_job_id
  - by_destination
  - by_container

- `required_line_fields`:
  - date
  - route
  - container_no
  - plate_no
  - trip_count
  - amount

## 3) Required Attachments

- POD (proof of delivery): required / optional
- ใบงานคนขับ: required / optional
- รูปถ่ายหน้างาน: required / optional
- ใบชั่ง/เอกสารพิเศษ: required / optional
- หมายเหตุเอกสาร:

## 4) Pricing Rules

- `price_source`: daily_rate / contract_rate / mixed
- `allow_manual_override`: yes/no
- `discount_rule`:
- `surcharge_rule`:
- `non_billable_conditions`:
  - กรณีงานยกเลิก
  - เอกสารไม่ครบ
  - เงื่อนไขพิเศษลูกค้า

## 5) Validation Rules Before Issue Invoice

- ต้องมีข้อมูลขั้นต่ำ:
  - job date
  - driver/vehicle
  - destination
  - amount
- ถ้าขาดเอกสาร required ห้ามออกใบวางบิล
- ถ้า amount = 0 ต้องระบุเหตุผล
- ถ้ามี manual override ต้องเก็บผู้อนุมัติ

## 6) Submission/Delivery Rules

- `delivery_channel`: email / line / portal / print
- `recipient_name`:
- `recipient_email`:
- `recipient_line_id`:
- `delivery_deadline`: เช่น ทุกวันที่ 3 ของเดือน
- `delivery_note`:

## 7) Payment Tracking Rules

- `due_date_rule`: invoice_date + credit_days
- `partial_payment_allowed`: yes/no
- `payment_reference_required`: yes/no
- `overdue_alert_days`: เช่น 3 วันก่อนครบกำหนด

## 8) Special Cases

- เอกสารคนละชุดตามประเภทงาน:
  - domestic
  - export
  - import
- เงื่อนไขช่วงเทศกาล/วันหยุด:
- เงื่อนไขหักค่าเสียหาย:

## 9) Approval Matrix

- ผู้จัดทำใบวางบิล:
- ผู้ตรวจสอบ:
- ผู้อนุมัติสุดท้าย:
- owner override:

## 10) Versioning

- `profile_version`:
- `effective_from`:
- `effective_to`:
- `changed_by`:
- `change_reason`:

---

## Example Record (ย่อ)

- customer_code: `BIGC01`
- customer_name: `Big C Logistics`
- billing_cycle: `monthly`
- credit_days: `45`
- required attachments: `POD + ใบงานคนขับ`
- line grouping: `by_destination`
- partial payment: `yes`

