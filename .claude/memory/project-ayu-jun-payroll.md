---
name: project-ayu-jun-payroll
description: "AYU June payroll computed from real daily — 15 trip OK, office copied, 4 เหมา draft awaiting prices"
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย.: เงินเดือน AYU รอบ มิ.ย. (cycle 2026-06 = 26พ.ค.-25มิ.ย.) **payrun #18 draft net 228,577** คิดจากเดลี่จริง ([[project-ayu-daily-import]] เป็น prerequisite).

**3 กลุ่ม:**
- **15 คน ayu_trip**: trip_fee − petty (คิดจากเดลี่ ครบ ไม่ขึ้น revenue) — ถูกต้อง
- **12 office_monthly** (รัตนาวดี 40k/พงษกาญจน์[โอ] 20k/จุฑามาศ 20k/...): **ลอกยอด net จาก payrun พ.ค.** เพราะ `base_salary=0` ใน DB → engine คิดเองได้ 0−SS=−1,450 (ผิด). **GOTCHA: `compute_pay_run` recompute ทับ office เป็น 0 ทุกครั้ง → ต้อง re-copy office หลัง recompute เสมอ** (รัน ayu_office_copy logic หลัง petty_itemize ที่ recompute).
- **4 ayu_mao** (นิวัติ139/เรวัตร140/ธัชชนพล143/เสรี144 = **ระบบเหมา** โอยืนยัน, set จาก ayu_trip→ayu_mao): 60%×revenue−น้ำมัน−ทางด่วน. **draft รอราคา** เพราะ revenue ในเดลี่ลงไม่ครบ (นิวัติ 1/42 เที่ยวมีราคา, เรวัตร 17/58) → net ติดลบชั่วคราว (นิวัติ −12,350, ธัชชนพล −4,304). **โอจะใส่ราคา AYU ทีหลัง แล้ว recompute**. นิวัติพิเศษ: 250 ในเดลี่=ค่าพ่วง ให้คนขับ 100 (ไม่ใช่รายได้จริง).

**petty:** itemize จากไฟล์ `AYU\สดย่อยวังน้อย หมิว.xlsx` ชีท `JUN 26` (ชื่อ caps! ไม่ใช่ "Jun 26") ผ่าน `petty_itemize.py --site AYU` (เพิ่ม AYU ใน config) = 182 บรรทัด/14 คน (match สมาชิก payrun, กันชน สมัย ราศรี[BigC]≠สมัย[AYU137]).

**FLAG net ติดลบ 3 (รอโอ):** นิวัติ/ธัชชนพล (เหมารอราคา) + สมัย137 (petty > gross — สดย่อยเยอะ). ปล่อย draft ไม่ finalize.

**UPDATE 29มิ.ย. (โออัปเดตไฟล์สดย่อย re-import):** petty 182→**188 บรรทัด** (ยอดต่อคนเพิ่ม: สมัย 15,530→19,425, เรวัตร 13,800→15,800, นิวัติ 11,050→13,050...). AYU มิ.ย. net 228,577→**205,892**. ติดลบ 3: นิวัติ −14,350/ธัชชนพล −4,304 (เหมารอราคา), **สมัย −5,975** (petty 19,425>gross 14,900). **GOTCHA ยืนยัน: petty_itemize recompute ลบ office → ต้อง re-copy office ทุกครั้งหลัง re-import** (รัน ayu_office_copy logic). deploy DB ขึ้น server แล้ว.

**สำคัญ — CFO ขาดทุน = revenue ไม่ครบ ไม่ใช่บั๊กน้ำมันซ้ำ** (โอถาม): ไล่ P&L แล้ว น้ำมันคิดครั้งเดียวถูก. BigC พ.ค. ขาดทุน 864k เพราะ revenue ลงแค่ 9% (45/462 เที่ยว, 31,070) แต่ต้นทุนครบ (น้ำมัน 675k+เงินเดือน 220k). LCB ใส่ราคา 63% → กำไร 979k(+39%). AYU เหมาก็ปัญหาเดียวกัน. **แก้=ลงราคาค่าขนส่งให้ครบ** (ค้าง costing-from-status BigC + ราคา AYU).

deploy DB push (integrity ok, byte ตรง, login 200); other payruns ไม่แตะ (LCB 268,457/BigC 131,856/AYU พ.ค. 267,117).

related: [[project-ayu-daily-import]], [[project-payroll-slip-petty-itemize]], [[project-multisite-payroll-onboard]], [[project-bigc-column-e-customers]]