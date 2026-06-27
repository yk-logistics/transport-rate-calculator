# Fuel exclude-from-driver (per-bill) + สุภาพ → lcb_mao

วันที่: 2026-06-27
สถานะ: design approved (โอ 2026-06-27)
Branch: `feat/fuel-exclude-from-driver`

## ปัญหา

คนเหมา (lcb_mao / lcb_mixed) ถูกหักน้ำมัน 100% ของบิล FuelTxn ทุกใบในรอบ
แต่ตามกฎโอ มีบิลที่ **ไม่ควรหักคนขับ**:

- **น้ำมันที่เติมก่อนคนขับเริ่มวิ่งงานจริง** (รถจอด/ซ่อมช่วงรับรถใหม่) — เติมแล้วแต่ยังไม่ได้ใช้ทำงาน
- **ถังเต็มถังแรกตอนเริ่มเหมา** — บริษัทออกให้ถังแรก (กฎเหมา)

เคสจริง: **สุภาพ (id100)** รับรถ 71-9627 เริ่มรอบ มิ.ย. (16/5–15/6)
- 16/5 เติม 60 ลิตร 2,488฿ (รถจอด — ยังไม่วิ่ง)
- 17/5 รถจอด, 18/5 รถซ่อม
- 19/5 เติมเต็มถัง 139.86 ลิตร 5,800฿ (ถังแรกก่อนออกวิ่งวันแรก KAO)

ทั้ง 2 บิล = ไม่หัก (โอยืนยัน "เติมแล้วแต่ยังไม่ได้วิ่งงาน").
สุภาพยังตั้ง pay_mode=lcb_trip ผิด (งานจริง ratio=0.60 ทุกวัน = เหมา) → ต้องแก้เป็น lcb_mao ด้วย.

โอเลือกวิธีแก้: **override รายบิล** (ติ๊กในหน้าเงินเดือน) — ไม่ทำ auto-detect (กระทบเหมาทุกคน เสี่ยง).

## Scope

1. Schema: เพิ่ม flag บน FuelTxn
2. Engine: ยอดหักน้ำมันข้ามบิลที่ติ๊ก
3. UI: หน้า /payroll/{id} ติ๊ก "ไม่หัก" รายบิล + recompute
4. สุภาพ: เปลี่ยน lcb_trip→lcb_mao + ติ๊ก 2 บิล + recompute (หลังปุ่มเสร็จ)

นอก scope: auto-detect "วันเริ่มวิ่งจริง", per-day mode override (งานอื่น).

## ส่วนที่ 1 — Schema

เพิ่ม field บนตาราง `fueltxn`:

```
exclude_from_driver: bool = Field(default=False)
```

Migration ตาม pattern โปรเจกต์ (ไม่ใช้ Alembic):
- bump `SCHEMA_VERSION` ใน main.py (ปัจจุบัน 18 → ค่าใหม่; ตรวจค่าจริงตอนทำ)
- `ALTER TABLE fueltxn ADD COLUMN exclude_from_driver BOOLEAN DEFAULT 0` ใน lifespan() guard ด้วย version check

ค่า default 0 = บิลเดิมทุกใบ "หักปกติ" → ไม่กระทบใคร.

## ส่วนที่ 2 — Engine (services/payroll.py)

2 helper ที่ sum น้ำมัน เพิ่มเงื่อนไขกรองบิลที่ติ๊ก:

- `_sum_fuel_cost()` (lcb_mao, ayu_*self_fuel) — เพิ่ม `.where(FuelTxn.exclude_from_driver == False)` หรือกรองใน list comprehension
- `_sum_fuel_cost_for_dates()` (lcb_mixed) — กรองเช่นกัน

**ไม่แตะ logic อื่น.** mode อื่น (bigc rebate, lcb_trip) ไม่หักน้ำมันจาก FuelTxn อยู่แล้ว → ไม่กระทบ.

Regression: default False → ทุกบิลถูกนับเหมือนเดิม → เหมา/mixed ทุกคน net เท่าเดิมเป๊ะ.

## ส่วนที่ 3 — UI (templates หน้า /payroll/{id})

ในส่วนรายละเอียดคนที่ pay_mode หักน้ำมัน (lcb_mao, lcb_mixed, ayu self-fuel):

- แสดง **ตารางบิลน้ำมัน** ของคนนั้นในรอบ: วันที่ | ทะเบียน | ลิตร | บาท | สถานะ
- แต่ละแถวมี toggle "ไม่หัก" (checkbox/ปุ่ม HTMX)
- toggle → POST endpoint ใหม่ (เช่น `POST /payroll/fuel/{fueltxn_id}/toggle-exclude`) → set exclude_from_driver → recompute payrun item ของคนนั้น → คืน partial ที่อัปเดตยอด
- บิลที่ติ๊กแสดงชัด (ขีดฆ่า/สีจาง + ป้าย "ไม่หัก ✓")
- แสดงยอดรวม: "หักจริง X฿ (ยกเว้น N บิล = Y฿)"

Endpoint อยู่ใน main.py (monolith) ตาม pattern route อื่น. ใช้ HTMX swap (ตาม stack — ไม่มี Node build).

## ส่วนที่ 4 — สุภาพ (script ทำหลังปุ่มเสร็จ)

1. UPDATE employee SET pay_mode='lcb_mao' WHERE id=100 (backup ก่อน)
2. UPDATE fueltxn SET exclude_from_driver=1 — เฉพาะ 2 บิล (driver_id=100, txn_date 16/5 = 2,488฿ และ 19/5 = 5,800฿) **ระบุด้วย id ของบิล** ไม่ใช่ filter กว้าง (กฎ test-data-cleanup-safety)
3. recompute payrun#2 (compute_pay_run recompute=True)
4. ตรวจ: สุภาพ fuel_cost_self = 37,119 − 2,488 − 5,800 = **28,831฿**, net ตรงมือคำนวณ

## เทสต์ (TDD)

- unit `_sum_fuel_cost`: บิลปกติ + บิลติ๊ก → ผลรวมข้ามบิลติ๊ก
- unit `_sum_fuel_cost_for_dates`: เช่นเดียวกัน
- regression: เหมา 8 คน (ปกรณ์/พัฒิยะ/รัฐภูมิ/นิพล/ณัฐวุฒิ/พิชิต/วิโรจน์/วราวุฒิ) + mixed 2 (พชร/สุรเดช) → net **เท่าเดิมเป๊ะ** ก่อน-หลังเพิ่ม flag (default False)
- สุภาพ: หลังแก้ → fuel_cost_self=28,831, gross/net ตรงคำนวณมือ

## Deploy

- ทำบน branch `feat/fuel-exclude-from-driver` → merge main
- Deploy server: full-file overwrite Dev app.db → server (วิธีที่โอเลือก, ตาม [[project-lcb-mixed-mode]])
- **เตือน:** overwrite ทำให้เงินเดือน**ทุกคน**บน server กระโดดเป็นชุด Dev ล่าสุด (xlsx reimport + gapfill + KB + สุภาพ) ไม่ใช่แค่สุภาพ → backup server ก่อน + สรุปตัวเลขที่เปลี่ยนให้โอดู
- restart server ตาม [[reference-mvp-deploy-restart-gotcha]] (kill main.py by-path)
- payrun#2 ยัง draft — โอตรวจบน server

## ความปลอดภัยเงิน

- backup app.db ก่อน recompute ทุกครั้ง
- regression test ยืนยันคนอื่นไม่ขยับ ก่อนแตะสุภาพ
- ติ๊กบิลด้วย id ไม่ใช่ filter
