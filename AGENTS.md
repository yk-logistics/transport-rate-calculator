# Project YK — Agent Brief (read me first)

> เปิดทุกแชทใหม่: ไฟล์นี้ + `.cursor/rules/project-yk-context.mdc` ต้องอ่านก่อน

## Who

- **Owner of this project**: โอ (พงษกาญจน์) — ผู้จัดการ ลูกชายเจ้าของ
- **Business**: ขนส่งตู้คอนเทนเนอร์ + ขนส่งสินค้า (YK) 3 ไซท์
  - AYU (อยุธยา) — มี 2 ระบบ: รายเที่ยว + เหมาน้ำมัน
  - BIGC (บางปะอิน/หลาย Hub) — เงินเดือน + ค่าเที่ยว + เรทน้ำมัน rebate
  - LCB (แหลมฉบัง) — รายเที่ยว + เหมาน้ำมัน
- **Team**: ~7 คนออฟฟิส + ~50 คนขับ + ช่าง/ยาม

## What we're building

"One Platform" ครอบคลุม: **Dispatch → Daily → Petty Cash → Billing → Payroll → Maintenance → Accounting → Owner Dashboard**

ปัจจุบัน (เม.ย. 2026) อยู่ใน `ProjectYK_System/` — FastAPI + SQLite + HTMX.

## Current state

- Daily/Billing/Petty Cash/Payroll MVP: ✅ ทำเสร็จ + smoke test ผ่าน
- Maintenance (PM/RM/Tire/Stock/VendorPrice/Inspection) v10: ✅
- Fuel-Adjusted Pricing v11: ✅
- **Phase 2 DONE** (2026-04-08): v12 `DailyJob.source`, import จริง DailyJob 1,552 + PettyCashTxn 50,753 (ย้อน 2019), `/billing` + CSV export, backfill FK script, pin `starlette<0.40`
- **Phase 3 DONE** (2026-04-08): v13 `Loan` + `LoanPayment`, `services/finance.py`, หน้า `/finance` (Dashboard + P&L + Vehicles + Cashflow + Loan CRUD + amortization) — ผู้ใช้ทยอยกรอกข้อมูลหนี้เองผ่าน UI
- **Phase 4 Wave 1 DONE** (2026-04-08): v14 Driver PWA — `DriverSession` + `DriverSubmission` + `Employee.pin_hash`, `services/driver_auth.py` (scrypt PIN, cookie session, rate-limit, phone normalize), mobile-first pages `/driver/login|home|today|check|alcohol|history`, ถ่ายรูป + GPS + client-side compression, admin `/admin/drivers/pins` + `/admin/submissions` (filter + review workflow)
- **Next**: 
  - Admin ตั้ง PIN ให้คนขับ 1-2 คนทดลอง → ให้คนขับลองเข้า `/driver/login` บนมือถือ
  - Phase 4 Wave 2: Job photo capture per DailyJob (ผูก `daily_job_id`), fuel receipt OCR, container OCR, signature capture, earnings self-service (ดูเงินตัวเองจาก payroll)
- Phase 5 (Line OA) planned
- Phase 6 (Open-Book + Profit Share) planned

## How the user works

- **Non-coder**, vibe-codes: ให้ AI เขียน, รันเอง, ทดสอบเอง, แจ้งบั๊ก
- **ตอบเป็นภาษาไทย** เสมอ
- ชอบให้ **ทำจริง ไม่ pitch นาน** — cut to code
- ยอม **อดนอน** เพื่อให้ feature จบในคืนเดียว
- **สำคัญ**: ถ้าคำสั่งยังมีจุดกำกวม — AI **ถามให้เคลียร์ก่อนลงมือ** ทุกแชท (ดู `.cursor/rules/oa-careful-default.mdc`)

## Key files to read at session start

1. `.cursor/rules/project-yk-context.mdc` (bootstrap rule)
2. `ProjectYK_System/AGENT_BOOTSTRAP.md`
3. `ProjectYK_System/MODULE_REGISTRY.md`
4. `ProjectYK_System/CHANGELOG_MASTER.md` — **เฉพาะ 3 หัวข้อล่าสุด** (ไม่อ่านทั้งไฟล์)
5. `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md`
6. **`ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`** — แบ่งงาน Cursor vs Claude Code, rtk/Graphify/claude-mem, บล็อกส่งต่อ (ประหยัดโทเค็น)
7. ถามเรื่อง Context/Conversation ใน Cursor → **`ProjectYK_System/docs/CONTEXT_TOKENS.md`**

## Commit / update rules

- Update `CHANGELOG_MASTER.md` ทุกครั้งที่มี design decision หรือจบ feature
- Update `NEXT_ACTION_PLAN.md` mark `[done]` → ย้ายไป "Next"
- ถ้าผู้ใช้สอน domain fact ใหม่ → บันทึก `CONTEXT_LOG.md`

## Money rules of thumb (for CFO Dashboard later)

- Payroll base: BIGC 9,000 / LCB 9,240 + ดูแลรถ 3,000 / AYU การันตี 12,000 (6ล้อ) / 15,000 (10ล้อ)
- Fuel rebate BIGC: `(budget − actual) × 16฿`
- Driver deposit: 10,000 หัก 1,000/เดือน
- Social security: ~5% ของฐาน 9,000 (capped)
- Accident deduction: 2,000 (ผ่อน 500×4 ได้)
