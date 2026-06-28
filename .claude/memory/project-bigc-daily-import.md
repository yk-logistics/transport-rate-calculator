---
name: project-bigc-daily-import
description: "BIGC daily per-trip data imported to system (Goal 2); engine-pay (Goal 1) still pending โอ's formula"
metadata: 
  node_type: memory
  type: project
  originSessionId: 680ccdb1-b9cb-48f4-aff9-02a774812328
---

DONE 29มิ.ย. (merged main, NOT yet deployed to server): นำเดลี่รายเที่ยว BIGC 6 เดือนเข้าระบบเป็น DailyJob (เหมือน LCB) — ก่อนหน้านี้ระบบมีรายเที่ยวแค่ LCB. นี่คือ "ข้อ 2" ของ handoff; "ข้อ 1" (engine คิดเงินเดือน BIGC เอง) ยังไม่ทำ — ต้องถาม โอ ขอสูตรจ่ายก่อน (BIGC เป็นพนักงานเงินเดือน คอลัมน์ `เงินเดือน` ในชีต, ไม่มีสูตร base/route → ลอก net จากแบงค์ปลอดภัยกว่า).

**Tool:** `ProjectYK_System/tools/import_bigc_daily.py` (TDD, 10 tests ใน `app/tests/test_import_bigc_daily.py`). รัน: `--dry-run` / `--wipe-prior` / `--cycle YYYY-MM`. Guard: `_bigc_guard_snapshot.py before|after` (เช็ก BIGC net ไม่ขยับ + LCB ไม่แตะ). Link audit: `_bigc_link_report.py`.

**ไฟล์ต้นทาง BIGC (ตรวจแล้ว — ต่างจาก LCB):** ไฟล์ละเดือน `2564Daily Report (04.21).xlsx` ชีต `เดือน06.21`, หัวตาราง **2 แถวซ้อน** (รวม top+bottom เป็นชื่อเดียว). **ไฟล์อยู่ในโฟลเดอร์เดือนถัดไป** (1.Jan=ข้อมูล ธ.ค., …, 6.Jun=ข้อมูล พ.ค.). cycle_tag=YYYY-MM ของเดือนข้อมูล (รอบ BIGC=1→สิ้นเดือน). column-map หา by header text. source tag=`bigc_<cycle_tag>`.

**ผล import:** 6 cycle (2025-12..2026-05) = 2,381 DailyJob + 810 FuelTxn. FuelTxn ทุกบิล `exclude_from_driver=True` (BIGC เงินเดือน ไม่หักน้ำมันคนขับ — โอเลือก). counts/rev/trip ต่อเดือนตรง dry-run. **GUARD OK: BIGC payrun net 6 รอบเท่าเดิมทุกบาท, LCB ยัง 1116.** CFO `/finance/revenue` เห็น BIGC แล้ว (พ.ค. rev 31,070.03/462 เที่ยว/9 คัน, ลูกค้า="(ไม่ระบุ)" เพราะชีต BIGC ไม่มีคอลัมน์ลูกค้า).

**GOTCHA — r0 totals cell ไม่น่าเชื่อถือ:** แถวยอดรวม (r0) ในชีต BIGC บางไฟล์ STALE (ธ.ค. r0 trip=14,300 แต่ข้อมูลจริง 404 แถว=123,300). reverse-check ที่ถูก = importer sum == raw column-sum ของแถวข้อมูล (ตรงทุกเดือน). อย่าใช้ r0 เป็น baseline.

**ค้าง — 3 ชื่อ unlinked (ให้ โอ ยืนยัน):** ชรินทร์(54แถว,71-8009,trip 18,300)/วิทัศน์(14,71-8004,2,200)/โกสินทร์(42,71-8003,13,850) — โผล่เฉพาะ พ.ค.2026 มี trip จริง แต่ไม่มีใน employee table เลย → น่าจะคนใหม่ พ.ค. (ไม่ใช่ cross-site/typo). อีก 13/16 ชื่อผูก emp BIGC ได้ด้วยชื่อต้น. **ยังไม่ผูก driver_id จริง** — รอ โอ ยืนยัน (ไม่เดา map). [[project-multisite-payroll-onboard]] [[project-cfo-revenue-drilldown]]

**⚠️ ประเด็นสำคัญสุดสำหรับ session ถัดไป — column E (สถานะงาน/costing key):** BIGC ชีต column E (index 4, หัว="รับตู้/สถานที่") **ไม่ใช่ origin จริง** แต่เป็น **รหัสสถานะงาน/ประเภทเที่ยว** (ค่า: Oatside 141, 2BigC 78, 2++ 33, 2BH 29, ABF 18, รับรถ 11(=รถจอด), Homepro, 1BH, 2DV) — เทียบได้กับ `status_code` ของ LCB (KLND/CJ/รถจอด) ที่เป็น costing key. **ตอนนี้ importer ใส่ E ลง `origin` → `status_code` ของ BIGC ว่างหมด 2,381 แถว** → CFO โชว์ลูกค้า BIGC="(ไม่ระบุ)", และ engine "costing-from-status" ของ [[project-bigc-may-payroll]] ยังไม่มี field ให้คิด. parallel session ก็เจอ bug เดียวกัน ("เขา map E→origin ผิด"). **FIX (รอ โอ/engine-session เคาะ field ปลายทาง):** เปลี่ยน map E→`status_code` ใน import_bigc_daily.py แล้ว re-import `--wipe-prior` (guard พิสูจน์ net ไม่ขยับ). ไม่ทำเองคืนนี้เพราะเป็น design ของฝั่ง costing + มี parallel session ถืออยู่ (ไม่เดา money-mapping).

**TODO ถัดไป:** (1) **[สำคัญสุด] เคาะ column E → status_code + re-import** (ดูด้านบน) — unblock engine costing. (2) มิ.ย. ยังไม่มีไฟล์เดลี่ BIGC (ล่าสุดจบ 31 พ.ค.; ไฟล์ มิ.ย.จะอยู่โฟลเดอร์ 7.Jul ที่ยังไม่มี) — import เมื่อไฟล์ออก. (3) deploy ขึ้น server (overwrite app.db ผ่าน Tailscale) — รอ โอ สั่ง. (4) link driver_id 13 ชื่อ + เพิ่ม emp 3 คนใหม่ (ชรินทร์/วิทัศน์/โกสินทร์) — รอ โอ ยืนยัน. (5) AYU import (Daily Report.xlsx ไฟล์เดียวหลายแท็บ หัวแถวเดียว — ง่ายกว่า BIGC). (6) ข้อ 1 engine pay — รอสูตร โอ.
