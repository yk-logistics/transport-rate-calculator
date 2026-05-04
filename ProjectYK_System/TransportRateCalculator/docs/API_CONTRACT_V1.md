# API CONTRACT V1

เอกสารนี้กำหนด REST API ชุดแรกสำหรับเริ่มพัฒนา MVP

Base path: `/api/v1`
Data format: `application/json`

## 1) Common Response

## Success
```json
{
  "success": true,
  "data": {},
  "meta": {}
}
```

## Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "human readable message",
    "details": []
  }
}
```

## 2) Auth (initial)

### `POST /auth/login`
- Request:
```json
{
  "username": "user1",
  "password": "********"
}
```
- Response: access token + role

### `POST /auth/refresh`
- Request: refresh token
- Response: new access token

## 3) Master Data

### Employees

### `GET /employees`
- Query: `site_code`, `status`, `q`, `page`, `page_size`

### `POST /employees`
- Create employee

### `PATCH /employees/{employee_id}`
- Update employee

### Vehicles

### `GET /vehicles`
- Query: `site_code`, `status`, `q`

### `POST /vehicles`
- Create vehicle

### `PATCH /vehicles/{vehicle_id}`
- Update vehicle

## 4) Dispatch / Job Orders

### `GET /jobs`
- Query:
  - `site_code`
  - `status`
  - `date_from`
  - `date_to`
  - `customer`
  - `driver_id`
  - `vehicle_id`

### `POST /jobs`
- Create draft job
- Request:
```json
{
  "site_code": "LCB",
  "job_date": "2026-04-08",
  "job_type": "domestic",
  "origin": "LCB Port",
  "destination": "Wangnoi",
  "container_no": "MSKU8171520",
  "planned_revenue": 4500.0
}
```

### `PATCH /jobs/{job_id}`
- Update job detail

### `POST /jobs/{job_id}/assign`
- Assign driver/vehicle
- Request:
```json
{
  "driver_id": "emp_001",
  "vehicle_id": "veh_001"
}
```

### `POST /jobs/{job_id}/status`
- Change status with reason
- Request:
```json
{
  "to_status": "dispatched",
  "reason": "line message sent"
}
```

### `POST /jobs/{job_id}/line-message-preview`
- Generate line message template text

## 5) Daily Operations

### `GET /daily-jobs`
- Query:
  - `site_code`
  - `work_date`
  - `driver_id`
  - `status`

### `POST /daily-jobs`
- Create daily job record

### `PATCH /daily-jobs/{daily_job_id}`
- Update daily row before lock

### `POST /daily-jobs/import`
- Upload/import excel
- Mode:
  - `dry_run=true` -> return validation only
  - `dry_run=false` -> commit records

## 6) Fuel + Petty Cash

### Fuel

### `POST /fuel/import`
- import fuel file with site profile

### `GET /fuel-txns`
- query by period/site/driver

### Petty cash

### `POST /advance-txns`
- create petty cash transaction

### `GET /advance-txns`
- query by period/site/driver/category/pending_flag

### `PATCH /advance-txns/{advance_txn_id}`
- update petty cash (before lock)

## 7) Billing

### `POST /billing/generate`
- Generate draft billing from period/site
- Request:
```json
{
  "site_code": "BigC",
  "period_start": "2026-03-16",
  "period_end": "2026-04-15"
}
```

### `GET /billing-docs`
- Query: `site_code`, `status`, `customer_code`, `period`

### `POST /billing-docs/{billing_id}/issue`
- Issue invoice

### `POST /billing-docs/{billing_id}/status`
- Update payment status: `sent`, `partial`, `paid`, `overdue`

## 8) Payroll

### `POST /payroll/run`
- Start payroll calculate
- Request:
```json
{
  "site_code": "AYU",
  "period_start": "2026-03-16",
  "period_end": "2026-04-15"
}
```

### `GET /payroll/runs`
- list payroll runs

### `GET /payroll/runs/{payroll_run_id}/lines`
- payroll lines detail

### `POST /payroll/runs/{payroll_run_id}/approve`
- Approve payroll run (trigger lock)

## 9) Maintenance + Stock

### `POST /maintenance/jobs`
- open PM/RM job

### `PATCH /maintenance/jobs/{maintenance_job_id}`
- update maintenance job

### `POST /maintenance/jobs/{maintenance_job_id}/close`
- close job + write costs

### `GET /stock/items`
- list stock status

### `POST /stock/moves`
- stock in/out/adjust

## 10) Lock + Adjustment

### `POST /periods/{site_code}/{period_id}/lock`
- lock data for period

### `POST /adjustments`
- submit adjustment request after lock

### `POST /adjustments/{adjustment_id}/approve`
- approve and create adjustment entries

## 11) Reports

### `GET /reports/daily-normalized`
### `GET /reports/billing-summary`
### `GET /reports/payroll-summary`
### `GET /reports/cashflow-summary`
### `GET /reports/maintenance-cost`

All reports support:
- `site_code`
- `period_start`
- `period_end`
- `format=json|xlsx|csv`

