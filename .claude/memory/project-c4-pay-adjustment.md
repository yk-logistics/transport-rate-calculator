---
name: project-c4-pay-adjustment
description: C4 ค่าเที่ยวตกหล่น/จ่ายตามหลัง DONE 3ก.ค. — PayAdjustment v36; แก้ tfd ในรอบ finalized ผ่าน grid → ตั้งยอดอัตโนมัติ → engine บวก/หักรอบถัดไป idempotent
metadata: 
  node_type: memory
  type: project
  originSessionId: 742a8c2c-bba6-475f-bb99-ce05aba9b6ba
---

**C4 DONE 3 ก.ค. 2026 (งานเงินแตะ engine — Fable; runbook docs/PAY_ADJUSTMENT_RUNBOOK.md):**
flow: แก้ trip_fee_driver ในหน้า /daily ของแถวที่อยู่ช่วงรอบ **finalized** → grid-save ตั้ง `PayAdjustment` (v36) อัตโนมัติ (Δ=ใหม่−เก่า, source_run=รอบปิด) → กล่องฟ้าใน /payroll/<id> เห็น pending + ยกเลิกได้ → `compute_pay_run` ดูดเข้า other_income(+)/other_deduction(−) ของรอบใหม่ + mark applied + note "ตกหล่นจากรอบก่อน" + กล่องเขียวสรุป

**กติกา engine (`_apply_pay_adjustments` ใน services/payroll.py):**
- idempotent: recompute รอบเดิม = ดูดชุด applied ของรอบนั้นกลับมาใหม่ (items ถูกลบตอน recompute) — ไม่ double ไม่หาย
- ไม่ดูดเข้ารอบเก่า: เฉพาะรอบ period_end ใหม่กว่ารอบต้นเหตุ + ไซท์เดียวกัน
- ดู trip_fee_driver ตัวเดียว เพราะ engine จ่ายจาก Σ tfd ทุก pay_mode (revenue=ฝั่งบิล)
- คนไม่มีเดลี่ในรอบใหม่ → engine ข้ามคน → pending ค้างรอรอบถัดไป (ไม่หาย)

เทสต์ 7 ตัว tests/test_pay_adjustment.py (จ่ายเพิ่ม/หักคืน/ไม่มีpending=เดิมเป๊ะ/recomputeไม่double/ไม่เข้ารอบเก่า/grid-saveสร้างเฉพาะรอบปิด/cancel) — **เคสจริงแรก: ราคา AYU ที่โอจะแก้ทีหลัง (แผนบอกไว้ตอนปิดรอบ มิ.ย.) ให้ตรวจตาม runbook §วิธีตรวจย้อนกลับ + net_guard**

related: [[project-jun-close-3sites]] [[project-master-plan-jul26]]
