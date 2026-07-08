# Tire Tracking — "หยุดเลือด" (Stop the Bleed) — Design Spec

**วันที่:** 2026-07-08
**โมดูล:** OnePlatformApp (`ProjectYK_System/app/`)
**เจ้าของโดเมน:** โอ (พงษกาญจน์)
**สถานะ:** design — รออนุมัติก่อนเขียน plan

---

## 1. ปัญหา (Problem)

ค่ายางเดือนที่แล้วเกือบ **200,000 บาท** ไม่มีใครรู้ว่ายางเส้นไหนเปลี่ยนเมื่อไหร่ ทำไมถึงเปลี่ยน หรือยางแบบไหน (หล่อ vs แท้) คุ้มกว่ากัน — ตัดสินใจสั่งยางแบบไม่มีข้อมูล

โครงสร้างระบบยางมีอยู่แล้วครบ (`Tire`, `TireEvent`, event engine `_apply_tire_event`, Quick Setup grid, ตำแหน่งยางจริงของ YK รวมหางพ่วง 8 ล้อ) แต่ **มีข้อมูล 0 แถว** — เครื่องมือพร้อมแต่ไม่มีใครกรอกเข้า จึงวิเคราะห์อะไรไม่ได้

### เป้าหมายที่โอเลือก (จาก brainstorm)
1. **หยุดเลือด — รู้ว่าเงิน 200k หายไปไหน** (โฟกัสหลักที่โอเลือก)
2. เทียบ **ยางหล่อ vs ยางแท้** ว่าแบบไหนอยู่ทน/คุ้มกว่า

### ข้อเท็จจริงหน้างาน (จาก brainstorm — กำหนดดีไซน์)
- **บิลค่ายาง = กระดาษ/รูปถ่าย** ยังไม่ดิจิทัล
- **เลขไมล์ (odometer): มีบ้างไม่มีบ้าง** — บางคันรู้ บางคันไม่รู้ → ระบบต้องรองรับทั้งคิดเป็น "กิโล" และคิดเป็น "เดือน" **ห้ามบังคับกรอกเลขไมล์**
- **คนกรอก = ธุรการคีย์เข้าทีหลังจากคอมพิวเตอร์** (ไม่ใช่ช่างหน้างานผ่านมือถือ)

---

## 2. ขอบเขต (Scope)

### จงใจ "ไม่ทำ" (กัน over-engineer — YAGNI)
- ❌ **ไม่ทำ PWA ช่าง / ไม่ทำ OCR บิล** — โอยืนยันธุรการคีย์เข้าทีหลังจากคอม
- ❌ **ไม่บังคับเลขไมล์** — คันมีคิดเป็นกิโล คันไม่มีคิดเป็นเดือน ระบบไม่พังเมื่อข้อมูลไม่ครบ
- ❌ **ไม่แตะ payroll/cycle** — ค่ายางเข้า `MaintRecord` ตามทางเดิม ไม่ยุ่งรอบเงินเดือน
- ❌ **ไม่รื้อ event engine เดิม** — ต่อยอด `_apply_tire_event` เท่านั้น (mount/unmount/rotate/retread/scrap/inspect ทำงานถูกอยู่แล้ว รวม auto-unmount ยางที่อยู่ตำแหน่งเดิม)

### ทำ 3 ชิ้น
| # | ชิ้น | ตอบโจทย์ |
|---|------|----------|
| A | เก็บ **เหตุผล (reason)** + **ประเภทยาง (หล่อ/แท้)** ตอนถอด/ทิ้ง/ติดตั้ง | ติดตามว่าเกิดเหตุอะไร + เตรียมข้อมูลเทียบหล่อ/แท้ |
| B | **หน้าคีย์บิลยางเร็ว** (ธุรการ) — ฟอร์มเดียวจบ | เก็บบิลกระดาษเข้าระบบให้เร็ว ไม่ค้าง |
| C | **หน้ารายงานความคุ้ม** (dashboard ยาง) | รู้เงินหายไปไหน + เทียบหล่อ/แท้ (บาท/กิโล, บาท/เดือน, อายุ) |

---

## 3. Schema changes (SCHEMA_VERSION 47 → 48)

ตอนนี้ `tire` / `tireevent` = 0 แถว → เพิ่มคอลัมน์ปลอดภัย 100% ใช้ helper `_ensure_column(...)` (pattern เดิมใน `_apply_additive_migrations`, SQLite ALTER ADD COLUMN — non-destructive; PostgreSQL ใช้ create_all/ALTER ตามทางเดิม).

### 3.1 `Tire` — เพิ่ม 2 คอลัมน์
```python
tire_type: str = Field(default="new", index=True)
#   new     = ยางใหม่/ยางแท้ (ซื้อใหม่)
#   retread = ยางหล่อดอก
#   used    = ยางมือสอง
# ใช้แยกต้นทุน/อายุ หล่อ vs แท้. สอดคล้อง retread_count เดิม (retread_count>0 → เคยหล่อ)

removal_reason: str = Field(default="", index=True)
#   เหตุที่ถอด/ทิ้งครั้งล่าสุด (สำเนาไว้ที่ตัว Tire เพื่อ query เร็ว)
#   ค่า = ตาม TIRE_REMOVAL_REASONS ด้านล่าง
```

### 3.2 `TireEvent` — เพิ่ม 1 คอลัมน์
```python
reason_code: str = Field(default="", index=True)
#   เหตุของ event (โดยเฉพาะ unmount/scrap): burst|wire|worn|bulge|puncture|retread_send|rotate_plan|damage|other
```

### 3.3 constants ใหม่ใน `models.py`
```python
TIRE_TYPES = (
    ("new",     "ยางแท้ (ซื้อใหม่)"),
    ("retread", "ยางหล่อดอก"),
    ("used",    "ยางมือสอง"),
)

TIRE_REMOVAL_REASONS = (
    ("burst",        "ยางระเบิด"),
    ("wire",         "ลวดโผล่/ผ้าใบขาด"),
    ("worn",         "ดอกหมด/หมดสภาพ"),
    ("bulge",        "บวม/ปูด"),
    ("puncture",     "ตำ/รั่ว ซ่อมไม่ได้"),
    ("retread_send", "ส่งหล่อดอก"),
    ("rotate_plan",  "สลับตามแผน (ยังใช้ได้)"),
    ("damage",       "เสียหายอื่น (บาด/ฉีก)"),
    ("other",        "อื่น ๆ"),
)
```
> **หมายเหตุ:** `TIRE_CONDITION_FLAGS` เดิม (ok/near/problem) = รายงานสภาพจากคนขับ/ช่าง — คนละความหมายกับ `removal_reason` (เหตุที่ถอดจริง) เก็บทั้งคู่ไว้ ไม่ทับกัน

---

## 4. ชิ้น B — หน้าคีย์บิลยางเร็ว (`/maint/tires/bill`)

**ผู้ใช้:** ธุรการ นั่งคอม มีกองบิลกระดาษ
**หลักการ:** *กรอกครั้งเดียว สร้างทุกอย่างให้อัตโนมัติ* — 1 บิล = 1 submit → สร้าง Tire ใหม่ + mount event (พร้อม reason) + MaintRecord (ค่าใช้จ่าย) + ผูก vendor. ถ้ามียางเส้นเก่าที่ถอดออก → unmount event พร้อม removal_reason.

### 4.1 ฟอร์ม (หน้าเดียว)
**หัวบิล (กรอกครั้งเดียวต่อบิล):**
- รถคันไหน (dropdown plate) *— บังคับ*
- วันที่ทำ *— บังคับ, default วันนี้*
- ร้านยาง (Vendor kind=tire; dropdown + ปุ่ม "+ ร้านใหม่" inline)
- เลขไมล์รถ *(ไม่บังคับ — ว่างได้)*
- เลขที่บิล/ใบเสร็จ (receipt_ref)
- จ่ายโดย: เงินสด/เครดิต/สดย่อย/หักคนขับ (`MAINT_PAID_BY` เดิม)

**รายการยางที่เปลี่ยน (ทำซ้ำได้หลายแถว — JS add-row):**
ต่อ 1 เส้น:
- ตำแหน่ง (dropdown จาก `_tire_positions_for_vehicle(v)` ของรถที่เลือก — โหลดผ่าน HTMX เมื่อเลือกรถ)
- ประเภท: ยางแท้ / ยางหล่อ / มือสอง (`tire_type`)
- ยี่ห้อ / รุ่น / สเปค / ซีเรียล (ยี่ห้อ+รุ่นพอ, ที่เหลือ optional)
- ราคา/เส้น
- ดอกยาง mm (optional)
- **เหตุที่เปลี่ยนเส้นเดิม** (`removal_reason` dropdown) — ระเบิด/ลวดโผล่/ดอกหมด/…

### 4.2 Server logic (route `POST /maint/tires/bill`)
1. สร้าง `MaintRecord(kind="tire_change", ...)` — vendor, work_date, mile_snapshot, paid_by, receipt_ref, mechanic_name(ว่างได้)
2. ต่อแต่ละแถวยางใหม่:
   - ถ้ามียางเก่าที่ตำแหน่งนั้นบนรถ → `_apply_tire_event(old, event_type="unmount", reason_code=removal_reason, ...)` (ตั้ง `old.removal_reason`)
   - สร้าง `Tire(tire_type=..., status="new", ...)` → `_apply_tire_event(new, event_type="mount", to_vehicle_id, to_position, ...)`
   - สร้าง `MaintPart(maint_record_id, tire_id=new.id, qty=1, unit_price=ราคา, total=ราคา)`
3. `parts_cost = Σ MaintPart.total`; `total_cost = parts_cost + labor + other`
4. ถ้า paid_by=petty_cash → ผูก `linked_petty_cash_id` ตาม pattern MaintRecord เดิม (`_apply_maint_form` มี logic นี้อยู่ — reuse ให้มากที่สุด)
5. อัปเดต `Vehicle.current_mile` ถ้ากรอกไมล์ (ตามที่ comment ใน model ระบุว่า MaintRecord เป็นตัวอัปเดต)

> **หลักการ reuse:** อย่าเขียน MaintRecord creation ใหม่ทั้งก้อน — เรียก `_apply_maint_form`/helper เดิมถ้าทำได้ แล้วเสริมเฉพาะส่วนผูกยาง. `_apply_tire_event` ต้องรับ `reason_code` เพิ่ม (เพิ่ม kwarg, default "" — ไม่กระทบ caller เดิม 2 จุด: office route + mechanic magic-link).

### 4.3 หลังบันทึก
redirect → `/maint/tires/by-vehicle/{vehicle_id}` (เห็นผังยางล่าสุดของคันนั้นทันที) + flash "บันทึกบิลแล้ว: เปลี่ยน N เส้น รวม X บาท"

---

## 5. ชิ้น C — หน้ารายงานความคุ้ม (`/maint/tires/report`)

ตอบ 3 คำถามเงินของโอ ในหน้าเดียว เลือกช่วงเดือนได้ (default เดือนปัจจุบัน).

### 5.1 การ์ดสรุปหัวหน้า (ตอบ "เงินหายไปไหน")
- ค่ายางรวมช่วงที่เลือก (Σ MaintRecord kind=tire_change total_cost)
- จำนวนเส้นที่เปลี่ยน / จำนวนครั้ง
- เฉลี่ยบาท/เส้น
- **เทียบเดือนก่อนหน้า** (เดือนนี้ vs เดือนที่แล้ว — ขึ้น/ลง กี่ %)

### 5.2 ตาราง "เหตุที่เปลี่ยน" (ตอบ "เกิดเหตุอะไร")
group by `removal_reason`: ระเบิด X เส้น (คิดเป็น Y บาท), ดอกหมด …, ลวดโผล่ … เรียงมาก→น้อย
→ เห็นทันทีว่าเงินหมดไปกับ "ยางระเบิด" (ปัญหาคุณภาพ/แรงดัน) หรือ "ดอกหมด" (สึกตามปกติ)

### 5.3 ตารางรายคัน (ตอบ "คันไหนกินยาง")
ต่อรถ: จำนวนเส้นเปลี่ยน / ค่ายางรวม / เหตุเด่น → คันไหนเปลี่ยนบ่อยผิดปกติ (อาจช่วงล่างเสีย/ศูนย์ล้อเพี้ยน ไม่ใช่ยางไม่ดี)

### 5.4 ตารางเทียบ **หล่อ vs แท้** (ตอบคำถามหลัก)
สำหรับยางที่ **ถอด/ทิ้งไปแล้ว** (มี mount event + unmount/scrap event → คำนวณอายุได้):

| ประเภท | จำนวนเส้น(เลิกใช้) | อายุเฉลี่ย (วัน) | กิโลเฉลี่ย* | ราคาเฉลี่ย/เส้น | **บาท/เดือน** | **บาท/1,000กม.*** |
|--------|--------------------|-----------------|-------------|-----------------|---------------|--------------------|
| ยางแท้ | … | … | … | … | … | … |
| ยางหล่อ| … | … | … | … | … | … |

- **อายุ (วัน)** = unmount/scrap event_date − mount event_date
- **กิโล** = unmount.mile − mount.mile *(เฉพาะเส้นที่มีเลขไมล์ทั้ง 2 จุด; เส้นไม่มีไมล์ = ไม่นับในคอลัมน์กิโลแต่ยังนับในคอลัมน์อายุ)*
- **บาท/เดือน** = ราคา ÷ (อายุวัน/30)
- **บาท/1,000กม.** = ราคา ÷ (กิโล/1000)
- แสดงจำนวน sample กำกับ (เช่น "จาก 12 เส้น") — เตือนถ้า sample น้อย < 5 ว่า "ข้อมูลยังน้อย"

> **ความจริงที่ต้องยอมรับ:** ตารางนี้จะ "ว่าง" จนกว่าจะมียางครบวงจร (ติดตั้ง→ถอด) อย่างน้อยสองสามเส้น. เดือนแรกจะเห็นแค่ 5.1–5.3 (ค่าใช้จ่าย+เหตุ). ค่าเทียบหล่อ/แท้ทยอยแม่นขึ้นเมื่อข้อมูลสะสม — เป็นเรื่องปกติ ไม่ใช่บั๊ก.

### 5.5 gotcha การคำนวณ
- ยางที่ยัง in_use (ยังไม่ถอด) → ไม่เข้าตารางเทียบ (ยังไม่จบวงจร) แต่แสดงแยกเป็น "ยางที่ยังวิ่งอยู่ + อายุถึงวันนี้" ได้ (optional, ถ้าเวลาพอ)
- เส้นที่ retread แล้วกลับมาวิ่ง = ถือเป็น tire_type=retread ในรอบชีวิตถัดไป (retread_count เดิมเก็บจำนวนครั้ง)

---

## 6. เมนู / navigation

`/maint` (maint_dashboard.html) มีการ์ดยางอยู่แล้ว — เพิ่มลิงก์ 2 ปุ่ม:
- "📋 คีย์บิลยาง" → `/maint/tires/bill`
- "📊 รายงานความคุ้มยาง" → `/maint/tires/report`

ไม่เพิ่มเมนูระดับบนสุด (อยู่ใต้ Maintenance ตามโครงเดิม).

---

## 7. ไฟล์ที่แตะ

| ไฟล์ | แก้อะไร |
|------|---------|
| `models.py` | +2 คอลัมน์ Tire, +1 คอลัมน์ TireEvent, +2 constant tuples |
| `main.py` | SCHEMA_VERSION→48; `_ensure_column` × 3 ใน `_apply_additive_migrations`; `_apply_tire_event` รับ `reason_code`; route `GET/POST /maint/tires/bill`; route `GET /maint/tires/report`; ลิงก์ใน /maint |
| `templates/tire_bill.html` | **ใหม่** — ฟอร์มคีย์บิล (HTMX โหลดตำแหน่งตามรถ + JS add-row) |
| `templates/tire_report.html` | **ใหม่** — dashboard 4 การ์ด/ตาราง |
| `templates/maint_dashboard.html` | +2 ปุ่มลิงก์ |
| `tests/test_tire_bill_report.py` | **ใหม่** — pytest ครอบเกณฑ์ข้อ 2–5 |

**ไม่แตะ:** payroll, finance, daily grid, billing, cycle logic, event engine เดิม (แค่เพิ่ม kwarg)

---

## 8. เกณฑ์ผ่าน (Success Criteria)

1. **Migration:** แอปเริ่มด้วย SCHEMA_VERSION=48 บน DB เดิมได้โดยไม่ error; คอลัมน์ใหม่ปรากฏใน `tire`/`tireevent` (ตรวจ PRAGMA table_info)
2. **คีย์บิล end-to-end:** กรอกบิลจำลอง (รถ 1 คัน, เปลี่ยน 2 เส้น: 1 แท้ 1 หล่อ, เหตุ=ระเบิด+ดอกหมด, ราคา, ไม่กรอกไมล์) → กด submit → เกิด: Tire 2 แถว (tire_type ถูก), TireEvent mount 2 + reason_code, MaintRecord 1 (kind=tire_change, total ถูก), MaintPart 2 ผูก tire_id → เห็นบน `/maint/tires/by-vehicle/{id}`
3. **คีย์บิลที่มีไมล์ + ยางเก่าถูกถอด:** เปลี่ยนยางตำแหน่งที่มีเส้นเก่าอยู่ → เส้นเก่าได้ unmount event + removal_reason + status=stored/scrapped; เส้นใหม่ mount แทน
4. **รายงาน:** `/maint/tires/report` แสดงค่ายางรวมถูกต้อง (ตรงกับ Σ ที่คีย์), ตารางเหตุ group ถูก, ตารางหล่อ/แท้คำนวณ บาท/เดือน + บาท/กิโล ถูกสำหรับเส้นที่ถอดแล้ว, เส้นไม่มีไมล์ไม่ทำให้ทั้งตารางพัง (คอลัมน์กิโลว่างเฉพาะเส้นนั้น)
5. **ไม่บังคับไมล์:** คีย์บิลโดยไม่กรอกเลขไมล์ได้สำเร็จทุกกรณี
6. **แอปยังรันได้:** `start.bat` เปิดได้, หน้าอื่นไม่พัง (smoke test /maint, /maint/tires, /finance)
7. **pytest เขียว:** ชุดเดิม 545 tests ยังผ่าน + เพิ่มไฟล์ทดสอบใหม่ `tests/test_tire_bill_report.py` ครอบเกณฑ์ข้อ 2–5 (คีย์บิลสร้าง object ครบ, unmount เส้นเก่า, รายงาน aggregate ถูก, ไม่มีไมล์ไม่พัง) — รัน `pytest -q` ผ่านทั้งหมด

---

## 9. Verify / preflight

- **pytest ก่อน:** รัน `pytest -q` เห็นชุดเดิมเขียวก่อนแก้ (baseline) — conftest ใช้ throwaway SQLite reset schema ต่อ test เอง ไม่แตะ DB จริง
- **ก่อน migrate DB จริง:** ยืนยัน `SELECT COUNT(*) FROM tire` = 0 และ `tireevent` = 0 บน `app.db` (ปลอดภัยที่จะ ALTER; ถ้า > 0 ให้หยุดทบทวน default)
- **หลัง migrate:** `PRAGMA table_info(tire)` เห็น tire_type, removal_reason; `PRAGMA table_info(tireevent)` เห็น reason_code
- **ตรวจย้อนกลับเงิน:** ค่ายางที่คีย์เข้า = MaintRecord kind=tire_change → ต้องโผล่ใน `/finance/vehicles` (ค่าใช้จ่ายต่อรถ) และไม่รั่วเข้ารอบ payroll (kind=tire_change ไม่ใช่ deduction ของคนขับ เว้นแต่ paid_by=deduct_driver ซึ่งเป็น flow เดิมของ MaintRecord)
- **เกณฑ์การเงินหลัก:** ตรงกับ success criteria ข้อ 2, 4 — Σ MaintPart.total = MaintRecord.parts_cost = ยอดบิลที่ธุรการคีย์; รายงานรวมต้องเท่ากับผลรวมที่คีย์เป๊ะ (reconcile ในเทสต์)

---

## 10. Handoff note (สำหรับโมเดลเล็กทำต่อ)

งานนี้ mechanical เป็นส่วนใหญ่ (schema additive + 2 route + 2 template) **ยกเว้นตรรกะการเงินใน route คีย์บิล (ชิ้น B ข้อ 4.2)** ที่ต้อง reuse MaintRecord/petty ให้ถูก — จุดนั้นตัวหลักตรวจ diff เอง. ตารางเทียบหล่อ/แท้ (5.4) เป็นแค่ SQL aggregate + คณิตหาร ไม่แตะเงินจริง มอบให้ Sonnet เขียนได้ แล้วตัวหลัก verify ตามเกณฑ์ข้อ 8.4.
