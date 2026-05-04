# Daily Module Design (v0.1)

เอกสารนี้ต่อยอดจาก `TransportRateCalculator/COST_MODEL.md` เพื่อเริ่มโมดูล Daily แบบครบ flow:

1. กรอกงานรายวัน (Daily)
2. ออกวางบิลอัตโนมัติ (Billing)
3. สรุปเงินเดือน (Payroll)

โดยรองรับหลายไซต์พร้อมกัน: `AYU`, `BigC`, `LCB`

## เป้าหมายรอบแรก

- ใช้โครงข้อมูลกลางเดียวกัน แม้แต่ละไฟล์ Excel โครงไม่เหมือนกัน
- ให้แยก "คำนวณวางบิลลูกค้า" ออกจาก "คำนวณรายได้คนขับ" ชัดเจน
- ใช้กฎเดียวกับระบบเดิม (`payroll_system.py`) แต่ย้ายเป็นโมดูลที่แยกชั้นมากขึ้น
- เก็บ audit trace ต่อพนักงานและต่อใบงาน เพื่อย้อนตรวจได้

## อินพุตหลัก

- Daily report (แหล่งหลัก: AYU/BigC/LCB)
- Fuel report (โดยเฉพาะ LCB มีรายละเอียดครบ)
- สดย่อย/เงินเบิก
- Master พนักงาน

## Data Contract กลาง

### 1) DailyJob
- work_date
- site_code (`AYU`/`BigC`/`LCB`)
- driver_raw_name
- driver_name (หลัง normalize + match Master)
- plate_no
- container_no
- trip_type (Domestic/Export/Import/อื่นๆ)
- customer_name
- origin / destination
- revenue_customer (ค่าขนส่งที่วางบิลลูกค้า)
- trip_fee_driver (ค่าเที่ยวพขร.)
- extra_amount (OT/พิเศษ/รับตู้คืนตู้แทน)
- fuel_mile / fuel_liter / fuel_amount (ถ้าผูกน้ำมันลง Daily)

### 2) FuelTxn
- txn_date
- site_code
- plate_no
- driver_raw_name
- driver_name
- liter
- amount
- mile
- source_sheet
- source_row

### 3) AdvanceTxn
- txn_date
- site_code
- driver_raw_name
- driver_name
- amount
- note

### 4) EmployeeMaster
- employee_id (optional)
- full_name
- clean_name
- site_code
- pay_type (`Trip`/`Mao`)
- social_security_enabled
- deposit_accumulated
- skip_first_fuel (option)
- skip_fuel_before_date (option)

## Pipeline 3 ชั้น

### A) Daily Ingestion + Validation
- อ่านหลายชีทและเลือกช่วงรอบ 16-15
- normalize ชื่อคนขับ + map กับ Master (ห้ามเดา)
- เตือนข้อมูลผิด:
  - เบอร์ตู้ซ้ำผิดเงื่อนไข
  - ค่าเที่ยวว่าง
  - ชื่อไม่ match master
  - วันที่อยู่นอกรอบ

ผลลัพธ์: `normalized_daily_jobs`

### B) Billing Builder (Auto วางบิล)
- group ตามลูกค้า/งาน/รถ/วัน ตาม profile ของแต่ละไซต์
- สร้าง billing lines:
  - รายรับลูกค้า (`revenue_customer`)
  - หมวดต้นทุนสำคัญจาก Cost Model (fuel, maintenance, back office, finance cost)
- ให้มีทั้ง:
  - `invoice_detail` (แถวรายการ)
  - `invoice_summary` (สรุปต่อรอบ/ลูกค้า)

ผลลัพธ์: `billing_result`

### C) Payroll Builder
- ใช้กฎ Trip/Mao ตาม Master
- Trip:
  - เงินเดือนฐาน + ค่าดูแลรถ (เฉลี่ยตามวันในรอบ หักลา)
  - ค่าเที่ยว + พิเศษ + รับ/คืนตู้แทน
- Mao:
  - รายได้จากค่าเที่ยว/เปอร์เซ็นต์เหมา
  - หักค่าน้ำมันตามรอบ (รองรับ skip first tank)
- หัก: สดย่อย, ประกันสังคม, ภาษี, เงินประกันตน
- ออก `payroll_summary` + `payroll_audit`

ผลลัพธ์: `payroll_result`

## Site Profile (AYU/BigC/LCB)

เพราะหัวคอลัมน์ต่างกัน ให้ใช้ `SiteProfile` ระบุ alias คอลัมน์:
- date aliases
- driver aliases
- plate aliases
- revenue aliases
- trip fee aliases
- status aliases

แนวคิดนี้ช่วยให้เพิ่มไซต์ใหม่โดยไม่ต้องแก้ core logic

## โครงสร้างไฟล์ที่เริ่มทำ (v0.1)

- `Salary/daily_module/contracts.py` -> dataclass กลาง
- `Salary/daily_module/site_profiles.py` -> profile AYU/BigC/LCB
- `Salary/daily_module/pipeline.py` -> orchestration Daily -> Billing -> Payroll
- `Salary/daily_module/run_daily_pipeline.py` -> จุดเริ่มรันแบบ CLI

## ขอบเขต v0.1

- เป็น foundation และ dry-run พร้อมอ่านไฟล์ + normalize
- ยังไม่แทนที่ `payroll_system.py` ทันที
- ตั้งใจให้ migrate แบบปลอดภัย: รันคู่กันเพื่อเทียบผลก่อน

## Roadmap ถัดไป (แนะนำ)

1. ทำ adapter อ่านไฟล์ Excel แบบ "จำ mapping ต่อไซต์" (interactive รอบแรก)
2. ย้าย formula เงินเดือนจาก `payroll_system.py` เข้า payroll service แบบแยกฟังก์ชัน
3. เพิ่ม generator Excel output 3 ชีทมาตรฐาน:
   - `Daily_Normalized`
   - `Billing_Summary`
   - `Payroll_Summary` + `Payroll_Audit`
4. เพิ่ม regression check เทียบยอดรวมกับไฟล์เดือนก่อน
