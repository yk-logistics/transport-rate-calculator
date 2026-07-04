---
name: project-ayu-daily-import
description: AYU per-trip daily imported (Jun 26 cycle); cross-site drivers left unlinked for โอ
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย.: import เดลี่รายเที่ยว AYU เข้าระบบ (prerequisite ให้ route AYU โชว์ + CFO เห็น AYU).

**ไฟล์:** `Work\Salary\2026\6.Jun\AYU\Daily โฮมโปร-ทั่วไป.xlsx` ชีท `Jun 26`. คอลัมน์ fixed (header row0): 0 วันที่/1 ทะเบียน/2 ประเภทรถ/3 พขร/**4 ลูกค้า**/**5 ขึ้นสินค้า(โหลด)**/6 รหัสสาขา/**7 ส่งสินค้า(ปลายทาง)**/8 เลขที่/9 ค่าขนส่ง/10 ค่าเที่ยว/11 ไมล์/12 ลิตร/13 ราคา/14 บาท/15 หมายเหตุ.
map: ขึ้นสินค้า→`pickup_location`, ส่งสินค้า→`destination`, ลูกค้า→`customer_name_raw`+`status_code`. route AYU=pickup→destination ([[project-slip-route-display]]).

**รอบ AYU = 26→25.** cycle_tag 2026-06 = work_date **2026-05-26..2026-06-25** (ชีทมีถึง 30 มิ.ย.=overflow รอบถัดไป ตัดทิ้งอัตโนมัติ). เขียน **841 DailyJob + 178 FuelTxn** (exclude_from_driver=True). tool `import_ayu_daily.py` (--cycle/--dry-run/--wipe-prior). reverse: ค่าขนส่ง 445,330 / ค่าเที่ยว 226,612.

**ผูกคนขับ:** tool `ayu_link_drivers.py` — ผูก **เฉพาะ home_site_code=AYU** (534 แถว/12 คน: เรวัตร/วัชร์นล/สมปอง/สิทธิชัย/ติ๋ว/สมัย/สุริยันต์/ทองสุข/นิวัติ/ธัชชนพล/ชัชวาล/เสรี). **ค้าง 17 ชื่อ unlinked รอโอ (ห้ามเดา cross-site):**
- **11 คน LCB/BigC โผล่ในชีท AYU** (driver_raw_name มี): LCB=อภิชาติ96/นันทสิทธิ์88/รัฐภูมิ85/สุวิทย์90; BigC=สมประสงค์106/โกสินทร์163/ณัชพน108/มานพ112/เกรียงไกร103/เสกสรร111/วิทัศน์164. **คำถามโอ:** คน LCB/BigC ขับงาน AYU จริง (ผูก cross-site) หรือชีทรวมงานหลายไซต์?
- **6 คนใหม่ไม่มีในระบบ:** บุญนาม มหาพล/ธันา ปาวรีย์/ปรีชา แก้วมณีโชติ/สุธรรม สารนอก/พ้น ทองเภา/ชัยเจริญ บุญขัน.

**GUARD ok:** payrun ทุกไซต์ net เท่าเดิม (AYU 5 รอบ copied-net ไม่แตะ — รอบเก่ากว่า period นี้; LCB/BigC ไม่แตะ); DailyJob LCB 1116/BIGC 2381 ไม่ขยับ; integrity ok. **AYU ยังไม่มี payrun 2026-06** (มีแค่ 01-05 copied) → ยังไม่มีสลิป AYU มิ.ย.

**cross-site dups (DONE+deployed 29มิ.ย.):** 11 คน LCB/BigC ในชีท AYU = **เที่ยวซ้ำ** (พี่หวานใส่เผื่อหมิววางบิล AYU เห็น เพราะหมิวมองไม่เห็นไซต์อื่น — ไม่ใช่งาน AYU จริง). 162 แถว tag `source` ลงท้าย `_xsite`; CFO (monthly_pnl + revenue_breakdown) exclude ผ่าน `_not_xsite()` (source notlike %_xsite). AYU CFO รายได้รอบ 26พ.ค.-25มิ.ย. = **387,556** (679 เที่ยวจริง, ตัด 162 ซ้ำ=57,774; Oatside ลดจาก 143→1). เก็บแถวไว้ หมิววางบิลได้. tool `ayu_mark_xsite_dup.py`. **FUTURE:** `ayu_link_drivers.py` auto-tag _xsite ตอน import ครั้งหน้า (home≠AYU); พอหมิวทำในระบบเห็นทุกไซต์ก็ไม่ต้องใส่ซ้ำอีก. **6 คนใหม่** (บุญนาม/ธันา/ปรีชา/สุธรรม/พ้น/ชัยเจริญ) ยังไม่ได้เพิ่ม — รอโอ.

**ค้าง:** **สดย่อย AYU** ไฟล์ `Work\Salary\2026\6.Jun\AYU\สดย่อยวังน้อย หมิว.xlsx` ชีท `Jun 26` (โอส่งแล้ว) — **ยังไม่ทำเพราะ AYU ไม่มี payrun รอบ มิ.ย.** (มีแค่ ม.ค.-พ.ค. copied) → ต้องสร้าง payrun AYU มิ.ย.ก่อน หรือรอ. costing/CFO AYU เต็มรูป.

related: [[project-bigc-daily-import]], [[project-slip-route-display]], [[project-multisite-payroll-onboard]], [[project-rojruam-bunnam-todo]]
