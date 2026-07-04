---
name: project-slip-cancel-remark-leak
description: "สลิปงานยกเลิกรั่ว remark \"ค่าเที่ยว=1200\" ออกหน้าคนขับ — แก้โชว์ \"รถจอด\" แทน (DONE+deployed)"
metadata: 
  node_type: memory
  type: project
  originSessionId: f9e14b24-a2e2-4523-8f07-25bd5c5ed620
---

DONE+deployed 29มิ.ย. (main a33c683): งานที่ถูกตัดออกจากค่าจ้าง (เก็บเงินลูกค้าได้แต่ไม่จ่ายคนขับ) เก็บของเดิมไว้ใน `dailyjob.remark` = `[งานยกเลิก-ตัดออกจากค่าจ้าง] เดิม: ... ค่าเที่ยว=1200`. สลิปเดิม (template `_slip_body.html` loop ปกติ) โชว์ remark นี้ออกหน้าคนขับ → คนขับเห็นเลขค่าเที่ยวที่ไม่ได้จ่าย = **อันตราย** (โอแจ้ง).

**เคสจริง:** สุภาพ(id100)/นิพล(id97) 26/5/2026 KAO ตู้ยกเลิก — เงินถูกแล้ว (rev=0 fee=0 override=0 status=รถจอด) แค่ remark รั่ว. = เคสเดียวกับ [[project-lcb-jun-audit-round2]].

**Fix (display-only, ไม่แตะเงิน):** helper ใน `services/payroll_slip.py`:
- `slip_route_cell(r)` = route จริง หรือ `status_code` (รถจอด) แทนขีด —
- `slip_route_remark(r)` = remark ที่ปลอดภัย; **remark ขึ้นต้น `[` = โน้ตภายใน ไม่โชว์**.
ใส่ใน ctx (`route_cell`/`route_remark`), แก้ `_slip_body.html:99`. โอเลือก "โชว์รถจอด ไม่โชว์ remark".

**GOTCHA:** print-all (`payroll_print_all.html`) include `_slip_body.html` ผ่าน `{% with %}` — **ต้องเติม route_cell+route_remark ใน with block** ไม่งั้น 500 (UndefinedError) เหมือน gotcha fuel_grade_by_job ของ [[project-fuel-b7b20-grade]]. tests `test_slip_cancelled_job_no_leak.py` 7 ผ่าน + slip suite 24 ไม่ regression. mixed-mode loop ไม่รั่ว (โชว์ customer_name_raw ไม่ใช่ remark) ปล่อยไว้.
