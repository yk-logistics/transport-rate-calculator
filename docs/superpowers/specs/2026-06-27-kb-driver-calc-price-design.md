# KB (ใต้โต๊ะ) + ราคาคำนวณคนขับ — แยกราคาวางบิลจริง ออกจากราคาที่คิดเงินคนขับ

วันที่: 2026-06-27
Branch: `feat/kb-driver-calc-price` (ยังไม่สร้าง — implement บน branch แยก ไม่ทำบน main)
สถานะ: design approved (โอ ยืนยัน 2026-06-27 ผ่าน /grill-me)

## ปัญหา

ราคาที่ "วางบิลลูกค้า" กับราคาที่ "ใช้คิดเงินคนขับ" บางครั้งไม่เท่ากัน แต่ระบบ
ปัจจุบันมีตัวเลขเดียวคือ `DailyJob.revenue_customer` ทำให้คนขับ (โดยเฉพาะระบบเหมา
ที่เงินผูกกับราคาขนส่งโดยตรง) คิดเงินผิด สาเหตุที่ทำให้ 2 ราคาต่างกันมี 2 แบบ:

1. **KB (ใต้โต๊ะ / commission)** — ค่าคอมมิทชั่นที่จ่ายให้ "คนจ่ายงาน" ฝั่งลูกค้า
   เราวางบิลลูกค้าเต็ม แต่ส่วน KB เป็นเงินที่ส่งต่อ (เราเก็บไว้ 10% + ออกใบหัก ณ
   ที่จ่าย 3% ที่เหลือจ่ายคนจ่ายงาน) → ไม่ใช่รายได้จริงของเรา และต้องไม่ปนเข้า
   ฐานคิดเงินคนขับ
   - NHL = 110 บาท/ตู้ ทุกตู้ (คงที่)
   - MOL = 100 บาท/ตู้ ทุกตู้ (คงที่)
   - CY = ไม่คงที่ (200–900 แล้วแต่คนจ่ายงานเก็บได้) — **มี KB ทุกเที่ยว** กรอกเอง

2. **ราคากลาง / over-market override** — บางงานเราวางบิลเกินราคาตลาดได้ แต่คนขับ
   ระบบเหมาต้องคิดจาก "ราคากลาง" ไม่ใช่ราคาที่วางบิลจริง
   - ตัวอย่างหลัก: ลูกค้า DHL Overflow — ราคาคนขับ (ก่อนหัก 60%) = 5,500 = ราคากลาง
     แม้วางบิลลูกค้าจริงจะมากกว่า

### ground truth (จาก app.db, ปัจจุบัน)

- `Customer` table = ว่าง (0 แถว), `customer_id` = NULL ทุกแถว → **ชื่อลูกค้าอยู่ใน
  ช่อง `status_code`** (ตรงกับช่อง "Status" ในไฟล์ LCB)
- `status_code` distinct (LCB): `KLND 229, รถจอด 190, NHL 161, KAO 111,
  DHL Overflow 111, WHALE 84, CJ 78, ลา/ไม่พร้อม 32, CY 23, รถอุบัติเหตุ 17,
  DHL 14, ...` — ปนทั้งชื่อลูกค้าและสถานะรถจอด/ลา/ซ่อม
- NHL: 1 แถว = 1 `container_no` → KB เป็นยอด **ต่อแถวแบบแบน** (110) ไม่ต้องคูณจำนวนตู้
- DHL Overflow: `revenue_customer=5500, trip_fee_driver=0` ปัจจุบัน → ฐานคนขับ
  ไม่ไหลเข้าเงินถูกต้อง (นี่คือบั๊กที่ต้องแก้)

## นโยบายที่โอยืนยัน (money rule — อย่าเดา)

1. **เก็บ KB เป็นตัวเลขได้** เพราะผูกกับต้นทุนจริง/รายงาน ไม่ใช่แค่กันออกจากเงินคนขับ
2. **สูตรราคาคนขับ:**
   ```
   base = price_override  ถ้าตั้งไว้  มิฉะนั้น = revenue_customer
   driver_calc_price = base − kb_amount
   ```
   - override **แทน** ราคาฐาน, KB **หักจากฐานเสมอ** — ซ้อนกันได้ (override−KB จริง)
   - `price_override` ใช้ **เฉพาะเมื่อราคาวางบิลจริง ≠ ราคากลาง** เท่านั้น ถ้าวันนี้
     `revenue_customer` บังเอิญเท่าราคากลางอยู่แล้ว (เช่น DHL Overflow ที่
     `revenue_customer=5500`) → **ไม่ต้องตั้ง override**, ปล่อย None, ฐาน=5,500 ตรง
     KB=0 → driver_calc=5,500; ถ้าวันหน้าวางบิลเกิน 5,500 ค่อยตั้ง override=5500
3. **KB auto-fill จาก rule ต่อ `status_code`** + แก้มือต่อแถวได้
   - NHL → default 110, MOL → default 100
   - CY → **required = true, default ว่าง**: ถ้าแถว CY ไม่มี KB → **เตือน** (ไม่บล็อก)
     ข้อความประมาณ "แถว CY นี้ไม่มี KB — ไม่มีจริงใช่ไหม?" กันลืม
   - status ที่เป็นรถจอด/ลา/ซ่อม/อุบัติเหตุ → ไม่มี rule, ไม่มี KB
4. **10%/WHT 3% ไม่เก็บเป็น field** — เก็บแค่ `kb_amount`; รายงานคำนวณสดจาก config
   คงที่ (`KB_OUR_CUT=0.10`, `KB_WHT=0.03`): เราเก็บ=KB×10%, WHT=KB×3%,
   จ่ายคนจ่ายงาน=KB×87%
5. **Payroll ใช้ `driver_calc_price`** ทุกที่ที่เดิมอ่าน `revenue_customer` เพื่อ
   คิดเงินคนขับ (รวม ratio ของ `lcb_mixed`); ฝั่งวางบิล/P&L ลูกค้า ยังใช้
   `revenue_customer` (วางบิลจริง)
6. **Recompute ย้อนหลังได้ แต่ต้องมี preflight** โชว์ net เปลี่ยนต่อคนให้โอเซ็นก่อน
   — ไม่ silently re-run run ที่ finalize แล้ว (ตรงกฎ [LCB driver extra fees])
7. **Visibility:** คอลัมน์ KB + ราคาคนขับ โชว์ใน `/daily` ให้ **แอดมินทุกคน** (หางาน/
   วางบิล/ผู้บริหาร); **Driver PWA: ไม่โชว์ KB** — คนขับเห็นแค่ยอดเงินตัวเอง

## Data model

### DailyJob — เพิ่ม 2 column จริง (bump SCHEMA_VERSION + ALTER ใน lifespan())

| field | type | ความหมาย |
|-------|------|----------|
| `kb_amount` | float = 0.0 | KB ต่อแถว/ตู้ (seed จาก rule, แก้มือได้) |
| `price_override` | Optional[float] = None | ราคากลางที่ตั้งเอง; None = ไม่ override |

- `revenue_customer` (มีอยู่แล้ว) = ราคาวางบิลจริง — **ไม่แตะความหมายเดิม**
- `driver_calc_price` = **คำนวณสด ไม่เก็บเป็น column** (lazy, ไม่มี field ซ้ำซ้อน)
  - มีฟังก์ชัน/helper เดียวคืนค่า `driver_calc_price(row)` ให้ payroll + template ใช้ร่วม

### KB rule — ตารางเล็ก keyed by status_code

```
class KbRule(SQLModel, table=True):
    id: Optional[int] = primary_key
    status_code: str = unique index   # 'NHL' | 'MOL' | 'CY' | ...
    default_kb: float = 0.0           # 110 / 100 ; CY = 0.0
    required: bool = False            # CY = True → trigger คำเตือนถ้า kb=0
    note: str = ""
```
seed เริ่มต้น: NHL(110,req=F), MOL(100,req=F), CY(0,req=T)

## สูตรกลาง (helper เดียว ใช้ร่วมทุกที่)

```python
def driver_calc_price(row) -> float:
    base = row.price_override if row.price_override is not None else (row.revenue_customer or 0.0)
    return round(base - (row.kb_amount or 0.0), 2)
```
- payroll `_classify_lcb_days` ratio เปลี่ยนเป็น `trip_fee_driver / driver_calc_price`
- ที่อื่นใน `payroll.py` ที่ sum `revenue_customer` เพื่อฐานคนขับ → ใช้ helper นี้
- finance/billing ที่เป็นฝั่งลูกค้า → **คงเดิม** ใช้ `revenue_customer`

## UI

### /daily grid (admin)
- เพิ่ม 2 คอลัมน์ข้างๆ revenue: **KB** | **ราคาคนขับ** (driver_calc, read-only/คำนวณ)
- KB auto-fill จาก `status_code` ตอนสร้าง/แก้แถว; แก้ทับได้
- แถว `status_code` ที่มี rule `required=True` (CY) และ `kb_amount==0` → ขึ้น
  คำเตือน inline กันลืม (ไม่บล็อกการบันทึก)
- `price_override` แก้ในคอลัมน์ราคา (เดียวกับที่คีย์งาน) — ถ้าตั้งจะ override
- เข้า edit-log/undo/redo ที่มีอยู่ (DailyJobAudit) เหมือนช่องอื่น

### Driver PWA
- **ไม่ render คอลัมน์ KB เด็ดขาด** — คนขับเห็นเฉพาะยอดเงินตัวเอง (driver_calc ที่
  ไหลเข้า trip fee / slip)

## รายงาน KB (P&L ฝั่งต้นทุน — รอบนี้คำนวณสด)

ต่อ cycle/site:
```
KB รวม         = Σ kb_amount (เฉพาะแถวที่มี KB)
เราเก็บ 10%    = KB รวม × 0.10
WHT 3%         = KB รวม × 0.03
จ่ายคนจ่ายงาน  = KB รวม × 0.87
```
รอบแรกแสดงเป็นสรุป (อาจในหน้า finance หรือ preflight) — ไม่เพิ่ม field, ไม่ผูก
ใบหัก ณ ที่จ่ายจริงในรอบนี้

## Migration / rollout

1. Schema: bump `SCHEMA_VERSION`, ALTER TABLE เพิ่ม `kb_amount`, `price_override`;
   สร้าง `kbrule` + seed NHL/MOL/CY
2. Backfill KB ย้อนหลังจาก rule ตาม `status_code` (NHL→110, MOL→100) สำหรับแถว
   ประวัติ — CY ปล่อยว่างให้คนกรอก (จะ trigger เตือน)
3. **Preflight ก่อน recompute**: สคริปต์ใน `tools/` โชว์ net เปลี่ยนต่อคนต่อ run
   (เทียบ before/after) — โอเซ็นก่อน แล้วค่อย recompute
4. ไม่แตะ run ที่ finalize แล้วโดยไม่ขอ

## ตรวจย้อนกลับ (preflight / กฎเงิน)

- สคริปต์ read-only: list ทุกแถวที่ `price_override IS NOT NULL` หรือ `kb_amount>0`
  พร้อม `revenue_customer` vs `driver_calc_price` ส่วนต่าง
- สรุป net เปลี่ยนต่อคน (เน้น over-market/KB rows: NHL/MOL/CY/DHL Overflow)
- list แถว CY ที่ `kb_amount==0` (กันลืม) ให้โอรีวิว

## ขอบเขตที่ **ไม่** ทำรอบนี้ (YAGNI)

- ไม่ทำ Customer master / map origin→customer_id (ใช้ `status_code` พอ)
- ไม่เก็บ field 10%/WHT/our_cut แยก (คำนวณสด)
- ไม่ผูกใบหัก ณ ที่จ่ายจริง / เอกสารภาษี
- ไม่ทำ KB แบบต่อขนาดตู้ (20/40) — flat ต่อแถว
- ไม่ทำ RBAC ละเอียดต่อ admin (admin ทุกคนเห็น KB; เส้นแบ่งคือ admin vs driver)
