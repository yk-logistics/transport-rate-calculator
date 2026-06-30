# สลิป: โชว์น้ำมันตาม "วันที่เติมจริง" (รวมหลายบิลในแถวเดียว)

**วันที่:** 2026-06-30
**ขอบเขต:** display-only บนสลิปทุกไซต์ทุกคน — ไม่แตะ DB, ไม่แตะเงิน (fuel_cost_self / net คงเดิม)
**อนุมัติพฤติกรรมโดยโอ** (เลือก visual ผ่าน AskUserQuestion): น้ำมันโชว์ใต้วันที่เติมจริง, หลายบิลวันเดียว = อัดในแถวเดียว เป็นบรรทัดย่อยตัวเล็ก (ลิตร/บาท ซ้อนกัน), ไม่เพิ่มแถวใหม่.

## ปัญหา

ตารางเดลี่ในสลิปอ่านน้ำมันจาก `DailyJob.fuel_amount/fuel_liter` (สเกลาร์ต่อแถว) → โชว์ใต้ `work_date` ของ DailyJob ที่บิลผูกอยู่. แต่คนคีย์มักผูกบิลที่ "เติมจริงเมื่อวาน" ไว้กับงานวันนี้:
- LCB มิ.ย.: **74/384 บิล (19%)** มี `FuelTxn.txn_date` = `work_date − 1 วัน เป๊ะ** (ที่เหลือ delta=0).
- `DailyJob.fuel_date` (คอลัมน์ AC วันเติม) **ว่างทั้งหมด** → วันเติมจริงที่เชื่อได้ = `FuelTxn.txn_date`.
- **ทั้ง 74 เคสเป็น Case A:** วันที่เติมจริงมี "แถวงานของวันนั้นอยู่แล้วเสมอ" (ไม่มีเคสวันเติม=วันว่าง).

## ข้อเท็จจริงข้อมูล (verified, LCB#2 602 jobs in-cycle)
- `DailyJob.fuel_amount` == Σ `FuelTxn.amount` ที่ผูก job นั้น = **ตรง 100% (0 mismatch)**; liter ตรงด้วย.
- ทุก job มี FuelTxn ผูกอยู่ **0 หรือ 1 ใบ** (ไม่มี job ผูก >1, ไม่มี job ที่มี fuel แต่ไม่มี FuelTxn).
- ผลรวมน้ำมันในตาราง (footer) = `daily_jobs|sum(fuel_amount)` — **ไม่เปลี่ยน** ไม่ว่าจะย้ายโชว์บรรทัดไหน.

## ออกแบบ

### data layer — `build_payroll_slip_context` (payroll_slip.py)
แทนที่ `fuel_merge_by_job` (เดิม: anchor/merged สำหรับ B7+B20 เท่านั้น) ด้วยโครงสร้างทั่วไป **`fuel_lines_by_job: dict[int, list[dict]]`**:

1. รวม FuelTxn ที่อยู่ในตาราง (`daily_job_id` ชี้ job ใน `daily_jobs`) เป็นกลุ่มตาม **วันเติมจริง = `txn_date`** ต่อคน.
2. ต่อกลุ่ม: **anchor = DailyJob ที่ `work_date == txn_date`** ถ้ามี (Case A ทุกเคส); ถ้าไม่มี (เผื่ออนาคต) anchor = job ที่ตำแหน่งแสดงผลบนสุดในกลุ่ม (เดิม).
3. `fuel_lines_by_job[anchor.id]` = list ของ sub-line เรียงตาม `txn_date,id`:
   `{liter, amount, grade, excluded}` (excluded = `FuelTxn.exclude_from_driver` ต่อใบ — สำคัญ: ป้าย "ไม่หัก" ต้องตามใบ ไม่ใช่ตาม host row).
4. job อื่นในกลุ่มที่ไม่ใช่ anchor → `fuel_lines_by_job[j] = []` (= merged, เว้นช่อง).
5. job ที่ไม่มี FuelTxn (เช่นวันไม่เติม) → ไม่อยู่ใน dict เลย → template fallback ใช้ `r.fuel_liter/amount` เดิม (ปลอดภัย ไม่เปลี่ยน).

**ป้าย "หัก/บริษัท":** เดิม key ที่ `r.work_date in fuel_deduct_dates` (วันของ host). หลังย้าย sub-line อาจมาจากวันอื่น → ป้าย "หัก" ของ **กลุ่มทั้งกลุ่ม** ใช้ `txn_date` (=วันเติม=วัน anchor) ตัดสิน ซึ่ง = work_date ของ anchor พอดี → logic เดิมยังถูกเพราะ anchor.work_date==txn_date. (ป้าย "บริษัท" สำหรับ trip ก็ตามชนิดวันของ anchor.)

### template — `_slip_body.html` (2 branch: ปกติ + mixed)
ช่องลิตร + ช่องน้ำมัน฿: 
- ถ้า `r.id in fuel_lines_by_job`:
  - ถ้า list ว่าง (merged) → `↳`.
  - ถ้ามี ≥1 → loop โชว์แต่ละ sub-line เป็นบรรทัดย่อย (`<div class="fline">`), ลิตรฝั่งซ้าย, บาท+เกรด+ป้ายฝั่งขวา. หลายบรรทัดซ้อนในเซลล์เดียว (ตัวเล็กลงเล็กน้อย).
- else → เดิม (`r.fuel_liter/amount` + grade ต่อ job + ป้าย).
- **footer ไม่แตะ** (`daily_jobs|sum(...)`).

### print-all — `payroll_print_all.html`
เพิ่ม `fuel_lines_by_job=r.ctx.fuel_lines_by_job` ใน `{% with %}` (กัน UndefinedError 500 — บทเรียนเดิม) + ลบ `fuel_merge_by_job` ออกจาก with. body ใช้ `|default({})`.

### CSS (payroll_slip.css หรือ inline)
`.daily td .fline` — บรรทัดย่อยในเซลล์น้ำมัน: `font-size` เล็กลง ~1px, line-height แน่น, ขีดเส้นบางคั่นบรรทัด (อ่านออกบน A4). 2 บรรทัดในเซลล์ความสูงเท่าแถวเดียว.

## ทดสอบ (TDD)
1. `fuel_lines_by_job` anchor = job ที่ work_date==txn_date (เคส txn=work−1).
2. หลายบิลวันเติมเดียว → anchor มี ≥2 sub-line, รวมลิตร/บาท = Σ.
3. job ที่โดน merge → list ว่าง.
4. **total reconcile:** Σ ทุก sub-line ที่โชว์ + บรรทัด fallback = `daily_jobs|sum(fuel_amount)` (ไม่รั่ว/ไม่ซ้ำ).
5. excluded ตามใบ (บิล exclude_from_driver=True → sub-line.excluded=True แม้ host row ไม่ excluded).
6. ไม่มี FuelTxn → ไม่อยู่ใน dict (fallback เดิม).
7. render ทั้ง payroll_slip + print_all ไม่ 500; net/fuel_cost_self คงเดิม.

## ไม่ทำ (YAGNI)
- ไม่ย้ายข้อมูลใน DB (ไม่แตะ FuelTxn.daily_job_id / DailyJob.fuel_amount).
- ไม่ทำ UI ตั้งค่า, ไม่แตะ engine คิดเงิน.
- ไม่รวมข้ามวัน (เฉพาะ "วันเติมจริงเดียวกัน" เท่านั้น).
