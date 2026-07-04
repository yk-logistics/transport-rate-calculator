---
name: project-ayu-mao-pertrip-pay
description: AYU เหมา (ayu_mao) คิดค่าจ้างจาก trip_fee_driver ต่อเที่ยว แทน revenue×60% ใหม่ — DONE+deployed
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (main d5bda3d): bug = engine โหมด `ayu_mao` คิด `fuel_share_income = Σ(driver_calc_price × 0.60)` **ใหม่ทุกเที่ยว** → ทับค่าจ้างต่อเที่ยวที่บันทึกไว้ในเดลี่ (`trip_fee_driver`) ที่โอแก้มือบางเที่ยวให้ไม่ใช่ 60% (เช่น "งานฝาก เฮงเค็ล" rev 250 จ่าย 100 ไม่ใช่ 150) → จ่ายเกิน.

**แก้:** `calc.fuel_share_income = _sum_trip_fees(...)` (= Σ `trip_fee_driver`) แทน `revenue * share_rate`; note เปลี่ยนเป็น "ค่าขนส่งต่อเที่ยว {sum} − น้ำมัน − ทางด่วน/Mflow". importer ลง trip_fee_driver=rev×60% เป็น default อยู่แล้ว → summing มันเลยเคารพทั้ง default + manual override. ตรวจ: ทุกแถวที่ rev>0 มี tfd>0 (ไม่มี data หาย).

**recompute:** เฉพาะ 4 คนเหมา run18 (`ayu_mao_recompute_run18.py` calc_one_employee → set 28 ITEM_FIELDS ทับ PayRunItem in-place) — **ไม่เรียก compute_pay_run ทั้งรอบ เพื่อเลี่ยง gotcha office copy ถูกล้าง**. Δ: เรวัตร −199.99 (4 เฮงเค็ล×50), นิวัติ −49.99, ธัชชนพล −2,814.70, เสรี −1,283.50; net รอบ #18 204,200.61→**199,852.43** (24 items). net_guard `after --allow 18` = OK รอบอื่นนิ่ง. mao 4 คนยังติดลบ (เสรี/ธัชชนพล) = "เหมารอราคา"เดิม ไม่ใช่บั๊กนี้ (แก้ทำให้ติดลบมากขึ้นเล็กน้อย=ถูก เพราะเดิมจ่ายเกิน).

**สลิปไม่ต้องแก้:** income อ่านจาก PayRunItem.fuel_share_income (persist) = ตามที่แก้; `_slip_daily_rows` โชว์ central(ราคากลาง)+trip_fee ตรงจาก DailyJob ไม่ recompute 60%.

**DEPLOY GOTCHA: deploy_mvp.sh marker สแกนแค่ main.py+templates/*.html ไม่สแกน services/** → change ใน payroll.py ใช้ --markers พิสูจน์ไม่ได้. ทำ surgical manual: scp payroll.py + clean DB→app_incoming.db + `_ayu_mao_deploy.ps1`(by path) ที่ stop 8010 by PID→verify incoming integrity ขณะ stop→swap→start→grep ayu_mao block มี `_sum_trip_fees` ไม่มี `revenue * share_rate`→8020 รอด. **DB ต้อง backup-API+wal_checkpoint(TRUNCATE) ก่อน scp (WAL mode raw scp=malformed แม้ byte ตรง)** [[reference-deploy-mvp-selfverify]]. verified live: integrity ok, run18 199,852.43, public 200.

related: [[project-ayu-jun-payroll]], [[project-jun-payroll-ayu-bigc-status]], [[project-kb-driver-calc-price]], [[reference-net-guard]]
