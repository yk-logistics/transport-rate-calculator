# ENUMS AND RULES

เอกสารล็อกค่า enum กลางของระบบ เพื่อให้ database/API/frontend ใช้ค่าเดียวกัน

## 1) Site Code

- `AYU`
- `BigC`
- `LCB`

## 2) Job Status (`job_orders.status`)

- `draft`
- `planned`
- `dispatched`
- `in_progress`
- `completed`
- `billable_review`
- `ready_to_invoice`
- `invoiced`
- `partial_paid`
- `paid`
- `overdue`
- `closed`
- `cancelled`

## 3) Payroll Pay Type (`employees.pay_type`, `payroll_lines.pay_type`)

- `Trip`
- `Mao`

## 4) Invoice Status (`billing_docs.status`)

- `draft`
- `sent`
- `partial`
- `paid`
- `overdue`
- `cancelled`

## 5) Petty Cash Category (`advance_txns.category`)

- `advance` - โอนล่วงหน้า/เงินสำรอง
- `cash_return` - เงินทอนกลับ
- `expense` - ค่าใช้จ่ายหน้างาน
- `pending_deduction` - ค้างหักเงินเดือน
- `installment` - ผ่อนชำระ
- `accident` - ค่าเสียหาย/อุบัติเหตุ
- `fuel_support` - เงินช่วยค่าน้ำมัน
- `other`

## 6) Petty Cash Flags

### `billable_flag`
- `true` = นำไปรวมวางบิลลูกค้าได้
- `false` = ต้นทุนภายใน

### `pending_flag`
- `true` = ต้องหักใน payroll รอบถัดไป/ตามกำหนด
- `false` = ปิดรายการแล้ว

## 7) Maintenance Job Type (`maintenance_jobs.job_type`)

- `PM` - preventive maintenance
- `RM` - repair maintenance

## 8) Maintenance Status (`maintenance_jobs.status`)

- `open`
- `in_progress`
- `waiting_parts`
- `closed`
- `cancelled`

## 9) Stock Move Type (`stock_moves.move_type`)

- `in`
- `out`
- `adjust`
- `return`

## 10) Approval Status (generic)

- `draft`
- `submitted`
- `approved`
- `rejected`
- `locked`

## 11) Validation Severity

- `info`
- `warn`
- `error`
- `blocker`

## 12) Non-billable Reason (proposed)

- `customer_rejected`
- `cancelled_job`
- `internal_error`
- `missing_document`
- `other`

