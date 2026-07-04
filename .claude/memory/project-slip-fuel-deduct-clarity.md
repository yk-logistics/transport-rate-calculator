---
name: project-slip-fuel-deduct-clarity
description: Slip shows fuel liters + clearly separates น้ำมันหักจริง vs ไม่หัก(ถังแรก)/วัดถัง
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย.: สลิปเคยโชว์น้ำมันทุกบรรทัดในตาราง + รวมน้ำมัน(ทั้งหมด) แต่ **ยอดหักจริง (`fuel_cost_self`) ไม่รวมบิลถังแรก(ไม่หัก)+วัดถัง** → คนขับเข้าใจผิดว่าหักหมด (โอ: "เขาคงไม่นั่งบวกทีละบรรทัด"). แก้ทั้ง 2 สลิป:

**กลไก (verified):** `fuel_cost_self` = Σ FuelTxn ที่ `exclude_from_driver=False`. บิล `exclude_from_driver=True` = ถังแรก/ก่อนวิ่ง ไม่หัก ([[project-fuel-exclude-from-driver]]). บิล `source=mao_tank_measure` (`daily_job_id=None`) = วัดถัง หักจริงแต่ไม่โผล่ในตารางเดลี่ ([[project-mao-fuel-tank-measure]]).

**`build_payroll_slip_context` เพิ่ม:** `fuel_excluded_amt` (Σไม่หัก), `fuel_deducted_amt/_liter` (หักจริง), `tank_measure_rows` (บิลวัดถัง off-table), `excluded_job_ids` (daily_job_id ของบิลไม่หัก → mark บรรทัด).

**`payroll_slip.html` (หน้ารายคน, normal table):**
- คอลัมน์ น้ำมัน(L) มีอยู่แล้ว; mark "ไม่หัก"(เขียว) บรรทัด `r.id in excluded_job_ids`
- แถววัดถัง (เหลือง "🛢 วัดถัง") เพิ่มจาก tank_measure_rows
- footer 2 บรรทัด: "รวมน้ำมันในตาราง(ทั้งหมด)" vs **"น้ำมันที่หักจริง"** (=item.fuel_cost_self, แดง) + note "ไม่หัก X (ถังแรก/ก่อนวิ่ง)"
- (mixed-mode table มี หัก/บริษัทออก per-row อยู่แล้ว)

**`payroll_print_all.html` (print/ZIP):** เพิ่ม L ต่อบิลในคอลัมน์น้ำมัน + note ใต้ตาราง "น้ำมันที่หักจริง X บาท (Y L) · ไม่หัก Z (ถังแรก/ก่อนวิ่ง)". print route (`/payroll/{id}/print`) ส่ง fuel fields จาก slip_ctx (reuse single source) + `_slip_daily_rows` เพิ่ม `fuel_liter`.

verified headless Chrome: สุภาพ(lcb_mao) ตาราง 37,119 → **หักจริง 28,831 + ไม่หัก 8,288** ชัดเจน ทั้ง 2 สลิป. deploy code-only + verify ไฟล์ server (SLIP_OK ไม่ revert).

related: [[project-fuel-exclude-from-driver]], [[project-mao-fuel-tank-measure]], [[project-payroll-slip-petty-itemize]], [[project-slip-route-display]]