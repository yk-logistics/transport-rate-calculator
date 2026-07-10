# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Project YK — คู่มือสำหรับ Claude Code

ไฟล์นี้อยู่ที่ราก repo เพื่อให้ **Claude Code** จับบริบทและทำงาน **ทีละก้อน** โดยไม่ต้องเท context ยาวทุกเซสชัน

## Commands (สั่งรันจากราก repo)

```powershell
# เริ่มแอป (Windows — จาก ProjectYK_System/app/)
.\ProjectYK_System\app\start.bat          # auto-create venv, pip install, เปิด browser

# หรือรันตรง (venv ต้อง activate แล้ว)
cd ProjectYK_System\app
.venv\Scripts\python.exe main.py          # default port 8010, bind 0.0.0.0

# install deps เฉพาะ (ถ้า venv มีอยู่แล้ว)
.venv\Scripts\pip install -r requirements.txt

# import scripts (รันจากราก repo, ต้องการ openpyxl)
python ProjectYK_System\tools\import_daily.py
python ProjectYK_System\tools\import_petty_cash.py
ProjectYK_System\tools\phase2_import.bat  # รันทั้งสองพร้อมกัน

# migrate to PostgreSQL (cloud demo)
python ProjectYK_System\tools\sqlite_to_postgres.py

# รัน test suite (จากราก repo หรือใน app/) — 545 tests, throwaway SQLite ผ่าน conftest
cd ProjectYK_System\app
.venv\Scripts\python.exe -m pytest -q          # ทั้งชุด
.venv\Scripts\python.exe -m pytest tests\test_security_hardening.py -q   # ไฟล์เดียว
```

**มี pytest suite ใน `ProjectYK_System/app/tests/`** (545 tests, ไม่มี linter) — `conftest.py`
บังคับ throwaway SQLite + reset schema ต่อ test เอง รันได้เลยไม่แตะ DB จริง งานเงิน/import
ยังต้องผ่าน preflight scripts ใน `tools/` เพิ่มด้วย

## Architecture ที่ต้องรู้ก่อนแก้โค้ด

### โครงสร้างหลัก `ProjectYK_System/app/`

```
main.py          — FastAPI app + route handlers ทั้งหมด (monolith, SCHEMA_VERSION=18)
models.py        — SQLModel table definitions (Employee, DailyJob, FuelTxn, PayRun, …)
db_config.py     — สลับ SQLite↔PostgreSQL ด้วย env var DATABASE_URL (ถ้าไม่ set = SQLite)
preview_auth.py  — HTTP Basic auth middleware สำหรับ cloud demo
services/
  payroll.py     — engine คำนวณ pay run (cycle dates, pay modes, deductions)
  finance.py     — P&L / cashflow queries
  email_ingest.py / email_oauth.py — inbox sync (Gmail OAuth)
  promote.py     — link driver ↔ vehicle ↔ plate
  import_wizard.py — import from Excel
  alias_map.py   — normalize ชื่อคนขับ/ทะเบียน
templates/       — Jinja2 HTML (HTMX + Tailwind CDN, ไม่มี Node build)
```

### Schema migration

ไม่ใช้ Alembic — เพิ่ม `SCHEMA_VERSION` ใน `main.py:SCHEMA_VERSION` แล้วใส่ `ALTER TABLE` block ใน `lifespan()` ที่ตรวจ version ก่อนรัน เมื่อแก้ schema ต้องอัปเดต `SCHEMA_VERSION` พร้อมกันทุกครั้ง

### Pay cycles (critical — อย่าเดา)

| Site | วงรอบ | cycle_tag |
|------|-------|-----------|
| BIGC | 1 → สิ้นเดือน | YYYY-MM |
| LCB  | 16 → 15 ถัดไป | เดือนที่ cycle จบ |
| AYU  | 26 → 25 ถัดไป | เดือนที่ cycle จบ |

### Jinja2 filters (ใช้ใน template เสมอ — อย่าฟอร์แมตวันตรง)

- `{{ value | dmy }}` → dd/mm/yyyy (CE)
- `{{ value | dmy_hm }}` → dd/mm/yyyy HH:MM

### Version pins (ห้ามอัปเกรดโดยไม่ทดสอบ)

```
fastapi>=0.139,<1    # migrate แล้ว 4 ก.ค. 2026 — TemplateResponse ใช้ signature ใหม่
starlette>=1.3,<2    # (request, name, ctx) ทั้ง 130 จุด; ดู docs/STARLETTE_MIGRATION_NOTES.md
```

pin เก่า (fastapi<0.115/starlette<0.40 เรื่อง Jinja2 globals) **ปลดแล้ว** — ถ้าเขียน route ใหม่ให้เรียก `templates.TemplateResponse(request, "x.html", ctx)` เสมอ (แบบเก่า `("x.html", ctx)` จะพังบน starlette 1.x)

## Memory ถาวร (อ่านเมื่อเริ่ม session ใหม่)

ไฟล์เหล่านี้อยู่ใน repo → **รอด format เครื่อง** — อ่านตามที่งานต้องการ:

| ไฟล์ | อ่านเมื่อ |
|------|----------|
| [`CLAUDE_MEMORY/user_profile.md`](CLAUDE_MEMORY/user_profile.md) | ทุกครั้ง (โออเป็นใคร, วิธีสื่อสาร) |
| [`CLAUDE_MEMORY/feedback_working_style.md`](CLAUDE_MEMORY/feedback_working_style.md) | ทุกครั้ง (กฎทำงานร่วมกัน) |
| [`CLAUDE_MEMORY/project_overview.md`](CLAUDE_MEMORY/project_overview.md) | งานแรกของ session / งานใหม่ |
| [`CLAUDE_MEMORY/business_domain.md`](CLAUDE_MEMORY/business_domain.md) | งานที่แตะ payroll / billing / ราคา |
| [`SKILLS.md`](SKILLS.md) | ทุกครั้ง (Karpathy coding principles — think, simplify, surgical, goal-driven) |

## โหมด Opus — จูนพฤติกรรมหลัง Fable ออกจาก Plan (13 ก.ค. 2026)

ถ้าเซสชันนี้รันด้วย **Opus** (ตัวใหญ่สุดที่เหลือ) ให้ทำตามนี้ทุกเซสชัน — เขียนโดย Fable เพื่ออุดจุดที่ Opus 4.8 มักพลาดบนโปรเจกต์นี้:

1. **เซสชันแรก/งานใหม่: อ่าน `ProjectYK_System/docs/FABLE_MINDSET_FOR_OPUS.md` ก่อน 1 รอบ** (8 นิสัย + จังหวะมาตรฐานต่องาน) แล้วทำตามแบบไม่มีข้อยกเว้น — หัวใจคือ "verify บนของจริงก่อนพูดว่าเสร็จ" กับ "เช็คของสดก่อนเชื่อความจำ/เอกสาร"
2. **เรื่องเล็ก ตัดสินใจเองแล้วจดข้อสมมติไว้** (ชื่อตัวแปร, ค่า default, ทางเลือกที่เทียบเท่ากัน) — อย่าถามโอ อย่าปิดท้ายด้วย "ต้องการให้…ไหมครับ?" สำหรับก้าวถัดไปที่ชัดอยู่แล้ว; หยุดถามเฉพาะ **เงินออกกระเป๋า / ลบ-ทับข้อมูล / ความกำกวมโดเมนที่เดาแล้วเงินเข้าผิดคน**
3. **เงียบระหว่างทำ สรุปตอนจบ**: ระหว่าง tool calls เขียนแค่ตอนเจอของสำคัญหรือเปลี่ยนทิศ (1 ประโยค) — จบงานค่อยสรุปสั้น ภาษาคน ผลลัพธ์ขึ้นก่อน ไม่โชว์โค้ด/คำสั่ง/path เว้นแต่โอขอ
4. **อย่ารอใครสั่งให้หยิบเครื่องมือ** (Opus มักไม่หยิบเอง): เจอ gotcha/ตัดสินใจอะไร → เขียน `.claude/memory/` **ในเทิร์นนั้น**; งานอ่าน/สำรวจเยอะ → dispatch Qwen/Haiku ตาม delegation ladder; ก่อนอ้างว่าเสร็จ → รันคำสั่ง verify จริง (curl/pytest/marker) เสมอ
5. **สกิลประจำบ้านใน `.claude/skills/` ต้องเรียกก่อนลงมือเมื่อเข้าเงื่อนไข**: `yk-money-task` (งานเงินทุกชนิด — รวมปิดรอบ LCB 15 ก.ค.), `yk-deploy` (ขึ้น server), `yk-session-close` (ปิดเซสชัน)

## ใครเป็นเจ้าของงาน

- **โอ (พงษกาญจน์)** — ผู้จัดการ, non-coder: ตัดสินใจโดเมน, ทดสอบหน้างาน, แจ้งบั๊ก
- **ภาษา:** คุยธุรกิจกับโอเป็นภาษาไทยได้; **ข้อมูลดิบ** ส่งเป็น JSON/CSV โดยใช้ **key ภาษาอังกฤษ** จะประหยัดโทเค็นและลดความกำกวม

## สแต็ก (ห้ามเปลี่ยนโดยไม่ได้รับอนุญาต)

- Backend: **FastAPI + SQLModel**
- DB dev: **SQLite** `ProjectYK_System/app/app.db` → production **PostgreSQL**
- UI: **Jinja2 + HTMX + Tailwind (CDN)** — ไม่มี Node build
- Driver: **PWA** (ไม่ native app)

## อ่านก่อนลงมือ (ลำดับบังคับ)

1. `ProjectYK_System/AGENT_BOOTSTRAP.md`
2. `ProjectYK_System/MODULE_REGISTRY.md`
3. `ProjectYK_System/CHANGELOG_MASTER.md` (เฉพาะ **3 หัวข้อ `##` ล่าสุด** — ดู `ProjectYK_System/docs/CHANGELOG_POLICY.md`)
4. `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md`
5. งาน Claude ↔ Cursor / ประหยัดโทเค็น: `ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`

โมดูลหลักแอป: `ProjectYK_System/app/` · import CLI: `ProjectYK_System/tools/`

## กฎเงิน / ข้อมูล (เข้ม)

- **ห้ามเดา** เมื่อกำกวมเรื่อง ไซท์, รอบเดือน (วิ่ง vs จ่าย), ชื่อคนขับคล้ายกัน, cross-site
- เตือนเรื่อง **unlinked records**, **cycle tag**, **source mismatch** (daily / fuel / petty / payroll)
- ถ้าเปลี่ยน logic ที่กระทบเงิน ต้องระบุวิธี **ตรวจย้อนกลับ** / preflight

## Superpowers — subagent-driven-development (การ์ดถามก่อนใช้)

ลง **superpowers v5.1.0** แล้ว (scope = Project YK เท่านั้น) — skills auto-trigger ได้ แต่ `subagent-driven-development` กิน token สูง (1 implementer + 2 reviewer ต่อ 1 task + วน review) จึงมีกฎ:

1. **ถามก่อน "เริ่ม" ทุกครั้ง** — สกิลออกแบบให้วิ่งรวดเดียว ไม่หยุดถามระหว่าง task ฉะนั้น gate อยู่ **ก่อนสตาร์ทจุดเดียว**: สรุปให้โอก่อนว่ากี่ task, ใช้โมเดลอะไร, ประมาณค่าใช้จ่าย แล้วรอ "go"
2. **subagent ใช้โมเดลถูกก่อน** — งาน mechanical (1–2 ไฟล์ สเปคชัด) → Haiku/Sonnet; integration → Sonnet; เก็บ Opus เฉพาะ design + final review (ตรงกับหัวข้อ *Model Selection* ของสกิลเอง)
3. **ห้ามรันบน `main`** — สกิล commit ทีละ task ต้องอยู่บน worktree/branch แยกก่อน (สกิลบังคับ `using-git-worktrees`) ปัจจุบัน repo มักอยู่ `main` + มีไฟล์ค้าง → จัดการ branch ให้เรียบร้อยก่อน
4. **งานเงิน (payroll/billing) ยังต้องผ่าน preflight ตามปกติ** — subagent ไม่ข้ามกฎ "กฎเงิน" ด้านบน

## Model routing — "ผู้ใหญ่คิด เด็กเขียน" (ออโต้ ตัวหลักเลือกเอง)

โอสั่ง 2 ก.ค. 2026: ตัวหลัก (Fable/Opus) **ประเมินก่อนเขียนโค้ดทุกครั้ง** แล้วเลือกเส้นทางเองโดยไม่ต้องถาม — แจ้งโอสั้นๆ บรรทัดเดียวว่าเลือกทางไหนเพราะอะไร

| เงื่อนไขงาน | เส้นทาง |
|---|---|
| แก้เล็ก: ≤2 ไฟล์, รู้จุดแก้ชัด, ราวไม่กี่สิบบรรทัด | ตัวหลักทำเองเลย (dispatch ไม่คุ้ม overhead — เด็กต้องอ่านบริบทใหม่หมด) |
| โค้ดก้อนใหญ่: หลายไฟล์ / โค้ดยาว / mechanical ตามสเปคได้ | เขียนสเปคละเอียด (ไฟล์ไหน แก้ตรงไหน เกณฑ์ผ่าน gotcha) → dispatch subagent **Sonnet** ทำ + ให้มัน self-verify → ตัวหลักตรวจแค่ diff + ผลเทสต์ |
| อ่าน/สำรวจ/สรุปเยอะ | Explore/Haiku subagent (หรือ Qwen ตาม delegation ladder) |
| **งานเงิน payroll/billing/แก้ DB** | **ตัวหลักทำเองเสมอ ห้าม delegate** (กฎเงินด้านบนใช้เต็ม) |
| subagent แก้ตามรีวิวแล้ว 1 รอบยังไม่ผ่าน | ตัวหลักยึดงานมาทำเองต่อ — อย่าวนสั่งแก้รอบ 3 (แพงกว่าทำเองแล้ว) |

- ถ้าตัวหลักของเซสชันเป็น **Sonnet อยู่แล้ว**: ทำเองทั้งหมด ไม่ต้อง delegate — ยกเว้นเจองานเงิน/ออกแบบ ให้หยุดแล้วเตือนโอสลับ `/model` เป็น Opus ก่อน
- ตัวหลักสลับโมเดลตัวเองไม่ได้ — ถ้างานทั้งเซสชันไม่จำเป็นต้องใช้โมเดลแพง ให้บอกโอตอนจบว่า "งานแบบนี้ครั้งหน้าเปิดด้วย Sonnet พอ"
- กฎนี้คือ default รายวัน; `subagent-driven-development` (หัวข้อถัดไป) ใช้เฉพาะงานใหญ่แตกหลาย task และยังต้องถามก่อนเริ่มตามเดิม

## ทำงานกับ Cursor vs Claude Code

- **Cursor Agent** กับ **`claude` ในเทอร์มินัล** เป็นคนละผลิตภัณฑ์ — Cursor **เปิดเซสชัน Claude Code แทนโอโดยตรงไม่ได้**
- เวลาส่งต่องานจาก Cursor ใช้บล็อก **[HANDOFF Project YK → Claude Code]** ใน `AI_CURSOR_CLAUDE_WORKFLOW.md`

## ประหยัดโทเค็น (ปฏิบัติ)

1. **หนึ่งเซสชัน = หนึ่ง scope** — ระบุไฟล์/งานชัด; หลีกเลี่ยง “ทำทั้งระบบจบในเธรดเดียว”
2. **ข้อมูลเป็นโครงสร้าง** — JSON/CSV; ไทยอยู่ที่ value; ใช้ `emp_id`, `cycle_tag`, `site_code` แทนการพิมพ์ชื่อซ้ำ
3. **เชลล์ / `rtk`** — ใช้ `rtk git status`, `rtk git diff`, `rtk pytest` เมื่อเหมาะสม แทนการดึงไฟล์ยาวด้วยเครื่องมืออ่านดิบ
4. **Graphify** — หลังโครงสร้างใหญ่เปลี่ยน: จากราก repo `cd` แล้ว `/graphify .` (ดูรายละเอียดใน workflow doc)
5. **ความจำระยะยาวใน CC** — ใช้ปลั๊กอิน **claude-mem** ตาม `AI_CURSOR_CLAUDE_WORKFLOW.md`

### Lean read policy (สำหรับงานเล็ก/ขอบเขตชัด)

- ถ้าเป็นงาน scope เล็ก ให้เริ่มอ่านแค่:
  1) `ProjectYK_System/AGENT_BOOTSTRAP.md`
  2) `ProjectYK_System/MODULE_REGISTRY.md`
- จากนั้นเข้าโค้ดเป้าหมายทันที (`ProjectYK_System/app/` และ template ที่เกี่ยว)
- `CHANGELOG_MASTER.md` / `CONTEXT_LOG.md` / `NEXT_ACTION_PLAN.md` ให้อ่านเฉพาะตอนจำเป็น และอ่านเฉพาะช่วงท้ายล่าสุด
- ถ้างานกระทบเงิน/import/payroll ให้กลับไปใช้โหมดรอบคอบเต็มรูปแบบ (ไม่ใช้ lean)
- ใช้ snippet พร้อมวางได้ทันทีจาก:
  - `ProjectYK_System/tools/CC_LEAN_START.txt`
  - `ProjectYK_System/tools/CC_ULTRA_LEAN_5LINES.txt`
  - `ProjectYK_System/tools/CC_BENCHMARK_LOG.md`
- Team default: งานเล็กเริ่มจาก `CC_ULTRA_LEAN_5LINES.txt` ก่อน แล้วค่อย fallback ไป `CC_LEAN_START.txt` ถ้าเริ่มช้าหรือถามกลับเยอะ

## แผนแบบ “Gantt ในเน็ต” — ต้องทำเหมือนรูปไหม?

**ไม่จำเป็นต้องมี Gantt 33 สัปดาห์แบบ Accounting SaaS ทั้งก้อน**

- แผนในรูปเป็นตัวอย่างการ **แตกเฟส + ลำดับความสำคัญ** — ใช้ไอเดีย “ทำทีละกล่อง” กับ CC ได้
- Project YK **ไม่ใช่** SaaS บัญชีทั่วไป: โฟกัสคือ **dispatch/daily → billing → petty → payroll → finance/CFO → maintenance → (อนาคต) Line OA / Open-Book**
- ให้ใช้ **`NEXT_ACTION_PLAN.md` + milestone เล็ก** แทนการล็อกวันยาว — พอสำหรับให้ CC รู้ว่า “ตอนนี้อยู่เฟสไหน” และไม่โหลด context ซ้ำ

### เฟสอ้างอิง (โครงสูง — ปรับตามของจริงใน NEXT_ACTION_PLAN)

| เฟส | ความหมาย (YK) | หมายเหตุ |
|-----|----------------|----------|
| Foundations | สแต็ก, master data, import path, auth พื้นฐาน | ส่วนใหญ่ทำแล้ว |
| Operations / Money flow | DailyJob, billing, petty cash, payroll engine | งานหลัก + ต้องรักษาความถูกต้องรอบเงิน |
| Finance / CFO | `/finance`, หนี้, P&L, cashflow | มีแล้ว — เติมข้อมูลจริงตามทีม |
| Field / Compliance | Driver PWA, หลักฐาน, audit | Wave 1 มีแล้ว — Wave 2+ ตามแผน |
| Integrations | LINE Messaging API, OCR ฯลฯ | เฟสหลัง — ไม่บังคับก่อน ops นิ่ง |
| Open-Book / Profit share | โชว์ตัวเลขภายในองค์กร | เป้าหมายยาว — ออกแบบหลังตัวเลขหลักเชื่อถือได้ |

## เช็คก่อนปิดงาน

- แอปยังรันได้: `ProjectYK_System/app/start.bat`
- ถ้าแตะ DB/import/payroll: มี preflight / จำนวนแถวที่กระทบ
