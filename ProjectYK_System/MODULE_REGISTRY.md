# Project YK Module Registry

สารบัญกลางของระบบทั้งหมดใน Project YK เพื่อให้ Agent และทีมงานหา context ได้เร็ว

| Module | Purpose | Main Path | Agent Memory | Decision Log | Other Key Docs |
|---|---|---|---|---|---|
| AccidentCases | รายงานสอบสวนอุบัติเหตุแบบ HTML-first | `AccidentCases/` | `AccidentCases/AGENT_MEMORY.md` | `AccidentCases/DECISION_LOG.md` | `AccidentCases/README.txt`, `AccidentCases/_TEMPLATE_CASE/index.html` |
| TransportRateCalculator | ระบบออกบิล/ต้นทุน/เงินเดือน/เอกสารสเปกระบบ + เครื่องคิดเรท HTML | `ProjectYK_System/TransportRateCalculator/` | `ProjectYK_System/TransportRateCalculator/docs/CONTEXT_LOG.md` | `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md` | `ProjectYK_System/TransportRateCalculator/docs/README.md`, `ProjectYK_System/TransportRateCalculator/docs/MASTER_SPEC.md`, **`ProjectYK_System/TransportRateCalculator/docs/OATSIDE_CUSTOMER_REPORT_SPEC.md`** (รายงาน Oatside ลูกค้า) |
| OnePlatformApp | เว็บแอป one-platform (Daily → Dispatch → Billing → Petty Cash → Payroll → Maintenance) ปัจจุบัน Phase 1.1 (Master Data + Daily ขยาย) | `ProjectYK_System/app/` | `ProjectYK_System/app/README.md` | `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md` | `ProjectYK_System/app/main.py`, `ProjectYK_System/app/models.py`, `ProjectYK_System/app/start.bat`, **`ProjectYK_System/tools/`** (import CLI), **`ProjectYK_System/dev_scripts/`** (สคริปต์ทดสอบชั่วคราว) |

## Registration Rule
- ทุกโมดูลใหม่ต้องถูกเพิ่มในตารางนี้
- ต้องระบุอย่างน้อย `Main Path`, `Agent Memory`, `Decision Log`
