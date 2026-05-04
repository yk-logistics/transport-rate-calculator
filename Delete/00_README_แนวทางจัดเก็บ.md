# โฟลเดอร์ Delete — ใช้ทำอะไร

โฟลเดอร์นี้ใช้ **เก็บของที่น่าจะลบหรือแยกออกจากงานหลัก** ให้คุณโอเปิดดูทีหลังแล้วตัดสินใจลบจริงหรือย้ายกลับ

- **อย่า commit ข้อมูลสำคัญ** (เงินเดือน, รหัส, DB) เข้า git โดยไม่ตั้งใจ — ตรวจ `.gitignore` ก่อนเสมอ
- ถ้าย้ายแล้วแอป/สคริปต์ error ให้ย้ายโฟลเดอร์กลับตำแหน่งเดิม

---

## แผนที่โปรเจกต์ YK (หมวดหมู่หลัก)

| หมวด | โฟลเดอร์/ไฟล์ | งานที่เกี่ยวข้อง |
|------|----------------|------------------|
| **แอปหลัก (One Platform)** | `ProjectYK_System/` โดยเฉพาะ `app/` | FastAPI + SQLite + หน้าเว็บ Daily / Petty / Payroll / ซ่อม / Driver PWA — **ห้ามลบโดยไม่สำรอง** |
| **สเปก + เครื่องคิดเรท + เอกสารระบบ** | `TransportRateCalculator/` | HTML เครื่องคิด, โฟลเดอร์ `docs/`, `reports/` |
| **อุบัติเหตุ (รายงาน HTML)** | `AccidentCases/` | เคส + template + รูปประกอบเคส |
| **สคริปต์ import / ช่วยงาน** | `tools/` | import daily, petty, phase2, ฯลฯ — ผูกกับ Phase 2 ใน bootstrap |
| **ข้อมูลนำเข้า/ส่งออก AYU** | `AYU_sheets_csv/` | CSV จากชีต AYU |
| **ลูกค้า/งานวิ่ง (Oatside ฯลฯ)** | `Oatside/` | Excel รายงานผ่านจุด, สคริปต์ build report |
| **บิลลิ่ง** | `Billing/` | ไฟล์บิลลูกค้า (เช่น BigC) |
| **เอกสารอุบัติเหตุ (นอกเคส)** | `AccidentReports/` | HTML/PDF รายงานสอบสวน |
| **ผลลัพธ์สคริปต์/รายงานชั่วคราว** | `Resulted/` | output จากการรัน |
| **Logbook / จด** | `logbooks/` | ไฟล์ logbook ที่ generate |
| **ข้อมูลอ่อนไหว (ไม่ควร commit)** | `Salary/`, `Fuel/` | ตั้งใจ ignore ใน `.gitignore` |
| **สำรองดีไซน์** | `Daily module design backup/` | สำเนา markdown ดีไซน์ |
| **รากโปรเจกต์ — สคริปต์ชั่วคราว** | `_check_*.py`, `_inspect_*.py`, `_summary_*.py`, `_payroll_v*.txt` | สคริปต์/ล็อกทดสอบรอบเดียว — **ย้ายมา Delete ได้ถ้าไม่รันแล้ว** |
| **ความทรงจำชื่อคอลัมน์ (สคริปต์เก่า)** | `name_memory.json`, `price_memory.json`, `column_memory.json`, `clean_name_memory.json` | state ช่วย parse Excel — ย้ายได้ถ้าไม่มีสคริปต์อ้างอิงแล้ว |
| **Deploy / สำเนาเว็บ** | `transport-rate-calculator-repo/` | มี `.git` ของตัวเอง — อาจซ้ำกับ `TransportRateCalculator/` — **ตรวจก่อนว่ายัง deploy จากโฟลเดอร์นี้ไหม** |
| **รวม PDF ชั่วคราว** | `PDF Merge/` | รูป JPG หลายใบ — มักเป็นของชั่วคราวจากเครื่องมือ merge — **ย้ายมาพิจารณาได้ถ้าไม่ใช้แล้ว** |
| **โฟลเดอร์ทดลองชื่อกลางๆ** | `New folder/` | มี `fill_oil_to_daily.py` + Excel VOLVO — **อาจซ้ำกับงานใน tools/ — อย่าลบถ้ายังใช้สคริปต์นี้อยู่** |
| **Word / เทมเพลต** | `Driver_Choice_Letter_TH_files/`, `Demurrage_Summary_Customer_TH.docx` | ไฟล์คู่กับจดหมาย/สรุป demurrage |
| **เกม / ไม่เกี่ยวธุรกิจ** | (ย้ายไป `Delete/unrelated_valorant/`) | โปรเจกต์ overlay เกม |

---

## โครงใน `Delete/` (แนะนำ)

| โฟลเดอร์ | ความหมาย |
|----------|----------|
| `unrelated_valorant/` | โปรเจกต์ Valorant (เดิม `valorant_spike_overlay/`) — ย้ายมาแล้วเป็นตัวอย่าง |
| `candidates_you_move_here/` | ให้คุณโอลาก `_payroll_v*.txt`, `PDF Merge`, ฯลฯ มาวางเองถ้าตัดสินใจแล้ว |

---

## DB สำรองในแอป (ระวัง)

ใน `ProjectYK_System/app/` มีไฟล์ `app.db.bak_*` — เป็นสำรองฐานข้อมูล

- **ลบได้เฉพาะเมื่อ** มั่นใจว่ามีสำรองอื่น + ไม่ต้อง rollback
- ถ้าจะเก็บไว้พิจารณา ให้ย้ายทั้งไฟล์มาใต้ `Delete/db_backups_review/` (กินพื้นที่มาก)

---

## ไฟล์รากที่ควรเก็บไว้กับงานหลัก

- `AGENTS.md`, `AGENT_START_HERE.md`, `PHASES.md`, `.cursorrules` — คู่มือ Agent / ทิศทางโปรเจกต์
- `requirements.txt` — dependency ราก (ถ้ายังใช้)
- `Employee_Master.xlsx`, `Payroll_V19_*.xlsx` — ข้อมูลคน (ระวังความลับ)

---

*สร้างโดย Agent เพื่อช่วยจัดหมวด — ปรับแก้รายการตามการใช้งานจริงของทีมได้เลย*
