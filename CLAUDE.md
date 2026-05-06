# Project YK — คู่มือสำหรับ Claude Code

ไฟล์นี้อยู่ที่ราก repo เพื่อให้ **Claude Code** จับบริบทและทำงาน **ทีละก้อน** โดยไม่ต้องเท context ยาวทุกเซสชัน

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
3. `ProjectYK_System/CHANGELOG_MASTER.md` (หัวข้อล่าสุด)
4. `ProjectYK_System/TransportRateCalculator/docs/NEXT_ACTION_PLAN.md`
5. งาน Claude ↔ Cursor / ประหยัดโทเค็น: `ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`

โมดูลหลักแอป: `ProjectYK_System/app/` · import CLI: `ProjectYK_System/tools/`

## กฎเงิน / ข้อมูล (เข้ม)

- **ห้ามเดา** เมื่อกำกวมเรื่อง ไซท์, รอบเดือน (วิ่ง vs จ่าย), ชื่อคนขับคล้ายกัน, cross-site
- เตือนเรื่อง **unlinked records**, **cycle tag**, **source mismatch** (daily / fuel / petty / payroll)
- ถ้าเปลี่ยน logic ที่กระทบเงิน ต้องระบุวิธี **ตรวจย้อนกลับ** / preflight

## ทำงานกับ Cursor vs Claude Code

- **Cursor Agent** กับ **`claude` ในเทอร์มินัล** เป็นคนละผลิตภัณฑ์ — Cursor **เปิดเซสชัน Claude Code แทนโอโดยตรงไม่ได้**
- เวลาส่งต่องานจาก Cursor ใช้บล็อก **[HANDOFF Project YK → Claude Code]** ใน `AI_CURSOR_CLAUDE_WORKFLOW.md`

## ประหยัดโทเค็น (ปฏิบัติ)

1. **หนึ่งเซสชัน = หนึ่ง scope** — ระบุไฟล์/งานชัด; หลีกเลี่ยง “ทำทั้งระบบจบในเธรดเดียว”
2. **ข้อมูลเป็นโครงสร้าง** — JSON/CSV; ไทยอยู่ที่ value; ใช้ `emp_id`, `cycle_tag`, `site_code` แทนการพิมพ์ชื่อซ้ำ
3. **เชลล์ / `rtk`** — ใช้ `rtk git status`, `rtk git diff`, `rtk pytest` เมื่อเหมาะสม แทนการดึงไฟล์ยาวด้วยเครื่องมืออ่านดิบ
4. **Graphify** — หลังโครงสร้างใหญ่เปลี่ยน: จากราก repo `cd` แล้ว `/graphify .` (ดูรายละเอียดใน workflow doc)
5. **ความจำระยะยาวใน CC** — ใช้ปลั๊กอิน **claude-mem** ตาม `AI_CURSOR_CLAUDE_WORKFLOW.md`

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
