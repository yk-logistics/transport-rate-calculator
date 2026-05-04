# Petty Cash (สดย่อย) — Spec & Excel Mapping

## 1. สรุปเจตนา

โมดูลสดย่อยเป็น **Track A Quick Win** เพื่อให้แอดมินหยุดใช้ Excel สดย่อยและคีย์ในระบบแทน
ทุกแถวที่บันทึกจะไหลเข้า 2 ปลายทาง:

1. **รายงานรายจ่าย/รายรับประจำรอบ** — สรุปต้นทุนต่อไซต์
2. **คิวรอหักเงินคนขับ** (ถ้าติก `deduct_from_driver`) — ดึงเข้ารอบเงินเดือนอัตโนมัติ

## 2. Excel เดิม — Column Layout

ไฟล์ `data/Salary/{AYU|BigC|LCB}/สดย่อยวังน้อย.xlsx` มีหลาย sheet (Jan 20, Feb 20, ...) โดยโครงสร้างหลัก:

| คอลัมน์ Excel | ข้อมูล |
|---|---|
| วัน-เดือน-ปี | วันที่รายการ |
| ชื่อผู้เบิก | ชื่อคนขับ/ร้าน/บุคคล |
| รายการ | คำอธิบาย เช่น "ค่าทางด่วน 28/2", "ค่าน้ำมัน 71-0563" |
| รายรับ | เงินเข้าสดย่อย (เจ้าของโอนมา, ลูกค้าคืน) |
| รับเงินทอน | เงินทอนรับคืน |
| ยอดจ่าย | ยอดจ่ายออก |
| มีใบเสร็จ | ยอดส่วนที่มีใบเสร็จ |
| ไม่มีใบเสร็จ | ยอดส่วนที่ไม่มีใบเสร็จ |
| ซ่อมรถ | หมวดซ่อม |
| วางบิล Tops / สดย่อย CJ/Volvo | หมวดพิเศษต่อลูกค้า |
| น้ำมัน | หมวดน้ำมัน |
| ค่าจอด-เข้า AO | หมวดค่าจอด |
| ค่าลงของ | หมวดค่าลงของ |
| ค่าจ้าง | หมวดค่าจ้างพิเศษ |
| ค่าปรับ | หมวดค่าปรับ |
| รอ / ทอน หรือใบเสร็จ | ยอดค้างรอคืน |
| เงินสด | เงินสดที่ติดมือคนขับ |
| **พขร.เบิก หัก เงินเดือน** | ★ ยอดที่จะหักจากเงินเดือนคนขับ |
| คงเหลือ | ยอดสดย่อยคงเหลือหลังรายการ (running balance) |
| หมายเหตุ | หมายเหตุ |

คอลัมน์เปลี่ยนเล็กน้อยตามยุค (Aug 20 ย้ายคอลัมน์ลูกค้าจาก "Tops" → "CJ/Volvo")

## 3. Schema ใหม่: `PettyCashTxn`

ลดจาก 25 คอลัมน์ → **normalized form** 1 แถว = 1 รายการ โดยแยกหมวดเป็น field `category`

| Field | ตัวอย่าง | Excel origin |
|---|---|---|
| `txn_date` | 2026-02-28 | วัน-เดือน-ปี |
| `site_code` | BIGC | ไฟล์อยู่โฟลเดอร์ไหน |
| `direction` | out / in | ถ้ามีเลขในคอลัมน์ "รายรับ" → `in`, "ยอดจ่าย" → `out` |
| `amount` | 500 | ยอดจ่าย หรือ รายรับ |
| `requester_raw` | "ทองสุข" | ชื่อผู้เบิก |
| `driver_id` (FK) | 12 | matched กับ master เมื่อ parser run |
| `memo` | "ค่าทางด่วน 28/2" | รายการ |
| `category` | toll / fuel / repair / ... | เก็บตามคอลัมน์ที่มีเลข |
| `has_receipt` | true/false | มีใบเสร็จ > 0 |
| `deduct_from_driver` | true/false | "พขร.เบิก หัก เงินเดือน" > 0 |
| `deduct_amount` | 500 | ค่าในคอลัมน์นั้น |
| `deduction_status` | pending / deducted / waived | ตั้งต้น pending, เปลี่ยนตอนปิดรอบ payroll |
| `pay_cycle_tag` | 2026-02 | คำนวณอัตโนมัติจากไซต์+วันที่ |
| `linked_vehicle_plate_raw` | "71-0563" | regex หาในเมโม |
| `linked_vehicle_id` | FK | matched |
| `linked_daily_job_id` | FK | matched |
| `running_balance` | 3924 | คอลัมน์ "คงเหลือ" |
| `note` | - | หมายเหตุ |
| `status` | draft / posted / locked | ล็อกหลังปิดรอบ |
| `source` | manual / import | แยกของมือ/จาก Excel import |
| `parsed_confidence` | 0.0-1.0 | คะแนน parser (0.8+ = ล้าง posted, ต่ำ = ให้ admin ยืนยัน) |
| `parsed_payload_json` | - | เก็บ dict ที่ parser แกะได้ |

## 4. Category Mapping

```
Excel column with amount      → category
-----------------------------   -------------
ค่าปรับ                         → fine
น้ำมัน                           → fuel
ซ่อมรถ                          → repair
ค่าจอด-เข้า AO                   → parking
ค่าลงของ                         → loading
ค่าจ้าง                          → loading  (gru เดียวกันในระบบใหม่)
เมโมมี "ยาง"                    → tire
เมโมมี "ทางด่วน" / "mflow"      → toll
เมโมมี "เบิก" + หัก > 0          → driver_advance
เมโมมี "โอนเข้าสดย่อย"           → owner_transfer
เมโมมี "คืนประกันตน"             → deposit_refund
เมโมมี "เบิกเงินเดือน"           → salary_partial
เมโมมี "เคลม" / "อุบัติเหตุ"      → accident
default                          → other
```

## 5. Pay Cycle Tag (auto)

ฟังก์ชัน `_cycle_tag_for_site(site, date)` คืน `YYYY-MM` ของรอบที่ทรานแซคนั้นจะถูกหัก:

- **AYU** รอบ 26 → 25 ของเดือนถัดไป: ถ้าวันที่ ≥ 26 ใช้เดือนถัดไป ไม่งั้นใช้เดือนปัจจุบัน
- **BIGC** รอบ 1 → สิ้นเดือน: ใช้เดือนของวันที่นั้น
- **LCB** รอบ 16 → 15: ถ้าวันที่ ≥ 16 ใช้เดือนถัดไป ไม่งั้นใช้เดือนปัจจุบัน

ตัวอย่าง:
- AYU 2026-02-27 → `2026-03`
- BIGC 2026-02-15 → `2026-02`
- LCB 2026-02-20 → `2026-03`

## 6. UI Routes

- `GET /petty-cash` — ตารางรายการ + ฟิลเตอร์ (site, ช่วงวัน, คนขับ, หมวด, เฉพาะหัก)
- `GET /petty-cash/new` + `POST` — เพิ่มรายการใหม่
- `GET /petty-cash/{id}/edit` + `POST` — แก้ไข (ถ้า status ≠ locked)
- `POST /petty-cash/{id}/delete` — ลบ (ถ้า status ≠ locked)
- `GET /petty-cash/pending` — **สรุปรอหักต่อคนขับ** (filter ด้วย cycle + site)

## 7. Lock Policy

- สถานะ `locked` ตั้งเมื่อ payroll รอบนั้น ๆ ปิดแล้ว → ป้องกันแก้ไขข้อมูลประวัติ
- ต้องเปิดสิทธิ์ Manager ขึ้นไปเพื่อ unlock (จะทำใน phase RBAC)

## 8. อัปเดต 2026-04-08 — ผลลัพธ์ Track A หลัง Q&A รอบ 2

### A3 Parser + A4 Import — **เสร็จแล้ว**
สคริปต์ `tools/import_petty_cash.py`:
- สแกน 3 ไฟล์ใน `data/Salary/{AYU,BigC,LCB}/สดย่อยวังน้อย.xlsx` → พบว่าเป็น **ไฟล์เดียวก๊อปใส่ 3 โฟลเดอร์**
  (47,054 / 47,484 unique records ซ้ำทั้ง 3 ไฟล์ = 99.1%)
- ระบบจึงเลือก **ไฟล์ที่ mtime ล่าสุด** เป็น canonical แล้ว import เพียงครั้งเดียว
- ตั้ง `site_code = ""` (unassigned) เพราะไฟล์เดียวครอบคลุมทั้ง 3 ไซต์
- parser แกะ `category` จาก: (1) คอลัมน์หมวดที่มีเลข (2) keyword ใน memo
  (3) ถ้ามี `deduct_amt > 0` และไม่ตรง keyword → `driver_advance`
- extract plate number จาก memo ด้วย regex (`\d{2}-\d{4}`, `[ก-ฮ]{1,3}\d+`)

**ผลรัน (2026-04-08):**
| Metric | Value |
|---|---|
| Sheets scanned | 80 |
| Rows imported | 50,753 |
| With driver deduction | 17,458 (34.4%) |
| With pending clearance | 312 |
| Plate extracted | 15,705 (30.9%) |
| Date range | 2019-12-14 → 2026-06-14 |
| Total OUT | 313,021,880 THB |
| Pending deductions | 22,141,100 THB |

### A6 Payroll lock — ยังไม่ทำ
hook ตอนปิดรอบเงินเดือน → update `status=locked` + `deduction_status=deducted`
(จะพัฒนาเมื่อเริ่ม Payroll module)

## 9. การตัดสินใจหลัง Q&A

### Q1 — เบิกข้ามรอบ
- **`txn_date`** = ข้อเท็จจริง (เก็บไว้ไม่แก้) / **`pay_cycle_tag`** = intent (แก้ได้)
- ใน form: default จาก auto (fetch `/api/cycle-tag`) + ปุ่ม `auto` / `+1 เดือน` / พิมพ์เอง
- ใน list: badge `"ย้ายจาก 2026-03"` ถ้า override
- เมื่อ Payroll มี `PayrollCycleLock`: block การบันทึก txn ที่เลือกรอบปิดแล้ว

### Q2 — ปุ่ม "ปิดรอบ"
- **อยู่ที่หน้า Payroll** (คอนเฟิร์มตามความคิดผู้ใช้)
- Action: ตั้ง `status=locked` และ `deduction_status=deducted` ให้ทุก txn ของรอบนั้น
- Petty cash side มีแค่ lock guard (status==locked → แก้ไม่ได้)

### Q3 — Flexible categories
- เก็บเป็น **2-tier** (ยังไม่ implement ใน phase นี้):
  - **System categories** (14 อัน ปัจจุบัน): ผูก feature จริง (fuel→FuelTxn, repair→MaintenanceLog, accident→AccidentCase)
  - **Custom categories** (แอดมินเพิ่มเอง): label-only, ไม่ auto-link
- UI แสดงแยกกลุ่ม `[ระบบ]` vs `[กำหนดเอง]`

### Q4 — "รอ/ทอน" tracking — **ทำแล้ว**
เพิ่ม 3 field ใน `PettyCashTxn` (schema v4):
- `pending_amount` (float) — ยอดค้าง (รอใบเสร็จ/ทอน)
- `pending_note` (str) — คำอธิบาย เช่น "รอใบเสร็จ 200"
- `pending_cleared_at` (date|None) — null = ยังค้าง
+ หน้าใหม่ **`GET /petty-cash/clearance`** — list สีแดง/เหลืองตามอายุของค้าง + ปุ่ม "เคลียร์แล้ว"

## 10. Site Assigner — ยังไม่ทำ (หลัง Employee master มีข้อมูล)

`tools/assign_petty_site.py` (วางแผน):
1. อ่าน `PettyCashTxn` ที่ `site_code=""`
2. จับคู่ `requester_raw` กับ `Employee.full_name` (normalized match)
3. ถ้าจับคู่ได้ → ตั้ง `site_code = employee.home_site_code` + `driver_id = employee.id`
4. ถ้าเจอหลายคนชื่อเหมือนกันข้ามไซต์ → flag ให้ admin ยืนยัน
5. รายงาน hit-rate ต่อไซต์

## 11. งานต่อหลัง Phase A

- A6. Payroll lock hook
- B. Daily Excel import (FuelTxn, Daily rows)
- Assigner: Petty cash → site/driver link
