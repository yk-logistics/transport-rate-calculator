---
name: reference-payroll-close-runbook
description: runbook ปิดรอบเงินเดือนทุกไซท์ (docs/PAYROLL_CYCLE_CLOSE_RUNBOOK.md) — เขียน 5ก.ค. ให้ Opus/Sonnet ปิดรอบ LCB 15ก.ค. ได้เองหลัง Fable หมด 7/7
metadata: 
  node_type: memory
  type: reference
  originSessionId: 701a5a18-481b-4f29-9892-135e2950f72e
---

**`ProjectYK_System/docs/PAYROLL_CYCLE_CLOSE_RUNBOOK.md`** — คู่มือปิดรอบเงินเดือนฉบับรวม กลั่นจากรอบ มิ.ย. 2026 ทั้ง 3 ไซท์: กฎเหล็ก (ห้าม recompute finalized / server=จริง local=stale / ground truth=ไฟล์ xlsx), checklist ก่อนปิด 8 ข้อ (petty→fuel reconcile→preflight→เทียบไฟล์→deposit→KB→net_guard), กติกา engine ต่อโหมด, ท่า recompute ปลอดภัย (gotcha office copy), gate ตอน finalize, สลิป/เอกสารหลังปิด, ตารางเครื่องมือ, และ index memory รายเคส

ใช้เมื่อ: ปิดรอบใดๆ, แตะ engine เงิน, หรือรับมืองาน "ทำไมเงินคนนี้ไม่ตรง"

related: [[project-jun-close-3sites]], [[project-c4-pay-adjustment]], [[feedback-handoff-for-smaller-models]], [[project-fable-deadline-and-phase-p]]
