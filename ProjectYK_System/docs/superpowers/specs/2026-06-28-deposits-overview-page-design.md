# เงินประกันตนรวม — Deposits Overview Page

**Date:** 2026-06-28
**Owner:** โอ (พงษกาญจน์)
**Route:** `/deposits`
**Status:** approved (design) → implementation

## Problem

เงินประกันตน (driver security deposit — เงินค้ำที่บริษัทหักสะสมจากคนขับ แล้วคืนตอนออก)
ปัจจุบันดูได้ทีละคนเท่านั้น (หน้าแก้ไขข้อมูลพนักงาน) ไม่มีหน้ารวมให้ตรวจสอบทั้งบริษัท
โอต้องการหน้ารวมที่ดูยอดคงเหลือทุกคน + แก้ยอดได้เลย + ดูประวัติการหักรายคนได้

## Data model (ตามที่มีอยู่ — ไม่สร้างใหม่นอกจาก audit)

แหล่งข้อมูลจริงของเงินประกันตน = **2 field บน Employee** (static):

| field | ความหมาย | default |
|-------|----------|---------|
| `employee.deposit_balance` | สะสมแล้ว (หักไปกี่บาทแล้ว) | 0.0 |
| `employee.deposit_target` | เพดาน (หักจนครบเท่าไหร่) | 10000.0 |

การหักรายรอบ บันทึกที่ `payrunitem.deposit_install` (หักรอบละ 1,000 จนครบเพดาน — logic ใน
`services/payroll.py:1159`). **ไม่แก้ logic นี้.**

### ข้อจำกัดข้อมูลที่ต้องสะท้อนในหน้า (สำคัญ)

- ตาราง `DriverDeposit` (models.py:228) มีนิยามไว้แต่ **ไม่เคยถูกเขียน/อ่าน** → ไม่ใช้
- ประวัติการหัก (`payrunitem.deposit_install > 0`) มีจริงแค่ **2 รอบ**: LCB 2026-05 (11 คน), LCB 2026-06 (9 คน) — รวม 12 คน
- แต่ `deposit_balance > 0` มี **48 คน** → ยอดสะสมของอีก ~36 คนถูกตั้งค่า/ลอกมา ไม่ได้หักผ่านระบบ
  (เพราะหลายไซต์ย้อนหลังลอกยอด net จากแบงค์ ไม่มีรายการหักแยก)
- **หน้าต้องบอกความจริงนี้** ไม่แกล้งโชว์ว่าประวัติครบ: หน้าประวัติรายคนแสดงส่วนต่าง
  (สะสมแล้ว − ผลรวมประวัติที่ระบบมี) เป็น "ยอดยกมา/ตั้งค่า ไม่ได้หักผ่านระบบ"

## Scope

หน้า `/deposits` ทำ 3 อย่าง (ตัวเลือก C + B ที่โออนุมัติ):

1. **ตารางรวมยอดคงเหลือ** ทุกคนที่มีเงินประกัน เรียงตามไซต์ + กรองตามไซต์
2. **แก้ยอดได้ในหน้า** (สะสมแล้ว/เพดาน) พร้อม audit log ทุกครั้ง
3. **ดูประวัติการหักรายคน** + เตือนข้อจำกัดข้อมูล

อ่าน-อย่างเดียวจาก `employee` + `payrunitem`; เขียนเฉพาะ `employee.deposit_balance/target`
(ผ่านปุ่มแก้) + INSERT `DepositAudit`. **ไม่แตะ logic payroll → ยอดเงินเดือนไม่เปลี่ยน.**

## Sections

### Section 1 — ภาพรวม + ตารางหลัก

**แถบสรุปบนสุด** (รวมตามไซต์ที่กรองอยู่):
- จำนวนคนที่มีเงินประกัน (นับคนที่ `deposit_target > 0`)
- ยอดสะสมรวม (Σ `deposit_balance`)
- ยอดที่ยังขาดอีกกว่าจะครบเพดานทุกคน (Σ max(0, target − balance))

**ตารางหลัก** — แถวต่อคน, เฉพาะคนที่ `deposit_target > 0`, เรียง `home_site_code, full_name`:

| คอลัมน์ | source |
|--------|--------|
| ชื่อ (กดดูประวัติ) | `full_name` |
| ไซต์ | `home_site_code` |
| สะสมแล้ว | `deposit_balance` |
| เพดาน | `deposit_target` |
| เหลืออีก | `max(0, target − balance)`; ถ้า ≤ 0 → "✓ ครบ" |
| สถานะ | progress bar + % (`balance/target`) |
| ✏️ | ปุ่มแก้ยอด |

ปุ่มกรองไซต์ `LCB / BIGC / AYU / ทั้งหมด` (querystring `?site=` แบบเดียวกับ `/employees`).

### Section 2 — แก้ยอด + ประวัติรายคน

**แก้ยอด** (`POST /deposits/{emp_id}/edit`):
- ฟอร์ม inline (HTMX) แก้ `deposit_balance`, `deposit_target` + ช่อง "เหตุผล" (optional)
- validate: ตัวเลข ≥ 0; ถ้าค่าไม่เปลี่ยน ไม่ INSERT audit
- เขียน `employee.deposit_balance/target` + INSERT `DepositAudit` หนึ่งแถวต่อ field ที่เปลี่ยน
- คืน partial ของแถวนั้น (refresh ตัวเลข + progress)

**ประวัติรายคน** (`GET /deposits/{emp_id}/history`):
- ลิสต์ `payrunitem` ที่ `employee_id = emp_id and deposit_install > 0`
  join `payrun` → แสดง (ไซต์, รอบ `pay_cycle_tag`, ยอดหัก)
- ผลรวมประวัติ = Σ deposit_install
- แถบเตือน: ส่วนต่าง = `deposit_balance − ผลรวมประวัติ`
  - ถ้า > 0: "ยอดยกมา/ตั้งค่า (ไม่ได้หักผ่านระบบ): X บาท — รอบที่ลอกยอดมาจะไม่มีรายการหักแยก"
  - ถ้า ≈ 0: ประวัติครบตามยอดสะสม
- รวมประวัติการ**แก้ยอด**ของคนนั้นจาก `DepositAudit` (ใครแก้ เมื่อไหร่ จาก→เป็น)

### Section 3 — เทคนิค

**Model ใหม่** (`models.py`) — mirror `DailyJobAudit`:
```python
class DepositAudit(SQLModel, table=True):
    """ประวัติการแก้ยอดเงินประกันตนในหน้า /deposits — INSERT-only."""
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    changed_by: str = ""
    field_name: str = ""        # deposit_balance | deposit_target
    old_value: str = ""
    new_value: str = ""
    reason: str = ""
```

**Schema:** bump `SCHEMA_VERSION` 27 → 28. ตารางใหม่ถูกสร้างอัตโนมัติโดย
`SQLModel.metadata.create_all(engine)` ใน `init_db()` — ไม่ต้องเขียน ALTER เอง.

**Routes ใหม่** (`main.py`):
- `GET  /deposits` → `deposits_list.html`
- `POST /deposits/{emp_id}/edit` → แก้ยอด + log, คืน row partial
- `GET  /deposits/{emp_id}/history` → partial/หน้า ประวัติรายคน

**Template ใหม่:** `templates/deposits_list.html` (+ row/history partial ตามสไตล์ HTMX ที่ใช้อยู่)
**เมนู:** เพิ่มลิงก์ "เงินประกันตน" ในเมนูหลัก (ที่เดียวกับ /employees, /payroll)
**`changed_by`:** ดึงจาก user ที่ login (เหมือน DailyJobAudit ใช้ในหน้า /daily).

## Testing

`app/tests/test_deposits.py`:
1. `GET /deposits` → 200, มีคนที่ deposit_target>0, ไม่มีคน target==0
2. summary: count/Σbalance/Σremaining ถูกต้องบน fixture เล็ก
3. กรอง `?site=LCB` → เฉพาะ LCB
4. `POST edit` เปลี่ยน balance → employee อัปเดต + DepositAudit 1 แถว (field=deposit_balance, old/new ถูก)
5. `POST edit` ค่าไม่เปลี่ยน → ไม่มี audit row ใหม่
6. `POST edit` ค่าติดลบ → reject (4xx), ไม่เขียน
7. history: ส่วนต่าง balance − Σdeposit_install คำนวณถูก (กรณีลอกยอด > ประวัติ)

## ตรวจย้อนกลับ (money safety)

- ก่อน/หลัง: ยอด net ของ payrun ทุกอันต้องเท่าเดิม (หน้านี้ไม่แตะ payroll engine)
- การแก้ยอด deposit ทุกครั้งมี DepositAudit → ตรวจได้ว่าใครแก้อะไรเมื่อไหร่
- snapshot `Σ deposit_balance` ก่อน deploy → เทียบหลัง deploy (ควรเท่าเดิมจนกว่าโอจะแก้)

## Out of scope

- ไม่ activate `DriverDeposit` ledger (แยกงาน ถ้าจะทำ ledger จริงค่อยคุยกัน)
- ไม่ย้อน backfill ประวัติการหักของรอบที่ลอกยอดมา
- ไม่แตะ logic การหัก 1,000/รอบ ใน payroll.py
