---
name: project-office-no-deposit
description: "พนักงานออฟฟิสไม่หักเงินประกันตน — code guard + data fix AYU#18, deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 47a74c78-604f-4986-9467-2650bdf9de02
---

DONE+deployed 30 มิ.ย. (main 445ab0b): **เงินประกันตน (deposit_install 1000/mo) หักเฉพาะคนขับ — พนักงานออฟฟิสไม่หัก**.

**Code guard** (payroll.py ~line 1238, ใน calc_one_employee): เพิ่ม `is_office = (employee.role=="office") or (mode=="office_monthly")`; ข้ามการหัก deposit ถ้า is_office. คนขับ logic เดิมไม่แตะ.

**Office staff = id 114–125** (role=office, mode=office_monthly). โอ list ชื่อ 12 คน (รัตนาวดี/จุฑามาศ/สมภพ/Nan khan/หัสยา/พิชญา/บรรเจิด/พบ/วิชัย/ศราวุธ/สมบูรณ์ไพราม + พงษกาญจน์) ตรงกับ id114-125 พอดี. ซองอู126/ทิว130 อยู่ใน list ด้วยแต่ role=driver/ayu_trip tgt=0 → ไม่โดนหักอยู่แล้ว.

**Data fix (stale)**: AYU payrun#18 (draft) มี office 12 คน deposit_install=1000 ค้าง (คำนวณตอน target ยัง>0; ตอนนี้ tgt=0). **อย่า recompute payrun#18!** office items มี base_salary_earned snapshot (เช่น 40000) แต่ emp.base_salary=0 → recompute จะลบ net เป็น 0 (GOTCHA เดิม [[project-jun-payroll-ayu-bigc-status]] "office copy"). แทนที่ → แก้ data ตรง: zero deposit_install + บวก 1000 คืน net per item. net_guard: เปลี่ยน exactly 12 รายการ +1000, คนขับนิ่งหมด.

ไม่มี payrun finalized ที่มี office deposit (เช็คแล้ว = แค่ #18 draft). tests 27 pass (deposits+print_all).

**DEPLOY GOTCHA**: deploy_mvp.sh --with-db scp app.db **ก่อน** stop app → Windows lock "dest open Failure". ต้อง stop 8010 by PID (spare 8020 archiver) ด้วย EncodedCommand ก่อน แล้ว re-run --with-db. Marker check ของสคริปต์สแกนแค่ main.py+templates **ไม่สแกน services/** → marker ใน payroll.py เด้ง false FAIL (verify ตรงด้วย Select-String บน services/payroll.py แทน). live: office_items 72 with_deposit 0, public 200.
