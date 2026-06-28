# Payroll — โชว์ พิเศษ / OT / รับตู้คืนตู้ แยกช่อง

วันที่: 2026-06-28
สถานะ: approved (โอ)

## ปัญหา

เงินคนขับส่วน **พิเศษ / OT / รับตู้คืนตู้** ถูกคำนวณและจ่ายให้ถูกต้องแล้ว
(รอบมิ.ย. 16/5–15/6 รวม 21,890฿ — special 18,800 / OT 3,240 / pickup −150)
แต่ตัวเลขถูก **รวมจมอยู่ใน `other_income`** และโผล่แค่ในข้อความ `note` เท่านั้น
→ ทั้งหน้าตาราง `/payroll/{run}` และหน้าสลิป `/payroll/{run}/employee/{id}`
ไม่มีคอลัมน์/บรรทัดให้เห็น โอเลยเข้าใจว่าระบบ "ไม่ได้คิดให้"

**ยืนยันแล้วว่าไม่ใช่บั๊กการคำนวณ** — เป็นปัญหาการแสดงผลล้วน

## เป้าหมาย

แตกตัวเลขออกเป็น **3 ช่องแยก** ในทั้ง 2 หน้า:
- หน้าตาราง: เพิ่ม 3 คอลัมน์ `พิเศษ · OT · รับตู้คืนตู้` (ต่อจาก ค่าเที่ยว)
- หน้าสลิป: เพิ่ม 3 บรรทัดในฝั่ง "รายได้" (ใต้ ค่าเที่ยว)
- ค่า 0 โชว์ `–` (เหมือนช่องว่างอื่นในตาราง)
- **ยอด net / รวมรายได้ ไม่เปลี่ยน** — แค่แตกตัวเลขเดิมให้เห็น

## วิธี (โอเลือก: เก็บถาวรในระบบ)

### 1. Schema — เพิ่ม 3 field ใน PayRunItem (v28 → v29)
```
special_income       REAL default 0   # พิเศษ (เฉพาะ trip/mixed; mao = 0)
ot_income            REAL default 0   # OT (ทุก mode LCB)
pickup_return_income REAL default 0   # รับตู้/คืนตู้แทน (ทุก mode LCB)
```
ใช้ `_ensure_column` ใน `_apply_additive_migrations()` ตาม pattern เดิม
(เหมือน v27 ที่เพิ่ม `payrunitem.transfer_note`)

### 2. Engine — `services/payroll.py` assign 3 field ใน 3 mode
ทั้ง 3 mode คำนวณ `extra = _sum_lcb_driver_extra_fees(...)` อยู่แล้ว แค่เก็บลง field:
- `lcb_trip` (~บรรทัด 1001): special/ot/pickup = extra ทั้ง 3
- `lcb_mao` (~บรรทัด 1022): **special = 0** (คนเหมาไม่ได้พิเศษ), ot/pickup = extra
- `lcb_mixed` (~บรรทัด 1054): special/ot/pickup = extra ทั้ง 3

`other_income` และ `note` คงเดิม — แค่เพิ่มการ assign field ใหม่ขนานกัน
→ ตัวเลข 3 field **การันตีตรงกับที่บวกเข้า other_income** เพราะมาจากการคำนวณเดียวกัน

### 3. Template
- `payroll_detail.html`: +3 `<th>` ใน header (หลัง ค่าเที่ยว), +3 `<td>` ใน body row
  รูปแบบ `{{ '{:,.0f}'.format(it.special_income) if it.special_income else '—' }}`
- `payroll_employee_detail.html`: +3 `<tr>` ในตารางรายได้ (หลังบรรทัด ค่าเที่ยว)

### 4. Recompute รอบมิ.ย. (draft #2) 1 ครั้ง
แถวเดิมมี field ใหม่เป็น 0 จน recompute → recompute draft มิ.ย.
**net ทุกคนเท่าเดิม** (21,890฿ อยู่ใน other_income อยู่แล้ว แค่แตกลง field)

## ขอบเขต / ข้อยกเว้น

- **รอบ พ.ค. (finalized/locked) ไม่แตะ** — slip พ.ค. จะโชว์ 3 field = 0 จนกว่าจะ recompute
  (display เท่านั้น ไม่กระทบเงิน) — ถ้าโออยากให้ พ.ค. โชว์ด้วย ค่อยตัดสินแยก
- ไซต์อื่น (BIGC/AYU) ไม่มี fee พวกนี้ → field = 0 → โชว์ `–` (ไม่กระทบ)
- ไม่แตะหน้า print/PDF (`payroll_slip.html`) ในรอบนี้ — ถ้าต้องการตามมาทีหลัง

## ตรวจย้อนกลับ (money-adjacent)

1. ก่อน recompute: จด net รวมรอบมิ.ย. (= 276,855 จากภาพ)
2. หลัง recompute: net รวมต้อง **เท่าเดิม**; ผลรวม special+ot+pickup ของทุกแถว = 21,890
3. สุ่มเช็ค: emp ที่ note เขียน `พิเศษ 2,700` → field special_income = 2,700
4. เช็ค mao ทุกคน special_income = 0 (กฎ คนเหมาไม่ได้พิเศษ)
