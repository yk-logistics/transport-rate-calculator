---
name: project-rewat-handover-fuel-jun
description: เรวัตร 1/6 handover fuel bill โอใส่ในชีทหลัง re-import → หักเต็ม + deploy DB-only WAL-safe
metadata: 
  node_type: memory
  type: project
  originSessionId: ae84219a-cb90-438f-9644-8edce591a1da
---

DONE+deployed 30มิ.ย. (คืน): โอใส่บิลน้ำมัน 1/6 ในชีท AYU **หลัง** gsheet re-import (30มิ.ย.เช้า) → ไม่เคยเข้า DB. note "น้ำมันในถัง ขึ้นขับ" = handover (เรวัตรขึ้นขับ 71-0556 1/6, 122.58L × 40.70 = 4,989.03฿).

**โอตัดสิน: หักเต็มเหมือนบิลอื่น** (ไม่ใช้กฎ handover-measure วัดถัง) → insert FuelTxn driver_id=140 site=AYU exclude_from_driver=0 source=`ayu_2026-06_handover_manual` (tool `tools/add_rewat_handover_fuel.py` idempotent). recompute เฉพาะ 4 mao run18 ผ่าน `tools/ayu_mao_recompute_run18.py` (calc_one_employee in-place, เลี่ยง office wipe).

**ผล:** เรวัตร fuel_cost_self 44,672→**49,661.03** (22→23 บิล), net 16,132.84→**11,143.81** (Δ−4,989.03); income (Σtrip_fee 78,054.84) ไม่ขยับ. payrun #18 199,852.43→**194,863.40**. net_guard `after --allow 18` = OK รอบอื่นนิ่ง (อีก 17 รอบไม่ขยับ). ยังเป็น draft.

**โอกำชับ "อย่าเอางานเก่าทับงานใหม่ส่วนอื่น" → พิสูจน์ก่อน push:** probe_db.py รัน local vs **live server** → payrun ทุกรอบเท่ากันเป๊ะ ยกเว้น run18 (server 199,852.43 / local 194,863.40) + fueltxn ต่าง 1 (1664→1665); DailyJob 4338/Employee 164 เท่ากัน → ยืนยัน local เป็น superset ของ server แค่ +การแก้นี้ ไม่มีงานใหม่บน server ให้ทับ. **วิธีพิสูจน์นี้ดีกว่าเดา — ทำทุกครั้งก่อน DB-push payroll.**

**DEPLOY DB-only WAL-safe (สำเร็จ — ห้าม deploy_mvp.sh --with-db เพราะมัน scp app.db ดิบ = WAL corrupt):** (1) local `PRAGMA wal_checkpoint(TRUNCATE)` + `src.backup(dst)` → app_clean (single-file consistent, integrity ok). (2) scp → server `app_incoming.db` (byte 57,524,224 ตรง). (3) verify incoming integrity+run18 net ผ่าน probe_db.py บน server **ก่อน** swap. (4) `swap_db.ps1` (100% ASCII, scp ไปรัน by-path เลี่ยง quote nesting): verify incoming integrity → Stop-ScheduledTask YK_MVP_APP + kill 8010 by PID → backup live app.db → rm -wal/-shm → Move-Item incoming→app.db → Start task → verify 8010 UP + 8020 archiver UP + run18 net. (5) public /login=200, live run18=194,863.40, fueltxn=1665. backup: local app.db.bak_before_rewat_handover_fuel_*, server app.db.bak_before_rewatfuel_*.

**GOTCHA ยืนยันซ้ำ:** inline SSH `python -c "..."` quote nesting พังตลอด (PS+bash+python 3 ชั้น) → เขียน .py/.ps1 scp ไปรัน by-path เสมอ. grep filter WARNING ทำ exit code เพี้ยน (ดู byte-size/integrity จริงแทน).

related: [[project-ayu-mao-pertrip-pay]], [[project-fuel-handover-measure-backlog]], [[project-jun-payroll-ayu-bigc-status]], [[reference-net-guard]], [[reference-deploy-mvp-selfverify]]
