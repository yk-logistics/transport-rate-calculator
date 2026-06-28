---
name: project-driver-pay-breakdown-daily-slip
description: แยกโชว์ ค่าเที่ยว/พิเศษ/OT/รับตู้คืนตู้ ของคนขับ ในเดลี่+สลิป; ค่าเสียเวลา=ของบริษัท. DONE+deployed 2026-06-28.
metadata: 
  node_type: memory
  type: project
  originSessionId: 02c533fb-7a28-4c02-9a0e-8fd0dafab220
---

**DONE + deployed server 2026-06-28** (branch feat/driver-pay-breakdown-daily-slip → main → Tailscale deploy). Display-only, ไม่แตะ engine เงิน/schema; gross+net ไม่เปลี่ยน.

**สิ่งที่ทำ:**
- **เดลี่** (`/api/daily/grid-data` + `daily_grid.html`): +3 คอลัมน์ **อ่านอย่างเดียว** พิเศษ/OT/รับตู้คืนตู้ ต่อแถว (sum จาก DailyJobFee ของ job ids หน้านั้น 1 query). อยู่ใน money preset + NUM_FIELDS + RIGHT_ALIGN. **ไม่อยู่ใน editable set** (ค่ามาจากตารางลูก) — แก้ที่หน้าแก้ไขงานเดี่ยว. ⚠ คอลัมน์ tuple ที่ 3 ใน ALL_FIELDS = **editable** (ไม่ใช่ defaultHidden) — visibility คุมด้วย PRESETS อย่างเดียว.
- **สลิปปริ้น 2 ไฟล์** (`payroll_slip.html` ปุ่มพิมพ์สลิปรายคน + `payroll_print_all.html` พิมพ์ทั้งหมด คนขับ/ผู้บริหาร): แตก พิเศษ/OT/รับตู้คืนตู้ ออกจากบรรทัดรวม "รายได้อื่น"; เหลือบรรทัด "รายได้อื่น" = other_income − (sp+ot+pk) เฉพาะถ้า ≠0 (กันยอดเพี้ยน). ซ่อนบรรทัดถ้า 0.
- **หน้ารวม payroll** (`payroll_detail.html`) + employee detail: มีอยู่แล้วจาก commit 9d63723 (เช้าวันเดียวกัน) — ไม่แตะ.

**กุญแจความถูกต้อง:** helper ใหม่ `classify_driver_fee(fee_type)->bucket|None` ใน services/payroll.py = single source of truth, ใช้ร่วม engine (`_sum_lcb_driver_extra_fees`) + grid endpoint → ตัวเลขเดลี่=สลิป=หน้ารวม=engine. buckets: special={special,พิเศษ,ค่าพิเศษ}, ot={ot,OT,ค่าล่วงเวลา}, pickup_return={pickup_return,รับตู้แทน}.

**ค่าเสียเวลา = ของบริษัท (โอยืนยัน):** มีจริงในข้อมูล (4 แถว 11,100฿) แต่ engine ไม่เคยนับเข้าเงินคนขับอยู่แล้ว (classify_driver_fee คืน None). โอเลือก "ไม่ต้องโชว์เลย" → ไม่โผล่ทุกหน้าจอฝั่งคนขับ. ค่ายกตู้/ผ่านลาน/คลีน/ชอร์/เข้าท่า = สำรองจ่าย เหมือนกัน. ดู [[project-lcb-driver-extra-fees]].

**Verify:** grid total == engine ทั้งรอบ LCB มิ.ย. (sp 18,800/ot 3,240/pk −150). +23 tests (classify 19 + slip breakout 4) ผ่าน. full suite 196 pass /1 fail = test_check_link_menu (pre-existing, maintenance menu, ไม่เกี่ยว). live render run2: ทุกคนแตกบรรทัดถูก ไม่มี remainder. ดู [[project-payroll-bank-print]].

**FOLLOW-UP 2026-06-28 (same day):**
1. **สลิป/หน้ารายละเอียดบน server โชว์ "—" ทั้งที่มีพิเศษ/OT** = ข้อมูลค้าง ไม่ใช่บั๊ก display. field special/ot/pickup เพิ่งมี (v29) แต่ค่าบน server เป็น 0 จน recompute. **แก้:** recompute LCB run2 (draft) บน server (backup ก่อน) → net **ไม่เปลี่ยน** 276,854.75→276,854.75, 0 คนเงินขยับ, emp89 พิเศษ 2,800+OT 100 ขึ้น, stale 14→0. **ยังเหลือ stale ที่ "ปล่อยไว้" (โอเลือก):** LCB พ.ค. (finalized, recompute เด้ง +661k) + BIGC ทุกเดือน (copied-net, recompute ลบยอด) → โชว์ใน "รายได้อื่น" ต่อไป.
2. **เพิ่มทุกช่องในหน้าเดลี่ (โอ: A+B+C เว้น เงินเบิก[อยู่สดย่อย]+เช็ครถ[ซ่อมบำรุง]).** branch feat/daily-grid-all-columns → main → deployed. **schema v30**: DailyJob +phone/shared_vehicle/receive_inv_no/bl_booking/fuel_date/gps_rate (display/อ้างอิง ไม่กระทบเงิน). กริดเพิ่มคอลัมน์ ค่าบริษัท read-only (ยกตู้/ผ่านลาน/คลีน/ชอร์/เข้าท่า/ชั่งน้ำหนัก/M-Flow จาก DailyJobFee) + ช่องอ้างอิงแก้ได้. importer xlsx เขียนช่องอ้างอิงลง field แยก (เลิกฝัง remark). +2 tests. ข้อมูลเก่ายังว่างจนกว่า re-import (แยกตัดสิน—เป็น money zone).

**⚠️ GOTCHA migration test:** `resolve_database_url()` (db_config.py) คืน `IS_SQLITE=False` **เมื่อ env DATABASE_URL ถูกตั้ง** (ไม่ดู prefix!). tests ทุกตัวตั้ง DATABASE_URL=sqlite:/// → IS_SQLITE=False → `_apply_additive_migrations` **ถูกข้าม** (tests พึ่ง create_all สร้าง table จาก model แทน). ผล: **ไม่มี test ตัวไหนเทสต์ ALTER migration เลย**. ทดสอบ migration จริงต้องรันแบบ **ไม่ตั้ง env** (default → IS_SQLITE=True). server ไม่ตั้ง DATABASE_URL → IS_SQLITE=True → migration วิ่งตอน restart (verified v30 ขึ้น server). ดู [[reference-mvp-deploy-restart-gotcha]].
