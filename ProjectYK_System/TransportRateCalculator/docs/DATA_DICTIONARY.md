# DATA DICTIONARY

เอกสารนี้นิยามโครงข้อมูลมาตรฐานกลางของระบบ

## 1) Naming Convention

- ใช้ `snake_case`
- วันที่ใช้ `date` (YYYY-MM-DD)
- เวลาทำรายการใช้ `timestamp`
- ค่าการเงินใช้ `numeric(14,2)`
- id หลักใช้ `uuid` หรือ `bigint` (เลือกตอน implement)

## 2) Core Tables

## 2.1 `employees`

- `employee_id` - รหัสพนักงาน (PK)
- `full_name` - ชื่อเต็มตามบัตร/เอกสาร
- `clean_name` - ชื่อ normalize สำหรับ map ข้ามไฟล์
- `site_code` - AYU/BigC/LCB
- `pay_type` - Trip/Mao
- `ss_enabled` - ส่งประกันสังคมหรือไม่
- `deposit_balance` - ยอดประกันสะสม
- `skip_first_fuel` - ข้ามถังแรกเดือนแรก
- `skip_fuel_before_date` - เริ่มหักน้ำมันตั้งแต่วันที่
- `status` - active/inactive
- `created_at`, `updated_at`

## 2.2 `vehicles`

- `vehicle_id` - รหัสรถ (PK)
- `plate_no` - ทะเบียนรถ
- `site_code` - AYU/BigC/LCB
- `vehicle_type` - หัวลาก/6W/อื่นๆ
- `brand`, `model`, `year`
- `current_mileage`
- `status` - active/maintenance/inactive
- `created_at`, `updated_at`

## 2.3 `job_orders`

- `job_id` - รหัสงาน (PK)
- `site_code`
- `customer_id` (nullable ช่วงแรก)
- `job_date`
- `job_type` - domestic/export/import/other
- `origin`, `destination`
- `container_no`
- `planned_revenue`
- `planned_driver_id` (nullable)
- `planned_vehicle_id` (nullable)
- `status` - draft/planned/dispatched/in_progress/completed/closed
- `line_message_text` - template ข้อความสำหรับส่งไลน์
- `created_by`, `created_at`, `updated_at`

## 2.4 `daily_jobs`

- `daily_job_id` - PK
- `job_id` (nullable ช่วง import)
- `site_code`
- `work_date`
- `driver_id` (nullable หากยังไม่ map)
- `driver_raw_name`
- `vehicle_id` (nullable)
- `plate_no_raw`
- `customer_name_raw`
- `trip_type`
- `origin`, `destination`
- `container_no`
- `status_note` - ลา/ไม่พร้อม/พักงาน/หมายเหตุ
- `mileage_start`, `mileage_end`
- `trip_fee_driver`
- `extra_amount`
- `customer_revenue`
- `source_file`, `source_sheet`, `source_row`
- `created_at`, `updated_at`

## 2.5 `fuel_txns`

- `fuel_txn_id` - PK
- `site_code`
- `txn_date`
- `driver_id` (nullable)
- `driver_raw_name`
- `vehicle_id` (nullable)
- `plate_no_raw`
- `mile`
- `liter`
- `amount`
- `station_name`
- `source_file`, `source_sheet`, `source_row`
- `created_at`

## 2.6 `advance_txns` (สดย่อย)

- `advance_txn_id` - PK
- `site_code`
- `txn_date`
- `driver_id` (nullable)
- `driver_raw_name`
- `category` - advance/cash_return/expense/pending_deduction/installment/accident
- `billable_flag` - วางบิลได้/ไม่ได้
- `pending_flag` - ค้างหักเงินเดือนหรือไม่
- `amount`
- `description`
- `evidence_file_path`
- `source_file`, `source_sheet`, `source_row`
- `created_by`, `created_at`

## 2.7 `billing_docs`

- `billing_id` - PK
- `site_code`
- `customer_id` (nullable ช่วงแรก)
- `billing_period_start`, `billing_period_end`
- `invoice_no`
- `invoice_date`
- `due_date`
- `amount_subtotal`, `amount_tax`, `amount_total`
- `status` - draft/sent/partial/paid/overdue/cancelled
- `customer_profile_code`
- `attachment_path`
- `created_by`, `created_at`, `updated_at`

## 2.8 `billing_lines`

- `billing_line_id` - PK
- `billing_id` - FK
- `job_id` (nullable)
- `daily_job_id` (nullable)
- `line_date`
- `description`
- `quantity`
- `unit_price`
- `line_total`
- `cost_estimate`
- `margin_estimate_pct`

## 2.9 `payroll_runs`

- `payroll_run_id` - PK
- `site_code`
- `period_start`, `period_end`
- `status` - draft/approved/locked
- `approved_by`
- `approved_at`
- `created_at`

## 2.10 `payroll_lines`

- `payroll_line_id` - PK
- `payroll_run_id` - FK
- `employee_id`
- `pay_type`
- `work_days`
- `salary_amount`
- `care_amount`
- `trip_fee_amount`
- `extra_amount`
- `gross_income`
- `fuel_deduction`
- `advance_deduction`
- `social_security`
- `tax`
- `deposit_deduction`
- `net_income`
- `note`

## 2.11 `maintenance_jobs`

- `maintenance_job_id` - PK
- `site_code`
- `vehicle_id`
- `job_type` - PM/RM
- `opened_date`
- `mileage_at_open`
- `symptom`
- `vendor_name`
- `labor_cost`
- `parts_cost`
- `total_cost`
- `status` - open/in_progress/closed
- `closed_date`
- `mileage_at_close`
- `attachment_path`
- `created_by`, `created_at`

## 2.12 `maintenance_items`

- `maintenance_item_id` - PK
- `maintenance_job_id` - FK
- `part_code` (nullable)
- `part_name`
- `qty`
- `unit_cost`
- `line_total`
- `supplier_name`

## 2.13 `tires`

- `tire_id` - PK
- `serial_no`
- `brand`
- `model`
- `size`
- `purchase_date`
- `purchase_cost`
- `status` - in_use/in_stock/retired

## 2.14 `tire_history`

- `tire_history_id` - PK
- `tire_id` - FK
- `vehicle_id` - FK
- `position_code` - FL/FR/RL/RR/etc
- `action_type` - install/rotate/repair/remove/retire
- `action_date`
- `mileage`
- `note`

## 2.15 `stock_items`

- `stock_item_id` - PK
- `part_code`
- `part_name`
- `category`
- `uom`
- `min_qty`
- `on_hand_qty`
- `avg_cost`
- `last_purchase_price`
- `updated_at`

## 2.16 `stock_moves`

- `stock_move_id` - PK
- `stock_item_id` - FK
- `move_type` - in/out/adjust
- `qty`
- `unit_cost`
- `ref_type` - purchase/maintenance/manual
- `ref_id`
- `move_date`
- `note`

## 3) Site Mapping Minimum Columns

## 3.1 AYU Daily (minimum)
- date
- driver
- plate
- customer_revenue
- trip_fee_driver

## 3.2 BigC Daily (minimum)
- date
- driver
- plate
- customer_revenue
- trip_fee_driver
- status_note

## 3.3 LCB Daily (minimum)
- date
- driver
- plate
- customer
- container_no
- customer_revenue
- trip_fee_driver
- mileage/fuel columns (ถ้ามี)

## 4) Cross-module Reconcile Keys

- employee: `clean_name` -> `employee_id`
- vehicle: `plate_no` -> `vehicle_id`
- period: `period_start/period_end` เดียวกันทั้ง billing/payroll/accounting

