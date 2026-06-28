---
name: project-bigc-daily-import
description: "BIGC daily per-trip data imported to system (Goal 2); engine-pay (Goal 1) still pending โอ's formula"
metadata: 
  node_type: memory
  type: project
  originSessionId: 680ccdb1-b9cb-48f4-aff9-02a774812328
---

DONE 29มิ.ย. (merged main, NOT yet deployed to server): นำเดลี่รายเที่ยว BIGC 6 เดือนเข้าระบบเป็น DailyJob (เหมือน LCB) — ก่อนหน้านี้ระบบมีรายเที่ยวแค่ LCB. นี่คือ "ข้อ 2" ของ handoff. **ใช้เพื่อ CFO/รายงานรายเที่ยวเท่านั้น — ไม่ใช่ prerequisite ของ payroll.**

⚠️ **"ข้อ 1" (engine คิดเงินเดือน BIGC เอง) = โอ-confirmed ว่า "ไม่ทำ" ถาวร** (ดู `docs/ground-truth/bigc_engine_status.md` 2026-06-28): BIGC base/เที่ยว/น้ำมัน เป็นดุลพินิจรายเดือน โอกรอกเองใน Excel ไม่มีสูตร → **ลอก net (คอลัมน์ O ชีต รวม YK) คือวิธีที่ถูกต้องที่สุด**, engine `bigc_monthly` ที่มีอยู่จะ**ผิด**ถ้าใช้. base_salary field=0 ตั้งใจ. (memory เก่า [[project-bigc-may-payroll]] ที่ว่า "engine คิดจาก DailyJob ได้" = ล้าสมัย ground-truth override.) อย่ารัน `import_bigc_fuel_rate.py` กับ payrun ลอกยอด (auto compute ทับ COPY-LOCK ไม่กัน).

**Tool:** `ProjectYK_System/tools/import_bigc_daily.py` (TDD, 10 tests ใน `app/tests/test_import_bigc_daily.py`). รัน: `--dry-run` / `--wipe-prior` / `--cycle YYYY-MM`. Guard: `_bigc_guard_snapshot.py before|after` (เช็ก BIGC net ไม่ขยับ + LCB ไม่แตะ). Link audit: `_bigc_link_report.py`.

**ไฟล์ต้นทาง BIGC (ตรวจแล้ว — ต่างจาก LCB):** ไฟล์ละเดือน `2564Daily Report (04.21).xlsx` ชีต `เดือน06.21`, หัวตาราง **2 แถวซ้อน** (รวม top+bottom เป็นชื่อเดียว). **ไฟล์อยู่ในโฟลเดอร์เดือนถัดไป** (1.Jan=ข้อมูล ธ.ค., …, 6.Jun=ข้อมูล พ.ค.). cycle_tag=YYYY-MM ของเดือนข้อมูล (รอบ BIGC=1→สิ้นเดือน). column-map หา by header text. source tag=`bigc_<cycle_tag>`.

**ผล import:** 6 cycle (2025-12..2026-05) = 2,381 DailyJob + 810 FuelTxn. FuelTxn ทุกบิล `exclude_from_driver=True` (BIGC เงินเดือน ไม่หักน้ำมันคนขับ — โอเลือก). counts/rev/trip ต่อเดือนตรง dry-run. **GUARD OK: BIGC payrun net 6 รอบเท่าเดิมทุกบาท, LCB ยัง 1116.** CFO `/finance/revenue` เห็น BIGC แล้ว (พ.ค. rev 31,070.03/462 เที่ยว/9 คัน, ลูกค้า="(ไม่ระบุ)" เพราะชีต BIGC ไม่มีคอลัมน์ลูกค้า).

**GOTCHA — r0 totals cell ไม่น่าเชื่อถือ:** แถวยอดรวม (r0) ในชีต BIGC บางไฟล์ STALE (ธ.ค. r0 trip=14,300 แต่ข้อมูลจริง 404 แถว=123,300). reverse-check ที่ถูก = importer sum == raw column-sum ของแถวข้อมูล (ตรงทุกเดือน). อย่าใช้ r0 เป็น baseline.

**ค้าง — 3 ชื่อ unlinked (ให้ โอ ยืนยัน):** ชรินทร์(54แถว,71-8009,trip 18,300)/วิทัศน์(14,71-8004,2,200)/โกสินทร์(42,71-8003,13,850) — โผล่เฉพาะ พ.ค.2026 มี trip จริง แต่ไม่มีใน employee table เลย → น่าจะคนใหม่ พ.ค. (ไม่ใช่ cross-site/typo). อีก 13/16 ชื่อผูก emp BIGC ได้ด้วยชื่อต้น. **ยังไม่ผูก driver_id จริง** — รอ โอ ยืนยัน (ไม่เดา map). [[project-multisite-payroll-onboard]] [[project-cfo-revenue-drilldown]]

**ประเด็น column E ของชีต DAILY (เพื่อ CFO เท่านั้น — ไม่กระทบ payroll):** ชีต `2564Daily Report` column E (index 4, หัว="รับตู้/สถานที่") จริง ๆ เป็น **รหัสสถานะงาน/ประเภทเที่ยว** (Oatside 141, 2BigC 78, 2++ 33, 2BH 29, ABF 18, รับรถ 11=รถจอด, Homepro, 1BH, 2DV) คล้าย `status_code` ของ LCB. **importer ใส่ E ลง `origin` → `status_code` ว่าง 2,381 แถว → CFO โชว์ลูกค้า BIGC="(ไม่ระบุ)"**. ⚠️ ระวังสับสน: นี่คือ E ของชีต *เดลี่*; ส่วน "คอลัมน์ E" ใน `bigc_engine_status.md` = E ของชีต *รวม YK* = เงินเดือน (คนละชีต). **ผลกระทบจำกัดแค่การจัดกลุ่มใน CFO — ไม่กระทบ payroll (BIGC ลอก net ไม่คิดจากเดลี่).** ถ้าอยากให้ CFO จัดกลุ่มสวยขึ้น: map E→`status_code` แล้ว re-import `--wipe-prior` — priority ต่ำ รอ โอ.

**TODO ถัดไป (priority):** (1) deploy ขึ้น server (overwrite app.db ผ่าน Tailscale) — รอ โอ สั่ง (อาจรอ AYU/column-E ให้ deploy ทีเดียว). (2) มิ.ย. ยังไม่มีไฟล์เดลี่ BIGC (ล่าสุดจบ 31 พ.ค.; ไฟล์ มิ.ย.อยู่โฟลเดอร์ 7.Jul ที่ยังไม่มี) — import เมื่อไฟล์ออก. (3) link driver_id 13 ชื่อ + เพิ่ม emp 3 คนใหม่ — รอ โอ (อาจไม่จำเป็นถ้าใช้ CFO ระดับไซต์). (4) AYU import (Daily Report.xlsx ไฟล์เดียวหลายแท็บ หัวแถวเดียว — ง่ายกว่า BIGC). (5) [optional/low-pri] column E→status_code เพื่อ CFO grouping. **ไม่มีข้อ "engine คิดเงินเดือน BIGC" แล้ว — ground-truth ปิด: ลอก net ถาวร.**
