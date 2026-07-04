---
name: project-dhl-overflow-rate
description: "DHL Overflow = ลูกค้าเดียวกับ Oatside; เรทวางบิลผูกราคาน้ำมัน (สูตร trip_rate_baht ใน Oatside builder); ราคาคนขับ override 5,500"
metadata: 
  node_type: memory
  type: project
  originSessionId: dd159b75-a9ad-4971-90f9-dbb17a444943
---

**โอ-confirmed 2026-06-27: DHL Overflow = ลูกค้าเดียวกันกับ Oatside** (P&G/บ้านบึง). ดังนั้น**เรทวางบิล DHL Overflow ใช้สูตรเดียวกับ Oatside** (ผูกราคาน้ำมันไฮดีเซล).

**สูตรเรท (อยู่ใน `Oatside/build_oatside_reports.py` → `trip_rate_baht(date,cfg)`):**
```
เรท = base_rate × (1 + step_delta × step_pct%/100)
  step_delta = floor(ราคาน้ำมัน − base_fuel_min)
  step_pct = 1.5% ต่อ 1 บาท
```
config = `Oatside/oatside_config.json` → `trip_rates[]` (window from/to, rate_baht, base_fuel_min/max, step_pct_per_baht, floor_rate_baht) + `diesel_price_history[]` (ราคา Bangchak ไฮดีเซล S รายวัน — **คนละราคากับปั๊มจริง** ที่หักคนขับ). พ.ค.2026 window: base 6,400 @ 31.00-31.99. ราคาน้ำมันขาดวัน → `_resolve_diesel_price_for_date` carry-forward ใช้ราคาล่าสุดย้อนหลัง (โอ OK). ตรวจสูตรถูก: 30/5 น้ำมัน 40.7 → เรท 7,264 (ตรงรายงาน Oatside trips.html เป๊ะ).

**รันคำนวณเรท:** ต้องใช้ venv ที่มี openpyxl: `Oatside/../ProjectYK_System/app/.venv/Scripts/python.exe`; import build_oatside_reports ผ่าน importlib, `cfg=load_oatside_config()`, `trip_rate_baht(date(...),cfg)`.

**งานที่ทำ (2026-06-27, deployed):** ใส่ราคา DHL Overflow รอบ มิ.ย. (status_code "DHL Overflow", rev=0 เดิม) **เฉพาะ 16–31/5 = 19 แถว** (โอเลือกเฉพาะที่มีแถว; 1–15/6 ยังไม่ลงเดลี่ + ราคาน้ำมัน history ถึงแค่ 30/5). ใส่ **revenue_customer = เรทรายวัน (7,264–7,456)** + **price_override = 5,500 ทุกแถว** (ราคากลางคนขับ โอย้ำ) by id. เก็บ trip_fee_driver=350 เดิมไว้. รวม rev 140,320. **ทุกแถวเป็นของ เนื้อ ภาสดา (id87) = lcb_trip** → เงินคนขับคิดจาก fee ไม่ใช่ rev/override → **net เนื้อเท่าเดิม 14,940, payrun#2 total เท่าเดิม 256,942.96** (รายได้วางบิลล้วน ไม่กระทบเงินคนขับ). backup app.db.bak_before_dhl_overflow_*.

**ค้าง:** 1–15/6 ยังไม่มีแถวงาน + ราคาน้ำมัน history หยุดที่ 30/5 — ถ้าจะทำต่อต้อง import เดลี่ มิ.ย. + เพิ่ม diesel_price_history. ดู [[project-oatside-billing-recon]] [[project-kb-driver-calc-price]] (override=ราคาคิดเงินคนขับ).
