# Project YK Module Registry

สารบัญกลางของระบบทั้งหมดใน Project YK เพื่อให้ Agent และทีมงานหา context ได้เร็ว

| Module | Purpose | Main Path | Agent Memory | Decision Log | Other Key Docs |
|---|---|---|---|---|---|
| AccidentCases | รายงานสอบสวนอุบัติเหตุแบบ HTML-first | `AccidentCases/` | `AccidentCases/AGENT_MEMORY.md` | `AccidentCases/DECISION_LOG.md` | `AccidentCases/README.txt`, `AccidentCases/_TEMPLATE_CASE/index.html` |
| TransportRateCalculator | ระบบออกบิล/ต้นทุน/เงินเดือน/เอกสารสเปกระบบ + เครื่องคิดเรท HTML | `ProjectYK_System/TransportRateCalculator/` | `ProjectYK_System/TransportRateCalculator/docs/CONTEXT_LOG.md` | `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md` | `ProjectYK_System/TransportRateCalculator/docs/README.md`, `ProjectYK_System/TransportRateCalculator/docs/MASTER_SPEC.md`, **`ProjectYK_System/TransportRateCalculator/docs/OATSIDE_CUSTOMER_REPORT_SPEC.md`** (รายงาน Oatside ลูกค้า) |
| OnePlatformApp | เว็บแอป one-platform (Daily/Grid → Billing: พร้อมวางบิล/ออกใบ/**ทะเบียนใบวางบิล+สถานะเก็บเงิน (v52)** → Petty: สดย่อย/รอเคลียร์/**ใบเสร็จ 3 สถานะ (v53)** → Payroll/สลิป → Finance/CFO → Maintenance: บันทึกซ่อม/**กล่องบิล OCR (v51)**/**ระบบยางรายเส้น (v48+v52)**/PM → LINE inbox/POD/digest → Driver PWA) — **production ที่ app.yklogistics.uk, SCHEMA_VERSION ดูหัว main.py**; แผนงานปัจจุบัน `docs/MASTER_PLAN_2026-07.md` + `docs/PLAN_STATUS.json` (หน้า /admin/plan) | `ProjectYK_System/app/` | `ProjectYK_System/app/README.md` | `ProjectYK_System/docs/PLAN_STATUS.json` | `ProjectYK_System/app/main.py`, `ProjectYK_System/app/models.py`, `ProjectYK_System/app/start.bat`, **`ProjectYK_System/tools/`** (import CLI), **`ProjectYK_System/docs/*_RUNBOOK.md`** (runbook ต่อฟีเจอร์) |
| LineArchiver | บอทเก็บข้อความ+รูปกลุ่ม LINE ลง SQLite + forward Discord — service แยก port 8020 บน server (DB `line_archive.db` **ห้ามเขียนจากแอปหลัก**; MVP อ่าน ro ผ่าน `app/services/line_archive.py`) | `ProjectYK_System/line_archiver/` | memory `reference-line-archiver` | `docs/superpowers/specs/2026-06-11-line-archiver-design.md` | `SERVER_GUIDE.md`, `SETUP_CHECKLIST.md`, `installer/`, `fix_orphan_channels.py` |
| ProjectYK_SharedDocs | เอกสารข้ามโมดูล: ประหยัด context, changelog policy, บริบทบริษัทยาว | `ProjectYK_System/docs/` | `DOMAIN_AND_DIRECTION.md` | `CHANGELOG_POLICY.md` | **`CONTEXT_TOKENS.md`**, **`CHANGELOG_ARCHIVE.md`**, **`HOSTING_FREE_DEMO_TH.md`** |

## Registration Rule
- ทุกโมดูลใหม่ต้องถูกเพิ่มในตารางนี้
- ต้องระบุอย่างน้อย `Main Path`, `Agent Memory`, `Decision Log`
