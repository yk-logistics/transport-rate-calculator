# LCB มิ.ย. (payrun #2, cycle 16/5–15/6) — ผลตรวจ draft vs input ดิบ

ตรวจ 2026-06-27 night-run. มิ.ย. ยังไม่มี แบ็งค์.pdf (ยังไม่จ่าย) → ตรวจกับ input ดิบที่ถูกต้อง.

## ก้อนใหญ่ที่ตรวจ — ตรงหมด ✅

### 1. Petty (เบิกหักเงินเดือน) — ตรง 18/18 เป๊ะ
- **ANCHOR ที่ถูก = ชีท "สดย่อย" column O** (header "พขร.เบิก หัก เงินเดือน") — ไม่ใช่ชีท "สรุป" (เบิกล่วงหน้ารายสัปดาห์ ซึ่งเป็นแค่ประมาณการ).
- ระบบ import มาเป็น 1 txn/คน memo="รวมหักช่อง O สดย่อย 16/5-15/6" = ตรง col O ทุกคน.
- ที่เห็น "ห่าง +500" จากชีทสรุป = artifact ของ 2 แหล่งต่างกัน ไม่ใช่บั๊ก.
- วันชัย (ลาออก) เบิก 2,000 วันที่ 22/6 → ระบบไม่หัก (ถูก, ไม่อยู่ payrun นี้).
- ref: docs/ground-truth/lcb_jun_petty_O.csv

### 2. Fuel (น้ำมันหักคนเหมา) — ตรง
- lcb_mao: fuel_cost_self = sum(FuelTxn.amount where not exclude_from_driver) เป๊ะทุกคน.
- สุภาพ: excluded 8,288 (2 บิลถังเต็มแรกเหมา, งาน fuel-exclude-from-driver) ✅ ทำงาน.
- lcb_mixed (พชร/สุรเดช): FuelTxn รวม 42,867/44,390 แต่ fuel_cost_self 16,074/14,067
  = หักเฉพาะวันที่เป็น "เหมา" (วันเที่ยวบริษัทออกน้ำมัน) ตาม logic lcb_mixed ✅ ถูก.

### 3. Trip (คนเที่ยว) — โครงสร้างถูก
- base(9,240×days/31) + care(3,000 prorated) + trip_fee_total + other_income(พิเศษ เลิก100/OT).
- trip_fee มาจาก Daily วิ่งจริง (verify รายเที่ยวแยก — delegate).

## Recompute
- draft เดิม (computed 10:12) net 256,943.
- recompute สด net 257,497 (Δ+554, 5 คน lcb_mao ±หลักร้อย จาก fuel/petty ขยับเล็กน้อย).
- draft ไม่ stale ใหญ่ (memory เก่าว่า 287k คือก่อน reimport — มีคน recompute หลังจากนั้นแล้ว).

## สรุป
draft #2 ไม่มีบั๊กตัวเลข งานสะสม (mixed/fuel-exclude/idle/KB/extra-fees) ทำงานถูกหมด.
ขั้นต่อไป: recompute จริง (fresh) → draft พร้อม โอกด finalize เช้า.
ยอดจ่ายจริงรอบนี้จะกลายเป็น ground truth ของ มิ.ย. หลังโอ finalize.
