---
name: project-overview-yk
description: ภาพรวม Project YK — One Platform app, เฟสที่ทำแล้ว, โมดูลหลัก, โครงสร้าง repo
metadata:
  type: project
---

## บริษัท

**วาย.เค. โลจิสติกส์ โซลูชั่นส์ แอนด์ เซอร์วิส จำกัด** — ขนส่งสินค้า 3 ไซต์: AYU (อยุธยา), BIGC (วังน้อย), LCB (แหลมฉบัง)

## One Platform App

- Stack: **FastAPI + SQLModel + SQLite** (PostgreSQL รองรับผ่าน DATABASE_URL — ใช้เฉพาะ cloud demo legacy)
- UI: **Jinja2 + HTMX + Tailwind CDN** (ไม่มี Node build)
- Driver: **PWA** (ไม่ใช่ native app)
- **Production จริง: `app.yklogistics.uk`** (server เครื่อง YK, SQLite, deploy ตามสกิล `yk-deploy`)
- รันเครื่อง dev: `ProjectYK_System/app/start.bat` — **dev DB ว่าง ห้ามใช้ตัดสินข้อมูลจริง** (ดู `docs/DATA_TOPOLOGY.md`)

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

## งานที่ pending — อย่าอ่านจากไฟล์นี้ (ภาพเก่า พ.ค. เลิกใช้แล้ว)

สถานะงานจริงดูจากแหล่งสด 3 ที่เท่านั้น:
1. `ProjectYK_System/docs/PLAN_STATUS.json` (หน้า /admin/plan)
2. `ProjectYK_System/docs/HANDOFF_FABLE_TO_OPUS_*.md` ตัววันที่ใหม่สุด (งานค้างรอ trigger)
3. `.claude/memory/MEMORY.md` + CHANGELOG 3 หัวข้อล่าสุด

**Why:** รายการ pending ที่ฝังในไฟล์ static จะเก่าเสมอ — เคยมีรายการ พ.ค. ค้างอยู่ที่นี่ทั้งที่จบไปเดือนกว่าแล้ว
**How to apply:** ห้าม copy รายการงานมาไว้ที่นี่อีก ชี้ไปแหล่งสดแทน
