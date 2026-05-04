# Agent Bootstrap (Project YK)

ไฟล์นี้คือจุดเริ่มต้นเดียวสำหรับ AI Agent ใน Project YK

## Mandatory Read Order
1. `ProjectYK_System/AGENT_BOOTSTRAP.md` (ไฟล์นี้)
2. `ProjectYK_System/MODULE_REGISTRY.md`
3. `ProjectYK_System/CHANGELOG_MASTER.md`
4. อ่านไฟล์ของโมดูลที่ผู้ใช้กำลังทำงานอยู่ (ตาม registry)
5. ถ้างานเกี่ยวกับ **เครื่องมือ AI / ประหยัดโทเค็น / ส่งต่อ Claude Code** → อ่าน **`ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`**

## Agent Working Rules
- ต้องใช้ `MODULE_REGISTRY.md` เป็นแหล่งอ้างอิงว่าโมดูลไหนมีไฟล์ context อะไร
- เมื่อได้ข้อสรุปใหม่ ให้บันทึกทั้ง:
  - `DECISION_LOG.md` ของโมดูลนั้น
  - `ProjectYK_System/CHANGELOG_MASTER.md` (สรุประดับภาพรวม)
- หากมีโมดูลใหม่ ต้องเพิ่มรายการใน `MODULE_REGISTRY.md` ทันที

## Data import CLI (Phase 2)
- `python ProjectYK_System/tools/import_daily.py` — ต้องมี `openpyxl`; default นำเข้าตั้งแต่ **2018-01-01** (รันจากราก repo)
- `python ProjectYK_System/tools/import_petty_cash.py` — สดย่อย canonical xlsx; default เดียวกัน
- `ProjectYK_System/tools/phase2_import.bat` — รันทั้งสองต่อกัน (ส่ง `--wipe-prior` ได้)
- ไฟล์งานจริง (เงินเดือน / น้ำมัน / บิลลูกค้า) อยู่ที่ **`data/Salary`**, **`data/Fuel`**, **`data/Billing`** (ดู `data/README.md`)
- สเปกระบบ + เครื่องคิดเรท: **`ProjectYK_System/TransportRateCalculator/`** (`docs/`, `transport_rate_calculator.html`, `reports/`)
- หลัง import → เปิด `/admin/promote` ลิงก์คนขับ + ทะเบียน

## โฮสต์ทดลองบนคลาวด์ (ฟรี / พ่อ–คนใน)
- คู่มือ: **`ProjectYK_System/docs/HOSTING_FREE_DEMO_TH.md`** — Neon Postgres + Render + `sqlite_to_postgres.py` + HTTP Basic (`YK_PREVIEW_*`)
- รันบนเครื่องหลังได้ connection string จาก Neon: **`ProjectYK_System/tools/cloud_demo_setup.ps1`**

## User-Friendly Command (for future chats)
ผู้ใช้สามารถพิมพ์สั้นๆ ว่า:
- "ทำต่อจาก System Hub"

แล้ว Agent ต้องอ่านไฟล์ตาม Mandatory Read Order ก่อนลงมือ
