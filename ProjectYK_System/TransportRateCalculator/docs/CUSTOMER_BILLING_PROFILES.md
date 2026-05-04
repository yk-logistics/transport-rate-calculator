# CUSTOMER BILLING PROFILES (SEED)

เอกสารตั้งต้นสำหรับลูกค้า 3-5 เจ้าหลักในระบบ

หมายเหตุ: ค่านี้เป็น seed profile เพื่อเริ่มใช้งาน ต้องยืนยันรายละเอียดจริงกับผู้ปฏิบัติงานก่อน final

---

## PROFILE 01

- `customer_code`: `BIGC_CORE`
- `customer_name`: `Big C`
- `site_scope`: `BigC`
- `billing_cycle`: `monthly`
- `credit_days`: `45`
- `tax_type`: `VAT excluded`
- `invoice_template_type`: `custom`
- `line_grouping_rule`: `by_destination`
- `required_attachments`:
  - POD: required
  - ใบงานคนขับ: required
  - รูปถ่ายหน้างาน: optional
- `allow_manual_override`: `yes` (ต้องมีผู้อนุมัติ)
- `delivery_channel`: `email + line`
- `partial_payment_allowed`: `yes`

## PROFILE 02

- `customer_code`: `LCB_GENERAL`
- `customer_name`: `LCB General Customers`
- `site_scope`: `LCB`
- `billing_cycle`: `monthly`
- `credit_days`: `30`
- `tax_type`: `VAT excluded`
- `invoice_template_type`: `standard`
- `line_grouping_rule`: `by_job_id`
- `required_attachments`:
  - POD: required
  - ใบงานคนขับ: required
  - เอกสารท่าเรือ: optional
- `allow_manual_override`: `yes`
- `delivery_channel`: `email`
- `partial_payment_allowed`: `yes`

## PROFILE 03

- `customer_code`: `AYU_ROUTE`
- `customer_name`: `AYU Route Accounts`
- `site_scope`: `AYU`
- `billing_cycle`: `monthly`
- `credit_days`: `30`
- `tax_type`: `VAT excluded`
- `invoice_template_type`: `standard`
- `line_grouping_rule`: `by_date`
- `required_attachments`:
  - POD: optional
  - ใบงานคนขับ: required
  - รูปถ่ายหน้างาน: optional
- `allow_manual_override`: `yes`
- `delivery_channel`: `line + print`
- `partial_payment_allowed`: `no`

## PROFILE 04

- `customer_code`: `EXPORT_SPECIAL`
- `customer_name`: `Export Special Accounts`
- `site_scope`: `LCB`
- `billing_cycle`: `semi_monthly`
- `credit_days`: `60`
- `tax_type`: `VAT excluded`
- `invoice_template_type`: `custom`
- `line_grouping_rule`: `by_container`
- `required_attachments`:
  - POD: required
  - ใบงานคนขับ: required
  - เอกสารตู้/ท่าเรือ: required
- `allow_manual_override`: `no`
- `delivery_channel`: `email`
- `partial_payment_allowed`: `yes`

## PROFILE 05

- `customer_code`: `DOMESTIC_FLEX`
- `customer_name`: `Domestic Flexible Accounts`
- `site_scope`: `ALL`
- `billing_cycle`: `weekly`
- `credit_days`: `15`
- `tax_type`: `VAT excluded`
- `invoice_template_type`: `standard`
- `line_grouping_rule`: `by_date`
- `required_attachments`:
  - POD: optional
  - ใบงานคนขับ: required
  - เอกสารพิเศษ: optional
- `allow_manual_override`: `yes`
- `delivery_channel`: `line`
- `partial_payment_allowed`: `no`

---

## Next Step

- ให้ทีม Billing ยืนยัน profile ทีละลูกค้า
- เมื่อยืนยันแล้ว ให้กำหนด `profile_version` และ `effective_from`

