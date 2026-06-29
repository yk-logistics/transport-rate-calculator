# Design — น้ำมัน B7/B20: เก็บเกรด + สลิปไม่โชว์วันที่ซ้ำ

วันที่: 2026-06-29
ไซต์ที่กระทบหลัก: LCB (มี FuelTxn รายเที่ยวจริง) — โครงรองรับทุกไซต์

## ปัญหา (จากโอ)

คนขับเติมน้ำมัน **ครั้งเดียว รถคันเดียว แต่ได้ B7 + B20 พร้อมกัน** (เช่นบิล 2 ใบจากปั๊มเดียวกัน). เวลามาร์ค (คนคีย์) ลงระบบ จะคีย์ต่อบรรทัดลงมา → กลายเป็นงานเดลี่ 2 แถว แถวละ 1 ยอดน้ำมัน. บางทีบรรทัดที่ 2 ตกไปอยู่ "วันถัดไป" → สลิปคนขับเห็นน้ำมันโผล่ 2 วัน ทั้งที่เติมครั้งเดียว → **คนขับสับสน**. โออยากให้รวม/ไม่งง และ **มุมบริหารอยากแยกได้ว่ายอดไหน B7 ยอดไหน B20**.

## ข้อเท็จจริงจากข้อมูลจริง (สำคัญ — เป็นฐานการตัดสินใจ)

ตรวจ DB จริง (LCB รอบ 16/5–15/6, source `lcb_may-jun2026`):

1. **FuelTxn ผูกกับ DailyJob 1:1** — 0 daily_job มี FuelTxn ≥2 ใบ. ฉะนั้น "วันเดียวกัน 2 ยอดน้ำมัน" = **DailyJob 2 แถว** (คนละ id) ไม่ใช่ 1 แถวมี 2 บิล.
2. **ราคา/ลิตรแยกเกรดได้ชัด**: histogram เป็น 2 ก้อนชัด — กลุ่ม **~35–36 ฿/L** (B20, ถูกกว่า) และ **~40–42 ฿/L** (B7). ช่อง 37–39 ฿/L แทบว่าง. (โอประเมินถูก: B20 ถูกกว่า B7 อย่างเห็นได้ชัด ~6 ฿/L)
3. **แต่ auto-merge ไม่ปลอดภัย**: กฎจับ "วันเดียว+คันเดียว+1 บิล B20+1 บิล B7" เจอ 57 คู่ ในรอบนี้ → **~26 คู่เป็น 2 เที่ยวงานคนละเที่ยวจริง** (rev>0 ทั้งคู่ คนละ route) + ~31 คู่น่าจะ 1-fill-2-grade. รวมอัตโนมัติ = **ผิดเกือบครึ่ง** (ยุบ 2 เที่ยวจริงเป็นเที่ยวเดียว). ระบบ **แยก "เติมครั้งเดียว 2 เกรด" จาก "2 เที่ยววันเดียว" ไม่ได้** เพราะหน้าตาข้อมูลเหมือนกัน.
4. **เกรดของข้อมูลเก่าไม่ได้ถูกเก็บไว้ที่ไหน** — ไฟล์ import (ชีท Daily) ไม่มีคอลัมน์เกรด; note/station ว่าง. เกรดต้อง "เดา" จากราคาเท่านั้น.

**สรุปการตัดสินใจ (โอยืนยัน):**
- ❌ **ไม่ทำ auto-merge** (เสี่ยงรวมผิดครึ่ง + ต้องให้โอยืนยันทีละคู่ = เพิ่มงานโอ ซึ่งโอไม่ต้องการ).
- ✅ **ข้อ 1**: สลิปยุบ "การแสดงวันที่" ที่ซ้ำกัน — แสดงวันที่ครั้งเดียวต่อกลุ่มวันเดียวกัน. **แค่การแสดงผล ไม่แตะข้อมูล/เงิน/จำนวนแถว**.
- ✅ **ข้อ 3**: เพิ่มช่อง `fuel_grade` (B7/B20) ในระบบ + กรอก/แก้ได้ + backfill เดาจากราคาแบบ relative-per-group + โอแก้ทับได้. **แค่ป้ายเกรด ไม่แตะ liter/amount/exclude/เงิน**.

## ขอบเขต (scope)

**ทำ:**
1. สลิป (`_slip_body.html`): กลุ่ม DailyJob ที่ `work_date` เดียวกัน → โชว์วันที่ครั้งเดียว, แถวถัดมาในวันเดียวกันเว้นช่องวันที่ (หรือใส่ป้าย "↳ วันเดียวกัน"). ใช้ได้ทั้ง branch ปกติและ mixed.
2. `FuelTxn.fuel_grade: str = ""` (ค่าว่าง=ไม่ระบุ) — schema v31, additive.
3. Backfill tool: เดาเกรดจากราคา/ลิตร **relative ต่อกลุ่ม (วันเดียว+คันเดียว)** ไม่ผูกเลขบาทตายตัว — ในกลุ่มที่ราคาห่าง ≥3฿: ถูกกว่า=B20, แพงกว่า=B7. กลุ่ม/แถวที่แยกไม่ได้ (ราคาใกล้กัน หรือแถวเดี่ยว) → เดาจาก absolute cluster เป็น fallback (≤~38=B20, >~38=B7) **แต่ทำเป็น "ค่าเริ่มต้นที่แก้ได้" ไม่ใช่ความจริงตายตัว**.
4. หน้ากรอก: เพิ่มช่องแก้ `fuel_grade` ต่อบิลในหน้า **/fuel** (หน้าจัดการ FuelTxn ที่มีอยู่) — dropdown B7/B20/(ว่าง). มุมบริหารเห็นเกรดในตาราง /fuel + ใน CFO/รายงานถ้าต้องการภายหลัง.
5. Import (`import_lcb_may_jun2026_xlsx.py` + path import น้ำมันอื่น): ตั้ง `fuel_grade` จากราคาตอน import (ใช้ helper เดียวกับ backfill) ถ้าไฟล์ยังไม่มีคอลัมน์เกรด.

**ไม่ทำ (YAGNI / เกินขอบเขต):**
- auto-merge / ย้ายวันที่ FuelTxn ผิดวัน (เรื่องที่ 2 เดิม — พักไว้).
- เปลี่ยน logic เงิน/payroll ใดๆ.
- เพิ่มเกรดอื่นนอกจาก B7/B20 (ยังไม่มีในงานจริง).

## สถาปัตยกรรม / จุดแก้

### 1. Schema (additive, v31)
`models.py` — `FuelTxn`:
```python
fuel_grade: str = Field(default="")   # "B7" | "B20" | "" (ไม่ระบุ)
```
`main.py`:
- `SCHEMA_VERSION = 31`
- ใน `_apply_additive_migrations`: `_ensure_column("fueltxn", "fuel_grade", "TEXT", default="")`

### 2. Helper เดาเกรด (single source of truth)
ที่ใหม่: `services/fuel_grade.py`
```python
B20_MAX_HINT = 38.0   # เส้น absolute ใช้เป็น fallback เท่านั้น (ราคาผันผวนได้)

def guess_grade_from_price(price_per_liter: float) -> str:
    """เดาเกรดจากราคา/ลิตร แบบหยาบ (fallback). คืน 'B7'|'B20'|''."""

def assign_grades_for_group(prices: list[float]) -> list[str]:
    """รับราคาของบิลในกลุ่มวันเดียว+คันเดียว คืน grade ต่อบิลแบบ relative:
       ถ้า max-min >= 3 → ถูกสุดฝั่ง=B20 แพงสุดฝั่ง=B7 (แบ่งครึ่งตามช่องว่าง);
       ถ้าใกล้กัน → ใช้ guess_grade_from_price ทีละตัว."""
```
ใช้ทั้ง backfill, import, และ (ถ้าต้อง) ตอนเพิ่มบิลใหม่.

### 3. Backfill tool
`tools/backfill_fuel_grade.py` (read DB → set `fuel_grade` เฉพาะแถวที่ยังว่าง):
- จัดกลุ่ม FuelTxn ตาม (site_code, txn_date, plate_no_raw), liter>0.
- เรียก `assign_grades_for_group`.
- **เซฟเฉพาะ `fuel_grade`** — ไม่แตะ field อื่น.
- พิมพ์สรุป: กี่แถวตั้ง B7 / B20 / เว้นว่าง; แสดงตัวอย่างกลุ่มที่ไม่ชัด.
- มี `--dry-run` (default) → ต้อง `--commit` ถึงเขียนจริง (กฎเงิน/ข้อมูล).

### 4. สลิป — ยุบวันที่ซ้ำ (display only)
`_slip_body.html`:
- ใน loop `for r in daily_jobs` (ทั้ง 2 branch): เทียบ `r.work_date` กับแถวก่อนหน้า. ถ้าซ้ำ → ช่อง `c-date` แสดงว่าง หรือ `<span class="wb-muted">↳</span>`.
- ทำด้วย Jinja: ใช้ `loop.previtem` (Jinja มี `loop.previtem`/`loop.first`).
- ไม่เปลี่ยนจำนวนแถว ไม่เปลี่ยนตัวเลข. tfoot/รวมเหมือนเดิม.
- (ออปชัน) ถ้า FuelTxn มี grade → โชว์ป้ายเล็ก "B7"/"B20" ท้ายช่องน้ำมัน เพื่อให้คนขับเห็นว่าเป็นคนละเกรด (ไม่บังคับ; ถามโอตอน review). **ต้องมี mapping job→grade** (ดูข้อ 5).

### 5. ส่ง grade เข้า context สลิป
`services/payroll_slip.py` `build_payroll_slip_context`:
- มี `fuel_rows` อยู่แล้ว. สร้าง `job_grade = {f.daily_job_id: f.fuel_grade for f in fuel_rows if f.daily_job_id and f.fuel_grade}` ส่งเข้า context เป็น `fuel_grade_by_job` เพื่อ template โชว์ป้ายเกรดต่อแถว (ถ้าเปิดออปชันข้อ 4 ของสลิป).

### 6. หน้า /fuel — แก้เกรด
- `fuel_list.html`: เพิ่มคอลัมน์ "เกรด" ในตาราง (โชว์ B7/B20).
- `fuel_form.html`: เพิ่ม dropdown (B7/B20/ว่าง) ตอนแก้บิล. ผูก endpoint แก้ FuelTxn ที่มีอยู่ (`_fuel_row_json` / update route ~main.py:3027–3130). เพิ่ม field `fuel_grade` ใน payload เดียวกับที่แก้บิลอยู่แล้ว.

### 7. Import
- `import_lcb_may_jun2026_xlsx.py`: ตอนสร้าง FuelTxn (บรรทัด ~299) เซ็ต `fuel_grade=guess_grade_from_price(price)` ถ้าไฟล์ไม่มีคอลัมน์เกรด. (ถ้าอนาคตไฟล์มีคอลัมน์เกรด → อ่านตรงจากไฟล์แทนการเดา.)

## Data flow
1. Import / กรอกมือ → FuelTxn (มี liter, amount, fuel_grade).
2. Backfill (ครั้งเดียวกับของเก่า) → เติม fuel_grade ที่ว่าง.
3. โอเปิด /fuel → เห็น/แก้เกรดได้ (มุมบริหาร).
4. สลิปคนขับ → แสดงวันที่ครั้งเดียวต่อวัน (ไม่ซ้ำ) + (ออปชัน) ป้ายเกรดต่อบิล.
5. payroll/เงิน → **ไม่เปลี่ยน** (fuel_grade ไม่เข้าไปในสูตรหักเงินเลย).

## Error handling / edge cases
- บิลที่ liter=0 → `guess_grade_from_price` คืน "" (เดาไม่ได้).
- กลุ่มที่ราคาใกล้กัน (เกรดเดียวกัน 2 บิล) → ทั้งคู่ได้เกรดเดียวกันจาก absolute fallback (ถูกต้อง — ไม่ใช่คู่ B7/B20).
- แถวเดี่ยว (ไม่มีคู่) → absolute fallback.
- สลิป mixed branch: ยุบวันที่ใช้กลไกเดียวกัน (loop.previtem).

## ความถูกต้อง / preflight
- **ยอดเงินต้องไม่ขยับ**: หลัง migration + backfill, รัน recompute ตรวจ net ของ payrun draft ทุกไซต์ที่แตะ = เท่าเดิม (fuel_grade ไม่อยู่ในสูตร). ตรวจ `sum(liter)`/`sum(amount)` ต่อรอบ = เท่าเดิม.
- **สลิป**: เทียบ PDF ก่อน/หลัง — จำนวนแถว + ทุกตัวเลขเท่าเดิม, ต่างแค่ช่องวันที่ที่ซ้ำหายไป.
- Backfill `--dry-run` ก่อนเสมอ; รายงานจำนวนแถวที่จะเปลี่ยน; โอดูตัวอย่างกลุ่มไม่ชัดก่อน `--commit`.

## ไฟล์ที่จะแตะ
- `models.py` (+1 field)
- `main.py` (SCHEMA_VERSION + migration 1 บรรทัด; /fuel route +field; อาจเพิ่มคอลัมน์ตาราง /fuel template)
- `services/fuel_grade.py` (ใหม่)
- `services/payroll_slip.py` (+ fuel_grade_by_job ใน context)
- `templates/_slip_body.html` (ยุบวันที่ซ้ำ + ออปชันป้ายเกรด)
- `templates/fuel_list.html` (คอลัมน์เกรดในตาราง) + `templates/fuel_form.html` (dropdown เกรดตอนแก้บิล)
- `tools/backfill_fuel_grade.py` (ใหม่)
- `tools/import_lcb_may_jun2026_xlsx.py` (เซ็ต grade ตอน import)

## Testing
- `tools/fuel_grade` helper: unit tests — relative split (gap≥3), same-price pair, single row, liter=0.
- Backfill: dry-run บน DB จริง (อ่านอย่างเดียว) → ตรวจตัวเลขสรุปสมเหตุสมผล (≈100 แถว B20, ≈281 B7 ในรอบ มิ.ย.).
- สลิป: render PDF 1 คนที่มีวันซ้ำ (เช่น เนื้อ/นิพล) → ยืนยันวันที่ไม่ซ้ำ + ตัวเลขเท่าเดิม.
