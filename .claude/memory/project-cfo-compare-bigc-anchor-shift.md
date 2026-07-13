---
name: project-cfo-compare-bigc-anchor-shift
description: "CFO เทียบทุกไซท์ โหมดรอบจ่าย: BIGC anchor เดือน M = วิ่งเดือน M-1 (โอยืนยัน 13ก.ค.) — _compare_cycle_period ใน main.py"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0c9c0dfc-38d0-40a0-9a66-dfaa453bd45b
---

โอถาม 13ก.ค.: "BigC รอบจ่ายตามไซท์ เลือกเดือน 6 ต้องโชว์งานวิ่งเดือน 5 ใช่ไหม" — **ใช่** และเดิมระบบทำผิด (map BIGC = ปฏิทินเดือน anchor ตรงๆ → แถว BIGC เป็น 0)

**กติกาโดเมน (ยืนยันจากการปิดรอบจริง):** งวดจ่าย "เดือน 6" = {LCB tag 2026-06 (16/5–15/6), AYU tag 2026-06 (26/5–25/6), **BIGC tag 2026-05 (วิ่ง 1–31 พ.ค. จ่าย 1 ก.ค.)**} — ตรงกับ finalize ปิดรอบ มิ.ย. (LCB#2/AYU#18/BIGC#4) และ [[project-bigc-may-payroll]] ("BigC เดือน มิ.ย." ของโอ = วิ่ง พ.ค.) เพราะ **cycle_tag BIGC = เดือนวิ่ง** ต่างจาก LCB/AYU ที่ tag = เดือนที่รอบจบ

**Fix (13ก.ค.):** `main._compare_cycle_period(site, y, m)` — BIGC ถอย 1 เดือนก่อนเรียก `_cycle_period_for_tag`; ลิงก์กดชื่อไซท์ในหน้า compare พา `row["link_month"]` (tag ที่โชว์จริง) ไปหน้า single ให้ตัวเลขตรงกัน; banner อธิบายใหม่. เทสต์ `tests/test_finance_compare_bigc_cycle.py` (2 ตัว — helper mapping + render หน้าจริงผ่าน TestClient)

**ระวัง:** โหมด single-site BIGC dropdown รอบยังใช้ tag = เดือนวิ่งตรงๆ (label มีช่วงวันที่ชัดอยู่แล้ว ไม่กำกวม) — อย่าไปเลื่อนซ้ำ. `/finance/pnl` + `/finance/vehicles` ยังเป็นปฏิทินล้วนตามเดิม (ดู [[project-cfo-cycle-vs-calendar]])
