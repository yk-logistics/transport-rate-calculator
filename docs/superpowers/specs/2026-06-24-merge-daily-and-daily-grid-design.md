# Design: ยุบรวมหน้า Daily + Daily Grid เป็นหน้าเดียว

**วันที่:** 2026-06-24
**สถานะ:** อนุมัติ design แล้ว — รอ review spec ก่อนทำ implementation plan

## ปัญหา

MVP มีสองเมนูที่ทำหน้าที่ทับซ้อนกันจน user สับสน:

- `/daily` → `daily_list.html` (เมนู "Daily")
- `/daily/grid` → `daily_grid.html` (เมนู "Daily Grid")

ทั้งสองหน้าใช้ Tabulator + Excel-style header filter + subtotal mode + column dialog +
dirty-tracking + endpoint บันทึกเดียวกัน (`/api/daily/grid-save`) แทบทุกอย่างเหมือนกัน
ต่างกันจริงแค่ไม่กี่จุด

## ความต่างจริงระหว่างสองหน้า (ก่อนยุบ)

| ด้าน | `/daily` (List) | `/daily/grid` (Grid) |
|---|---|---|
| โหลดข้อมูล | ฝัง `rows_json` ตอน render (cap 3,000) | AJAX `/api/daily/grid-data` (cap 800) |
| คอลัมน์ | 17 คอลัมน์สรุป — มี **linked name** (driver/plate/tail/customer ชื่อจริงจาก master) | ~38 คอลัมน์ดิบ — มี id, container, invoice, fuel station, source ฯลฯ |
| ช่องค้น | คนขับ + ทะเบียน แยกช่อง | `q` รวม (driver/plate/origin/destination/customer) |
| ตัวกรอง "ค่าที่ยังว่าง" (AD/U/any) | ❌ | ✅ |
| Ctrl+Enter เติมหลายแถว | ❌ | ✅ |
| Preset แดง "LCB ยังกรอกไม่ครบ" | ❌ | ✅ |
| localStorage key | `yk_daily_list_hidden_v1` | `yk_daily_grid_hidden_v3` |

## การตัดสินใจ (ยืนยันกับโอแล้ว)

1. **วิธีโหลด:** AJAX แบบ Grid
2. **คอลัมน์ default:** เริ่มแบบ Grid (ชุดเดิมของ grid)
3. **URL/เมนู:** เหลือ `/daily` เป็นหลัก; `/daily/grid` redirect มา `/daily` พร้อม query string
4. **ช่องค้น:** ใช้ `q` รวมอย่างเดียว (ไม่เก็บช่องคนขับ/ทะเบียนแยก — `q` ครอบคลุมกว่า + ยังมี Excel-filter รายคอลัมน์)

หลักการรวม: **ไม่ตัดฟีเจอร์ใด** เอาความสามารถของทั้งสองหน้ามารวม เลือก "ตัวที่ดีกว่า"
เฉพาะจุดที่ทับซ้อนกันตรง ๆ (วิธีโหลด, ช่องค้น)

## สถาปัตยกรรมหน้ารวม

- **ฐาน = `daily_grid.html`** ย้ายมาเสิร์ฟที่ route `/daily`
- ตั้งชื่อ template ใหม่เป็น `daily_grid.html` คงเดิม (หรือ rename ตามที่ plan ตัดสิน) — เสิร์ฟโดย handler `daily_list()` เดิม โดยเปลี่ยน TemplateResponse
- `daily_grid_page()` handler → เปลี่ยนเป็น **redirect 301** ไป `/daily` พร้อม forward query string
- ลบ `daily_list.html` หลังย้ายฟีเจอร์ที่ขาดเข้ามาครบ

### ฟีเจอร์จาก List ที่ต้องยกเข้ามา (ไม่ให้หาย)

**คอลัมน์ linked-name** — ชื่อจริงจาก master (ไม่ใช่ raw):
- `driver_name` (จาก Employee.full_name ผ่าน driver_id)
- `plate_no` (จาก Vehicle.plate_no ผ่าน head_vehicle_id)
- `tail_plate` (จาก Vehicle.plate_no ผ่าน tail_vehicle_id)
- `customer_name` (จาก Customer.name ผ่าน customer_id)

ต้องทำสองส่วน:
1. `/api/daily/grid-data` ส่งฟิลด์ทั้งสี่นี้เพิ่ม (resolve จาก master maps แบบที่ `daily_list()` ทำใน `_display_row`)
2. เพิ่มเข้า `ALL_FIELDS` ใน template เป็นคอลัมน์ **อ่านอย่างเดียว** (linked = แก้ raw ไม่ได้ตรง ๆ) ตั้งให้ **ซ่อน default**

### ฟีเจอร์จาก Grid ที่คงไว้ครบ (ไม่แตะ)

ตัวกรอง "ค่าที่ยังว่าง" (AD/U/any), Ctrl+Enter เติมหลายแถว, ปุ่มแดง "LCB ยังกรอกไม่ครบ",
คอลัมน์ดิบ ~38 ช่อง, subtotal mode, Excel-filter, column dialog + preset

### Preset คอลัมน์

รวมเป็นชุดเดียว: `basic / money / fuel / container / all`
(Grid มี fuel เพิ่มจาก List — ครอบคลุมทั้งคู่อยู่แล้ว ไม่ต้องเพิ่มอะไร)

### localStorage

รวมเป็น key เดียว: `yk_daily_hidden_v1`
(key เก่าทั้งสองตัวถูกทิ้ง — user จะกลับไปที่ default hidden ครั้งแรกหลัง deploy ซึ่งยอมรับได้)

## สิ่งที่ไม่แตะ

- `/api/daily/grid-save` (logic บันทึก/ตรวจ/ผูกเงิน) — ไม่แตะเลย
- `/api/daily/grid-data` query/filter logic (`_daily_grid_filters`) — ไม่แตะ logic เดิม เพิ่มแค่ฟิลด์ linked-name ใน response
- กฎเงิน/payroll/billing — งานนี้เป็น UI/route ล้วน ไม่กระทบตัวเลข

## จุดเสี่ยง / ตรวจย้อนกลับ

- เป็นงาน UI/route ล้วน **ไม่กระทบเงิน** — ไม่ต้อง preflight payroll
- ต้องตรวจ: route `/daily` แสดงผลแบบ grid ได้, `/daily/grid?...` redirect แล้ว query string ตามมาครบ,
  คอลัมน์ linked-name แสดงชื่อจริงถูก, Save ยังทำงาน, ตัวกรอง "ค่าที่ยังว่าง" + Ctrl+Enter + ปุ่มแดง LCB ยังครบ
- เมนู base.html: ลบรายการ "Daily Grid" ออก เหลือ "Daily" อันเดียว
- เช็คทุก template ที่ลิงก์ไป `/daily/grid` (เช่นปุ่มใน daily_list เดิม) — redirect รับได้อยู่แล้ว แต่ควรชี้ตรงเพื่อลด hop

## Out of scope

- ไม่ปรับ schema
- ไม่เพิ่มฟีเจอร์ใหม่ที่ไม่มีในสองหน้าเดิม
- ไม่แตะหน้า daily_form / daily_batch (ฟอร์มแก้รายแถว — ยังใช้ต่อ)
