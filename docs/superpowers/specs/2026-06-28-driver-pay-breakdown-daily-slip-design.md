# Spec — แยกโชว์เงินคนขับ (ค่าเที่ยว / พิเศษ / OT / รับตู้คืนตู้) ใน เดลี่ + สลิป

วันที่: 2026-06-28
ผู้สั่งงาน: โอ (พงษกาญจน์)
ประเภท: display-only (ไม่แตะ engine เงิน / ไม่ migrate schema)

## เป้าหมาย

โชว์รายได้ของ **คนขับ** ให้ครบและแยกช่องในทุกหน้าจอ: **ค่าเที่ยว · ค่าพิเศษ · ค่า OT · ค่ารับตู้คืนตู้**
ส่วน **ค่าเสียเวลา (และค่ายกตู้/ผ่านลาน/คลีน/ชอร์/เข้าท่า) เป็นของบริษัท** ไม่เกี่ยวกับคนขับ → ไม่โชว์ในโซนเงินคนขับ

## ความจริงที่ตรวจแล้ว (ground truth)

- engine (`services/payroll.py`) คิดเงินคนขับจาก DailyJobFee เฉพาะ 3 กลุ่มนี้ (ผ่าน `_sum_lcb_driver_extra_fees`):
  - `LCB_SPECIAL_FEE_TYPES = {"special", "พิเศษ", "ค่าพิเศษ"}`
  - `LCB_OT_FEE_TYPES = {"ot", "ค่าล่วงเวลา"}` + ค่า `"OT"` (จับแบบ lower() แล้ว `ot`)
  - `LCB_PICKUP_RETURN_FEE_TYPES = {"pickup_return", "รับตู้แทน"}`
- `ค่าเสียเวลา` **มีจริง**ในข้อมูล (4 แถว, 11,100฿) แต่ engine ไม่จับเข้าเงินคนขับ → เป็นของบริษัทอยู่แล้ว **ไม่ต้องแก้ logic**
- engine เก็บผลแยกไว้แล้วใน PayRunItem: `special_income`, `ot_income`, `pickup_return_income`, `trip_fee_total` (เป็น subset ของ `other_income` ไม่บวกซ้ำ gross) — schema v29 มีแล้ว ไม่ต้องเพิ่ม field
- ค่าใน DailyJobFee เป็น **ไทยปนอังกฤษ** ทุกที่ที่ sum ต้องใช้ชุดประเภทเดียวกับ engine เป๊ะ มิฉะนั้นตัวเลขจะเพี้ยนกัน

## ขอบเขต 3 ส่วน

### ส่วนที่ 1 — หน้ารวม payroll (`templates/payroll_detail.html`) + หน้ารายละเอียดคนขับ (`templates/payroll_employee_detail.html`)
**ไม่แตะ** — commit 9d63723 (28มิ.ย. เช้า) เพิ่มคอลัมน์/บรรทัด ค่าเที่ยว/พิเศษ/OT/รับตู้คืนตู้ ครบแล้ว

### ส่วนที่ 2 — สลิปที่ปริ้น (2 ไฟล์)
ไฟล์: `templates/payroll_slip.html` (ปุ่ม "พิมพ์สลิป" รายคน), `templates/payroll_print_all.html` (ปุ่ม "พิมพ์ทั้งหมด" คนขับ/ผู้บริหาร)

ปัจจุบัน: โซนรายได้โชว์ `รายได้อื่น` = `item.other_income` ก้อนเดียว → ฝัง พิเศษ/OT/รับตู้ ไว้ข้างใน มองไม่เห็น

แก้เป็น: แยกบรรทัดในโซน "รายได้"
- `ค่าเที่ยว` — มีบรรทัดอยู่แล้ว (`item.trip_fee_total`) ไม่แตะ
- `พิเศษ` → `item.special_income` (แสดงเมื่อ ≠ 0)
- `OT` → `item.ot_income` (แสดงเมื่อ ≠ 0)
- `รับตู้คืนตู้` → `item.pickup_return_income` (แสดงเมื่อ ≠ 0)
- บรรทัด `รายได้อื่น` ที่เหลือ = `other_income − special_income − ot_income − pickup_return_income`
  (แสดงเฉพาะเมื่อ "ส่วนที่เหลือ" ≠ 0 — กันยอดรวมเพี้ยนสำหรับเคสที่มี other_income อื่น เช่นโบนัส BIGC)
- ลบบรรทัดหมายเหตุเดิมใน `payroll_slip.html` ("เงินพิเศษ/OT/รับตู้แทน รวมอยู่ใน รายได้อื่น ด้านล่าง") — ไม่จริงแล้ว

กฎแสดงผล: ซ่อนบรรทัดถ้าเป็น 0 (ตาม pattern `{% if ... %}` เดิมของสลิป) เพื่อสลิปคนขับสะอาด

ยอดรวม (`gross_total`, รวมรายได้, net) **ไม่เปลี่ยน** — แค่แตกบรรทัดเดิมออก

### ส่วนที่ 3 — เดลี่ (`/api/daily/grid-data` ใน main.py + `templates/daily_grid.html`)
เพิ่ม 3 คอลัมน์อ่านอย่างเดียวในกริด: **พิเศษ / OT / รับตู้คืนตู้** วางถัดจาก `ค่าเที่ยว (AD)`

endpoint `daily_grid_data` (main.py ~1648):
- หลัง query rows แล้ว ดึง `DailyJobFee` ของ `job ids` หน้านั้นทีเดียว (1 query, `daily_job_id IN (...)`)
- sum ต่อ job ตามชุดประเภทเดียวกับ engine → คืน 3 field ต่อแถว: `fee_special`, `fee_ot`, `fee_pickup_return`
- ใช้ helper เดียวร่วมกับ engine (re-use ชุด `LCB_*_FEE_TYPES` จาก payroll.py — import มา ไม่ก๊อปสตริง) เพื่อกันค่าเพี้ยน; `ค่าเสียเวลา`/reserve types ตกหล่นไปฝั่งบริษัทเหมือน engine

template `daily_grid.html`:
- เพิ่ม 3 entry ใน config คอลัมน์ (header + field) ให้ default view ที่เกี่ยวข้องเห็น
- เพิ่ม 3 field ใน NUM_FIELDS + RIGHT_ALIGN (จัดขวา, ฟอร์แมตตัวเลข)
- **ไม่** ใส่ใน grid-save / ไม่อยู่ใน editable set — แก้ค่าพวกนี้ทำที่หน้าแก้ไขงานเดี่ยวเหมือนเดิม (ค่ามาจากตารางลูก ไม่ใช่ field บน DailyJob)

จำนวนแถว, คอลัมน์อื่น, ตัวเลขเงินเดิม **ไม่เปลี่ยน**

## ไม่ทำ (out of scope)
- ไม่แตะ engine/payroll recompute, ไม่ finalize/แก้ payrun ใด
- ไม่แตะ logic ค่าเสียเวลา (ถูกอยู่แล้ว = ของบริษัท)
- ไม่เพิ่ม/แก้ schema (ใช้ field เดิมทั้งหมด)
- ไม่ทำให้ 3 คอลัมน์เดลี่แก้ไขได้ในกริด

## ตรวจย้อนกลับ (verify)
1. รอบ LCB มิ.ย. (run2): ผลรวม พิเศษ/OT/รับตู้ จาก (ก) กริดเดลี่ sum ทั้งช่วง (ข) คอลัมน์หน้ารวม payroll (ค) `_sum_lcb_driver_extra_fees` ของ engine — ต้องตรงกันทั้ง 3
2. สลิปคน เช่น emp86: ค่าเที่ยว+พิเศษ+OT+รับตู้+(รายได้อื่นที่เหลือ)+เงินเดือน+ค่าดูแล+เรท+60%+การันตี = `gross_total` เป๊ะ; net ไม่เปลี่ยนจากก่อนแก้
3. `ค่าเสียเวลา` ไม่โผล่ในทุกหน้าจอฝั่งเงินคนขับ
