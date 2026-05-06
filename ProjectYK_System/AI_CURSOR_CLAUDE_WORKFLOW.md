# Cursor ↔ Claude Code — workflow ประหยัดโทเค็น (Project YK)

ไฟล์นี้เก็บกติกาที่ **โอ** ตกลงใช้กับ AI เพื่อให้แชทรอบหน้า **อ่านแล้วทำตามได้ทันที** โดยไม่ต้องอธิบายซ้ำทุกครั้ง

## Cursor จะ “แจ้งออโต้” เรื่องประหยัดโทเค็นไหม?

**ไม่มีการแจ้งอัตโนมัติจากตัว Cursor เป็นค่าเริ่มต้น** — ไม่มีป๊อปอัปหรือสวิตช์ระบบว่า “รอบนี้ใช้ท่าไหนประหยัดโทเค็น”  
ให้ใช้ **กติกาในไฟล์นี้ + รายการอ่านใน `AGENTS.md`** เพื่อให้ **Agent ใน Cursor** ตอบกลับมาพร้อม **บรรทัดสรุปท่าประหยัดโทเค็น** ทุกครั้งที่เกี่ยวข้อง (ดูหัวข้อ “เมื่อผู้ใช้ขอ prompt สำหรับ Claude Code” ด้านล่าง)

## ขอบเขตสำคัญ (อ่านก่อน)

- **Cursor (แชทกับ Agent ใน IDE)** กับ **Claude Code (`claude` ในเทอร์มินัล)** เป็นคนละโปรแกรม — Agent ใน Cursor **เปิดเซสชัน `claude` หรือพิมพ์ใน prompt ของ Claude Code แทนผู้ใช้โดยตรงไม่ได้**
- **ความจำข้ามแชท:** ใน Cursor ไม่มี “ความจำเดียว” กับ Claude Code — ใช้ไฟล์นี้ + กฎใน `.cursor/rules/` + **Claude-Mem ใน Claude Code** แยกกัน
- **เมื่อ context ใกล้เต็ม:** เริ่มเธรดใหม่ / compact ตามเครื่องมือ — Agent **มองไม่เห็น** % context ของผู้ใช้แบบเรียลไทม์

## แบ่งงาน (หลักการ)

| ใช้ | เมื่อไหร่ |
|-----|-----------|
| **Cursor Composer / Agent** | สแกนโค้ดกว้างๆ, หาตำแหน่ง logic, boilerplate, แก้ไฟล์ใน repo, รันสคริปต์ในเทอร์มินัลของ Cursor |
| **Claude Code** | logic หนัก, refactor ยาว, ใช้เครื่องมือเทอร์มินัลคู่กับ **Graphify + Claude-Mem + rtk** |

## rtk (Windows + PATH แล้ว)

- **ติดตั้ง integration กับ Claude Code (ครั้งแรกหรือหลังอัปเดต):** ใน PowerShell  
  `rtk init -g`  
  จากนั้น **รีสตาร์ท Claude Code**
- **ถ้าใช้ Cursor ให้ hook แยก (ถ้าต้องการ):**  
  `rtk init -g --agent cursor`  
  แล้วรีสตาร์ท Cursor
- **บน Windows แบบ PowerShell:** มีฟิลเตอร์ `rtk git status`, `rtk pytest`, `rtk ruff check`, ฯลฯ ได้ — **ไม่มี auto-rewrite** แบบ Linux/WSL; ถ้าต้องการครบตามเอกสาร rtk แนะนำ **WSL**
- **อย่าดับเบิ้ลคลิก `rtk.exe`** — รันจากเทอร์มินัลเท่านั้น
- **เช็คสถิติ:** `rtk gain`

โปรเจกต์ Python (TMS): เน้นใช้ **`rtk pytest`**, **`rtk ruff check`**, **`rtk git diff`**, **`rtk git status`** เมื่อให้ AI อ่านผลจากเชลล์

## Graphify + Claude-Mem (ใน Claude Code)

1. เปิดเทอร์มินัลที่รากโปรเจกต์ที่ต้องการอินเด็กซ์ เช่น  
   `cd "C:\Users\Home\Desktop\Project YK"`
2. รัน `claude` → ล็อกอินตามระบบ (ครั้งแรก)
3. ปลั๊กอิน (ทำครั้งหรือหลังอัปเดต):  
   `/plugin marketplace add thedotmack/claude-mem`  
   `/plugin install claude-mem@thedotmack`  
   `/reload-plugins`
4. อินเด็กซ์โค้ด (หลังโครงสร้างเปลี่ยนเยอะ):  
   `/graphify .`  
   เมื่อ Claude ถามอนุญาตรัน PowerShell สำหรับ Graphify — **อ่านคำอธิบายแล้วกด Yes ได้** ถ้าเป็นคำสั่งติดตั้ง/บันทึก Python path ของ Graphify (ไม่ใช่ “Yes ทุกอย่าง” โดยไม่ดู)

**หมายเหตุจาก upstream rtk:** เครื่องมือในตัวอย่าง Read/Grep/Glob ของ Claude Code **ไม่ผ่าน bash hook** — ถ้าต้องการ output แบบย่อ ให้ใช้เชลล์หรือ `rtk read` / `rtk grep`

## บล็อก “ส่งต่อ” จาก Cursor → Claude Code (คัดลอกวาง)

เมื่อคุยกับ Cursor จบงานหนึ่งแล้วอยากให้ Claude Code ทำต่อ — ให้ Agent ใน Cursorสรุปเป็น bullet แล้ว **คัดลอกบล็อกด้านล่างไปวางใน `claude`** (แก้ข้อความใน `[ ]` ให้ตรงงาน)

```text
[HANDOFF Project YK → Claude Code]

บริบท: FastAPI + SQLite + HTMX อยู่ใต้ ProjectYK_System/app/
งานที่ต้องการทำต่อ:
- [ bullet งาน 1 ]
- [ bullet งาน 2 ]

ขอบเขต / ห้ามแตะ:
- [ เช่น อย่าแก้ payroll ถ้ายังไม่ยืนยัน cycle ]

ไฟล์หรือโมดูลที่เกี่ยว:
- [ เช่น ProjectYK_System/app/... ]

คำสั่งเทอร์มินัลที่อยากให้ใช้แบบประหยัดโทเค็น (ถ้ารัน):
- rtk git status
- rtk git diff
- rtk pytest (หรือ path ทดสอบที่ระบุ)
- rtk ruff check

Graphify: ถ้ายังไม่อินเด็กซ์ล่าสุด ให้รัน /graphify . จากราก Project YK
```

## สิ่งที่ Agent ใน Cursor ต้องทำ (Claude Code / prompt ส่งต่อ)

### ก) เมื่อผู้ใช้ขอให้ “เขียน prompt ให้ Claude Code” / “สร้าง prompt ส่ง claude” / ใกล้เคียง

**บังคับ:** ก่อนหรือหลังบล็อก prompt ที่ให้คัดลอก ให้ใส่หัวข้อสั้นๆ ชัดเจน เช่น:

**ท่าประหยัดโทเค็นที่ใช้ในรอบนี้**

- บล็อก **[HANDOFF …]** ตามเทมเพลตด้านบน (ขอบเขต + ไฟล์ + คำสั่ง `rtk …` ที่เหมาะกับงาน)
- แนะนำให้ใน Claude Code ใช้เชลล์/`rtk …` แทนการดึงไฟล์ยาวด้วยเครื่องมืออ่านดิบเมื่อไม่จำเป็น
- ถ้างานแตะโครงสร้างโปรเจกต์มาก: แนะ **`/graphify .`** จากราก `Project YK` (หลัง `cd`)
- ความจำระยะยาว: ฝั่ง Claude Code ใช้ **claude-mem** (ไม่ใช่แชท Cursor)

### ข) เมื่อผู้ใช้บอกว่า “ทำต่อใน Claude Code”

1. สรุปงานเป็น bullet ชัดๆ ใส่ในบล็อก HANDOFF ด้านบน
2. เตือนให้ `cd` ไปรากโปรเจกต์ก่อนรัน `/graphify .`
3. **ไม่สัญญา** ว่าจะควบคุม `claude` แทนผู้ใช้ — ให้ผู้ใช้วางบล็อกเองหนึ่งครั้ง
4. ใส่หัวข้อ **ท่าประหยัดโทเค็นที่ใช้ในรอบนี้** ตามข้อ **ก)** ด้วย

## Prompt mode สำหรับโอ (Vibecoding)

ถ้าโอสั่งว่า “ช่วยเขียน prompt อังกฤษให้ส่ง Claude Code” ให้ Cursor ใช้โหมดนี้ทันที:

1. สรุปโจทย์ภาษาไทยของโอเป็นอังกฤษแบบสั้น (ไม่เกิน 12 บรรทัด)
2. ใส่บล็อกข้อบังคับ 4 checks:
   - unlinked records
   - cycle tag integrity
   - cross-site name collision
   - source mismatch (daily/fuel/petty/payroll)
3. บังคับ Claude Code รายงานผลเป็นตัวเลข (`count + amount`) เมื่อมีความเสี่ยงข้อมูลเงินตกหล่น
4. บังคับให้ Claude Code recompute และสรุป before/after
5. ถ้ามีจุดกำกวมที่กระทบเงิน ให้ถามกลับไม่เกิน 3 ข้อก่อนลงมือ

เอกสารอ้างอิง prompt pack:
- `ProjectYK_System/TransportRateCalculator/docs/CLAUDE_CODE_VIBECODING_PLAYBOOK.md`

## อ้างอิงภายนอก

- rtk: https://github.com/rtk-ai/rtk  
- ลง rtk บน Windows: แตก zip แล้วเพิ่มโฟลเดอร์ที่มี `rtk.exe` เข้า PATH (โอเคแล้วถ้าตั้งตามนั้น)
