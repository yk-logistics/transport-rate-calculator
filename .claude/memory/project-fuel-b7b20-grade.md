---
name: project-fuel-b7b20-grade
description: เก็บเกรดน้ำมัน B7/B20 ต่อบิล + ป้ายบนสลิป + สลิปไม่โชว์วันที่ซ้ำ (ไม่ทำ auto-merge)
metadata: 
  node_type: memory
  type: project
  originSessionId: 3199fe8f-6b87-44c8-94f9-2b684fc66bf4
---

DONE+deployed 29มิ.ย. (ก่อนจ่ายเงินเดือน): โอถามเรื่องน้ำมันเติมครั้งเดียวได้ B7+B20 พร้อมกัน แต่มาร์ค(คนคีย์)ลงต่อบรรทัด → ยอดตกคนละวัน คนขับงง.

**สำคัญ — ไม่ทำ auto-merge:** ข้อมูลจริง LCB มิ.ย. = FuelTxn ผูก DailyJob 1:1; "วันเดียว 2 ยอดน้ำมัน" ส่วนใหญ่เป็น **2 เที่ยวงานจริง** ไม่ใช่ B7/B20. กฎจับ "วันเดียว+คันเดียว+ราคา B20+ราคา B7" เจอ 57 คู่ แต่ ~26 เป็น 2 เที่ยวจริง (rev>0 ทั้งคู่ คนละ route) → **รวมอัตโนมัติ = ผิดเกือบครึ่ง**. ระบบแยกไม่ได้ (หน้าตาข้อมูลเหมือนกัน). โอเลือก: ไม่ทำ merge, ยึดตามคนคีย์.

**ทำแทน 3 อย่าง (ไม่แตะเงินเลย — net+fuel fingerprint เท่าเดิมเป๊ะ):**
1. **`FuelTxn.fuel_grade`** (B7/B20/"" ป้ายเกรด, schema **v31** additive) — ไม่เข้าสูตรเงิน.
2. **สลิป**: ป้าย B7/B20 ท้ายช่องน้ำมัน + ยุบวันที่ซ้ำ (โชว์วันครั้งเดียวต่อกลุ่ม ใช้ Jinja `loop.previtem`). `_slip_body.html` ใช้ `{% set _grades = fuel_grade_by_job|default({}) %}`.
3. **/fuel** กรอก/แก้เกรด (fuel_form dropdown + fuel_list Tabulator column `editor:"list"`) + import LCB ตั้งเกรดอัตโนมัติ.

**แยกเกรดจากราคา (โอยืนยัน B20 ถูกกว่า B7 ~6฿/L):** `services/fuel_grade.py` — **relative-per-group เป็นหลัก** (ถูกกว่าในกลุ่มวันเดียว+คันเดียว=B20, gap≥3฿) + absolute B20_MAX_HINT=38 เป็น **fallback เท่านั้น** (โอเตือน: เลขบาทตายตัวพังเมื่อราคาผันผวน). histogram จริง: B20 cluster 35-37, B7 cluster 40-44, ช่อง 38-39 ว่าง. backfill: `tools/backfill_fuel_grade.py` (dry-run default, --commit, เซฟเฉพาะ fuel_grade ของแถวว่าง, idempotent). ผล: B7=902 B20=761 ทุกไซต์.

**GOTCHA ที่เจอ:**
- **print-all 500 (จับโดย final whole-branch review, per-task review พลาด):** `payroll_print_all.html` มี `{% with %}` block ลิสต์ ~21 keys ส่งเข้า `_slip_body.html` แต่ลืม `fuel_grade_by_job` → `UndefinedError` ทุกรอบที่มีบิลน้ำมัน (หน้าปริ้นสลิปก่อนจ่ายเงิน!). แก้: เพิ่ม `fuel_grade_by_job=r.ctx.fuel_grade_by_job` ใน with + `|default({})` ใน body. **บทเรียน: แก้ context สลิปต้องอัปเดต {% with %} ใน print-all ด้วยเสมอ** (cross-task gap ที่ per-task review มองไม่เห็น).
- **deploy restart พลาด (ซ้ำ [[reference-mvp-deploy-restart-gotcha]]):** deploy_mvp_to_server.sh copy templates สำเร็จแต่ app ไม่ restart จริง (pid เดิม) → migration v31 ไม่รัน (fuel_grade column ไม่มีบน server) ทั้งที่ template ใหม่ขึ้นแล้ว = mix อันตราย. แก้: kill by 8010-listener PID + Start-ScheduledTask → newpid + FUEL_GRADE_COL=YES. **ต้อง verify migration applied บน server เสมอ ไม่ใช่แค่ template.**
- **backfill บน server:** deploy script ไม่ copy tools/ → scp `backfill_fuel_grade.py` แยก + รันด้วย `PYTHONPATH=<app>` (tool's parents[1]/app path math ผิดบน server layout). server net_fp ก่อน/หลัง = เท่าเดิม (MONEY_UNCHANGED=True).
- **pre-existing test fail (ไม่ใช่ของงานนี้):** ตอนแรกวินิจฉัยผิดว่า 2 ตัว fail เพราะ `#333` CSS collision — **ผิด**. ความจริง: (1) `test_driver_slip_hides_kb_and_real_revenue` fail เพราะ print-all 500 (fuel_grade_by_job bug) → **หายเองหลังแก้ print-all** + มี `_slip_body()` helper strip `<style>` อยู่แล้ว KB ไม่ leak (333 ใน body=0); (2) `test_boss_slip_shows_kb_and_real_revenue` fail จริง = **boss slip (?for=boss) หายคอลัมน์ ค่าขนส่งจริง/ราคากลาง/KB ตอน Waybill redesign** (route+`_slip_daily_rows(is_boss)` ยังคำนวณ show_central/rev_real/kb แต่ `_slip_body.html` ไม่ render — vestigial). **ฝั่งซ่อน (คนขับ) ปลอดภัยครบ มีแค่ฝั่ง boss-เห็น ที่หาย.** โอ 29มิ.ย.: **อีก session กำลังทำ boss slip อยู่ — อย่าแตะ.**

built via subagent-driven-development (6 tasks, haiku impl for transcription + sonnet integration + opus final review). spec/plan: docs/superpowers/{specs,plans}/2026-06-29-fuel-b7b20-*. related: [[project-mao-fuel-tank-measure]], [[project-fuel-exclude-from-driver]], [[reference-mvp-deploy-restart-gotcha]], [[project-slip-one-page-per-driver]].
