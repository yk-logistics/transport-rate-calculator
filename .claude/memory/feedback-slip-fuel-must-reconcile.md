---
name: feedback-slip-fuel-must-reconcile
description: "กฎโอ: สลิปคนเหมาน้ำมัน — ผลรวมน้ำมันในตาราง ต้อง = น้ำมันหักจริง (fuel_cost_self); ส่วนต่างต้องมีบรรทัดชี้แจง ห้ามหมก"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

โอสั่ง 30มิ.ย. (หลังเจอเรวัตร/ธัชชนพลน้ำมันซ่อนหลายรอบ): **บนสลิปคนเหมาน้ำมัน (mao) ผลรวมคอลัมน์น้ำมันในตารางเดลี่ ต้องเท่ากับ "น้ำมันที่หักจริง" (fuel_cost_self / fuel_deducted_amt) เสมอ**. ถ้าไม่ตรง (มีบิลพิเศษ ยกยอด/ทำคืน/วัดถัง/handover/manual ที่ job fuel_amount=0) → **ต้องมีบรรทัด off-table ชี้แจงส่วนต่างให้ครบทุกบาท ห้ามหมก/ซ่อน**.

**Why:** คนขับเหมาน้ำมันต้องเห็นว่าหักอะไรบ้างครบ ไม่งั้นไม่เชื่อใจยอด (เจอ "น้ำมันซ่อน" 3 รอบ: เรวัตร handover 4,989, ธัชชนพล ยกยอด/ทำคืน, ส่วนต่างตาราง≠หักจริง).

**How to apply:** รัน **`python ProjectYK_System/tools/fuel_slip_reconcile.py [run_id]`** (read-only, เขียนแล้ว) — flag คน mao ที่ Σ(DailyJob.fuel_amount + off-table) ≠ fuel_cost_self. ทุกครั้งที่แตะน้ำมัน mao หรือก่อนปิดรอบ. ถ้า MISMATCH → หาบิลตกหล่นทำให้โผล่ (ขยาย _OFFTABLE_FUEL หรือแก้ data).

**GOTCHA ที่ทำให้ mismatch (เจอจริง):** ตอน**ย้ายน้ำมันข้ามคน/รถ** ต้องแก้ **2 ที่**: (1) FuelTxn (driver_id/plate/daily_job_id → คุม fuel_cost_self) **และ** (2) **DailyJob.fuel_amount/fuel_liter** บน job เดิม (→ คุมที่สลิปโชว์ในตาราง). ลืม (2) → fuel_cost_self ลดถูกแต่สลิปยังโชว์ของเดิม = ส่วนต่างซ่อน. (เคสเรวัตร: ย้าย 4,400 ไปวัชร์นล แต่ลืม zero fuel_amount job 5088/5089 → diff +4,400). off-table logic [[project-slip-handover-manual-offtable]] (_OFFTABLE_FUEL=tank_measure/handover/manual + job fuel_amount=0). related: [[project-slip-offtable-fuel-display]], [[project-ayu-mao-pertrip-pay]], [[project-fuel-move-0556-0560]]
