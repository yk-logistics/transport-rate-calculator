---
name: project-slip-handover-manual-offtable
description: "สลิปไม่โชว์น้ำมัน handover_manual (เรวัตร 4,989) ทั้งที่หักจริง — แก้ _OFFTABLE_FUEL จับ handover ทุกแบบ — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (main c1a765a, code-only): โอ "งง น้ำมันที่ซ่อนได้ เรวัตร 4,989 คืออะไร". = บิล FuelTxn id2039 (เรวัตร140, 1/6, 4,989.03, 122.58ล, **source=`ayu_2026-06_handover_manual`**, daily_job_id=None, exclude_from_driver=0). **หักเงินจริงอยู่ใน fuel_cost_self 49,661 แล้ว** แต่**ไม่โผล่บนสลิป** = ที่โอเรียก "ซ่อน".

**root cause:** `payroll_slip.py` `_OFFTABLE_FUEL = ("tank_measure", "handover_measure")` จับเฉพาะ substring พวกนี้ + daily_job_id=None → บิล source `handover_manual` (≠ handover_measure) หลุดทั้ง 2 ทาง (ไม่มี daily_job_id=ไม่อยู่ตารางเดลี่ + source ไม่ match=ไม่อยู่ off-table) → หักแต่ไม่ render.

**fix (display-only):** เปลี่ยน `"handover_measure"` → **`"handover"`** จับทั้ง handover_measure + handover_manual (เช็คแล้ว 2 source นี้เท่านั้นที่มี handover, ทั้งคู่ daily_job_id=None ถูกต้อง ไม่ false-positive). fuel_deducted/net **ไม่เปลี่ยน**; 58 slip tests pass; verified live: tank_measure_rows เรวัตร =1 โชว์ 4,989 (1/6).

**รอบ 2 (ธัชชนพล, main 2b58db6):** บิล source=`ayu_2026-06_manual` (ยกยอด +3,960 / ทำคืน −3,164.06) **ผูก daily_job_id ของเที่ยวจริง** (4348/5152) แต่ job นั้น `fuel_amount=0` → ต่างจากเรวัตร (djid=None). สลิปอ่านคอลัมน์น้ำมันจาก **DailyJob.fuel_amount (=0)** ไม่ใช่ FuelTxn → ไม่โชว์; off-table filter เดิม `daily_job_id is None` ก็ข้าม. แก้: เพิ่ม **"manual"** ใน _OFFTABLE_FUEL + ผ่อนเงื่อนไข `daily_job_id is None OR job not in _jobs_with_table_fuel(fuel_amount>0)` → บิลที่ job ไม่มีน้ำมันในตารางโชว์ off-table ได้ (กันซ้ำกับบิลปกติที่โชว์ในตารางแล้ว). verified live ธัชชนพล 2 rows, เรวัตร ไม่ regression.

**deploy code-only (ไม่แตะ DB):** surgical scp `services/payroll_slip.py` + `_restart_verify.ps1`(by path: kill 8010 by PID, restart task, verify code marker+8020). marker scan ปกติไม่ครอบ services/ → restart script เช็ค content เอง. related: [[project-slip-offtable-fuel-display]] (เคสเดียวกัน วัดถัง/handover), [[project-rewat-handover-fuel-jun]] (บิล 4,989 นี้มาจากตรงนั้น), [[project-mao-fuel-tank-measure]]
