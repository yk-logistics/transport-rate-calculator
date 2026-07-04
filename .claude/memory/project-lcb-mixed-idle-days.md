---
name: project-lcb-mixed-idle-days
description: lcb_mixed fix — วันรถจอด(company_no_work) ต้องได้ฐาน; ตัวหาร=(trip+idle)/days; +banner เตือนวันรอลงราคา. Done+deployed server 2026-06-25.
metadata: 
  node_type: memory
  type: project
  originSessionId: e32115de-0d73-42b0-a56a-16f79e936916
---

**สิ่งที่แก้ (2026-06-25, branch fix/lcb-mixed-idle-days → merged main → deployed server):**

โอจับได้ว่า lcb_mixed คิดเงิน "วันรถจอด" ผิด — คนขับมาแต่บริษัทไม่มีงานวิ่ง (status=รถจอด) ต้องได้เงินฐาน/ค่าดูแล แต่ระบบไม่นับ. 3 จุดใน `services/payroll.py`:

1. **ตัวหารฐาน lcb_mixed**: เดิม `base × (n_trip/days)` → ใหม่ `× ((n_trip + n_idle)/days)` โดย n_idle = `calc.days_company_no_work`.
2. **`_count_work_days` is_company_no_work**: เดิมจับแค่ "รถจอด/รองาน/ไม่มีงาน". เพิ่ม `อุบัติเหตุ`, `ซ่อม`, `dhl overflow` (โอ: ทั้งหมดนี้=รถจอด ได้ฐาน; "ลา/ไม่พร้อม"=ไม่ได้). **กับดักไทย:** tokenizer แตกคำไม่ได้ ("รถอุบัติเหตุ"=token เดียว) → ใช้ **substring match บน status_blob** ไม่ใช่ exact-token-in-tokens.
3. **banner วันรอลงราคา** (`find_pending_price_days` + payroll_detail ctx/template): วันที่ rev=0+fee=0 แต่ status เป็นรหัสลูกค้า (KAO/KLND…ไม่ใช่ idle/leave) = พี่ตาลยังไม่ลงราคา → เตือนสีส้มในหน้า /payroll/{id} ให้ไล่เติม, ไม่เดาเงิน.

**ผลเงิน (payrun#2 recompute):** พชร(86) 12,092→**16,435.33**, สุรเดช(91) 13,120→**17,067.97**; อีก 16 คน LCB **net เท่าเดิมเป๊ะ** (lcb_trip/lcb_mao คิดฐานแบบ base−(base/days)×missed ซึ่ง missed ไม่รวม company_no_work → ไม่ขยับ). verify ด้วย `tools/verify_idle_fix_impact.py` (golden snapshot ใน spec).

**ขึ้น server แล้ว:** full-file overwrite Dev app.db → server (โอเลือกวิธีนี้). Server backup `app.db.bak_before_dev_overwrite_20260625_124123`. payrun#2 ยัง draft. ดู [[project-lcb-mixed-mode]], [[reference-mvp-server-deploy]], [[reference-mvp-deploy-restart-gotcha]].

**[2026-06-26] น้ำมันวันรถจอด 'ช่วงเหมา' ต้องหักด้วย (โอ):** เดิม fuel_cost_self หักเฉพาะ mao_dates → น้ำมันวันรถจอดไม่ถูกหัก. กฎใหม่: รถจอดคั่นช่วงเหมา→หัก, คั่นช่วงเที่ยว→ไม่หัก. helper `_idle_dates_in_mao_phase(split)` หาวันจอดที่วันทำงานใกล้สุดเป็นเหมา (tie→เหมา=ปลอดภัย=หัก); fuel_dates = mao_dates ∪ idle_mao_dates. recompute run2: พชร net 16,335→**10,598** (fuel 10,337→16,074), สุรเดช 16,468→**8,977** (→14,067); mao เปลี่ยนแค่ income_tax ripple (fuel/gross เท่าเดิม). ขึ้น server แล้ว (backup `app.db.bak_before_idlefuel_*` ทั้ง dev+server). **ค้าง — per-day override:** โออยากให้ User เลือกเองได้ว่าวันนั้นเป็นระบบเหมา/เที่ยว (default = auto nearest-neighbor นี้); ต้องมี storage field + UI, ยังไม่ทำ.

**Why:** วันรถจอดเป็นวันที่คนขับพร้อมทำงานแต่บริษัทไม่มีงานให้ ≠ ลา → ต้องได้ฐาน. การไม่นับทำให้ฐานต่ำผิด.
**How to apply:** งาน lcb payroll ใดๆ ที่แตะ "วันไม่มีรายได้" ต้องแยก รถจอด(ได้ฐาน) / ลา(ไม่ได้) / รอลงราคา(เตือน เติมก่อน). อย่า exact-match token ไทยที่ติดกัน — ใช้ substring.
