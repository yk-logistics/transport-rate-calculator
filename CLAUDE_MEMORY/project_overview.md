---
name: project-overview-yk
description: ภาพรวม Project YK — One Platform app, เฟสที่ทำแล้ว, โมดูลหลัก, โครงสร้าง repo
metadata:
  type: project
---

## บริษัท

**วาย.เค. โลจิสติกส์ โซลูชั่นส์ แอนด์ เซอร์วิส จำกัด** — ขนส่งสินค้า 3 ไซต์: AYU (อยุธยา), BIGC (วังน้อย), LCB (แหลมฉบัง)

## One Platform App

- Stack: **FastAPI + SQLModel + SQLite** (dev) / PostgreSQL (prod)
- UI: **Jinja2 + HTMX + Tailwind CDN** (ไม่มี Node build)
- Driver: **PWA** (ไม่ใช่ native app)
- รันเครื่อง: `ProjectYK_System/app/start.bat`
- DB path: `ProjectYK_System/app/app.db`

## เฟสที่ทำเสร็จแล้ว (ณ 2026-05-28)

| เฟส | สถานะ | หมายเหตุ |
|-----|--------|----------|
| Phase 0: Blueprint | ✅ Done | DATA_DICTIONARY, JOB_STATUS_FLOW, SQL schema |
| Phase 1: Skeleton | ✅ Done | FastAPI app, DailyJob CRUD, Master Data UI |
| Phase 2: Ops/Money | ✅ Done | Petty Cash, Daily import, Fuel, Payroll MVP, Billing export |
| Phase 3: CFO | ✅ Done | /finance, Loan CRUD, P&L, Cash Flow, Break-even |
| Phase 4 Wave 1: Driver PWA | ✅ Done | Login, Vehicle Check, Alcohol Test, Admin review |

## โมดูลหลักใน app/

- DailyJob (งานรายวัน 3 ไซต์)
- PettyCash (สดย่อย — 50,753 rows 2019–2026)
- Payroll (3 ไซต์ + cycle policy)
- Fuel (import Caltex LCB)
- Maintenance (Wave 1: Record/Vendor/Part/Stock)
- RateCard (auto-learn จาก DailyJob)
- Finance/CFO (/finance/*)
- Driver PWA (/driver/*)

## โมดูลนอก app/

- **TransportRateCalculator** — เครื่องคิดเรทขนส่ง HTML-only (`transport_rate_calculator.html`) + deploy บน GitHub Pages
- **Oatside** — รายงาน GPS/billing ลูกค้า Oatside P&G (`build_oatside_reports.py`)
- **AccidentCases** — รายงานสอบสวนอุบัติเหตุ HTML

## GitHub Org

`yk-logistics` — `transport-rate-calculator` repo บน Pages
Path: `https://yk-logistics.github.io/transport-rate-calculator/`

## งานที่ pending หลักๆ (2026-05-28)

- AYU run 7: เคลียร์ unresolved 33 คน (23,716 บาท)
- BigC unresolved queue pass 2 (7 คน)
- Import Wizard: Employee/Vehicle master (dry-run/rollback)
- TR Calculator: โอทด 6 โรง LINE → Export PDF
- LCB fuel dispatch: bat + push Pages รอบใหม่

**Why:** track ว่าตอนนี้อยู่เฟสไหน และอะไรค้างอยู่
**How to apply:** ดูก่อนเริ่มงาน เพื่อไม่ทำซ้ำสิ่งที่ทำไปแล้ว
