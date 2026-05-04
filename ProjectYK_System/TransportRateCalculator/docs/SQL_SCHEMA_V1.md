# SQL SCHEMA V1 (PostgreSQL)

เอกสารนี้เป็น DDL ตั้งต้นให้ทีมพัฒนาเริ่มสร้างฐานข้อมูลได้ทันที

หมายเหตุ:
- ใช้ `bigserial` เป็น PK รุ่นแรกเพื่อความง่าย
- ถ้าต้องการ `uuid` ค่อย migration ใน v2 ได้

```sql
-- 1) employees
create table if not exists employees (
  employee_id bigserial primary key,
  full_name text not null,
  clean_name text not null,
  site_code text not null,
  pay_type text not null check (pay_type in ('Trip','Mao')),
  ss_enabled boolean not null default true,
  deposit_balance numeric(14,2) not null default 0,
  skip_first_fuel boolean not null default false,
  skip_fuel_before_date date null,
  status text not null default 'active',
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);

create index if not exists idx_employees_site on employees(site_code);
create index if not exists idx_employees_clean_name on employees(clean_name);

-- 2) vehicles
create table if not exists vehicles (
  vehicle_id bigserial primary key,
  plate_no text not null,
  site_code text not null,
  vehicle_type text null,
  brand text null,
  model text null,
  year int null,
  current_mileage numeric(14,2) not null default 0,
  status text not null default 'active',
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);

create unique index if not exists uq_vehicles_plate_site on vehicles(plate_no, site_code);

-- 3) job_orders
create table if not exists job_orders (
  job_id bigserial primary key,
  site_code text not null,
  customer_code text null,
  job_date date not null,
  job_type text null,
  origin text null,
  destination text null,
  container_no text null,
  planned_revenue numeric(14,2) not null default 0,
  planned_driver_id bigint null references employees(employee_id),
  planned_vehicle_id bigint null references vehicles(vehicle_id),
  status text not null default 'draft',
  line_message_text text null,
  created_by text null,
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);

create index if not exists idx_job_orders_site_date on job_orders(site_code, job_date);
create index if not exists idx_job_orders_status on job_orders(status);

-- 4) daily_jobs
create table if not exists daily_jobs (
  daily_job_id bigserial primary key,
  job_id bigint null references job_orders(job_id),
  site_code text not null,
  work_date date not null,
  driver_id bigint null references employees(employee_id),
  driver_raw_name text null,
  vehicle_id bigint null references vehicles(vehicle_id),
  plate_no_raw text null,
  customer_name_raw text null,
  trip_type text null,
  origin text null,
  destination text null,
  container_no text null,
  status_note text null,
  mileage_start numeric(14,2) null,
  mileage_end numeric(14,2) null,
  trip_fee_driver numeric(14,2) not null default 0,
  extra_amount numeric(14,2) not null default 0,
  customer_revenue numeric(14,2) not null default 0,
  source_file text null,
  source_sheet text null,
  source_row int null,
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);

create index if not exists idx_daily_jobs_site_date on daily_jobs(site_code, work_date);
create index if not exists idx_daily_jobs_driver on daily_jobs(driver_id);

-- 5) fuel_txns
create table if not exists fuel_txns (
  fuel_txn_id bigserial primary key,
  site_code text not null,
  txn_date date not null,
  driver_id bigint null references employees(employee_id),
  driver_raw_name text null,
  vehicle_id bigint null references vehicles(vehicle_id),
  plate_no_raw text null,
  mile numeric(14,2) null,
  liter numeric(14,3) not null default 0,
  amount numeric(14,2) not null default 0,
  station_name text null,
  source_file text null,
  source_sheet text null,
  source_row int null,
  created_at timestamp not null default now()
);

create index if not exists idx_fuel_txns_site_date on fuel_txns(site_code, txn_date);
create index if not exists idx_fuel_txns_driver on fuel_txns(driver_id);

-- 6) advance_txns
create table if not exists advance_txns (
  advance_txn_id bigserial primary key,
  site_code text not null,
  txn_date date not null,
  driver_id bigint null references employees(employee_id),
  driver_raw_name text null,
  category text not null,
  billable_flag boolean not null default false,
  pending_flag boolean not null default false,
  amount numeric(14,2) not null,
  description text null,
  evidence_file_path text null,
  source_file text null,
  source_sheet text null,
  source_row int null,
  created_by text null,
  created_at timestamp not null default now()
);

create index if not exists idx_advance_txns_site_date on advance_txns(site_code, txn_date);
create index if not exists idx_advance_txns_pending on advance_txns(pending_flag);

-- 7) billing_docs
create table if not exists billing_docs (
  billing_id bigserial primary key,
  site_code text not null,
  customer_code text null,
  billing_period_start date not null,
  billing_period_end date not null,
  invoice_no text null,
  invoice_date date null,
  due_date date null,
  amount_subtotal numeric(14,2) not null default 0,
  amount_tax numeric(14,2) not null default 0,
  amount_total numeric(14,2) not null default 0,
  status text not null default 'draft',
  customer_profile_code text null,
  attachment_path text null,
  created_by text null,
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);

create index if not exists idx_billing_docs_site_period on billing_docs(site_code, billing_period_start, billing_period_end);
create index if not exists idx_billing_docs_status on billing_docs(status);

-- 8) billing_lines
create table if not exists billing_lines (
  billing_line_id bigserial primary key,
  billing_id bigint not null references billing_docs(billing_id) on delete cascade,
  job_id bigint null references job_orders(job_id),
  daily_job_id bigint null references daily_jobs(daily_job_id),
  line_date date null,
  description text null,
  quantity numeric(14,3) not null default 1,
  unit_price numeric(14,2) not null default 0,
  line_total numeric(14,2) not null default 0,
  cost_estimate numeric(14,2) not null default 0,
  margin_estimate_pct numeric(7,2) not null default 0
);

create index if not exists idx_billing_lines_billing_id on billing_lines(billing_id);

-- 9) payroll_runs
create table if not exists payroll_runs (
  payroll_run_id bigserial primary key,
  site_code text not null,
  period_start date not null,
  period_end date not null,
  status text not null default 'draft',
  approved_by text null,
  approved_at timestamp null,
  created_at timestamp not null default now()
);

create index if not exists idx_payroll_runs_site_period on payroll_runs(site_code, period_start, period_end);

-- 10) payroll_lines
create table if not exists payroll_lines (
  payroll_line_id bigserial primary key,
  payroll_run_id bigint not null references payroll_runs(payroll_run_id) on delete cascade,
  employee_id bigint not null references employees(employee_id),
  pay_type text not null check (pay_type in ('Trip','Mao')),
  work_days numeric(7,2) not null default 0,
  salary_amount numeric(14,2) not null default 0,
  care_amount numeric(14,2) not null default 0,
  trip_fee_amount numeric(14,2) not null default 0,
  extra_amount numeric(14,2) not null default 0,
  gross_income numeric(14,2) not null default 0,
  fuel_deduction numeric(14,2) not null default 0,
  advance_deduction numeric(14,2) not null default 0,
  social_security numeric(14,2) not null default 0,
  tax numeric(14,2) not null default 0,
  deposit_deduction numeric(14,2) not null default 0,
  net_income numeric(14,2) not null default 0,
  note text null
);

create index if not exists idx_payroll_lines_run on payroll_lines(payroll_run_id);
create index if not exists idx_payroll_lines_employee on payroll_lines(employee_id);

-- 11) maintenance_jobs
create table if not exists maintenance_jobs (
  maintenance_job_id bigserial primary key,
  site_code text not null,
  vehicle_id bigint not null references vehicles(vehicle_id),
  job_type text not null check (job_type in ('PM','RM')),
  opened_date date not null,
  mileage_at_open numeric(14,2) null,
  symptom text null,
  vendor_name text null,
  labor_cost numeric(14,2) not null default 0,
  parts_cost numeric(14,2) not null default 0,
  total_cost numeric(14,2) not null default 0,
  status text not null default 'open',
  closed_date date null,
  mileage_at_close numeric(14,2) null,
  attachment_path text null,
  created_by text null,
  created_at timestamp not null default now()
);

create index if not exists idx_maintenance_jobs_vehicle on maintenance_jobs(vehicle_id);
create index if not exists idx_maintenance_jobs_status on maintenance_jobs(status);

-- 12) maintenance_items
create table if not exists maintenance_items (
  maintenance_item_id bigserial primary key,
  maintenance_job_id bigint not null references maintenance_jobs(maintenance_job_id) on delete cascade,
  part_code text null,
  part_name text not null,
  qty numeric(14,3) not null default 1,
  unit_cost numeric(14,2) not null default 0,
  line_total numeric(14,2) not null default 0,
  supplier_name text null
);

create index if not exists idx_maintenance_items_job on maintenance_items(maintenance_job_id);

-- 13) tires
create table if not exists tires (
  tire_id bigserial primary key,
  serial_no text not null unique,
  brand text null,
  model text null,
  size text null,
  purchase_date date null,
  purchase_cost numeric(14,2) not null default 0,
  status text not null default 'in_stock'
);

-- 14) tire_history
create table if not exists tire_history (
  tire_history_id bigserial primary key,
  tire_id bigint not null references tires(tire_id),
  vehicle_id bigint null references vehicles(vehicle_id),
  position_code text null,
  action_type text not null,
  action_date date not null,
  mileage numeric(14,2) null,
  note text null
);

create index if not exists idx_tire_history_tire on tire_history(tire_id);
create index if not exists idx_tire_history_vehicle on tire_history(vehicle_id);

-- 15) stock_items
create table if not exists stock_items (
  stock_item_id bigserial primary key,
  part_code text not null,
  part_name text not null,
  category text null,
  uom text null,
  min_qty numeric(14,3) not null default 0,
  on_hand_qty numeric(14,3) not null default 0,
  avg_cost numeric(14,2) not null default 0,
  last_purchase_price numeric(14,2) not null default 0,
  updated_at timestamp not null default now()
);

create unique index if not exists uq_stock_items_part_code on stock_items(part_code);

-- 16) stock_moves
create table if not exists stock_moves (
  stock_move_id bigserial primary key,
  stock_item_id bigint not null references stock_items(stock_item_id),
  move_type text not null,
  qty numeric(14,3) not null,
  unit_cost numeric(14,2) not null default 0,
  ref_type text null,
  ref_id text null,
  move_date date not null,
  note text null
);

create index if not exists idx_stock_moves_item_date on stock_moves(stock_item_id, move_date);
```

## Notes

- `status` และ `category` ให้ validate ซ้ำชั้น API ตาม `ENUMS_AND_RULES.md`
- แนะนำเพิ่ม trigger set `updated_at` อัตโนมัติในขั้น implement

