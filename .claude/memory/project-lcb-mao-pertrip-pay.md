---
name: project-lcb-mao-pertrip-pay
description: LCB เหมา (lcb_mao) คิดค่าจ้างจาก trip_fee_driver ต่อเที่ยว แทน revenue×60% รวมรอบ — DONE+deployed
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (main fbb4830): โอ "lcb_mao ควรคิดรายเที่ยวจากเดลี่ ไม่ใช่ 60% รวมรอบ เพราะบางเที่ยว override manual". = บั๊กคลาสเดียวกับ [[project-ayu-mao-pertrip-pay]].

**bug:** engine `lcb_mao` คิด `fuel_share_income = Σrevenue×60%` รวมรอบ → ทับ trip_fee_driver ต่อเที่ยวที่แก้มือ. เจอ NHL หลายเที่ยว tfd > 60% (ปกรณ์ 8 เที่ยว +66 ต่อเที่ยว = +528; รัฐภูมิ +198; พิชิต +132) → engine จ่ายขาด.

**fix:** `calc.fuel_share_income = _sum_trip_fees(...)` แทน revenue×share. recompute run2(16/5-15/6) lcb_mao 12 คน: **ปกรณ์92 +528, รัฐภูมิ85 +198, พิชิต93 +132**, อีก 9 คนเท่าเดิม (tfd=60% อยู่แล้ว); net_guard run2 only (Δ+858).

**DISPROOF ที่ต้องระวัง:** all-history มี lcb_mao rows rev>0 แต่ tfd=0 (รอบเก่า importer ไม่ลง tfd) → ถ้า recompute รอบเก่าจะ drop. แต่ **run2 ทุกเที่ยว rev>0 มี tfd>0 ครบ** (เช็คแล้ว) + รอบเก่า finalized/copy-lock ไม่ recompute → ปลอดภัย. **เฉพาะรอบที่ recompute จากเดลี่ครบ (มี tfd ทุกเที่ยว) เท่านั้นที่ปลอดภัย — รอบเก่าอย่า recompute.**

**UPDATE 30มิ.ย.(2) — เทียบไฟล์ `Daily แหลมฉบัง2 (1).xlsx` ชีท `Daily 16.05.69-15.06.69` (col E=คนขับ, Y=ค่าขนส่ง, AL=ค่าเที่ยวพขร, B=Status):**
- **"NHL +66/เที่ยว" ไม่ใช่ override — เป็น KB!** ไฟล์ ค่าเที่ยว=60%ของ**ค่าขนส่งเต็ม** (2,410×0.6=1,446) แต่ DB `driver_calc_price`=rev−KB(110) แล้ว×60% (2,300×0.6=1,380) → ต่าง 66=60%×110. NHL มี KbRule default 110. **revenue DB ตรงไฟล์ทุกแถว, tfd ตรงไฟล์** — ไม่มีใส่ผิด (โอเดา KB ถูก). _sum_trip_fees จ่าย tfd=ไฟล์ตรง (ถูกแล้ว).
- **MY BUG: job 718/719 26/5 ผมเติม tfd=2,898.60 เองตอนคิดว่า display-only แต่ไฟล์ ค่าเที่ยว=0** (KLND ยังไม่ลงค่าเที่ยว) → หลังแก้ engine เป็น sum tfd กลายเป็นจ่ายเกิน 2,898.60×2. **revert tfd=0** (ปกรณ์ net 24,262→21,363.80, ณัฐวุฒิ 19,948→17,049.90, Δ−5,797.20). reconcile ไฟล์↔DB: ค่าขนส่ง+ค่าเที่ยว ทั้ง 4 คนตรงเป๊ะ.
- **บทเรียน: เทียบ ground truth จากไฟล์ต้นทาง (xlsx) ไม่ใช่แค่ DB ภายในแถว; mao อย่าเติม tfd มั่ว ต้องตามไฟล์.**

**UPDATE 30มิ.ย.(3) — หัก KB ก่อนคิด 60% (main 5812d9e):** โอยืนยัน NHL ค่าเที่ยว = 60% ของ (ค่าขนส่ง−KB) ไม่ใช่ 60% ของเต็ม. ไฟล์คีย์ tfd=60%เต็ม (1,446) แต่ต้อง 60%×(2,410−110)=**1,380**. เพิ่ม `_sum_mao_kb_share` → `fuel_share_income = Σtfd − Σ(kb×share เฉพาะแถว tfd>0)`. NHL มี KbRule 110: ปกรณ์ −528/รัฐภูมิ −198/พิชิต −132 (13 แถว, −858); ณัฐวุฒิไม่มี KB ไม่ขยับ. **engine lcb_mao = Σtrip_fee_driver − KB-share (honor override ต่อเที่ยว + หัก KB อัตโนมัติ).** ต่างจาก _sum_gross_revenue×60% (ที่จะ re-add แถว tfd=0).

**ที่มา:** โอเจอ job 718/719 26/5 "ค่าขนส่งแต่ไม่มีค่าเที่ยว 60%" → ตอนแรกผมคิดว่า display-only (เพราะ 60% รวมรอบนับ rev แล้ว) แต่โอถูก: ต้องคิดรายเที่ยวจากเดลี่ เพราะ tfd ต่อเที่ยวเป็น source ที่ override ได้. related: [[project-ayu-mao-pertrip-pay]], [[project-kb-driver-calc-price]]
