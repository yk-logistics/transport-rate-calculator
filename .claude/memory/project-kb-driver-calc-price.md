---
name: project-kb-driver-calc-price
description: "KB (ใต้โต๊ะ) + ราคาคำนวณคนขับ — แยกราคาวางบิลจริงออกจากราคาคิดเงินคนขับ; built on branch, awaiting โอ merge + recompute decision"
metadata: 
  node_type: memory
  type: project
  originSessionId: 03ab1379-4cf3-4cb5-a780-e00d14128f62
---

แยก "ราคาวางบิลลูกค้า" ออกจาก "ราคาคิดเงินคนขับ" — รองรับ KB (commission ใต้โต๊ะ จ่ายคนจ่ายงานฝั่งลูกค้า) และราคากลาง override.

**สถานะ:** DONE+DEPLOYED 2026-06-27 — merged main (11079fc), Dev backfill+recompute เสร็จ, **ขึ้น server live แล้ว** (app.yklogistics.uk). โออนุญาตครบ. CY 23 แถวโอจะกรอกเองในระบบ live.

**Server deploy (สำคัญ — 2 gotcha):** (1) server app.db แยกจาก Dev → ต้อง backfill+recompute บน server ซ้ำ (Dev ไม่ไปเอง). (2) **รันสคริปต์ payroll บน server ต้องใช้ VENV python** `C:\Users\yklog\YK_MVP\app\.venv\Scripts\python.exe` (มี sqlmodel) — **global pythoncore-3.12 ไม่มี sqlmodel** (เคยรัน global → ModuleNotFoundError หลัง BACKUP แล้วเงียบ เพราะ ssh ซ่อน stderr; เพิ่ม `2>&1` ถึงเห็น). ลำดับ: deploy code → restart by PORT-OWNER (ดู [[reference-mvp-deploy-restart-gotcha]], name-filter พลาดอีก PID เก่า 3112) → **stop app (ปลด lock) → restore backup → backfill+recompute ตอน app ดับ → restart**. server net: run1 +333,782 (=Dev, staleness fix), run2 259,888→256,907 (KB −2,981, 7 คน; server run2 baseline ต่างจาก Dev อยู่แล้ว = ปกติ, judge เทียบ server-before ไม่ใช่ Dev).

**ผล recompute:** run2 มิ.ย. = KB impact สะอาด 7 คน รวม −3,716 (−132..−1,405/คน, ถูกต้อง: เหมา (ราคา−KB)×60%). run1 พ.ค. = −327k→+334k (20 คนขึ้นหมด ไม่มีลง) — **เป็น staleness-fix gross=0 เก่า ไม่ใช่ KB** (ดู [[project-lcb-driver-extra-fees]]); recompute เลยซ่อมของเก่าด้วย. backup: app.db.bak_before_kb_backfill_* + app.db.bak_before_kb_recompute_*.

**Data model (schema v25):** `DailyJob.kb_amount` (float, seed จาก rule แก้มือได้), `DailyJob.price_override` (Optional[float], None=ใช้ revenue_customer). ตาราง `KbRule(status_code unique, default_kb, required)` seed NHL=110, MOL=100, CY=0+required.

**สูตรกลาง** `services.payroll.driver_calc_price(row)` = `(price_override ?? revenue_customer) − kb_amount`. payroll หันมาใช้ตัวนี้แทน revenue_customer 3 จุด: `_classify_lcb_days` ratio, mixed `mao_rev`, `_sum_gross_revenue`. ฝั่ง billing/finance คงใช้ revenue_customer เดิม.

**Customer key = `status_code`** (ช่อง Status ในไฟล์ LCB; Customer table ว่าง, customer_id NULL ทุกแถว — อย่าไปสร้าง customer master). NHL=161 แถว, CY=23, ปนกับ รถจอด/ลา/ซ่อม.

**กฎเงินที่โอยืนยัน:** KB ซ้อน override ได้ (override−KB). CY ต้องมี KB ทุกเที่ยว → ถ้า kb=0 เตือน (ไม่บล็อก). 10%/WHT 3% ไม่เก็บ field คำนวณสด (KB_OUR_CUT/KB_WHT ใน services/kb.py). KB โชว์แอดมินทุกคน, **คนขับไม่เห็น** (guard test).

**Preflight ก่อน recompute (ยังไม่ทำ):** `tools/backfill_kb_from_rule.py` (dry-run; จะเติม NHL 160 แถว @110) + `tools/preflight_kb_driver_price.py` (read-only). SIM หลัง backfill: gross-base ลด 15 คน รวม −17,600 (เป็นพฤติกรรมถูก — KB ไม่เคยเป็นเงินคนขับ; pay จริง×60% สำหรับเหมา). 23 แถว CY ยังลืม KB.

**Pre-existing red tests (ไม่เกี่ยว KB):** test_lcb_mixed_splits_income_and_prorates_base + test_existing_modes_net_unchanged — แดงบน main ก่อนแล้ว (ยุค [[project-lcb-driver-extra-fees]]).

spec: docs/superpowers/specs/2026-06-27-kb-driver-calc-price-design.md
plan: docs/superpowers/plans/2026-06-27-kb-driver-calc-price.md
related: [[project-lcb-mixed-mode]] [[project-lcb-driver-extra-fees]] [[project-merge-daily-grid]]
