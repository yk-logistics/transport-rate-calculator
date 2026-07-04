---
name: project-slip-merge-fuel-same-fill
description: "สลิปรวมน้ำมันเติมรอบเดียวกัน (B7+B20) ให้โชว์ช่องเดียว — display-only, key=วันเติมจริง"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6cfc9eaa-d4ec-4977-a941-7221e9150304
---

DONE+deployed 30มิ.ย. (main cb18b37): โอถาม (รอบนี้ชี้ไฟล์ `Y2026-น้ำมันคาลเท็ก(-).xlsx`) ว่าน้ำมันเติมรอบวันเดียวกันให้ไปอยู่ "ช่องเดียว" ได้ไหม. ต่างจากรอบ 29มิ.ย. [[project-fuel-b7b20-grade]] ที่ตอบ "ไม่ทำ auto-merge": รอบนั้น key=วันที่อย่างเดียว → กำกวม (แยก B7/B20-split จาก 2-เที่ยวจริงไม่ได้). รอบนี้พบว่า **เลขไมล์แยกได้ชัด** (71/90 กลุ่ม LCB มิ.ย. = ไมล์เดียวกัน = เติมครั้งเดียว split B7+B20).

**โอตัดสิน 2 ข้อ (ผ่าน AskUserQuestion):** (1) รวมบน **สลิป** เท่านั้น; (2) **แสดงผลอย่างเดียว** ห้ามแตะ DailyJob/FuelTxn/net; (3) **key = วันที่เติมจริง (FuelTxn.txn_date) ไม่อ้างเลขไมล์** ("เอาวันที่เติมจริงเป็นหลักไปเลย"). ยอมรับว่าถ้า 2 เติมจริงวันเดียว(ไมล์ต่าง)จะรวมด้วย — OK เพราะผลรวมยังถูก.

**กลไก (display-only):** `build_payroll_slip_context` สร้าง `fuel_merge_by_job: {job_id: {...}}`. group `fuel_rows` ที่มี `daily_job_id` (ในตาราง) ตาม `txn_date` ต่อคน → กลุ่มที่แตะ ≥2 DailyJob: บรรทัดบนสุดในลำดับ `daily_jobs` = **anchor** (`{role:anchor, liter:Σ, amount:Σ, grades:[...]}`), ที่เหลือ = `{role:merged, anchor:id}`. `_slip_body.html` (ทั้ง branch ปกติ + mixed): anchor โชว์ลิตร+ยอดรวม+เกรดทุกตัว ; merged เว้น 2 ช่องน้ำมันเป็น `↳`. **footer sum ยังใช้ `daily_jobs|sum(fuel_amount/liter)` เดิม → reconcile** (anchor-รวม + บรรทัดว่าง = grand total เท่าเดิม). fuel_cost_self ไม่แตะ.

**สำคัญ — txn_date ≠ work_date:** บิล B7+B20 เติมครั้งเดียววันที่ X อาจถูกคีย์ลง DailyJob คนละ work_date (เช่น job 833 work_date 1มิ.ย. + job 853 work_date 2มิ.ย. แต่ FuelTxn ทั้งคู่ txn_date=1มิ.ย. ไมล์ 286149 เท่ากัน). group ตาม txn_date จึงรวมถูก (ตามที่โอต้องการ "วันเติมจริง").

**verified:** render LCB#2 บน **server จริง** (live app.db) → 6 คนโชว์ anchor รวม "50 1,941 B20 B7" ช่องเดียว, print-all ไม่ 500. local: 3 tests ใหม่ (anchor/no-merge/total-reconcile) + slip+print-all suite 33 pass, full suite exit 0. disp_total==true_total ทุกคน (สุภาพ/พชร/ประจัก).

**GOTCHA print-all 500 (ซ้ำรอย [[project-fuel-b7b20-grade]]):** เพิ่ม context key ใหม่ → ต้องส่งผ่าน `{% with %}` ใน `payroll_print_all.html` (เพิ่ม `fuel_merge_by_job=r.ctx.fuel_merge_by_job`) + `|default({})` ใน body. ไม่งั้น UndefinedError ทุกครั้งที่มีบิลน้ำมัน.

**GOTCHA DEPLOY (คอขวดจริงรอบนี้) — อีก session แก้ payroll.py พร้อมกัน:** working tree มี `services/payroll.py` แก้ค้าง (BigC ลาหยุด/อนุโลม `full_blob_parts`) ของ session อื่น. **`deploy_mvp.sh` copy ทั้ง `services/` + `templates/` dir → จะลาก payroll.py ที่ยังไม่เสร็จขึ้น production.** โอสั่ง "อย่าทับ/ชน session อื่น". แก้: **deploy แบบ surgical — scp เฉพาะ 3 ไฟล์ของเรา** (payroll_slip.py + _slip_body.html + payroll_print_all.html) + `_deploy_remote.ps1` แล้วรัน cutover เอง (มี marker `fuel_merge_by_job`). **ไม่ copy ทั้ง dir, ไม่ --with-db** → server payroll.py(เก่า)+app.db ไม่แตะ. พิสูจน์หลัง deploy: server `full_blob_parts`=False (ไม่ได้ ship ของเขา). + ระหว่างทาง session อื่น commit payroll.py ลง main (6435913) → `git checkout main` ทำ working-tree revert งานเรา (อยู่บน branch แยก ปลอดภัย) merge branch เข้า main ทีหลังได้สะอาด ([[reference-branch-switch-during-session.md]]).

related: [[project-fuel-b7b20-grade]] [[project-slip-fuel-deduct-clarity]] [[project-slip-offtable-fuel-display]] [[reference-deploy-mvp-selfverify]] [[feedback-merge-and-deploy-without-preview]]
