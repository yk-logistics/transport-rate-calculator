# Project YK Master Changelog

สรุปการตัดสินใจสำคัญระดับภาพรวมข้ามทุกโมดูล

> **Agent bootstrap:** อ่านเฉพาะ **3 หัวข้อ `##` แรกจากด้านบนลงมา** (ไม่รวมบรรทัดนี้) — **ห้าม**อ่านทั้งไฟล์ทุกแชต. นโยบาย/การย้าย archive: [`ProjectYK_System/docs/CHANGELOG_POLICY.md`](ProjectYK_System/docs/CHANGELOG_POLICY.md)

## 2026-06-11 (line_archiver — บอทเก็บข้อความ+รูปจากกลุ่ม LINE ลง SQLite/Discord)

- service ใหม่แยกขาด `ProjectYK_System/line_archiver/` (port 8020, DB แยก `line_archive.db`)
- LINE Messaging API webhook → เก็บ text/รูป/ไฟล์ลงเครื่อง → forward Discord (auto-create channel ต่อกลุ่ม)
- retry loop ทุก 5 นาที: บันทึก DB ก่อนเสมอ Discord ล่มข้อมูลไม่หาย; ไม่แตะ `app/main.py`, `app.db`
- spec: `docs/superpowers/specs/2026-06-11-line-archiver-design.md` · branch `feature/line-archiver`
- เปิดใช้ตาม `ProjectYK_System/line_archiver/SETUP_CHECKLIST.md` (LINE Developers + Discord Bot + cloudflared)

## 2026-06-10 (Daily batch entry — /daily/new เป็นตารางคีย์หลายแถว)

- `/daily/new` เปลี่ยนจากฟอร์มยาว 28 ช่อง → ตารางคีย์หลายแถวแบบ Excel (`daily_batch.html`): วันที่+ไซต์ตั้งครั้งเดียว, คอลัมน์ปรับตามไซต์ (LCB: JobRef/ตู้/Doc · BIGC: หาง), ช่องใช้น้อยพับใต้ปุ่ม ⋯, Enter/Ctrl+D, autocomplete master เขียว=ลิงก์ id เหลือง=เก็บ raw
- เพิ่ม `POST /daily/batch` (JSON หลายแถว, ผลรายแถว ok/error — แถวพังไม่ล้มชุด) + refactor `_apply_daily_fields()` ใช้ร่วมกับ `daily_save` เดิม (ฟอร์ม edit `/daily/{id}/edit` ไม่กระทบ)
- spec/plan: `docs/superpowers/specs/2026-06-10-daily-batch-entry-design.md` · branch `feature/daily-batch-entry`
- พบบั๊กเก่า (ยังไม่แก้): `petty_save` main.py ใช้ `driver_obj` ที่ไม่ถูกประกาศ → NameError ถ้าบันทึก petty โดยไม่ใส่ pay_cycle_tag เอง

## 2026-06-10 (Dispatch Booking — สเปคฟีเจอร์รับงาน→จัดรถ→ร่างเดลี่ + แผน GPS)

- grill-me รอบ 2 กับโอ → **`docs/DISPATCH_BOOKING_SPEC.md`**: booking = ออเดอร์มีจำนวนคัน, บอร์ดจัดรถแตะสองครั้ง (หัวหน้าลานใช้บนคอม แทน Notepad), จัดแล้วสร้างข้อความไลน์กลุ่ม + **ร่างเดลี่อัตโนมัติ** (เกณฑ์ผ่านหลัก), Location master = POI ของ GPS ในอนาคต
- แผนสร้าง B1–B4 เข้า MVP_TEST_PLAN (เริ่มหลัง S1, คู่ขนาน S3–S6, ทดสอบจริงใน S2)
- GPS: Mobile Innovation vs Cartrack ยังไม่สรุป — ออกแบบเป็น adapter ไม่ผูกเจ้า; เฟส เห็นรถ→Timeline→เตือน; โอมีการบ้านส่งคำถาม API 5 ข้อให้สองเจ้า
- ลำดับ backlog ใหม่: fuel เหมา → GPS 1–2 → ต้นทุนคงที่ → pricing engine

## 2026-06-10 (MVP Test Plan — เริ่มทดสอบ end-to-end)

- เคาะแผนทดสอบ MVP กับโอ (grill-me 9 ข้อ) → **`docs/MVP_TEST_PLAN.md`** (S1–S7 + กติกาเปิด/ปิดเซสชัน + findings ที่ `docs/MVP_TEST_FINDINGS.md`)
- ขอบเขต: DB จริง, LCB รอบ 2026-05 ก่อน (daily 508/fuel 288/petty 67/payrun draft); ground truth = ไฟล์เงินเดือนจริงที่ `Work\Salary\2026\5.May\LCB`
- มติเงิน: MVP เก็บราคา-ไม่คิดราคา, น้ำมันเหมาใช้ยอดโอคำนวณ, กำไรขั้นต้นไม่รอต้นทุนคงที่ — logic น้ำมันเหมา 2 แบบจดใน `CLAUDE_MEMORY/business_domain.md`
- หลัง MVP อันดับ 1: fuel เหมา auto-attribution

## 2026-05-25 (Transport Rate Calculator — หัวตารางใบสรุปเสนอราคา)

- แก้หัวตารางสีน้ำเงินมองไม่เห็นตัวอักษร (ใบสรุปเสนอราคา + ตารางโรงงาน) — บังคับตัวอักษรขาว; แก้ export PDF/PNG ที่เคยตั้งสีหัวตารางเป็นน้ำเงิน; push `e1017c9`

## 2026-05-25 (Transport Rate Calculator — ราคาน้ำมันขยายถึงวันนี้)

- หลังดึงข้อมูลย้อนหลัง: วันที่หลังปรับราคาล่าสุด (เช่น 21–25/5) ใช้เรทเดิมต่อถึงวันนี้ — ปฏิทินเลือกช่วงได้ถึงวันปัจจุบัน; badge `ราคาล่าสุด`; push `yk-logistics/transport-rate-calculator` `48d9a21`

## 2026-05-21 (LCB fuel dispatch — ชื่อลูกค้า WHALE/เหรินเหอ)

- แผน LINE: รองรับบล็อก WHALE5 [เหรินเหอ5] → โชว์ **เหรินเหอ** (50 ล./เที่ยว); HTML แสดงทุกคันที่ parse (ไม่ซ่อน Unknown); คลังวาฬนับ Bol.+Con. (รวมฟรีโซน)

## 2026-05-21 (Transport Rate Calculator — โหมด 2 โรงงานละตาราง)

- โรงงานละ Base + ช่วงฐาน + ตารางน้ำมันแยก; ช่วงน้ำมัน/% ปรับร่วมจากวิซาร์ด; + เพิ่มโรง, คัดลอก Base, ราคาเสนอ, PDF/Excel รวมทุกโรง

## 2026-05-21 (Transport Rate Calculator — ลูกค้า/หลายโรงงานบนหน้าผลลัพธ์)

- หน้าผลลัพธ์: ชื่อลูกค้า + รายการโรงงาน/ราคาเสนอ (default 1 แถว, + เพิ่มได้); สรุปด้านบนสำหรับพิมพ์ PDF/PNG/Excel; ปุ่มดึงราคาปัจจุบันจากตารางน้ำมัน

## 2026-05-21 (Transport Rate Calculator — ปัดเศษค่าขนส่ง)

- Step 4: เลือกปัดเศษ — ไม่ปัด / ทศนิยม (0–2 ตำแหน่ง) / หลักหน่วย / หน่วย 5|0 / หลักสิบ; จำในเครื่อง; ใช้กับตารางเรท + ราคาเป้าต้นทุน; sync `index.html`

## 2026-05-20 (LCB fuel dispatch — Pages full 16 trucks + URL note)

- สาเหตุ Pages เห็นแค่ 2 คัน: build จาก `fixtures/lcb_plan_sample.txt` (ทดสอบ) ไม่ใช่แผนจริง — **ไม่ใช่** filter ตาราง
- rebuild จาก `21.05.26.txt` → ตาราง **16 แถว** (รวม Oatside); ไฮไลต์เฉพาะ KAO 9628/0419 ที่ต้องเติม
- HTML เพิ่มหมายเหตุลิงก์: `…/reports/lcb-fuel-dispatch/` ≠ หน้าแรก transport-rate-calculator; push `79fa6c8`

## 2026-05-20 (LCB fuel dispatch — editable refill + diesel on HTML)

- `build_lcb_fuel_dispatch_from_plan.py` — หน้า HTML แก้ราคาดีเซล (ค่าเริ่มต้น 42.20), กรอกลิตรเติมต่อคัน, สรุปงบ 5k–10k, pre-fill คันต้องเติม (~buffer 12.5 ล.), Export PNG/CSV รวมคอลัมน์เติม

## 2026-05-20 (LCB fuel dispatch — build scripts in Git + bat English)

- commit `tools: LCB fuel dispatch build scripts` — `parse_lcb_plan_txt.py`, `build_lcb_fuel_dispatch_from_plan.py`, `build_lcb_fuel_dispatch_html.py` + bat ข้อความภาษาอังกฤษ (แก้กล่องสี่เหลี่ยมใน cmd)
- bat: Enter ว่าง → หา `*05.26*.txt` ใน Downloads; แสดง path เต็มของ HTML หลัง build

## 2026-05-20 (LCB fuel dispatch — GitHub Pages static path)

- build คัดลอก HTML ไป `reports/lcb-fuel-dispatch/index.html` — ลิงก์หลัง push: `https://yk-logistics.github.io/transport-rate-calculator/reports/lcb-fuel-dispatch/`
- bat พิมพ์ URL Pages; README ที่ `TransportRateCalculator/reports/lcb-fuel-dispatch/`

## 2026-05-20 (LCB fuel dispatch — diesel 42.20 + bat + route)

- ราคาดีเซลค่าเริ่มต้น **42.20 บาท/ล.**; bat ถาม path แผน + หา `*Fuel_Level*LCB*.xlsx` ใน Downloads อัตโนมัติ
- `GET /ops/lcb-fuel-dispatch` เสิร์ฟ `docs/print/lcb_fuel_dispatch_plan.html` หลังรัน bat
- Parser อ่านหัวแผน `งาน16วิ่ง16` — **16 คัน** ตรงหัวแผน; **17 เที่ยวตู้** (คลังวาฬ 2 ตู้/หัว) สำหรับงบน้ำมัน

## 2026-05-20 (LCB fuel dispatch — แผน LINE .txt + GPS + เติมคืนนี้)

- เพิ่ม `parse_lcb_plan_txt.py` + `build_lcb_fuel_dispatch_from_plan.py` — อ่านแผนจูเนียร์จาก LINE (เช่น `21.05.26.txt`) ผูก GPS CSV/xlsx, `--add-fuel`, กติกาเติมเมื่อหลังวิ่ง &lt; ~12.5 ล.
- อัปเดต `build_lcb_fuel_dispatch.bat` — รับ `plan.txt` + fuel file; default เติมคืนนี้ 0420 +30 ล. / 6803 +20 ล.
- สูตรล็อก: KAO/Conti/Lacation 50, Haier 100 (8684 แทน 8681), คลังวาฬ 25×เที่ยว, Oatside ~110/วัน; Lacation 71-8683 นับ 1 เที่ยวใน 16

## 2026-05-20 (LCB fuel dispatch — HTML แผนจัดคันจาก GPS)

- เพิ่ม `ProjectYK_System/docs/print/lcb_fuel_dispatch_plan.html` — ตารางจัดคัน LCB ตามน้ำมันในถัง + คอลัมน์ GPS อัปเดต + พิมพ์/PNG/CSV
- เพิ่ม `ProjectYK_System/tools/build_lcb_fuel_dispatch_html.py` + `build_lcb_fuel_dispatch.bat` — อ่านรายงาน Wialon `.xlsx` แล้วสร้าง HTML/CSV/XLSX ใหม่ (ตัด 72-1217 Oatside, 8681/1219 เสีย)

## 2026-05-18 (DLT Log Book form — Excel A4 portrait)

- เพิ่มแบบฟอร์ม `แบบบันทึกผลการบำรุงรักษารถ (Log Book)` เป็น Excel A4 แนวตั้งหน้าเดียวตามรูปตัวอย่างจริง: `ProjectYK_System/docs/forms/DLT_LogBook_Maintenance.xlsx`
- เพิ่ม generator `ProjectYK_System/tools/generate_dlt_logbook_exact.py` และให้ `generate_dlt_logbook_form.py` เรียก layout ใหม่เพื่อกันสร้างแบบ landscape เก่าทับ
- เพิ่ม blank export ไม่มีข้อมูล/ลายเซ็น: `ProjectYK_System/docs/forms/DLT_LogBook_Blank.pdf` และ `ProjectYK_System/docs/forms/DLT_LogBook_Blank.png`

## 2026-05-15 (Import Wizard — web UI รองรับ Daily / Employee / Vehicle)

- **Import Wizard Phase 1+2:** `/import` รองรับ 3 ประเภท — Daily Jobs (header-name mapping, LCB-style), Employees, Vehicles
- **Safety:** Employee/Vehicle ใช้ collision-skip (code/plate_no ซ้ำ → unresolved list, ไม่ merge อัตโนมัติ); Daily รองรับ rollback ด้วย source_tag; Employee/Vehicle rollback ไม่รองรับ bulk (แจ้งผู้ใช้ไปที่ UI)
- **ImportLog model** (schema v18): บันทึกทุก batch — import_type, site_code, source_tag, row/fee/fuel count, status (done/dry_run/rolled_back/failed), note รวม conflict list
- **HTMX flow:** type selector → upload → sheet picker → preview (field set ตาม type) → dry-run → import จริง → history refresh อัตโนมัติ
- **ถัดไป:** import ข้อมูลจริงผ่าน UI (Employees + Vehicles ก่อน แล้ว Daily LCB Jan 2026)

## 2026-05-14 (LCB Jan 2026 — import รอบ pay_cycle_tag=2026-01 สำเร็จ)

- **Import Wizard (/import):** ข้อความแยกชัด "รอบจ่าย (กรอง work_date)" vs "เดือนปฏิทิน CFO" + ตัวอย่าง LCB 16–15 + บล็อกเมื่อวันเริ่มรอบมากกว่าวันสิ้นรอบ
- **CFO `/finance`:** แถบอธิบายขอบเขตวันที่ปฏิทิน (รายได้/ต้นทุนส่วนใหญ่) แยกจาก `pay_cycle_tag` ของ Payroll
- **ช่วงงาน:** `work_date 2025-12-16 – 2026-01-15` (LCB ตัด 16–15 จ่ายวันที่ 1 ก.พ. 2569)
- **แหล่งข้อมูล:** `data/Salary/LCB/2026-01/วางบิล YK VOLVO Jan.xlsx` ชีท `Daily 16.12.68 - 15.01.69` — column layout ต่างจาก Book2 (driver=col4, extra BL./Booking, ค่ายกตู้=col15, revenue=col24, trip_fee=col34)
- **script ใหม่:** `ProjectYK_System/tools/import_lcb_jan2026.py` — header-name mapping, source=`lcb_jan2026`, รองรับ `--wipe-prior` / `--dry-run`
- **ผล:** DailyJob 694 แถว, DailyJobFee 272 รายการ (฿124,078), trip_fee รวม ฿13,450, revenue รวม ฿333,880
- **ขั้นตอนถัดไป:** สร้าง PayRun `pay_cycle_tag=2026-01` ผ่าน UI `/payroll` (period_start=2025-12-16, period_end=2026-01-15) แล้วรัน preflight; fuel ใช้ `import_caltex_fuel.py` แยก
- **safety gap บันทึก:** `import_daily.py` ไม่มี `--to-date` flag; preflight ไม่มี zero-rows guard ต่อ cycle — รอ harden รอบถัดไป

## 2026-05-12 (Dev tool — Paste คอลัมน์เฉพาะแถวมองเห็นระหว่างสอง .xlsx)

- เพิ่ม `ProjectYK_System/dev_scripts/paste_visible_column.py` — อ่านค่าจากคอลัมน์ต้นทางเฉพาะแถวที่ไม่ `row hidden` แล้วเขียนลงคอลัมน์ปลายทางตามลำดับแถวมองเห็น; รองรับ `--dry-run`, `--out`, `--inplace` + `--backup`; ข้อความ `--help` เป็นภาษาอังกฤษเพื่อหลีกเลี่ยง encoding บน Windows console

## 2026-05-09 (Transport Rate Calculator — fuel date-range UX)

- ปรับหน้าเครื่องคิดเรทราคาน้ำมันย้อนหลัง: เปลี่ยน `ตั้งแต่/ถึง` สองช่องเป็นปฏิทินเลือกช่วงเดียว (`วันเริ่ม -> วันถึง`) และทำตารางวันที่/เรทน้ำมันให้ลากปรับความสูงได้เอง; sync `ProjectYK_System/TransportRateCalculator/transport_rate_calculator.html` -> root `index.html`
- Fix เพิ่ม: กล่อง `สรุปช่วงที่คลุม` เรียงวันที่เริ่มก่อนวันที่สิ้นสุดเสมอ และตารางย้อนหลังเรียงวันเก่าอยู่บน / วันใหม่อยู่ล่าง

## 2026-05-09 (AYU run7 — nickname index fix, 33→5 unresolved)

- **root cause:** `_build_employee_name_index` ใน `tools/preflight_payrun.py` index แค่ `full_name` ไม่รวม `nickname` → ทำให้ชื่อสั้นอย่าง "เอ๊ะ" / "ช่างน้อย" / "ข้าวฟ่าง" หาไม่เจอแม้ employee มีอยู่ใน DB
- **fix:** เพิ่ม nickname index ใน `_build_employee_name_index` + เพิ่ม AYU aliases ใน `app/services/alias_map.py` (เอ๊ะ, ช่างน้อย, ข้าวฟ่าง)
- **ผล:** unresolved 33 → 5, quick_win 0 → 28 (฿18,666)
- **เหลือ:** 5 รายการ "สมัย อยุธยา" (฿5,050) — ไม่เจอในระบบ ต้องสร้าง employee ใหม่; 13 quick_win เป็น LCB cross-site ต้องให้โอยืนยัน
- **decision doc:** `reports/preflight_unresolved_queue/AYU_run7_decision_needed.md`

## 2026-05-08 (BIGC 1DH — โอยืนยันคำว่า «สาขาเดียว»)

- บันทึกใน [`DOMAIN_AND_DIRECTION.md`](ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md) และ [`SITE_PAYROLL_RULES.md`](ProjectYK_System/TransportRateCalculator/docs/SITE_PAYROLL_RULES.md)

## 2026-05-08 (Oatside — ถอด debug instrumentation หลัง reconcile Book3)

- ทำความสะอาด `ProjectYK_System/dev_scripts/reconcile_book3_vs_customer_summary.py` (ไม่เขียน NDJSON) + ลบ `fetch` ingest จาก `reports/oatside-pg-2026/trips.html` และ `reports/oatside-pg-2026/plates/71-5042.html` — คง client-side recalc เดิม

## 2026-05-08 (Payroll domain — LCB ไม่แบ่ง manual + SSO base รายคน + BIGC 1DH + Line OA scope)

- โอยืนยัน: LCB Mode B รายการไม่แบ่ง — **manual + ระบบจำครั้งถัดไป** (ไม่ล็อกลิสต์ตายตัว); ประกันสังคม — **เลือกได้รายคนตอนลงทะเบียนคนขับ**; BIGC `1DH` — อธิบายความหมายคำถาม + ล็อกว่าคิดเรทปลายทางเหมือนสาขาเดียว; Line OA — **โครงเดียวกับ One Platform** (เฟส 5) — อัปเดต [`DOMAIN_AND_DIRECTION.md`](ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md) §13 และ [`SITE_PAYROLL_RULES.md`](ProjectYK_System/TransportRateCalculator/docs/SITE_PAYROLL_RULES.md)

## 2026-05-08 (DOMAIN_AND_DIRECTION — เติม §15 ทิศทางผลิตภัณฑ์ระยะยาว)

- [`ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md`](ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md): เพิ่มหัวข้อ **§15** สรุปสั้น CFO / Driver PWA / LINE Messaging / Open-Book พร้อมชี้ `.cursor/rules/project-yk-context.mdc` และ `AGENTS.md` — ไม่ซ้ำข้อความยาว

## 2026-05-08 (DOMAIN_AND_DIRECTION — รวบรวมความรู้โดเมนจาก CONTEXT_LOG)

- เขียน [`ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md`](ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md) ใหม่แบบมีโครงสร้าง: 3 ไซท์, payroll/cycle, BIGC/Oatside/BDT, เคสเสนอราคา Direct-to-store, พื้นที่เช่าลาน, ความเสี่ยงข้อมูล — อ้างอิง session ใน `CONTEXT_LOG.md` เป็นต้นทาง ไม่เดาข้อเท็จจริงนอก log

## 2026-05-08 (Oatside — Book3 alignment: Trip_Date + ตารางเรทน้ำมันเม.ย.)

- สคริปต์ `ProjectYK_System/dev_scripts/book3_align_date_fuel.py` — ปรับ `c:\Users\Home\Downloads\Book3.xlsx` ชีท `Daily Report ` ให้คอลัมน์วันที่ตรง `Trip_Date` จาก `reports/oatside-pg-2026/exports/05_Trip_Detail.xlsx` (ลำแถว + เช็ก Plate) และเติม `Fuel rate` จากตารางรายวัน 1–30 เม.ย. 2026 เฉพาะเซลล์ที่ต่าง พร้อมพื้นเหลือง/คอมเมนต์; สำรอง `Book3.before_date_fuel_backup.xlsx`

## 2026-05-08 (Token context — bounded reads + executive brief + domain capture)

- เพิ่มกฎ `.cursor/rules/exec-brief-noncoder.mdc` — ตอบแบบ executive ภาษาคน (ไม่อธิบาย implementation โดยดีฟอลต์) คู่กับกฎเงิน/ข้อมูลเดิม
- เพิ่มเอกสาร [`ProjectYK_System/docs/CONTEXT_TOKENS.md`](ProjectYK_System/docs/CONTEXT_TOKENS.md), [`CHANGELOG_POLICY.md`](ProjectYK_System/docs/CHANGELOG_POLICY.md), [`CHANGELOG_ARCHIVE.md`](ProjectYK_System/docs/CHANGELOG_ARCHIVE.md), [`DOMAIN_AND_DIRECTION.md`](ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md)
- แก้ `.cursor/rules/project-yk-context.mdc` + [`ProjectYK_System/AGENT_BOOTSTRAP.md`](ProjectYK_System/AGENT_BOOTSTRAP.md) ให้ `CHANGELOG_MASTER` อ่านแค่ 3 หัวข้อล่าสุด และ `CONTEXT_LOG` อ่านท้ายไฟล์ 2–3 sessions
- อัปเดต [`ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`](ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md) หัวข้อ “หนึ่งเธรด = หนึ่ง scope”

## 2026-05-08 (Oatside UI hotfix — delay surcharge follows transport rate)

- แก้ไฟล์รายงาน publish ที่ใช้งานจริง (`reports/oatside-pg-2026/trips.html` + `reports/oatside-pg-2026/plates/*.html`) ให้คอลัมน์ `เสียเวลา+50%` และ `เสียเวลา+100%` คิดจาก `ค่าขนส่ง(฿)` ต่อแถวโดยตรง (50%/100%) แทนค่าคงที่เดิม
- เพิ่ม client-side guardrail หลังโหลดหน้า: ถ้าแถวนั้นมีการคิดค่าเสียเวลาอยู่ ระบบจะ re-calc จากค่า `ค่าขนส่ง(฿)` แล้ว format เป็น 2 ตำแหน่งทันที เพื่อลดความเสี่ยงตัวเลขค้างจาก build ก่อนหน้า

## 2026-05-08 (Oatside money 2dp standard + CSV exports + publish)

## 2026-05-08 (Oatside trips UI hotfix — move 71-5042 surcharge to +100%)

- แก้รายงาน HTML ที่ใช้งานอยู่ (`reports/oatside-pg-2026/trips.html` และ `reports/oatside-pg-2026/plates/71-5042.html`) โดยย้ายยอด `6,546.00` ของแถวทะเบียน `71-5042` (Origin In `2026-04-21 12:28:30`) จากคอลัมน์ `เสียเวลา+50%` ไป `เสียเวลา+100%` ตามที่ผู้ใช้ตรวจพบ
- คงค่าเงินอื่นเดิมทั้งหมดในแถวเดียวกัน (`ค่าขนส่ง 6,546.17`, `ตีเปล่า+50%=—`, `ขากลับ=—`) เพื่อลดความเสี่ยงกระทบยอดรวมส่วนอื่น

## 2026-05-08 (Oatside debug instrumentation cleanup)

- ลบ debug instrumentation (`_agent_debug_log` และ block `# region agent log`) ออกจาก `Oatside/build_oatside_reports.py` หลังผู้ใช้ยืนยันว่า issue ถูกแก้แล้ว
- ลบไฟล์ helper debug ชั่วคราว (`debug_instrument_oatside.py`, `debug_cleanup_oatside.py`) ออกจากราก repo

## 2026-05-08 (Oatside report cutoff — remove May from report window)

- เพิ่ม config ช่วงรายงานใน `Oatside/build_oatside_reports.py` (`report_start_date` / `report_end_date`) และใช้กรองทั้ง matched trips + unmatched legs ตาม `trip_date`/วันของ leg เพื่อกันข้อมูลนอกช่วงไหลเข้ารายงาน
- ตั้งค่า `Oatside/oatside_config.json` เป็น `report_end_date=2026-04-30` ตามคำขอผู้ใช้ "ตัดเดือน พ.ค. ออก" แล้ว rerun build ได้ผล `Trips 103` (จากเดิม 105), `exact=103, carry_forward=0, base_fallback=0`
- publish รายงานขึ้น GitHub Pages ด้วย `deploy_oatside_report.ps1 -Push` สำเร็จที่ commit `b944925` (repo publish)

- ปรับ `Oatside/build_oatside_reports.py` ให้ monetary presentation เป็น 2dp ทั้ง HTML และ Excel (`#,##0.00`) โดยคง logic คำนวณเดิมไม่ round ซ้ำหลายชั้น
- เพิ่มการส่งออก `exports/*.csv` คู่กับ split Excel tables โดย format monetary columns เป็น 2dp (UTF-8 BOM) ครอบคลุมชุดคอลัมน์เงินหลัก (`Trip_rate_baht`, `Downtime_50_baht`, `Downtime_100_baht`, `Blank_run_50_baht`, `Return_job_baht`)
- rerun `python Oatside/build_oatside_reports.py` แล้ว deploy publish ด้วย `deploy_oatside_report.ps1 -RepoPath transport-rate-calculator-repo -Push` สำเร็จที่ commit `4d203ab`

## 2026-05-08 (Oatside pricing mapping guardrail + publish deploy)

- แก้ `Oatside/build_oatside_reports.py` ให้ mapping คอลัมน์ surcharge ชัดเจนขึ้น: ชีต `Trips_Pricing_All` เปลี่ยนชื่อคอลัมน์เป็น `Downtime_50_baht` / `Downtime_100_baht` / `Blank_run_50_baht` และคง `Return_job_baht`
- เพิ่ม regression guard `_assert_pricing_bucket_mapping(...)` ตรวจเทียบยอด +50/+100 จาก `Surcharge_50pct_1Trip` เทียบกับทั้ง `Trip_Detail` และ `Trips_Pricing_All`; ถ้า mapping สลับ/ทับจะ `raise ValueError` ทันทีตอน build
- rerun `python Oatside/build_oatside_reports.py` ได้ `Trips 105 / Unmatched 15` และ diesel usage `exact=37, carry_forward=68, base_fallback=0`; deploy ด้วย `deploy_oatside_report.ps1 -RepoPath transport-rate-calculator-repo -Push` สำเร็จที่ publish commit `a0677c7`

## 2026-05-08 (Oatside publish sync — summary page uses latest pricing)

- ยืนยันว่า URL หน้า “รวมทั้งหมด” ที่ใช้งานจริงคือ `https://yk-logistics.github.io/transport-rate-calculator/reports/oatside-pg-2026/index.html` (ไม่ใช่ path เก่า `oatside-apr2026`)
- rerun `python Oatside/build_oatside_reports.py` แล้ว deploy ด้วย `deploy_oatside_report.ps1 -RepoPath transport-rate-calculator-repo -Push` ไปที่ repo publish โดยตรง
- push สำเร็จเป็น commit `e4516e9` และตรวจหน้า live ทั้งแบบปกติ+cache-bypass (`?nocache=commit-e4516e9`) พบว่าแสดง pricing rules ชุดใหม่ (fuel-linked) แล้ว

## 2026-05-08 (GitHub Pages — remove stale submodule gitlink)

- ตรวจ root cause ของ GitHub Pages failure (`actions/runs/25545958948`) แล้วพบว่า fail ที่ step `Checkout` ด้วยข้อความ `No url found for submodule path 'transport-rate-calculator-repo' in .gitmodules`
- แก้ใน repo `yk-logistics/transport-rate-calculator` โดยลบ gitlink mode `160000` ที่ path `transport-rate-calculator-repo` (ไม่มี `.gitmodules` อยู่แล้ว) และ push ขึ้น `main` เป็น commit `0243b51`
- ยืนยันรอบใหม่ว่า workflow `pages build and deployment` run `25546755229` ผ่านจุด `Checkout` แล้ว (ไม่ติด error เดิม)

## 2026-05-08 (Oatside — user-provided diesel history applied)

- เติม `Oatside/oatside_config.json` ช่อง `diesel_price_history` ด้วย anchor dates 19 จุดจาก user-provided historical table (Bangchak ไฮดีเซล S ปี 2569) เพื่อให้รายงาน Oatside คำนวณค่าขนส่งตามราคาน้ำมันจริงและใช้ carry-forward เมื่อไม่มี exact day
- rerun `python Oatside/build_oatside_reports.py` แล้ว diesel usage เปลี่ยนเป็น `exact=22, carry_forward=83, base_fallback=0` จากทั้งหมด 105 trip records ยืนยันว่าไม่มีรายการกลับไปใช้ base fallback
- แก้ typo ราคาช่วง 2026-04-17..2026-04-20 (ในตารางผู้ใช้พิมพ์ `429` เพราะลืมจุดทศนิยม) เป็น `42.90` ตามค่าจริงในแหล่งอ้างอิง แล้ว rerun รายงานได้ `exact=37, carry_forward=68, base_fallback=0`

## 2026-05-08 (Transport Rate Calculator — sync deploy index + publish Export CSV button)

- sync หน้า deploy โดยคัดลอก `ProjectYK_System/TransportRateCalculator/transport_rate_calculator.html` ไปที่ root `index.html` เพื่อให้ GitHub Pages ใช้ไฟล์ล่าสุดที่มีปุ่ม `Export CSV ตารางย้อนหลัง` และฟังก์ชัน `exportHistoricalCsv()`
- push ขึ้น `origin/main` แล้วสำหรับ commit ที่แตะ `index.html` โดยตรง เพื่อแก้ปัญหาหน้าเว็บจริงไม่เห็นปุ่ม export

## 2026-05-08 (Transport Rate Calculator — export fuel history CSV)

- เพิ่มปุ่ม `Export CSV ตารางย้อนหลัง` ใน `TransportRateCalculator/transport_rate_calculator.html` (Step 1 historical panel) เพื่อให้ผู้ใช้ดาวน์โหลดตารางราคาน้ำมันย้อนหลังจากข้อมูลที่โหลด/วางได้ทันที
- ใช้ safe default export เป็น CSV แบบ `UTF-8 BOM` รองรับภาษาไทย พร้อมคอลัมน์ `date/fuel_type/price_baht_per_liter/imputed/selected`
- ชื่อไฟล์แนบช่วงวันที่ข้อมูลอัตโนมัติ (`historical_oil_price_<fuel_type>_YYYYMMDD-YYYYMMDD.csv`) เพื่อ trace ย้อนกลับช่วงข้อมูลที่ใช้คำนวณ

## 2026-05-08 (Claude Code review log: Email Inbox/OAuth/Draft Daily/Grid)

- ปรับ `Oatside/build_oatside_reports.py` ให้คำนวณ `trip_rate_baht` ตาม **วันที่วิ่งงาน (trip_date)** + รองรับ `diesel_price_history` รายวันจาก config, ปรับกติกาฐานราคา Apr/May (Apr floor 6,500, May base 6,500 @ 31.xx, step 1.5%/บาท), และเพิ่ม `manual_return_trips` แบบ `percent_of_trip_rate` (งานขากลับ 50%)

- บันทึกผลตรวจจากเซสชัน Claude Code: ตรวจไฟล์ `app/services/email_oauth.py`, `app/services/email_ingest.py`, `app/templates/email_inbox.html`, `app/templates/daily_grid.html` และ route ที่เกี่ยวข้องใน `app/main.py`
- ยืนยันผล verify จาก CC: ผ่าน `python -m py_compile main.py services/email_ingest.py services/email_oauth.py`, ผ่าน `run_payroll_test.py`, และยืนยัน `dmy_hm` filter ยัง register ถูกต้อง
- ยืนยัน flow จาก CC: `draft-daily -> daily_form -> daily/new` มีการ link `inbox_mail_id` แล้ว และไม่พบผลกระทบกับ payroll regression
- ระบุความเสี่ยงที่ยังต้องตัดสินใจ 3 จุด: (1) sync redirect `?ok=1` ยังไม่มี flash ชัดใน inbox, (2) OAuth callback เป็น GET + state cookie check มีแต่ UX refresh callback อาจทำให้ผู้ใช้สับสน, (3) draft-daily ยังเขียน preview ลง remark โดยตรง (ยังไม่มี metadata/linked timestamp/status auto update หลัง save)

## 2026-05-08 (Daily/Daily Grid presets align to payroll cycles)

- ปรับ preset หน้า `/daily` และ `/daily/grid` ให้ใช้ช่วง **รอบ payroll ต่อไซต์** แทนเดือนปฏิทิน: `AYU 26→25`, `LCB 16→15`, และ `BIGC เดือนวิ่ง T-1 (1→สิ้นเดือน)`
- เพิ่ม helper ใน `app/main.py` สำหรับคำนวณช่วง preset กลาง `_daily_site_preset_cycles()` และผูกเข้า context ของทั้งสองหน้า เพื่อลด logic ซ้ำ
- ปรับ label preset ให้สื่อ intent ชัดเจนว่าเป็น “รอบ payroll” (โดยเฉพาะ BIGC แสดงเดือนวิ่ง `T-1`)

## 2026-05-08 (Plan C: driver pay-cycle policy-first + review queue guardrail)

- เพิ่ม `Employee.pay_cycle_policy` (default `site_default`) และ UI ตั้งค่าในหน้า `/employees/new|edit` ทันที พร้อมแสดงคอลัมน์ใน `/employees`
- เพิ่มตัวคำนวณกลางใน `services/payroll.py` (`compute_pay_cycle_tag_by_policy`, `normalize_pay_cycle_policy`) เพื่อย้ายแนวคิดจาก site-first เป็น driver-policy-first โดยยัง fallback แบบ backward compatible
- ปรับเส้นทางที่ใช้/ตรวจ `pay_cycle_tag` ฝั่งสดย่อยและ preflight ให้ยึด driver policy เป็นหลักเมื่อมี `driver_id`, และเพิ่ม review flag/filter สำหรับเคส `missing_driver / unclear_policy / tag mismatch`
- เพิ่ม finalize gate ฝั่ง payroll: ถ้ายังมีรายการใน policy review queue จะ block ปิดรอบ (`err=policy_review_block`) เพื่อกันเงินตกหล่นเงียบ
- คง preset เดือนปฏิทินในหน้าสดย่อยเดิม และเพิ่ม preset สำหรับคิว review policy แบบไม่ทับพฤติกรรมเดิม

## 2026-05-08 (Email OAuth2 + Inbox Draft Daily + Daily Grid parity)

- เพิ่ม `app/services/email_oauth.py` รองรับ Google OAuth2 (authorize/callback/refresh/XOAUTH2) และเก็บ refresh token ที่ `ProjectYK_System/app/data/email_google_refresh.token` (ignore ใน git)
- ขยาย `app/services/email_ingest.py` รองรับ `EMAIL_IMAP_AUTH=password|oauth2` พร้อม XOAUTH2 authenticate และ credential guard แยกตามโหมด
- ขยาย `app/main.py` + templates: route `/email/oauth/start|callback`, action Inbox `สร้างร่าง Daily`, link `inbox_mail_id -> linked_daily_job_id`, และอัปเกรด `/daily/grid` ให้ field ใกล้ parity กับ Daily form + filter `status/limit` + save ครอบคลุม
- `daily_grid.html` เพิ่มแผงซ่อน/แสดงคอลัมน์แบบ Excel ด้วย `localStorage['yk_daily_grid_hidden_v1']` และยังคง guardrail ว่าไม่ทำ action กระทบเงินอัตโนมัติ

## 2026-05-08 (Night Long-Run: payroll detail Ops bar + fuel/billing presets)

- หน้า `/payroll/{run_id}` (`payroll_detail.html`): เพิ่ม **แถบปฏิบัติการ Ops** — ลัดไปสดย่อย (ไซต์รอบ / คิวยังไม่ผูกตาม gate), เดลี่/น้ำมันช่วงรอบ, วางบิลเดือนเดียวกับแท็กรอบ, คัดลอกคำสั่ง `preflight_payrun.py` สำหรับ rerun รายงาน
- หน้า `/payroll/.../employee/...` (`payroll_employee_detail.html`): ลัดสดย่อยตาม `driver_id` + รอบ/ไซต์, เดลี่/น้ำมันช่วงรอบ
- `/fuel` + `fuel_list.html`: ส่ง `current_month_*` จาก `main.py` และเพิ่ม preset เร็ว (BigC/LCB/AYU เดือนนี้ + ยังไม่เชื่อม Job)
- `/billing` + `billing_page.html`: เพิ่ม preset เร็ว BigC/LCB/AYU เดือนปฏิทินปัจจุบัน (`current_billing_month`)

## 2026-05-08 (Night autopilot UX guardrail #2 + preflight manager summary)

- ทำ **Wave 1 Guardrail #2** ครบ 3 หน้า: เพิ่ม saved filter preset แบบคลิกเดียวใน `daily_list.html` / `petty_list.html` / `payroll_list.html` (BigC/LCB/AYU เดือนนี้, รออนุมัติ, ยังไม่ผูก) โดยใช้ URL query string ไม่เพิ่ม schema
- ขยายหน้า `/payroll` ให้กรอง `site/cycle/status` ได้ และเพิ่ม row action bar ลัดไปคิว `รอหัก`/`ยังไม่ผูก` ของรอบนั้นทันที เพื่อลดการคลิกซ้ำรายเดือน
- ขยาย `tools/preflight_payrun.py` เพิ่ม `manager_summary` (pending total + risk share %) และอัปเกรดไฟล์ morning queue ให้มี executive summary เชิงตัวเลขสำหรับผู้จัดการ

## 2026-05-07 (AYU preflight hardening + unresolved queue)

- ขยาย `ProjectYK_System/tools/preflight_payrun.py` ให้ทำ **safe-case triage** สำหรับ unlinked: แยก `quickwin_preflight_*.json` (single-match ปลอดภัย) ออกจาก `unresolved_preflight_*.json/.csv` (missing/ambiguous/no-match) โดยไม่แก้ DB และไม่เดา
- เพิ่มมิติรายงานใหม่ `dimension_unlinked_resolution` ใน preflight JSON เพื่อสรุปจำนวน/ยอดเงินของเคสค้าง vs quick win แบบตรวจสอบย้อนกลับได้
- ยืนยัน policy รอบล่าสุดผ่าน `TestClient`: finalize gate แบบ `cycle-date drift > 0` ยังคงบังคับเฉพาะ **BIGC/LCB**; ฝั่ง **AYU** คงพฤติกรรมเดิม (เช็ค `unlinked_pending` ก่อน)

## 2026-05-07 (Night-run: BIGC/LCB drift-first verify + tri-site preflight refresh)

- ปรับลำดับ gate ใน `POST /payroll/{run_id}/finalize` ให้ **BIGC/LCB** เช็ค drift ก่อน unlinked เพื่อให้ block reason ตรง policy ที่ล็อกไว้และสร้าง unresolved drift report ได้ทันที
- ยืนยัน finalize ซ้ำ 2 รอบ: `run_id=10 (BIGC)` และ `run_id=9 (LCB)` ตอบ `err=cycle_drift_block` ต่อเนื่อง; `run_id=7 (AYU)` ตอบ `err=unlinked_pending`
- รัน `tools/preflight_payrun.py` ใหม่ครบ `BigC -> LCB -> AYU` เพื่ออัปเดตรายงานความเสี่ยงล่าสุด (`reports/preflight_payrun_*`) และโน้ตคิวเช้า (`reports/preflight_morning_queue/PENDING_MORNING_preflight_*.md`)

## 2026-05-07 (LCB preflight readonly + finalize drift parity)

- เพิ่มเครื่องมือ readonly `ProjectYK_System/tools/preflight_payrun.py` — สแกน 4 มิติ (unlinked / cycle-date drift / cross-site indicator / source scan) และส่งออก JSON + โน้ตคิวเช้าเมื่อ `summary_risk_level=HIGH` ใต้ `reports/preflight_morning_queue/`
- ขยาย `POST /payroll/{run_id}/finalize` ให้ **บล็อก cycle-date drift** เหมือน BigC สำหรับ **`LCB`** พร้อม unresolved reason `lcb_cycle_date_drift_block` และ refactor predicate ร่วม `_cycle_drift_predicates_for_payrun()`
- ปรับข้อความ error หน้า `payroll_detail.html` เป็นนโยบาย payroll **BIGC/LCB**

## 2026-05-07 (BigC residual close-out pass 2)

- ปิด residual `พรศักดิ์ trip +1,300` ด้วย **surgical data fix** แถวซ้ำ `DailyJob.id=5211` (`source=bigc_fuel_rate`) โดยตั้ง `trip_fee_driver=0`, recompute `PayRun.id=10`, และ rerun audit ที่ `reports/audit_bigc_2026-03_recheck_mminus1_after_residual_focus/` ทำให้ `trip_fee_diff_total +1,300.00 -> 0.00`
- ยืนยัน residual `สมพร net -9,999.99` เป็น **manual-sheet net formula gap** (แถว `เงินประกันตน = -10000` ทำให้ `ยอดรับหลังหักค่าใช้จ่าย` สูงกว่าระบบ 9,999.99) และคงสถานะ unresolved แบบ safe-by-default รอผู้ใช้ยืนยันนิยาม net ที่ต้องใช้ตัดสิน

## 2026-05-07 (BigC finalize hard block + unresolved queue safety)

- บังคับ policy ฝั่งระบบจริง: `POST /payroll/{run_id}/finalize` จะ **block ทันที** เมื่อรอบ `BIGC` ยังมี `cycle-date drift > 0` (pending สดย่อยติด `pay_cycle_tag` รอบ แต่ `txn_date` อยู่นอกช่วงวิ่ง)
- เพิ่ม unresolved queue/fail logging อัตโนมัติลง `reports/payroll_unresolved_queue/` เมื่อโดน block ด้วยเหตุผล `bigc_cycle_date_drift_block` และถ้าเหตุเดิมเกิดซ้ำจะสร้างไฟล์ `PENDING_MORNING_*.md` ตามนโยบาย “หยุดวนลูปแล้วไปทำงานอื่น”
- ขยาย `tools/audit_bigc_manual_vs_system.py` ให้ใช้ safe skip กับชีทชื่อกำกวม/ไม่ match ระบบ พร้อมส่งออก `unresolved_queue.json/.csv` + history/repeat marker เพื่อไล่แก้เฉพาะเคสโดยไม่ล่มทั้งรอบ

## 2026-05-07 (Operational pack v1 — guardrails + performance + chat backup)

- ล็อกกติกา BigC cycle mapping รายเดือน: เดือนจ่าย `M` ต้อง map ไปเดือนวิ่ง `M-1` และสดย่อย `M-1` เสมอ
- รัน BigC recheck เดือนจ่ายเม.ย.2026 ตามกติกา `M-1` แล้ว (ใช้ `cycle_tag=2026-03`) พร้อม preflight 4 มิติ: unlinked=0, พบ cycle-date drift 1 รายการ 500 บาท, และตัวชี้วัด cross-site collision 6 คนสำหรับติดตามเชิงลึก
- ปรับ `audit_bigc_manual_vs_system.py` ให้ parse `Book1.xlsx` แม่นขึ้น (`อื่นๆ` + `ยอดรับหลังหักค่าใช้จ่าย`) ทำให้ช่องว่าง audit ลดลงมาก: `petty_diff +49,825.91 -> -2,000.00` และ `net_diff +107,749.01 -> -5,958.63`; พร้อมเพิ่ม guardrail cycle-date drift บนหน้า `/payroll/{run_id}` แสดงจำนวนรายการและยอดเงินกระทบ
- Drill-down line-level ยืนยันเคส `สมพร BIG-C`: ไฟล์ผู้ใช้ (`Book1` ชีทสมพร แถว 93/96) มีเงินเบิก 2,000 ตรงกับ DB (`PettyCashTxn.id=55933`) และ mismatch เดิมเกิดจาก payrun stale ก่อน recompute; หลัง recompute `petty_diff_total` เหลือ 0
- ปรับ parser fuel ใน `audit_bigc_manual_vs_system.py` ให้แยก amount ออกจาก ratio (`ค่าเรทน้ำมัน`/`น้ำมันทำได้` เท่านั้น และ preserve sign) ทำให้ `fuel_rate_diff_total` ลดจาก `-6,272.43` เหลือ `0.23`
- เพิ่มเอกสารใช้งานทันทีสำหรับผู้ใช้ 1 คน: `docs/CURSOR_CLAUDE_DAILY_GUARDRAILS_CHECKLIST_TH.md` (เช็กลิสต์ก่อนเริ่ม/ก่อนสรุปงาน + safe defaults)
- เพิ่ม `docs/PERFORMANCE_FIRST_PASS_CHECKLIST_TH.md` สำหรับวัดก่อน-หลังรอบแรกแบบเร็ว (time-to-first-change, token, clarification rounds) ผูกกับ `tools/CC_BENCHMARK_LOG.md`
- เพิ่ม `tools/CHAT_KNOWLEDGE_BACKUP_TEMPLATE_TH.md` เป็น template copy-paste กันความรู้หลุดจากแชต (session backup, domain facts, leak check, before/after, manual steps)
- อัปเดต `AI_CURSOR_CLAUDE_WORKFLOW.md` ให้ชี้ Daily Operation Pack และ backup template เพื่อให้เริ่มใช้งานได้จากจุดเดียว
- แก้เสถียรภาพ `.cursor` `sessionStart` hook บน Windows: `cursor-digest.ps1` retry ได้หลัง network fail (ไม่ lockout ทั้งวัน), stdout JSON ทุกเส้นทาง, และเพิ่ม timeout ใน `hooks.json` จาก 10s เป็น 20s

## 2026-05-07 (Wave 1 UX Guardrail #1 — Site pre-assignment in petty cash import)

- **Guardrail #1 implemented**: `services/alias_map.py` เพิ่ม `site_from_requester()` — ฟังก์ชันกลางตรวจ suffix ชื่อผู้เบิก (`BIG C/BIG-C/BIGC` → BIGC, `อยุธยา/AYU` → AYU, `แหลม/LCB/แหลมฉบัง` → LCB) สำหรับทุก tool ที่ต้องการ
- **`tools/import_petty_cash.py`**: เรียก `site_from_requester()` ตอน insert ทันที (ไม่รอ backfill) — กัน cross-site contamination ตั้งแต่แถวแรก; ย้าย duplicate site-hint logic ใน `link_drivers_safe()` มาใช้ฟังก์ชันเดิม (DRY)
- **Impact (existing DB)**: 299 blank-site rows ที่มี suffix ชัดเจน (BIGC 205 rows ฿505k, AYU 71 rows ฿32k, LCB 23 rows ฿72k) จะถูก pre-assign ในการ re-import ครั้งถัดไป; 38,928 rows ไม่มี suffix (พ่อ/โอ/ออฟฟิส) ยังคงว่างตามปกติ
- **Next (Guardrail #2)**: saved filter preset ต่อหน้าใน petty-cash/daily/payroll (`BigC เดือนนี้`, `รออนุมัติ`, `ยังไม่ผูก`) — link ผ่าน URL query string + คลิกเดียว

## 2026-05-07 (Forward Insight benchmark — เมนูเชิงระบบและ UX ที่ควรยืมใช้)

- สำรวจระบบตัวอย่างจริง (session login ผู้ใช้) แล้วได้ pattern ที่ใช้กับ One Platform ได้ทันที: โครงเมนูแบบ domain-first (`ขนส่ง/จัดซื้อ/บัญชี/บุคคล/ตั้งค่า`) + mega-menu รวมเมนูย่อยในจอเดียว ลดการคลิกหาเมนู
- ยืนยันคุณค่าของ flow เชื่อมงาน: `Trip -> Expense/Fuel -> Payroll` โดยมีคีย์อ้างอิงร่วม (`trip_no`/ทะเบียน/ผู้รับเหมา/พนักงาน) และสถานะงานแบบ workflow ชุดเดียว (ร่าง/กำลังดำเนินการ/รอชำระ/ชำระแล้ว)
- ตกลงเพิ่มงานปรับ UX/guardrail ฝั่ง YK: (1) action bar ระดับรายการ, (2) saved filter preset สำหรับงานซ้ำรายเดือน, (3) ป้ายสถานะมาตรฐานข้ามหน้า, (4) ปุ่ม export/report ที่ผูกกับ context filter ปัจจุบัน
- เพิ่มเอกสาร checklist ความครบของเมนู demo: `TransportRateCalculator/docs/FORWARD_INSIGHT_MENU_CHECKLIST.md` เพื่อปิดงานแบบติ๊กหน้า `[done]/[partial]/[todo]` ให้ตรวจสอบความครบได้ชัดเจน

## 2026-05-07 (BDT communication framing — DHL support vs distance-limited economics)

- บันทึกบริบทหน้างานการสื่อสารกับลูกค้า: เดิมช่วงวิ่งกับ DHL มีการซัพพอร์ตงานทดแทนเมื่อโหลดต่ำ แต่บริบทปัจจุบันกับ BDT ไม่มีกลไกทดแทนเทียบเท่า และโครงสร้างราคาไม่ผันตามกม. ทำให้รับงานได้เฉพาะช่วงระยะที่ไม่ขาดทุน (200–600 กม.) เพื่อคุม cash burn

## 2026-05-26 (Oatside — ราคาน้ำมันบางจาก พ.ค. + โชว์ลูกค้าเฉพาะ พ.ค.)

- เติม `diesel_price_history` พ.ค. จากตารางบางจาก (ไฮดีเซล S คอลัมน์ที่ 5); `report_start_date=2026-05-01`; `customer_rate_summary` ไม่โชว์เรท เม.ย.
- เก็บเงื่อนไขวางบิล เม.ย. ใน `Oatside/docs/BILLING_LOCKED_APR2026.md` + `_billing_locked_april_2026` ใน config
- Rebuild + push Pages `oatside-pg-2026` (commit `38b6166`)

## 2026-05-26 (Oatside — อัปเดต GPS พ.ค. 2569 + deploy Pages)

- นำเข้าไฟล์ GPS ใหม่ (26.05.2026) Oatside + P&G → `Oatside/`; ขยาย `report_end_date` เป็น `2026-05-31` ใน `oatside_config.json`
- Build ล่าสุด: **Trips 123 | Unmatched 18**; push ขึ้น `yk-logistics/transport-rate-calculator` → `reports/oatside-pg-2026/`

## 2026-05-05 (Claude Code — `CLAUDE.md` ที่ราก repo)

- เพิ่ม **`CLAUDE.md`** ที่ราก `Project YK`: บริบทโปรเจกต์, ลำดับอ่านบังคับ, กฎเงิน/ข้อมูล, การทำงานคู่กับ Cursor, ท่าประหยัดโทเค็น, และ **แผนแบบ milestone (ไม่บังคับ Gantt SaaS 33 สัปดาห์)** — อ้าง `NEXT_ACTION_PLAN.md` เป็นของจริง

## 2026-05-06 (Vibecoding playbook — Cursor -> Claude Code, ครบ 3 ไซท์)

- เพิ่มเอกสาร **`ProjectYK_System/TransportRateCalculator/docs/CLAUDE_CODE_VIBECODING_PLAYBOOK.md`**: working contract, DoD, preflight บังคับ 4 checks, จุดโฟกัสรายไซต์ (BigC/LCB/AYU), token-saving rules, และ prompt อังกฤษพร้อมใช้
- อัปเดต **`ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`** เพิ่ม “Prompt mode สำหรับโอ (Vibecoding)” เพื่อให้ Cursor สรุป prompt อังกฤษที่คุมความเสี่ยงข้อมูลเงินและบังคับ recompute before/after

## 2026-05-06 (Claude Code 2-Agent auto loop runbook)

- เพิ่มเอกสาร **`ProjectYK_System/TransportRateCalculator/docs/CC_AUTO_TWO_AGENT_RUNBOOK.md`**: ขั้นตอนใช้งานจริงแบบ 2 terminal (`Coordinator` + `Executor`), มาตรฐาน Task Card, วนลูป quality gate, token-saving tactics, และ handoff snapshot กัน context หลุด

## 2026-05-06 (BigC audit baseline script — manual Excel vs system)

- เพิ่มสคริปต์ **`ProjectYK_System/tools/audit_bigc_manual_vs_system.py`** สำหรับเทียบ baseline manual (Daily/Petty/Payroll/Fuel) กับผลระบบรอบ BIGC `2026-03`
- output เป็น **JSON + console summary** (`reports/audit_bigc_2026-03/summary.json`) และใช้ policy จับชื่อคนขับแบบ **nickname-first, fallback full_name**
- รันจริงแล้วได้ diff สรุปตัวอย่าง: `system_drivers=9`, `manual_sheets=22`, `matched=8`, `value_mismatch_drivers=8`, และ `net_diff_total=107,749.01`
- อัปเดตสคริปต์รอบสอง: ตัดชีท non-driver อัตโนมัติ + จำกัดชีทให้ตรงคนขับในระบบ, ปรับการอ่านตัวเลขจาก label ให้หยิบค่าถัดจาก label ก่อน (ลด false read), และเพิ่มไฟล์ CSV review (`matched_compare.csv`, `value_mismatch.csv`, `missing_in_manual.csv`, `extra_in_manual.csv`)

## 2026-05-05 (Oatside Excel — `Trip_Detail` เติมคอลัมน์ราคา)

- **`Oatside/build_oatside_reports.py`**: ชีต `Trip_Detail` เพิ่ม `Trip_rate_baht`, `Downtime_50_baht`, `Downtime_100_baht` (คง `Nw_outbound50_baht`, `Return_manual_baht`) โดยคำนวณตามกติกาเดียวกับหน้า `trips.html` (split +50/+100 เฉพาะเที่ยวแรกของทะเบียนในวัน `Dest_In`)

## 2026-05-05 (Oatside Excel — เพิ่มไฟล์ `15_Trips_Pricing_All.xlsx`)

- **`Oatside/build_oatside_reports.py`**: เพิ่มชีต/ไฟล์ส่งออก `Trips_Pricing_All` สำหรับ “รายการราคาเที่ยวทั้งหมด” คอลัมน์ `Dest_In_date`, `Plate`, `Trip_rate_baht`, `Downtime_0_trip_baht`, `Downtime_1_trip_baht`, `Blank_run_baht`, `Return_job_baht`

## 2026-05-01 (Oatside — ซ่อน/แสดงคอลัมน์บน `trips.html` + หน้า plate)

- **`Oatside/build_oatside_reports.py`**: แผง **แสดง/ซ่อนคอลัมน์** (checkbox + `localStorage` ต่อ path + ตาราง) สำหรับ `#tripsAllTable` / `#plateTripsTable` — สคริปต์ `_COL_TOGGLE_JS`

## 2026-05-04 (Oatside — trips.html: วัน+เวลาในคอลัมน์แรก; แถว UM เติม Orig/Travel/Dest Wait + `um_leg_prev_gap_h`)

- **`Oatside/build_oatside_reports.py`**: `um_leg_prev_gap_h`; UM แถวใช้ dwell/prev ใน 3 คอลัมน์รอ — เครื่องมือ `ProjectYK_System/tools/patch_oatside_trips_um_wait_time.py`, `patch_oatside_trips_date_cells.py`

## 2026-05-01 (Oatside — GitHub Pages: ไฟล์รวมใน exports/ + ลิงก์ไม่ใช้ ../../../Oatside)

- **`Oatside/build_oatside_reports.py`**: `write_split_excel_exports` คัดลอก workbook เต็ม → **`exports/00_Full_Workbook.xlsx`**; ลิงก์ «Excel รวมทุกชีต» ชี้ **`exports/00_Full_Workbook.xlsx`** (แทน path ออกนอกโฟลเดอร์รายงาน) — deploy ต้องรวมโฟลเดอร์ **`exports/`** ขึ้น Pages

## 2026-05-01 (Oatside — Unmatched เวลาอยู่จุด + gap ถึง In ถัดไป)

- **`Oatside/build_oatside_reports.py`**: `build_leg_timeline_by_plate` / `um_leg_dwell_gap_h` — คอลัมน์ **อยู่จุด (ชม.)** / **ถึงเข้าครั้งถัดไป (ชม.)** (HTML + Excel **Unmatched_Log** `Dwell_h`, `Gap_to_next_In_h`); แถว matched บน `trips`/`plates` เป็น `—` — **`ProjectYK_System/tools/apply_oatside_um_v2.py`** + อัปเดต **`OATSIDE_CUSTOMER_REPORT_SPEC.md`**

## 2026-05-04 (Oatside HTML — hero หน้าเที่ยว + Excel ขวาหัวแต่ละตาราง)

- **`Oatside/build_oatside_reports.py`**: ลบบล็อก **คำอธิบายสี / ไฮไลต์ชั่วโมงรอ**; แถบ **hero** ชวนเปิด `trips.html` + ลิงก์ Excel รวม; ลิงก์ **ดาวน์โหลด Excel** อยู่ **ขวาใน `<summary>`** ของแต่ละหัวข้อ; **`trips.html`** เน้น “หน้าหลักลูกค้า” + ปุ่ม Excel Trip Detail ขวาหัวตาราง — **`ProjectYK_System/tools/patch_oatside_hero_xlsx_inline.py`**
- **`Oatside/build_oatside_reports.py`**: CSS `summary.section-sum-row` ให้เต็มความกว้าง + ดันลิงก์ Excel ชิดขวา; ข้อความ **(คลิกเพื่อขยาย)** ของ Audit ย้ายไปหน้าหัวข้อ — **`ProjectYK_System/tools/patch_oatside_summary_flex_audit.py`**

## 2026-05-04 (Oatside Excel — export แยกต่อตาราง + จัดรูปแบบ)

- **`Oatside/build_oatside_reports.py`**: `beautify_oatside_workbook` (หัวตารางสีแบรนด์, zebra, filter, freeze, คอลัมน์เงิน `#,##0`) + **`write_split_excel_exports`** → โฟลเดอร์ **`reports/oatside-apr2026/exports/*.xlsx`** 14 ไฟล์ — **`ProjectYK_System/tools/patch_oatside_excel_exports.py`** (ลิงก์จาก UI ย้ายไปขวาหัวแต่ละตารางใน Session #107)

## 2026-05-01 (Oatside HTML — กรองทะเบียน trips + พับหัวข้อสรุป)

- **`Oatside/build_oatside_reports.py`**: `trips.html` — `<select>` + ช่องค้นหา + `data-plate` ต่อแถว + JS กรอง; **`index.html`** — หัวข้อสรุป/รายทะเบียน ใช้ `<details class='section-fold'>` แบบ Audit — **`ProjectYK_System/tools/apply_oatside_ui_trips_filter_index_fold.py`**

## 2026-05-01 (Oatside — manual_return_trips: ค่าขนส่งขากลับ flat)

- **`Oatside/build_oatside_reports.py`** + **`Oatside/oatside_config.json`**: `manual_return_trips` (ไม่เพิ่ม matched) — คอลัมน์ **ขากลับ(฿)** บน HTML + Excel `Return_trip_baht` / ชีต **`Manual_Return_Trips`** + บรรทัด **R** ใน Customer_Summary — `ProjectYK_System/tools/apply_oatside_manual_return_trips.py`

## 2026-05-01 (Oatside — manual_extra_trips: เที่ยวลูกค้าตกลงแต่ไม่มีใน GPS)

- **`Oatside/build_oatside_reports.py`** + **`Oatside/oatside_config.json`**: `manual_extra_trips` บวกเข้าฐาน/audit/CPD + ชีต **`Manual_Extra_Trips`**; **`ProjectYK_System/tools/patch_oatside_manual_extra_trips.py`** (แก้ anchor + comma ใน default JSON)

## 2026-05-01 (Oatside — คอลัมน์เงิน trips + dedupe origin24h + sticky หัวตาราง)

- **`Oatside/build_oatside_reports.py`**: คำอธิบายใต้ `trips.html` ว่าคอลัมน์เงินไม่ได้มาจากชั่วโมง Dest Wait โดยตรง; **อย่างมากหนึ่ง** surcharge `origin24h` ต่อ `(ทะเบียน, วัน Dest_In)` เพื่อกันซ้ำ 3,750+3,750=7,500; ตารางเที่ยวใช้ **`.table-scroll` + `thead th` sticky** (`trips.html`, `plates/*.html`)
- **`Oatside/build_oatside_reports.py`**: แถวตารางเที่ยวแบ่งโทนสีตามวัน (`day-band-0`/`day-band-1`; matched ยึด **Origin_In**, UM-D ใช้เวลา leg แทน) + รักษาไฮไลต์รอนาน; **เรียง matched ตาม `Origin_In`** ใน `interleaved_matched_unmatched_rows_html`

## 2026-05-01 (Oatside HTML — ป้าย surcharge: +100% ข้ามคืน + แยก ตีเปล่า / ค่าเสียเวลา)

- **`Oatside/build_oatside_reports.py`**: `fifty_kind` + `html_fifty_surcharge_badge` + คอลัมน์ **`Fifty_kind`** ใน Excel; การ์ด/ตาราง HTML ใช้คำว่า **ส่วนเพิ่ม** แทน +50% ตายตัว — `ProjectYK_System/tools/apply_oatside_fifty_patch.py`, `patch_oatside_audit_sub.py`
- **แก้ #98**: default วันงาน Origin 1 เที่ยว = **`downtime_origin_day`** (ป้าย **ค่าเสียเวลา +50%**); **ตีเปล่า** เฉพาะ `action: blank_run` หรือ note มี «ตีเปล่า»; ข้ามคืนเต็มเรท = **ค่าเสียเวลา +100%** — `ProjectYK_System/tools/patch_oatside_fifty_kind_v2.py`
- **#99**: คอลัมน์ส่วนเพิ่ม HTML — **หลายป้ายต่อวัน**; **No-work recovery** แสดงเป็น **ตีเปล่า +50%** ในคอลัมน์เดียวกับ fifty — `patch_oatside_multi_badge_nw.py`

## 2026-05-03 (Oatside — พิมพ์เขียว schema สำหรับ Claude บนเว็บ / Artifacts)

- **`TransportRateCalculator/docs/OATSIDE_BACKEND_SCHEMA.md`**: สรุปข้อมูล/ pipeline / billing / ชีต Excel / HTML สำหรับโยนให้ฝั่งเว็บออกแบบ UI โดยไม่ต้องอ่านทั้ง repo

## 2026-05-02 (Oatside — ปลายทางรอข้ามคืน → fifty เติมตาม `dest_date` + deploy.ps1)

- **`Oatside/build_oatside_reports.py`**: `long_dest_wait_midnight_fifty` + `supplement_long_dest_wait_midnight_fifty` (เช่น 71-6802 รอปลายทางข้ามคืน แต่ไม่มี Origin วันนั้น) — `ProjectYK_System/tools/patch_oatside_midnight_dwell_fifty.py`
- **`long_dest_wait_midnight_full_trip`** (default true): ค่าเติมข้ามคืน = **เรทเต็ม 1 เที่ยว** (ไม่ใช่แค่ +50%); **ไฮไลต์** รอต้นทาง/ปลายทางเกินเกณฑ์ชม. บน HTML — `patch_oatside_full_trip_midnight_highlight.py`
- **`deploy_oatside_report.ps1`**: แก้ `throw`/here-string ที่ทำให้ PowerShell parse พัง

## 2026-05-01 (Oatside — wave3: default `use_origin_24h_fifty` + no-work recovery + phantom/hints)

- **`Oatside/build_oatside_reports.py`**: default **`use_origin_24h_fifty=True`**; **`customer_no_work`** + **`outbound_half_dest_dates`** (auto วันหลังจบช่วง); บรรทัด **D** / รวม grand; **`Trip_Detail.Nw_outbound50_baht`**; ชีต **`NoWork_Outbound_50pct`**, **`Phantom_Trip_Candidates`**, **`Hints_DoubleOrigin`**; HTML **`grand_extra`** รวม no-work — สคริปต์ `ProjectYK_System/tools/apply_oatside_wave3_*.py`
- **นโยบาย recovery + fifty**: โอเลือก **เก็บคู่** (เที่ยวแรกวัน recovery อาจได้ทั้ง fifty ดาวน์ไทม์และ No-work 50% — บวกทั้งคู่); ชีต **Info** แถว **`Policy_recovery_plus_fifty`** — `ProjectYK_System/tools/apply_oatside_recovery_policy_info.py`

## 2026-05-02 (Oatside build — `customer_idle_windows` + optional `use_origin_24h_fifty`)

- **`Oatside/build_oatside_reports.py`**: ตัด `Dest_Wait` ช่วงฝากลูกค้า (`customer_idle_windows`, default **71-8967** 20–29 เม.ย.); `Trip_Detail` คอลัมน์ customer wait/cycle; **`use_origin_24h_fifty`** สลับกฎ +50% เป็น rolling 24h จาก `Origin_In` — `OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`; patch scripts ใต้ `ProjectYK_System/tools/patch_oatside_*.py`

## 2026-05-02 (Agent workflow — ถามก่อนลงมือ + Oatside เคส 71-8967)

- **นโยบายทุกแชท**: ถ้าคำสั่งยังกำกวม → **ถามให้เคลียร์ก่อนลงมือ** — `.cursor/rules/oa-careful-default.mdc`, `.cursor/rules/project-yk-context.mdc` §1b, `AGENTS.md`
- **Oatside / ฝากรถ P&G**: **`71-8967`** ช่วง **`2026-04-20 ~14:00`–`2026-04-29 ~17:00` (ไทย)** — เที่ยวส่งก่อนจอด **นับลูกค้าปกติ**; ช่วงจอดในโรงงานหลังนั้น **ไม่เกี่ยวลูกค้า** (ยกเว้น dwell/เตือน); หลัง `Dest_Out` ถ้ามีวิ่งต่อนับตีเปล่าปกติ — `CONTEXT_LOG.md` Session #91

## 2026-05-02 (Oatside — ชีต/หน้าเว็บ «จำนวนเที่ยวต่อวัน» สำหรับลูกค้า)

- `Oatside/build_oatside_reports.py`: **`customer_trips_per_day_rows()`** + ชีต Excel **`Customer_Trips_Per_Day`** + ตารางบน **`index.html`** (นับ matched ตามวันที่ `Dest_In` · รวมทุกทะเบียน) — เอกสาร **`OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`**, **`OATSIDE_LOCAL_UPDATE_WITHOUT_UPLOAD.md`**

## 2026-05-02 (Oatside GitHub Pages — path รายงานใหม่ `oatside-pg-2026`)

- **`deploy_oatside_report.ps1`**: **`PagesReportSlug`** (default `oatside-pg-2026`) + **`RemoveLegacyApr2026`** ลบ `reports/oatside-apr2026` เมื่อ deploy — **`deploy_oatside_report_one_click.bat`** ส่ง `-RemoveLegacyApr2026 $true` ให้ลิงก์เก่า 404 หลัง push; อัปเดตลิงก์ใน **`OATSIDE_LOCAL_UPDATE_WITHOUT_UPLOAD.md`**, **`NEXT_ACTION_PLAN.md`**, **`docs-public/one-platform-status/index.html`**

## 2026-05-02 (Payroll + Petty — unlinked ที่ `site_code` ว่างไม่ถูกนับใน guardrail)

- **ปัญหา**: แถวหักสดย่อย pending + ยังไม่ผูกคนขับแต่ `site_code` ว่าง → แบนเนอร์ payroll / finalize gate เดิมมองไม่เห็น (กรองแค่ไซต์รอบ)
- **แก้**: `main.py` — `_petty_unlinked_predicates_for_payrun` + stale petty scan; `payroll_detail.html` — ลิงก์สดย่อยใช้ `cycle=`; `payroll.py` + `payroll_slip.py` — รวม `site_code` ว่างเมื่อคิดยอด/สลิป

## 2026-05-02 (Cloud demo — Postgres + Basic auth + คู่มือฟรี)

- **`DATABASE_URL`** → แอปใช้ **PostgreSQL**; ไม่ตั้ง = SQLite เดิม (`db_config.py`, แก้ `main.py` + `_ensure_column` เฉพาะ SQLite)
- **`preview_auth.py`** + env **`YK_PREVIEW_AUTH` / `YK_PREVIEW_USER` / `YK_PREVIEW_PASSWORD`** — HTTP Basic กันคนนอก (ยกเว้น `/health`, `/static/`, `/uploads/`)
- **`ProjectYK_System/tools/sqlite_to_postgres.py`** + **`psycopg2-binary`** — ย้าย `app.db` → Postgres (`--wipe` บังคับ)
- **`ProjectYK_System/docs/HOSTING_FREE_DEMO_TH.md`** + **`render.yaml`** (ราก repo) — Neon + Render แบบฟรี
- **`ProjectYK_System/tools/cloud_demo_setup.ps1`** — รันบนเครื่องหลังได้ `DATABASE_URL` จาก Neon: pip + migrate + พิมพ์ env สำหรับ Render
- **`AGENT_BOOTSTRAP.md`** — ลิงก์คู่มือโฮสต์

## 2026-05-02 (Static pitch — One Platform สำหรับ GitHub Pages)

- เพิ่ม **`ProjectYK_System/docs-public/one-platform-status/index.html`** — หน้า HTML สรุป roadmap/สถานะระบบ (ไทย) + ลิงก์ไป Calculator root และรายงาน Oatside บน `yk-logistics.github.io`
- **`README_DEPLOY.md`** ในโฟลเดอร์เดียวกัน — วิธีคัดลอกไป `transport-rate-calculator/reports/one-platform-status/` แล้ว push
- **`build_public_stats.py`** + **`public-stats.json`** — ดึงสถิติจริงจาก `app.db` (จำนวนแถว / ช่วงวันที่ / จำนวนตามไซท์) ไม่มีชื่อคนหรือยอดเงินรายบรรทัด; หน้า `index.html` โหลด JSON แบบ `fetch`
- Push ขึ้น **`yk-logistics/transport-rate-calculator`** แล้ว (โฟลเดอร์ `reports/one-platform-status/` บนเครื่อง `transport-rate-calculator-repo`)
- หน้า pitch: เพิ่ม **`assets/screenshot-daily-desktop.png`** (หน้า Daily จริง) + คำอธิบายว่า GitHub Pages ไม่รัน FastAPI; ลบหัวข้องบ AI/IDE และ bullet Open-book / Profit share

## 2026-05-01 (Oatside — `match_plate` ปลายทางก่อน + ต้นทางล่าสุดก่อน Dest_In)

- `Oatside/build_oatside_reports.py`: แทนที่ origin-first greedy ด้วยการไล่ **`Dest` ตามเวลา** แล้วเลือก **`Origin_Out` ล่าสุด** ที่ feasible — ลด UM ผิดพลาด + ลดการชน `demote_chronology_violations` เป็นวง (ตัวอย่าง 71-6802 คู่ 19:51→21:35); เอกสาร **`OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`** §4 — build ล่าสุด **Trips 105 | Unmatched 15**

## 2026-05-01 (Oatside — อธิบาย UM 71-6802: greedy + chronology demote + build Origin 07-15-32)

- เอกสาร **`TransportRateCalculator/docs/OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`** (กรณีจอ UM 14:22/18:46) + **`OATSIDE_ORIGIN_CHAIN_MERGE_FIX.md`**; สคริปต์ **`ProjectYK_System/tools/run_oatside_may02_build.py`** ชี้ `...07-15-32 Oatside.xlsx` — build ล่าสุด **Trips 90 | Unmatched 45** (คู่กับ P&G `06-58-42`)

## 2026-05-01 (Oatside — ปิด chain-merge Origin ได้ทั้งก้อน + build ชุด GPS 02.05.2026)

- `Oatside/build_oatside_reports.py` + `oatside_config.json` template: **`enable_origin_chain_merge`** default **false** → ไม่รวมหลายแถวต้นทางก่อนปลายทาง; ตั้ง **true** ถ้าต้องการ merge พร้อม **`max_origin_chain_gap_h`** — อัปเดต **`TransportRateCalculator/docs/OATSIDE_ORIGIN_CHAIN_MERGE_FIX.md`** + สคริปต์ตัวอย่าง **`ProjectYK_System/tools/run_oatside_may02_build.py`**

## 2026-05-01 (Oatside — แก้ chain-merge Origin ผิดเมื่อปลายทางมาช้า)

- `merge_chained_origin_pairs(pairs, cfg.max_origin_chain_gap_h)`: หยุดรวมเมื่อช่องว่าง `Origin_Out` → `Origin_In` ช่วงถัดไปเกินเกณฑ์ — `OatsideConfig` + `oatside_config.json` **`max_origin_chain_gap_h`** (ค่าเริ่มต้น 3 ชม.) + เอกสาร **`TransportRateCalculator/docs/OATSIDE_ORIGIN_CHAIN_MERGE_FIX.md`**

## 2026-05-01 (Oatside HTML — Unmatched แทรกตามเวลา Dest In / leg.t_in)

- `Oatside/build_oatside_reports.py`: `interleaved_matched_unmatched_rows_html()` — เรียง matched (`d_in`) กับ unmatched (`leg.t_in`) ในตารางเดียว; `trips.html` / `plates/*.html`

## 2026-05-01 (Oatside HTML — Unmatched รวมแถวในตารางเดียวกับ matched)

- `Oatside/build_oatside_reports.py`: `unmatched_merged_trip_rows_html()` — แถว UM-O/UM-D ใช้คอลัมน์เดียวกับเที่ยว matched; เว้นวัน/เวลาฝั่งที่ยังไม่มีคู่เป็น em dash; `trips.html` / `plates/*.html` ตารางเดียว

## 2026-05-01 (Oatside — ปิดเก็บเงินค่าชดเชย min trips เมื่อใช้ชาร์จ 50%)

- `Oatside/build_oatside_reports.py` + `oatside_config.json` default: **`charge_min_trip_shortfall`** default **false** → ยอดลูกค้า = base + 50% เท่านั้น (การ์ด/Excel ยังโชว์เที่ยวขาดเป็น KPI แต่เงินชดเชย = 0); ตั้ง **true** ถ้าต้องการโหมดเก็บทั้งค่าชดเชย + 50% แบบเดิม

## 2026-05-01 (GitHub — Oatside/Pages repo อยู่ org `yk-logistics`)

- Repo **`yk-logistics/transport-rate-calculator`** + Pages รายงาน Oatside (อัปเดต path): `https://yk-logistics.github.io/transport-rate-calculator/reports/oatside-pg-2026/index.html` — เอกสาร deploy / `OATSIDE_LOCAL_UPDATE_WITHOUT_UPLOAD.md` / `deploy_oatside_report*.ps1|bat`

## 2026-05-01 (AI workflow — Cursor vs Claude Code + rtk/Graphify/mem)

- เพิ่ม **`ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`** (แบ่งงาน, Windows/rtk, Graphify, claude-mem, บล็อก HANDOFF คัดลอกวาง)
- อ้างอิงใน **`AGENTS.md`** (Key files #6) และ **`AGENT_BOOTSTRAP.md`** (อ่านเมื่องานเกี่ยวกับเครื่องมือ AI)
- อัปเดต workflow: ชัดว่า Cursor **ไม่แจ้งออโต้** — บังคับ Agent ให้ใส่หัวข้อ **ท่าประหยัดโทเค็นที่ใช้ในรอบนี้** เมื่อผู้ใช้ขอเขียน prompt สำหรับ Claude Code

## 2026-05-01 (Oatside — เรทเที่ยว 12-15 เม.ย. 2026 = 8000 นอกนั้น 7500)

- `Oatside/build_oatside_reports.py`: `trip_rate_baht` ใช้วันที่ **Dest_In** ช่วง **2026-04-12..15** → **8000** บาท · นอกช่วง → **7500** บาท (เดิม 9–11=7500 / อื่น=8000)

## 2026-05-01 (Oatside — billing 50% วันละ 1 เที่ยว + สรุปลูกค้า + overrides JSON)

- `Oatside/build_oatside_reports.py`: ตัด lost-time ตาม wait threshold; เก็บ **50%** เมื่อ matched **1 เที่ยว/วัน/ทะเบียน** (`Dest_In`); โหลด `Oatside/oatside_billing_overrides.json` (`exclude_50` / `include_50`) หรือ `OATSIDE_OVERRIDES_JSON`
- Excel: `Customer_Summary`, `Plate_DestDay`, `Surcharge_50pct_1Trip`; HTML: การ์ดยอดรวมลูกค้า + ตารางรายวัน + หน้า plate แสดงวันไหนโดน +50%

## 2026-05-01 (Oatside — guard ลำดับเวลา + deploy เลือกรายงานล่าสุด)

- `Oatside/build_oatside_reports.py`: `demote_chronology_violations` — ถ้า `Origin_In` เที่ยวถัดไป `< Dest_Out` เที่ยวก่อนหน้า (ทะเบียนเดียวกัน) ให้เที่ยวก่อนหน้าไป Unmatched แล้ววนจนนิ่ง
- `deploy_oatside_report.ps1`: เลือกโฟลเดอร์ `oatside-apr2026` ที่ `index.html` **แก้ล่าสุด** ระหว่าง `Oatside/` / `ProjectYK_System/` / ราก `TransportRateCalculator/` ก่อน copy + commit/push

## 2026-05-01 (Oatside — rebuild ด้วย export GPS 01.05.2026 21:33)

- รัน `Oatside/build_oatside_reports.py` ด้วย `OATSIDE_ORIGIN` / `OATSIDE_DEST` ชี้ไฟล์ `...21-33-31 Oatside.xlsx` + `...21-33-53 P&G.xlsx` → อัปเดต `Oatside/Oatside_PG_Trip_Summary_By_Site.xlsx` และ HTML ใต้ `Oatside/TransportRateCalculator/reports/oatside-apr2026` (Trips 88 / Unmatched 32)

## 2026-05-01 (Oatside GPS รายงาน — merge ต้นทางซ้อนก่อนปลายทาง)

- `Oatside/build_oatside_reports.py`: หลัง greedy จับคู่ เรียงตาม `Origin_Out` แล้วรวมหลายช่วงต้นทางเมื่อ `Origin_In` ถัดไป `< Dest_In` ปัจจุบัน; เลือกปลายทางรอบแรกด้วย `row_no` ตรงช่วงต้นทางล่าสุด รอบถัดไปเกาะ `d_acc` ถ้ายัง feasible; คำนวณ `origin_wait_h` เป็นผลรวมรายช่วง; orphan dest rematch กับต้นทางค้าง

## 2026-04-30 (TransportRateCalculator — ย้ายเข้า `ProjectYK_System/`)

- ย้าย **`TransportRateCalculator/`** → **`ProjectYK_System/TransportRateCalculator/`** (เครื่องคิดเรท + `docs/` สเปก + `reports/`)
- แก้ **`deploy_one_click.bat`** (`REPO_PATH=..\..`), **`deploy.ps1`** default repo path, **`tools/build_petty_cash_online.py`** (`ROOT_DIR` = parents[3], `OUTPUT_DIR` ใต้ TRC)
- แก้ **`deploy_oatside_report*.ps1|bat`** ให้ชี้ `ProjectYK_System\TransportRateCalculator\reports\oatside-apr2026`
- อัปเดต **`.cursor/rules/project-yk-context.mdc`**, **`AGENTS.md`**, **`MODULE_REGISTRY.md`**, **`.cursorignore`**

## 2026-04-30 (ข้อมูลธุรกิจ — รวมที่ `data/`)

- ย้าย **`Salary/`**, **`Fuel/`**, **`Billing/`** จากราก repo → **`data/Salary`**, **`data/Fuel`**, **`data/Billing`**
- **`.gitignore`**: ใช้บรรทัดเดียว **`data/`** แทนการ ignore แยก `Salary/` + `Fuel/`
- อัปเดต `_repo_paths.py` (`SALARY_DIR` / `FUEL_DIR` / `BILLING_DIR`), import scripts, `payroll_slip.salary_export_root()`, `ProjectYK_System/TransportRateCalculator/tools/build_petty_cash_online.py`, `dev_scripts/_paths.py`
- เพิ่มคำอธิบายโครงสร้าง: `data/README.md`

## 2026-04-30 (โครงสร้าง — รวมสคริปต์ระบบไว้ใต้ `ProjectYK_System/`)

- ย้าย `tools/` → `ProjectYK_System/tools/` + `_repo_paths.py` (ชี้ `REPO_ROOT` / `APP_DIR` / `SYSTEM_DIR`)
- สคริปต์ทดสอบราก `_*.py` → `ProjectYK_System/dev_scripts/` + `_paths.py`
- คำสั่ง import: รันจากราก repo เป็น `python ProjectYK_System/tools/import_daily.py` (ดู `AGENT_BOOTSTRAP.md`, `ProjectYK_System/tools/phase2_import.bat`)
- เพิ่ม `.cursorignore` ที่ราก repo เพื่อลดไฟล์ที่ Cursor index (ประหยัด token / โฟกัส)

## 2026-04-29 (Petty cash เม.ย. 2569 — `rev.1` ชีท APR 26)

- **DB**: backup → ลบเฉพาะ `book2_2026` + `pay_cycle_tag=2026-04` → import `ProjectYK_System/tools/import_petty_cash.py` จาก `petty_cash_all_sites_2026-04 rev.1.xlsx` (`--sheet APR 26`) เพื่อไม่ซ้ำเดือนอื่นและไม่ wipe หลายเดือน

## 2026-04-29 (Transport Rate Calculator — ดึงราคาย้อนหลัง + คลุมช่วงหาเฉลี่ย)

- **`TransportRateCalculator/transport_rate_calculator.html`**: Step 1 เพิ่ม historical panel ดึงข้อมูลรายวันจากเว็บ (Bangchak via proxy read), เลือกชนิดน้ำมัน/ปี และคลุมช่วงด้วยเมาส์เพื่อคำนวณค่าเฉลี่ย/ต่ำสุด/สูงสุด/จำนวนวัน
- เพิ่มปุ่มใช้ค่าเฉลี่ยที่คลุมเพื่อเติม `fuelPrice` อัตโนมัติ (workflow แบบ Excel selection)
- เพิ่ม fallback textarea ให้ paste ข้อมูลจากเว็บแล้ว parse เป็นตารางย้อนหลังได้ กรณี fetch อัตโนมัติไม่ผ่าน (CORS/network policy)
- parser รองรับข้อความแบบ tab-separated ที่ copy ตรงจากเว็บ (หลายคอลัมน์ราคา) และเลือกคอลัมน์ตามชนิดน้ำมันที่ user เลือก
- เพิ่ม normalization รายวัน: เติมวันที่ที่หายด้วยราคาวันก่อนหน้า (carry-forward) และติดป้าย `เติมวันหาย` ในตาราง
- เพิ่มตัวเลือกช่วงวันที่ `ตั้งแต่-ถึง` เพื่อ select แถวและเฉลี่ยอัตโนมัติ โดยใช้ workflow เดียวกับการคลุมเมาส์
- ปรับปี/วันที่ใน historical panel เป็นค.ศ.ทั้งหมด (input/filter/display) พร้อมรองรับ parse ข้อมูลต้นทางที่ยังเป็นพ.ศ.

## 2026-04-29 (Petty cash มี.ค. 2569 — MAR 26 เป็นหลัก)

- **DB**: ลบซ้ำรอบ `2026-03` ทั้ง `book2_2026` และ `import_petty_mar26` → import `rev.1.xlsx` ชีท **`MAR 26`** เท่านั้นเป็น bulk หลัก (`book2_2026`)

## 2026-05-02 (Payroll + Petty — unlinked ที่ `site_code` ว่างไม่ถูกนับใน guardrail)

- **ปัญหา**: แถวหักสดย่อย pending + ยังไม่ผูกคนขับแต่ `site_code` ว่าง → แบนเนอร์ payroll / finalize gate เดิมมองไม่เห็น (กรองแค่ไซต์รอบ)
- **แก้**: `main.py` — `_petty_unlinked_predicates_for_payrun` + stale petty scan; `payroll_detail.html` — ลิงก์สดย่อยใช้ `cycle=`; `payroll.py` + `payroll_slip.py` — รวม `site_code` ว่างเมื่อคิดยอด/สลิป (กันหลุมเมื่อผูก driver แล้วแต่ไซต์ว่าง)

## 2026-04-29 (Dev server LAN — bind `0.0.0.0` + `YK_BIND_HOST`)

- **`main.py`**: uvicorn default `host=0.0.0.0` เพื่อให้เครื่องอื่นใน LAN เข้าได้ · env `YK_BIND_HOST=127.0.0.1` ถ้าต้องการ localhost เท่านั้น · พิมพ์ลิงก์ `http://<LAN-IP>:port/daily`

## 2026-04-29 (Petty driver-link: BIG-C strip bug + GLOBAL alias สมพร)

- **`alias_map`**: GLOBAL alias `สมพร โม่งปราณีต` / typo `โม่งปรำณีต` → `สมพร BIG-C`
- **`tools/import_petty_cash.link_drivers_safe`**: ถ้าคัดจากชื่อหลัง strip site hint แล้วว่าง → ไม่ทับผลจับคู่จาก canonical key · `canonical_person_name(..., row_site)`

## 2026-04-29 (Payroll PDF — BIGC เดือนจ่าย vs งวดวิ่ง + seed เลขบัญชี + สลิปแนวนอนหนึ่งหน้า)

- **`salary_folder_month_tag` / `cycle_tag_th_label`**: BIGC เก็บไฟล์ที่ `Salary/BIGC/{YYYY-MM เดือนจ่าย}/Driver/` (งวดวิ่งมีนาคม → เดือนจ่ายเมษายน)
- **`merged_bank_terms` + `services/bigc_bank_seed.py`**: เติมธนาคาร/เลขบัญชีเมื่อยังไม่กรอกใน `custom_terms` — sync ตารางผู้ใช้ (กสิกร/SCB/กรุงไทย/กรุงศรี + `#N/A` บุญชอบ พูลสวัสดิ์)
- **`payroll_export_pdf.py`**: ตารางสรุป/โอนปรับโทนหัวตาราง + แถวสลับสี · สลิปรายคน landscape ซ้ายรายเที่ยวขวาสรุปเงิน · manifest เพิ่ม `folder_month_tag`

## 2026-04-29 (PDF bundle: สลิปทุกคน + สรุปรวม + โอนเงินบัญชี → Salary/…/Driver/)

- **deps**: `requirements.txt` เพิ่ม `fpdf2>=2.7,<3`
- **`services/payroll_slip.py`**: `build_payroll_slip_context()` — context เดียวกันสำหรับ HTML slip + PDF · `salary_export_root` / `export_driver_folder` → `Salary/{SITE}/{YYYY-MM}/Driver`
- **`services/payroll_export_pdf.py`**: `export_payroll_pdf_bundle()` สร้างด้วยฟอนต์ Windows Tahoma/Sarabun:
  - `{SITE}_{tag}_สรุปรวม.pdf` — landscape ตารางสรุป (เรียงชื่อ): ค่าเที่ยว / เงินเดือน / ค่าเรทน้ำมัน / รวมรายได้ / SS / ภาษี / หักสดย่อย / สุทธิ + แถวรวม
  - `{SITE}_{tag}_โอนเงินบัญชี.pdf` — ลำดับ / ชื่อ / ธนาคาร / เลขบัญชี / จำนวนโอน (`Employee.custom_terms`: `bank_name`, `bank_account`, `payment_note` — ว่างแสดง "กดเงินสด")
  - `{SITE}_{tag}_ชุดครบ_สรุปโอนสลิป.pdf` — รวมสรุป + โอน + สลิปแต่ละคนตามชื่อ (หนึ่งคนตามหลายหน้าถ้ายาว)
  - `รายคน/{ชื่อ}_{tag}.pdf` — แจกไลน์รายคน
- **`POST /payroll/{id}/export-pdfs`** → หน้า `payroll_export_done.html` แสดง path เต็ม
- **`payroll_detail.html`**: ปุ่ม **📄 ส่งออก PDF** (ใช้ได้แม้ปิดรอบแล้ว)
- **`employee_form.html`**: helper JSON `bank_name` / `bank_account` / `payment_note`

## 2026-04-29 (สลิปคนขับแบบมินิมอล — print-only view)

- **เคส**: หน้า `/payroll/{run}/employee/{id}` มีข้อมูล admin (UI controls, เตือน, override, etc.) เยอะ ไม่เหมาะปริ้นให้คนขับ
- **Reference**: ใช้ format จาก PDF เดิม `Salary/2026/3.Mar/BigC/คนขับ/เกรียงไกร.pdf` เป็นต้นแบบ
- **ใหม่** `templates/payroll_slip.html`: หน้าแยก minimal — ไม่ extend `base.html` (ไม่มี navbar)
  - Header: บริษัท + ช่วงงวด + รอบ
  - คนขับ + รหัส + ทะเบียนรถ (ดึงจาก `DailyJob.plate_no_raw` distinct)
  - ตาราง DailyJob: วันที่ / ทะเบียน / ส่งสินค้า+หมายเหตุ / ใบงาน / น้ำมัน(L) / ค่าเที่ยว / เรท — รวม placeholder rows ("ส่งงานต่อเนื่อง", "รองาน", note ของ admin)
  - Panel ซ้าย "การใช้รถ/น้ำมัน": ไมล์เริ่มต้น (min `mile_snapshot`) → ไมล์สิ้นสุด (max) → กม.วิ่ง → น้ำมันใช้ (FuelTxn liter หรือ DailyJob.fuel_liter) → เรทเฉลี่ย km/L → วันทำงาน/ลา/ขาด
  - Panel ขวา 2 ก้อน: **รายได้** (เฉพาะที่ ≠ 0: เงินเดือน, ค่าดูแลรถ, ค่าเที่ยว, ค่าเรทน้ำมัน, ส่วนแบ่งน้ำมัน, ชดเชยการันตี, รายได้อื่น) + **เงินหัก** (ประกันสังคม, ภาษี, เงินประกันผ่อน, ผ่อนอุบัติเหตุ, สดย่อย-แต่ละรายการพร้อมวันที่+memo, ค่าน้ำมันออกเอง, หักอื่น)
  - กล่องยอดสุทธิด้านล่าง สี emerald ถ้าบวก / rose ถ้าลบ
- `@media print { @page A4 portrait; toolbar hidden }` → ปริ้นได้สวยทันที
- **Route ใหม่** `GET /payroll/{run}/employee/{id}/slip` → ดึง DailyJob/PettyCash/FuelTxn + คำนวณไมล์/น้ำมัน → render template
- ปุ่ม "🖨 พิมพ์สลิป" ในหน้า detail เปลี่ยนจาก `window.print()` → ลิงก์เปิด tab ใหม่

## 2026-04-29 (Implicit absent: ไม่มี DailyJob ในวันนั้น = ขาดงาน)

- **เคส**: พรศักดิ์ทำงาน 1-25 มี.ค. แล้วเกิดอุบัติเหตุ 25/3 ไม่ได้ทำงาน 26-31 → admin ไม่ได้ใส่ end_date หรือ status='absent' → ระบบเดิมจ่ายเต็มเดือน 9,000 ฿
- **User policy**: "ชื่อใครถ้าไม่มีณ วันที่นั้นๆ หักออกเลย" — ทุกวันที่ไม่มี DailyJob = absent (ขาดงานเงียบ)
- **Refactor** `services/payroll.py`:
  - แยก `_resolve_effective_window(session, emp_id, start, end)` เป็น helper เดียว — ใช้ใน `_count_work_days` และ `calc_one_employee` (DRY)
  - เพิ่ม implicit absent calc: `implicit_absent_days = emp_window_days - len(by_date)` → รวมเข้า `days_absent`
  - **Guard สำคัญ**: ทำเฉพาะเมื่อ `by_date` ไม่ว่าง (มี DailyJob อย่างน้อย 1 วัน) → ป้องกันลงโทษ office_monthly staff ที่ไม่ใช้ DailyJob เลย (admin คน, ช่าง, ยาม, รปภ.)
- **ผล** BIGC `2026-03`:
  - พรศักดิ์ base 9,000 → **7,258.06** ฿ (= 9,000 × 25/31), ss 450 → 363
  - คนอื่นทำงานครบเดือน — ไม่กระทบ
  - Net total: 102,415.34 → 100,760.40 ฿
- **AYU office staff** ยังคงได้ base/ss เต็ม เพราะไม่มี DailyJob ทั้ง period → guard skip implicit absent ตามเจตนา

## 2026-04-29 (SS รายงานเป็นจำนวนเต็มบาทและปัดขึ้นเสมอ)

- ตามมาตรฐาน Thai SSO: ค่า contribution รายงานเป็นเลขเต็มบาทและปัดขึ้น (ceiling) เสมอ
- **Fix** `services/payroll.py`: เปลี่ยน `round(amount, 2)` → `math.ceil(amount)` สำหรับ `social_security`
- **ผล**: 82.50 → 83 (ขั้นต่ำ), 406.45 → 407, 435.48 → 436, 450.00 → 450 (เท่าเดิม)
- กระทบเล็กน้อย (รวมไม่กี่บาท): BIGC ss 3,213.38 → 3,216.00 / LCB ss 8,246.80 → 8,249.00 / AYU ไม่เปลี่ยน (ทุกคน 450 เท่ากัน)

## 2026-04-29 (Resignation trim: ใช้วันทำงานสุดท้ายแทน end_date paperwork)

- **บั๊ก**: สมพร BIG-C ลาออก 4/3 (`end_date=2026-03-04`) แต่ DailyJob มีแค่ 1, 2, 3 มี.ค. (วันที่ 4 ไม่ได้ทำงาน — น่าจะเป็นวันมาเซ็นเอกสาร) → ระบบนับ employed=4 → base = 9000 × 4/31 = 1,161.29 ฿
- **User เจตนา**: prorate ตามวันที่ทำงานจริง → 9000 × 3/31 = 870.97 ฿
- **Fix** `services/payroll.py` `calc_one_employee`: เพิ่ม "resignation trim" — ถ้า `employee.end_date` ถูกตั้ง ระบบจะ trim `eff_emp_end` ลงเป็น `last DailyJob.work_date` ภายใน period (เฉพาะกรณีที่ last_work < eff_emp_end). คนที่ไม่มี `end_date` (กำลังทำงาน) ไม่กระทบ
- **ผล** BIGC `2026-03`:
  - สมพร base 1,161.29 → **870.97** ✓
  - บุญชอบ ไม่กระทบ (ทำงานครบถึง 31/3 ใน period นี้)
  - Net total: 102,708.28 → 102,417.96 ฿

## 2026-04-29 (SS calc: prorate-then-clamp + start_date fallback)

- **บั๊กที่ user เจอ**: สมพร BIG-C ทำงาน 3/4 วัน (ลาออก 4/3) — ระบบโชว์ SS = 58.06 ฿ (ไม่ใช่ขั้นต่ำ 83 ฿ ตามกฎหมาย)
- **Root cause**: ลำดับคำนวณเดิมคือ `clamp(base, min, max) → ss_full → ss_full × work_factor` ทำให้ work_factor < 1 ดึง SS ลงต่ำกว่าขั้นต่ำได้
- **Fix** `services/payroll.py`: เปลี่ยนเป็น `prorated_base = base × work_factor → max(min_base, min(prorated_base, max_base)) → ss = capped × rate` → คนที่ทำงานอย่างน้อย 1 วันในรอบจะได้ SS ขั้นต่ำ 5% × 1,650 ≈ 82.50 ฿ เสมอ. คนที่ไม่ได้ทำงานเลย (factor=0) ยังคงได้ SS = 0
- **Fix start_date fallback**: บุญชอบเพิ่งเข้ามา 29/3/26 admin ยังไม่ใส่ "เริ่มทำงาน" ใน column G → start_date=None → ระบบนับ employment เต็มเดือน → SS เต็ม 450. เพิ่ม fallback ใน `calc_one_employee`: ถ้า `employee.start_date is None` → infer จาก `min(DailyJob.work_date)` ภายใน period (เฉพาะกรณีที่ first_work > period_start)
- **ผล** BIGC `2026-03`: สมพร 82.50 ✓, บุญชอบ 82.50 ✓, SS total ลดจาก 3,580.88 → 3,213.38 ฿
- **Note**: คนที่ลาออกกลางเดือน + ไม่ได้ทำงานเลย จะไม่มี SS — ตรงตามเจตนา (ต้องมีงานอย่างน้อย 1 วันในรอบจึงโดน clamp ขั้นต่ำ)

## 2026-04-28 (Manual day overrides + SS settings + imputed SS base for mao drivers)

- **PayRunAdjust** (ขยาย): เพิ่ม `days_worked_override`, `days_leave_override`, `days_absent_override`, `ss_rate_override`, `ss_base_min_override`, `ss_base_max_override`, `note` (per-employee overrides)
- **PayRun** (ขยาย): เพิ่ม `ss_rate`, `ss_base_min`, `ss_base_max` — ตั้งระดับ "ทั้งรอบ" สำหรับเดือนที่รัฐประกาศลด SS rate ชั่วคราว
- **payroll.py SS calc**: 4-tier resolution priority — PayRunAdjust → PayRun → Employee → defaults (5% / 1,650 / 15,000). Apply Thai legal min/max bounds. Imputed `social_security_base = 9,000` สำหรับ mao/trip drivers ที่ไม่มี base salary จริง (ตามข้อตกลง user "ฐานเงินเดือนแฝง"). หักลด SS proportional ตาม leave/absent/not-employed
- **payroll.py days override**: ค่าใน PayRunAdjust ทับค่า auto จาก _count_work_days สำหรับ days_worked/leave/absent → admin แก้ manual ได้เมื่อ data ผิด
- **UI** `payroll_employee_detail.html`: เพิ่มปุ่ม "แก้ Manual" เปิด panel กรอก override (วันทำงาน/ลา/ขาด + SS rate/min/max + note) มีปุ่ม "ล้าง (กลับ auto)" ด้วย ✎ icon ระบุค่าที่ overrideไว้
- **UI** `payroll_detail.html`: บรรทัดบนสุดแสดง SS rate/min/max ของรอบ + ปุ่ม [ตั้งค่า] เปิด panel ที่ใช้ POST `/payroll/{id}/ss-settings`
- **Endpoints ใหม่**:
  - `POST /payroll/{run_id}/employee/{emp_id}/override` — บันทึก/ล้าง PayRunAdjust + auto recompute
  - `POST /payroll/{run_id}/ss-settings` — บันทึก/ล้าง PayRun-level SS overrides + auto recompute
- ทดสอบ: AYU `2026-03` mao/trip/self_fuel drivers SS = 450.00 (5% × 9000 imputed) ✓ — เคยเป็น 0 เพราะไม่มี base salary

## 2026-04-28 (Rehire/Resign: employment-window aware payroll + UI quick action)

- เคสที่ user เจอ: ณัชพน บรรทัดแรกของวันที่ `1/3` มี note ว่า `เริ่มทำงาน07/02/25 ออก24/2/26 กลับมา 3/3` → ระบบไม่ได้ตีความ "กลับมา" เป็น rehire → start_date ยังเป็น 2025-02-07 → คำนวณ payroll ผิด
- **Schema (no breaking)**: ใช้ `Employee.start_date` เป็น "วันเริ่มของ employment ปัจจุบัน". เก็บ history ใน `Employee.custom_terms` JSON: `{"original_hire_date": "...", "rehire_log": [{"left": "...", "back": "..."}]}`
- **payroll** `services/payroll.py`:
  - `_count_work_days`: filter `DailyJob.work_date` ภายใน employment window (`max(period_start, emp.start_date)` ถึง `min(period_end, emp.end_date)`) → row ก่อน rehire/หลัง resign จะไม่ถูกนับ
  - `calc_one_employee`: เพิ่ม `not_employed_days = period_days - employed_days_in_period` รวมเข้าใน `missed` ของ base/care/SS → คนที่กลับมาวันที่ 3/3 ของเดือน 31 วัน → ได้ `base × (29-leave-absent)/31`
- **import_daily** `_apply_employee_dates`: ปรับให้ rehire (มี "กลับมา DD/MM") override → `start_date = return_date`, clear `end_date`, `status='active'`, append rehire log + เก็บ `original_hire_date`
- **UI** `employee_form.html`: เพิ่มกล่อง "⟲ บันทึกการลาออก/กลับมา" — แสดง original_hire_date + rehire_log, มีฟอร์ม quick action "ออก / กลับมา" → POST `/employees/{id}/rehire` (auto update + log)
- **Quick fix ณัชพน**: `tools/fix_natchapon_rehire.py` → start_date=2026-03-03, original_hire_date=2025-02-07
- ผลลัพธ์ BIGC `2026-03`: ณัชพน work=28 leave=1 base=8,129.03 (ก่อนหน้า 9,000) net=21,501.58. สมพร end=2026-03-04 work=3 base=1,161.29 (4/31 ของ 9,000) ✓
- Net total BIGC `2026-03`: 113,494.25 (ก่อนหน้า 121,463.61 — ลดลงเพราะ prorate ตาม employment window จริง)

## 2026-04-28 (Fix leave false-positives: substring "ลา" inside place names)

- **Root cause**: `_classify_status` ใน `tools/import_daily.py` และ `_count_work_days` ใน `services/payroll.py` ใช้ substring match (`"ลา" in joined`) → match ภายใน "ลาดพร้าว", "ลาดกระบัง", "ตลาดบุญเจริญ", "โนนศิลา" → ตั้ง `status_code='leave'` ผิด **118 แถว** (BIGC 2, AYU 25, LCB 91)
- เคสที่ user เจอ: เกศศักดิ์ 13/3 ไป Phangkhon (remark="โนนศิลา") เป็นเที่ยวจริง (rev 15,311.34, fee 1,400) → ระบบขึ้นเป็นลา
- **Fix 1** `services/payroll.py`:
  - **Money guard**: ถ้าวันใดมี trip ที่ `revenue_customer>0` หรือ `trip_fee_driver>0` → ห้าม classify เป็น leave/absent
  - **Token-based match**: split blob ด้วย `[\s/,;()\[\]\-_.]+` แล้ว exact-match keyword (ไม่ใช่ substring)
  - **ตัด `destination` ออกจาก scan ทั่วไป** (เป็นชื่อสถานที่ ไม่ใช่ status field) ยกเว้น `เข้าบ้าน` ที่เป็น status marker จริง
- **Fix 2** `tools/import_daily.py`: เปลี่ยน `_classify_status` เป็น token-based match เช่นเดียวกัน (ป้องกันการ import ครั้งหน้า)
- **Patch existing data**: `tools/fix_leave_falsepos.py` → clear `status_code`/`leave_status` 118 แถวที่ติด leave ผิดทั้งที่มี revenue/fee จริง
- Recompute: BIGC `2026-03` net=121,463.61, AYU `2026-03` net=368,750.13, LCB `2026-03` net=459,727.56
- เกศศักดิ์ work=31 leave=0 ✓, เกรียงไกร work=28 leave=3 (เข้าบ้าน) ✓

## 2026-04-28 (Petty cash redo: re-import MAR 26 + dedup 2 passes)

- **Pass 1 (MAR 26)**: ลบ `source='import_petty_mar26'` (740 rows) แล้ว re-import ชีท `MAR 26` ของ `petty_cash_all_sites_2026-04.xlsx` ด้วย logic ใหม่ → ทุก 740 rows tag `pay_cycle_tag=2026-03` ครบ (สมประสงค์ 26/2 + คนอื่นที่ตั้งใจหักรอบ มี.ค.)
- **Pass 1 dedup**: รัน fuzzy match (date + canonical name + amount + direction) → mark 102 rows จาก `book2_2026/import` เป็น `settled_offline` กันซ้ำ
- **Pass 2 (legacy)**: dedup `src='import'` ที่มาจาก master file ซ้ำ 3 ไซต์ → 391 affected groups, 778 rows mark `settled_offline` (memo prefix 25 chars เพื่อกัน false positive)
- หลัง dedup: BIGC dup_groups เหลือ 12 (ทั้งหมดเป็น false positive — ค่าปรับคนละสถานที่/คนละใบ ที่ amount เท่ากัน) — ปล่อยให้ user review เอง
- Recompute: BIGC `2026-03` net=120,853.28 (petty_ded 70,025.91), AYU `2026-03` net=368,266.43, BIGC `2026-02` net=119,341.78, AYU `2026-02` net=390,602.74
- Backup: `app.db.bak_petty_redo_20260428_231314`
- Tooling ใหม่: `tools/dedup_petty_mar26.py`, `tools/dedup_legacy_import.py` (idempotent, dry-run by default)

## 2026-04-28 (Petty cash cycle UX: filter + sheet auto-tag + bulk shift)

- เพิ่ม filter "รอบจ่าย" (`pay_cycle_tag`) ในหน้า `/petty-cash` (dropdown รวม count) — ใช้แทนการ filter ตามวันที่ เวลาที่ admin จะดูยอดของรอบ
- ปรับ `tools/import_petty_cash.py` ให้ default `pay_cycle_tag` ตามชื่อ sheet (`MAR 26 → 2026-03`, `มี.ค. 26 → 2026-03`, `MAR 2569 → 2026-03`) ทำให้รายการในชีท `MAR 26` ถึงจะเขียนวันที่ `26/2` ก็จะถูกหักรอบ มี.ค. ตามเจตนา admin (fallback per-site rule ถ้า sheet name parse ไม่ได้)
- เพิ่ม endpoint `/petty-cash/bulk-shift-cycle` + UI checkbox bulk-bar (ย้าย cycle ปลายทาง / ±1 เดือน) บน `petty_list.html` กรณีต้องโยกหลายแถวพร้อมกัน
- แก้เคส `เกรียงไกร 26/2 = 1,000` ที่อยู่ในชีท `MAR 26` ให้ tag `2026-03` พร้อม mark book2_2026 row เป็น `settled_offline` กันซ้ำ → BIGC `2026-03` หักสดย่อยเกรียงไกรรวม `11,000`

## 2026-04-27 (Reclassify Samai toll to AYU)

- ย้าย `PettyCashTxn` หมวด toll ของ `สมัย` ที่ติดไซต์ BIGC ผิด (source `book2_2026`, cycle `2026-03`) ไป `site_code=AYU`
- recompute BIGC `2026-03` ทำให้ยอดหักของ BIGC ลดลง 50 บาทตามข้อเท็จจริง

## 2026-04-28 (Transport Rate Calculator: add fixed-THB per range mode)

- หน้า `TransportRateCalculator/transport_rate_calculator.html` เพิ่มโหมดปรับราคาแบบ `บาท/ช่วง` ควบคู่โหมดเปอร์เซ็นต์เดิม
- อัปเดตสูตรคำนวณ, ตาราง preview/result และ Export Excel ให้รองรับทั้ง `%` และ `บาท/ช่วง` อย่างสอดคล้อง

## 2026-04-28 (Transport Rate Calculator: switch Step 1 to historical diesel-S workflow)

- เปลี่ยน Step 1 เป็นมุมมองราคาน้ำมันย้อนหลัง (Bangchak historical page)
- ปรับข้อความ UI ให้โฟกัสเฉพาะการดูและกรอก `ไฮดีเซล S` เพื่อลดความสับสนจากชนิดน้ำมันอื่น

## 2026-04-28 (Transport Rate Calculator: rollback historical iframe on Step 1)

- rollback Step 1 กลับ iframe ราคาน้ำมันปัจจุบัน เพราะหน้า historical ของ Bangchak บล็อกการฝัง (`refused to connect`)
- คงลิงก์ไปหน้า historical สำหรับเปิดแท็บใหม่แทนการ embed

## 2026-04-27 (BIGC petty deduction source-overlap dedup)

- ตรวจพบ deduction ซ้ำใน BIGC รอบ `2026-03` ระหว่าง `book2_2026` กับ `import_petty_mar26`
- ใช้ source priority: คง `import_petty_mar26` เป็น pending หลัก และ mark แถวซ้ำจาก `book2_2026` เป็น `settled_offline`
- หลัง dedup แล้ว pending duplicate groups = 0

## 2026-04-27 (BIGC duplicate-trip cleanup in fuel importer)

- `tools/import_bigc_fuel_rate.py` เพิ่ม idempotent cleanup:
  - purge `DailyJob source=bigc_fuel_rate` ของเดือนนั้นก่อน import
  - post-import dedup merge: ถ้าพบคู่ `import_daily + bigc_fuel_rate` key เดียวกัน ให้ merge ค่าใช้งานแล้วลบแถว `bigc_fuel_rate`
- ผลลัพธ์: duplicate trips ตาม key `(date,driver,plate,destination)` ใน BIGC มี.ค. ลดเหลือ 0

## 2026-04-27 (Payroll cross-site isolation fix)

- แก้ `services/payroll.py` ให้ aggregate ทุกส่วนกรอง `site_code` (ไม่ใช่แค่ driver_id+date)
- แก้ `/payroll/{run_id}/employee/{emp_id}` ให้ query `DailyJob/PettyCashTxn/FuelTxn` เฉพาะไซต์ของรอบ
- ปิดช่องโหว่คนขับชื่อเดียวกัน/driver_id เดียวกันที่มีประวัติข้ามไซต์แล้วถูกนับปนในรอบปัจจุบัน

## 2026-04-27 (Alias map centralization + finalize gate)

- เพิ่ม `app/services/alias_map.py` เป็น source เดียวสำหรับ normalize site/person aliases
- ผูก alias map เข้า `tools/import_daily.py`, `tools/import_petty_cash.py`, `tools/import_bigc_fuel_rate.py`
- เพิ่ม finalization guard ใน `/payroll/{run_id}/finalize`: ถ้ายังมี pending deductions ที่ unlinked ในไซต์เดียวกัน -> block finalize
- เพิ่ม filter `unlinked=1` ใน `/petty-cash` และแสดง badge `unlinked` ในตาราง

## 2026-04-27 (AI workflow default - OA careful mode)

- เพิ่ม rule ใหม่ `.cursor/rules/oa-careful-default.mdc` (`alwaysApply: true`)
- บังคับแนวตอบแบบรอบคอบทุกแชทในโปรเจกต์: completeness/leak check, ไม่เดาสุ่มเมื่อข้อมูลกำกวม, สรุปสิ่งที่ทำแล้ว/ค้าง/ความเสี่ยง/ขั้นถัดไป

## 2026-04-27 (Payroll guardrail - unlinked driver deductions)

- `/payroll/{run_id}` แสดง banner เตือนเมื่อมี `PettyCashTxn` หักคนขับที่ยัง `driver_id is null` ในรอบ/ไซต์เดียวกัน
- แสดงจำนวนรายการ + ยอดเงินรวมที่ยังไม่ถูกคิด payroll และลิงก์ลัดไป `/petty-cash?...&unlinked=1`
- `/petty-cash` เพิ่ม filter `unlinked=1` + badge `unlinked` ในตารางรายการ

## 2026-04-27 (BIGC column-G employment event parsing)

- `tools/import_daily.py` (BIGC): parse ข้อความคอลัมน์ G (`เริ่มทำงาน`, `ออก/ลาออก`, `กลับมา`) เพื่ออัปเดต `Employee.start_date/end_date/status`
- รองรับแถวแจ้งสถานะที่ไม่มีวันที่คอลัมน์ A โดย fallback วันที่จากข้อความใน G
- เพิ่ม fallback name match แบบชื่อแรก เพื่อรองรับ master ที่เก็บชื่อสั้น

## 2026-04-27 (BIGC worked-day semantics aligned to manual)

- `services/payroll.py::_count_work_days()` ปรับนิยาม `worked` เป็น `distinct DailyJob dates - leave - absent`
- `company_no_work` (รองาน/รถจอด) ไม่ถูกนำไปหัก worked อีกต่อไป
- กรณีไม่มี DailyJob ในช่วงเลย (เช่นยังไม่เริ่มงาน/ลาออกแล้ว) ให้ worked=0 ไม่เดาเป็น 31

## 2026-04-27 (BIGC leave deduction fix - Thai status aware)

- `services/payroll.py` ปรับ `_count_work_days()` ให้แปลสถานะวันจากคำไทยในเดลี่จริง (`ลา/ป่วย/ลากิจ/หยุด`, `ขาด`, `รถจอด/รองาน/ไม่มีงาน`) ร่วมกับ `status_code`
- แก้ปัญหา BIGC payroll ที่ก่อนหน้า leave ไม่ถูกนับเพราะโค้ดเดิมรองรับเฉพาะ token อังกฤษ

## 2026-04-27 (PettyCash import MAR 26 + duplicate-name safety)

- `tools/import_petty_cash.py` รองรับ `--file --sheet --source-tag --link-drivers` เพื่อ import เป็นรอบ/ชีทแบบควบคุมได้
- เพิ่ม safe driver-linker จาก `requester_raw` ไป `Employee`: link เฉพาะ match ชัดเจน, skip ชื่อกำกวมข้ามไซต์
- เพิ่ม site hint parser (`BIG C/BIG-C/BIGC`, `อยุธยา/AYU`, `LCB/แหลม`) ป้องกันปนชื่อซ้ำ เช่น `สมัย BIG C` vs `สมัย อยุธยา`
- `services/payroll.py` ปรับ employee selection ให้พิจารณา `start_date/end_date` ซ้อนทับรอบแทนกรอง `status=active` อย่างเดียว รองรับการคำนวณย้อนหลังของพนักงานลาออก

## 2026-04-27 (BIGC fuel residual ติดลบ × 32.15)

- `services/payroll.py`: ถ้า residual น้ำมัน BIGC ติดลบ ให้คูณ `BIGC_FUEL_OVERSPEND_THB_PER_L` (32.15) แทนเรทคืน 16 บาท/ลิตร — ตรงไฟล์เรทแอดมิน
- `tools/import_daily.py`: `--xlsx` / `--sheet`; `--wipe-prior` ร่วม `--site` (+ `--from-date`) ลบเฉพาะไซต์และช่วงวันที่
- `tools/import_bigc_fuel_rate.py`: `--tag YYYY-MM` override รอบ; ชื่อชีท `อาท` → เกรียงไกร สายแก้ว; fallback ชื่อไฟล์ `YYYY-MM`

## 2026-04-27 (BIGC payroll เม.ย. — โครงไฟล์ + 4 แหล่งข้อมูล)

- ข้อมูลรายเดือนอยู่ที่ **`data/Salary/BigC/YYYY-MM/`** (ไม่ใส่ใน `ProjectYK_System/`)
- ไฟล์วางบิลลูกค้าเก็บ **`data/Billing/BigC/YYYY-MM/`** สำหรับตรวจทานอนาคต (Rate WNDC, KM.& Rete_BPD)
- แหล่งที่ 1–3: daily, fuel_rate_daily (ชีทรวมเรท + รายคน), master `fuel_rate.xlsx` (ค่าเที่ยว + เรทน้ำมัน พี่ต้น/มาร์ค)

## 2026-04-25 (KYT Weekly workflow baseline)

- เพิ่มคู่มือมาตรฐาน `ProjectYK_System/docs/KYT_AUTOFILL_GUIDE.md` สำหรับการเติม KYT รายสัปดาห์จากรูปในไฟล์
- ล็อกกติกาใช้งาน: ห้ามเปลี่ยนขนาดแถว/คอลัมน์/เลย์เอาต์ template เดิม, ใส่เฉพาะข้อความลงตำแหน่งเซลล์มาตรฐาน Round 1-4
- ตกลงแนวทางต่อไป: เริ่มจาก `.md` workflow ก่อน แล้วค่อยต่อยอดเป็นหน้า HTML `KYT Assistant` (drag-drop + AI draft + export)
- ส่งมอบ MVP หน้า `/kyt` ใน One Platform: drag-drop รูป, วิเคราะห์ AI (fallback ได้), แก้ Round 1-4, และ export กลับเป็นไฟล์ `.xlsx` template เดิมโดยไม่แตะ row/column sizing
- ปรับ behavior KYT analyze: ถ้าไม่มี Vision จริง (ไม่มี key/ไม่มี local model) ให้คืนค่า **ว่าง** + ข้อความแจ้งไม่สามารถวิเคราะห์ได้ (ไม่ใช้ข้อความเดา)
- เพิ่มทางเลือก Local Vision ผ่าน Ollama (`OLLAMA_VISION_MODEL`, `OLLAMA_BASE_URL`) เพื่อลดค่าใช้จ่าย token cloud
- Hardened local output quality: เพิ่ม validation รูปแบบ KYT (prefix/จำนวนข้อ/ภาษาไทย) ถ้าไม่ผ่านให้คืนค่าว่างพร้อม note ชัดเจน
- เพิ่มความทนทานการเรียก Ollama Vision: ถ้า `/api/generate` 500 เมื่อใช้ `format=json` จะ retry อีกครั้งแบบไม่ใส่ `format` อัตโนมัติ

## 2026-04-25 (KYT rollback by user request)

- ถอดฟีเจอร์ KYT ออกจาก One Platform ตามคำขอผู้ใช้: ลบ route `/kyt*`, ลบเมนู `KYT AI`, และลบ service/template ที่เกี่ยวข้อง
- ลบเอกสาร `ProjectYK_System/docs/KYT_AUTOFILL_GUIDE.md` และสคริปต์ `tools/fill_kyt_weekly.py` ออกจากโปรเจกต์ เพื่อกลับไปใช้ workflow ผ่าน Cursor chat ตามเดิม

## 2026-04-08 (Phase 4 Wave 1 — Driver PWA: Auth + Vehicle Check + Alcohol Test)

- **Schema v14**:
  - `Employee.pin_hash` + `pin_set_at` — ตั้ง PIN 4-6 หลักต่อคนขับ (scrypt+salt)
  - `DriverSession` — cookie-based session token (30 วัน rolling), รองรับหลายอุปกรณ์ต่อคน
  - `DriverSubmission` — ตารางกลางเก็บทุกอย่างที่คนขับส่งจากมือถือ (`vehicle_check`, `alcohol_test`, `job_photo`, `fuel_receipt`, `signature`, `other`)
    - มี `vehicle_id`, `daily_job_id`, `gps_lat/lng/accuracy`, `photo_paths` (หลายรูป), `data_json` (flexible payload)
    - `review_status` + `review_note` สำหรับ admin
- **`services/driver_auth.py`** ใหม่:
  - `hash_pin` / `verify_pin` (stdlib scrypt, ไม่ต้องพึ่ง bcrypt/argon2)
  - In-memory rate limiting (5 ครั้งผิด → ล็อค 10 นาที)
  - `normalize_phone` — รับทุกรูปแบบ `081-234-5678`, `+66 81 234 5678`
  - `create_session` / `revoke_session` / `get_current_driver` (cookie `drv_session`)
  - `save_photo` — เก็บใน `uploads/driver/<emp_id>/<YYYY-MM-DD>/<kind>/<ts>.jpg`
- **Driver PWA pages (mobile-first)** — UI ใหญ่ เลือกได้ง่าย bottom-nav 4 ปุ่ม:
  - `/driver/login` — เบอร์โทร + PIN
  - `/driver` — home: tile ตรวจรถ/เป่าแอลกอฮอล์ (แสดงสถานะวันนี้), งานวันนี้, ส่งล่าสุด
  - `/driver/today` — รายการงานวันนี้ + 7 วันข้างหน้า
  - `/driver/check` — checklist 15 รายการ (ยาง/เบรค/ไฟ/น้ำมัน/เอกสาร…) + ถ่ายรูปหลายใบ + GPS
  - `/driver/alcohol` — ถ่ายรูปเครื่องเป่า + กรอกค่าอ่านได้ + GPS (ค่า > 0 = flagged อัตโนมัติ)
  - `/driver/history` — ประวัติการส่งของตัวเอง + สถานะตรวจ
- **Client-side image compression** — ย่อเป็น 1280px + JPEG 75% ก่อนอัพโหลด (ประหยัด data 4-10 เท่า)
- **Admin pages**:
  - `/admin/drivers/pins` — ตั้ง/เปลี่ยน/ล้าง PIN + เบอร์โทร (เปลี่ยน PIN = revoke sessions เก่าทั้งหมด)
  - `/admin/submissions` — ดูรายการจากคนขับทั้งหมด + filter (driver/kind/review/date) + review (approve/flag/archive) + preview รูป
- **Nav**: เพิ่มลิงก์ `📱 Driver` ในทุกหน้า admin
- **`/uploads` static mount** สำหรับ admin preview รูปภาพ

## 2026-04-08 (Phase 3 — CFO Dashboard + Debt/Loan tracking)

- **Schema v13**: `Loan` + `LoanPayment` tables (`models.py`)
  - รองรับ `term` (ลดต้นลดดอก), `hire_purchase` (งวดคงที่), `revolving` (OD/วงเงินหมุน), `informal` (ยืมส่วนตัว), `factoring`, `other`
  - ทุก Loan มี `code` auto (`L0001`), ผูก `linked_vehicle_id` ได้ (สำหรับไฟแนนซ์รถ)
- **`services/finance.py`** ใหม่: รวมสูตรการเงินทุกอย่างไว้ที่เดียว
  - `amortization_schedule` — คำนวณตารางผ่อนอัตโนมัติ (ลดต้นลดดอก / งวดคงที่ / ดอกเบี้ยอย่างเดียวสำหรับ revolving)
  - `loan_summary` — รวมยอดคงเหลือ + ภาระต่อเดือน + ประมาณดอกเบี้ยปีหน้า
  - `monthly_pnl` — รายรับ (ค่าขนส่ง + fees) − ต้นทุน (fuel + payroll + petty + maint + ดอกเบี้ย)
    - **Petty cash กรองหมวด**: รวมเฉพาะ `toll/parking/loading/fine/accident` เพราะ `fuel/repair/tire` ซ้ำกับ FuelTxn/MaintRecord, `driver_advance/salary_partial` หักผ่าน payroll เอง
    - มี toggle `include_other_petty` เผื่อข้อมูลเก่าที่ยัง `category="other"`
  - `cost_per_vehicle` — รายรับ/น้ำมัน/ซ่อม ต่อคัน + gross margin
  - `cash_flow_projection` — พยากรณ์ 30-180 วัน (AR M+1, หนี้ตามตารางผ่อน, payroll, fuel/petty รายวันเฉลี่ย)
  - `break_even_and_runway` — Contribution margin, break-even trips/เดือน, ค่าใช้จ่ายคงที่, สถานะ healthy/losing
- **หน้าเว็บใหม่ 5 หน้า**:
  - `/finance` — Dashboard หลัก (KPI + P&L + health + trend 6 เดือน + top 15 รถ)
  - `/finance/loans` — รายการหนี้ + สรุปยอดรวม + ภาระ/เดือน
  - `/finance/loans/new` & `/finance/loans/{id}` — ฟอร์มกรอก/แก้ไข + ตารางผ่อนอัตโนมัติ + บันทึกการชำระ
  - `/finance/pnl?year=YYYY` — กำไรขาดทุนรายเดือนทั้งปี (12 เดือน + สรุป)
  - `/finance/vehicles?month=YYYY-MM` — ต้นทุนต่อคันทั้งหมด
  - `/finance/cashflow?days=N` — ประมาณการกระแสเงินสด 30/60/90/120/180 วัน
- **Nav**: เพิ่มลิงก์ `💰 CFO` ในทุกหน้า
- **`.gitignore`** ใหม่: ป้องกันไฟล์ sensitive (Salary/, Fuel/, *.xlsx, *.pdf, app.db, secrets, nested .git, etc.)
- **ข้อมูลหนี้**: ผู้ใช้จะค่อยทยอยกรอกผ่านหน้า `/finance/loans/new` (ไม่บังคับ — ถ้าไม่มีข้อมูลหนี้ dashboard ก็ยังใช้ได้ แต่ break-even จะขาด fixed cost ส่วนดอก)

## 2026-04-08 (Phase 2 — import + provenance + billing export)

- **Schema v12**: `DailyJob.source` — `import_daily` | `manual` | `bigc_fuel_rate` | `""` (legacy)
  - ฟอร์มสร้างงานใหม่ใน UI → `source=manual`
  - `tools/import_daily.py` → `import_daily`; `--wipe-prior` ลบเฉพาะ `import_daily` (+ fees + fuel ผูก job นั้น) ไม่ลบงานคีย์มือ
  - `--mark-legacy-import` ใช้ครั้งเดียวเมื่ออัปเกรดจาก DB เก่า (ทุกแถว `source=""` เป็น import) — **ระวัง** ถ้ามีงาน manual เก่าที่ยัง `""`
- **Default import ย้อนหลัง**: `--from-date` เปลี่ยนเป็น **2018-01-01** ทั้ง `import_daily.py` และ `import_petty_cash.py`
- **`ProjectYK_System/tools/phase2_import.bat`**: รัน import Daily แล้วต่อด้วย Petty (ส่ง args ร่วมได้ เช่น `--wipe-prior`)
- **`import_bigc_fuel_rate.py`**: DailyJob ที่สร้างใหม่จากไฟล์เรท → `source=bigc_fuel_rate`
- **`tools/backfill_links.py`** ใหม่: เติม FK (driver_id/vehicle_id/etc.) ให้ DailyJob/PettyCash/FuelTxn จาก master เดิม — ใช้หลัง wipe+import
- **Billing export (P0-3)**:
  - หน้า `/billing` — กรอง site+เดือน+ลูกค้า, สรุปต่อลูกค้า (นับเที่ยว, ค่าขนส่ง, ค่าอื่น, ภงด.53, สุทธิ)
  - `/billing/export.csv` — ดาวน์โหลด CSV (UTF-8 BOM) ต่อ site/เดือน/ลูกค้า พร้อม extra fees รวมแล้ว
  - แบบฟอร์มใบวางบิลต่อลูกค้า (รูปเล่ม) เลื่อนไปทำเมื่อเก็บ requirements แต่ละเจ้าแล้ว
- **Dependency pin สำคัญ** (`ProjectYK_System/app/requirements.txt`):
  - `starlette>=0.36,<0.40` + `fastapi<0.115` — starlette 1.0 แตก Jinja2 template globals (unhashable type dict)
- **Import จริงใน DB**: DailyJob 1,552 (93% linked driver / 100% vehicle) · PettyCashTxn 50,753 ย้อนถึง 2019-12 (20% linked driver — ส่วนใหญ่เป็นพ่อ/office/คนขับเก่า) · FuelTxn 777
- **Roadmap Driver PWA**: ตรวจรถ + เป่าแอลกอฮอล์ (ถ่ายรูปมือถือ) + หลักฐาน Audit/Safety ลูกค้า (แนว compliance ลูกค้าใหญ่ / DHL-class) — บันทึกใน `AGENTS.md`

## 2026-04-21

- ตั้งศูนย์กลางบริบท AI ที่ `ProjectYK_System/`
- กำหนด bootstrap กลางให้ Agent อ่านจาก:
  - `AGENT_BOOTSTRAP.md`
  - `MODULE_REGISTRY.md`
  - `CHANGELOG_MASTER.md`
- ลงทะเบียนโมดูลหลัก:
  - `AccidentCases`
  - `TransportRateCalculator`
- วางกติกาอัปเดต context สองชั้น:
  - log ของโมดูล
  - changelog กลาง
- เพิ่ม template logo พร้อมใช้ที่:
  - `AccidentCases/_TEMPLATE_CASE/assets/images/yk_logo_mark.svg`
- เพิ่ม automation script สำหรับลงทะเบียนโมดูลใหม่:
  - `ProjectYK_System/bootstrap_module.py`

## 2026-04-22

- เริ่มใช้แนวทาง "Data First, UI Improve Later" สำหรับโมดูลสดย่อยออนไลน์
- เพิ่มเครื่องมือย้ายข้อมูลย้อนหลังจาก Excel ไปออนไลน์:
  - `TransportRateCalculator/tools/build_petty_cash_online.py`
- เพิ่มรายงานออนไลน์เบื้องต้นสำหรับใช้งานจริง:
  - `TransportRateCalculator/reports/petty-cash-online/index.html`
- เพิ่ม output กลางสำหรับต่อ API/DB ได้ทันที:
  - `petty_cash_records.csv`
  - `petty_cash_records.json`
  - `summary.json`
- ขยายการจัดหมวดต้นทุนให้รองรับรายการการเงิน (`finance`) เพื่อคำนวณต้นทุนจริง

- **เลือก Tech Stack สำหรับ One Platform**: FastAPI + SQLite + HTMX + Tailwind (CDN) + `start.bat`
  - เหตุผล: รันบนโน้ตบุ๊กได้ทันที ไม่ต้องติดตั้ง Node/Postgres/Docker เหมาะกับช่วง vibe-test
  - Migration path: ย้ายเป็น PostgreSQL ตอนขึ้น PC Server + Tailscale
- **สร้างโครง Day-1 ของโมดูล Daily** ที่ `ProjectYK_System/app/`
  - `main.py` (FastAPI) + `templates/` (base, daily_list, daily_new) + `start.bat`
  - โมเดล `DailyJob` เริ่มจาก contract ใน `Salary/daily_module/contracts.py`
  - CRUD ขั้นต้น: เพิ่ม/ดู/ลบ + ฟิลเตอร์ตาม site + วันที่
  - ทดสอบ: server ขึ้นได้, `/health` ตอบ `{"ok":true}`, `/daily` ใช้งานได้
- **บันทึกการตัดสินใจจากผู้ใช้**:
  - ผู้ใช้ไม่เขียนโค้ดเอง ทำหน้าที่ vibe-test (รัน, หาบัค, สั่งแก้)
  - ทีม 7 คน (บัญชี 2 / OP 3 / ผู้จัดการ 1 / เจ้าของ 1)
  - เร่งด่วนสุด เพราะเคยเสียเวลาเกือบ 1 ปีกับโปรแกรมเมอร์ภายนอกแล้วไม่ได้ใช้
  - เริ่มไหลจาก Daily → Dispatch → Billing/Accounting (สดย่อย) → Payroll

- **ตั้ง Cursor rule ให้ auto-update context**: `.cursor/rules/project-yk-context.mdc` (alwaysApply=true)
  - ทุก agent ที่เปิดแชทใหม่จะอ่านและอัปเดต CONTEXT_LOG / NEXT_ACTION_PLAN / CHANGELOG อัตโนมัติ
- **ทำ field mapping 3 ไซต์จากตัวอย่างจริง**: `ProjectYK_System/Daily.xlsx` → `docs/IMPORT_MAPPING_SPEC.md`
  - AYU 28 cols (งาน 1 เที่ยว/แถว), BIGC 19 cols (หัวลาก+หาง), LCB 40 cols (ตู้ container ซับซ้อน)
  - พบว่า `DailyJob` ต้องขยาย + แยกตาราง `daily_job_fees`, `fuel_txns`, `trucks`, `trailers`

- **เก็บ domain knowledge payroll/billing เต็มจากผู้ใช้**:
  - `docs/SITE_PAYROLL_RULES.md` — กฎเงินเดือน 3 ไซต์ (BIGC 9000 standard, LCB 2 modes, AYU 2 modes), common deductions (deposit/SSO/accident installments)
  - `docs/BIGC_BRANCH_RATE_SPEC.md` — สูตรค่าขนส่ง 1Big c / 1+ / 2BigC / 2++ / รับรถ / 1DH + ตารางสาขา (รอไฟล์จากผู้ใช้)
  - `docs/WORKFLOW_BY_TEAM.md` — บทบาท 7 คน, vision "Dispatch ต้นน้ำ บัญชีมาหยอดท้าย", cross-site scenario (BIGC → แหลม)
- **ยืนยันรอบจ่ายเงินเดือนต่อไซต์**: AYU 26→25 จ่ายสิ้นเดือน, BIGC 1→สิ้นเดือน จ่ายวันที่ 1, LCB 16→15 จ่ายวันที่ 1

- **Phase 1.1 เสร็จ: Master Data + Expanded Daily**:
  - `app/models.py` รวม 11 ตาราง: `SchemaInfo`, `Employee`, `Vehicle`, `Customer`, `PayCycle`, `DailyJob` (ขยาย 28 ฟิลด์), `DailyJobFee`, `LeaveRecord`, `AccidentCase`, `AccidentInstallment`, `DriverDeposit`, `BigcBranch`
  - Seed `pay_cycles` อัตโนมัติตอน startup (3 ไซต์)
  - UI CRUD: /employees /vehicles /customers + ฟอร์ม Daily ขยาย (dropdown + raw_name fallback + เลือกหาง)
  - Smoke test: สร้างคน 3 คน (BIGC standard / LCB trip / AYU mao+การันตี), รถ 3 คัน (head+tail+truck), ลูกค้า 2 ราย, daily 2 รายการ, แก้ได้ ลบได้ — ผ่านทุกจุด
  - Schema version track ในตาราง `schemainfo` (ปัจจุบัน v2)
- **ยืนยัน design principles รอบนี้จากผู้ใช้**:
  - AYU share rate 55-60% เก็บ**ต่อคน** (flexible) — ไม่ fix
  - LCB "ไม่แบ่ง" items (ค่าเสียเวลา, ค่าค้างคืน) → ใส่ใน `custom_terms` (JSON text) ไม่ hard-code
  - AYU การันตี = เต็มเดือน หักรายวันเมื่อลา
  - Cross-site: ใช้ pay rule ของไซต์**คนขับ** ไม่ใช่ไซต์งาน
  - ช่วงแรกคนกรอกค่าเที่ยวเอง cross-site ได้ (ไม่บังคับสูตร)
  - ทุก user เห็นทุกไซต์ (DB ไม่มีปัญหา Sheet filter ทับกัน)
  - ยังไม่ทำ Line OA — ใช้ copy-paste ไปก่อน

- **2026-04-22 Session 10 — Q&A + 2-Track Plan**:
  - เพิ่ม auto-gen code สำหรับ Employee (E0001) / Customer (C0001) — กรอกเองก็ได้
  - ยืนยัน search ด้วยชื่ออย่างเดียวใช้ได้ (substring, ไม่ต้องมีนามสกุล)
  - helper text: ภงด 53 = 1% ของค่าขนส่ง, ช่องน้ำมันใน daily_form จะย้ายเป็นหน้า /fuel แยก
  - วัน start/end รถตอนนี้เป็นแค่ info — Asset Register (DP/ค่าเสื่อม/มูลค่ารถ) เลื่อนไป Phase 2
  - Billing Profile อ้างอิง = text pointer ไป `CUSTOMER_BILLING_PROFILES.md` (จะเปลี่ยนเป็น FK dropdown ทีหลัง)
  - Raw name ไม่ auto-create master — ใช้ workflow "⚠️ + ปุ่ม promote" แทน
- **แผนใหม่: 2-Track Parallel** (ตามผู้ใช้เสนอ):
  - **Track A (Petty Cash Quick Win)** — `petty_cash_txns` + UI + parser memo ไทย + import Excel สดย่อยเก่า → แอดมินใช้แทน Excel ภายใน 1 สัปดาห์
  - **Track B (Daily Import + Foundation)** — FuelTxn + import scripts (AYU→BIGC→LCB) + promote-to-master UI
- **ลำดับถัดไป**: พรุ่งนี้เริ่ม Track A (Petty Cash) ก่อน

- **2026-04-23 Session 11 — Track A Petty Cash (A1+A2+A5 done)**:
  - schema v3: เพิ่มตาราง `PettyCashTxn` (20+ fields) + 4 enums ใหม่ใน `models.py`
  - `init_db` ใหม่: drop+recreate เมื่อ schema version mismatch (dev mode, สะดวก vibe-test)
  - UI /petty-cash: list + form + edit + delete + filter 6 มิติ + card 3 summary
  - UI /petty-cash/pending: สรุปรอหักเงินต่อคนขับ + แยกเคสไม่มี driver_id
  - auto compute pay_cycle_tag ตามไซต์ (AYU 26→25, BIGC 1→end, LCB 16→15)
  - lock guard: status=locked → แก้/ลบไม่ได้
  - เอกสาร `docs/PETTY_CASH_SPEC.md` mapping Excel เดิม → schema ใหม่
  - smoke test HTTP ผ่านทุก endpoint (health, list, new, edit, pending, filter)
- **ยังเหลือ A3 (parser memo), A4 (import Excel), A6 (payroll lock hook)**

## 2026-04-08 — Maintenance Module Full Scope (rm7 + rm8)

- **Schema v10 เสร็จสมบูรณ์** (Wave 2 + Wave 3 + full maintenance):
  - `Vehicle` + nickname/old_plate_no/brand/model/engine_no/chassis_no/current_mile
  - `PmPlan` + fluid_kind/alert_km_before + next_due_date/next_due_mile auto-compute
  - ตารางใหม่: `VendorPrice`, `VehicleSpec`, `MaintInspection`, `MaintInspectionItem`
  - ENUMs: `FLUID_KINDS`, `INSPECTION_STATUS`, `INSPECTION_ITEM_STATUS`
- **UI ครบชุด** (7 หน้าใหม่):
  - PM list/form + mark_done + auto next-due + dashboard overdue/due_soon
  - Tire list/form + per-vehicle visual layout + event system (mount/rotate/unmount/inspect/retread/scrap)
  - Part detail + VendorPrice CRUD + prefer + auto-learn from stock-in + comparison view
  - MaintInspection list/form + dynamic checklist + auto overall_status
- **Import tools เสร็จ**:
  - `tools/import_fluid_history.py` — `ProjectYK_System/ประวัติเปลี่ยนของเหลว.xlsx`
    - 8 VehicleSpec, 279 PmPlan (น้ำมันเครื่อง/เกียร์/เฟืองท้าย/จารบี/หล่อเย็น), 45 VendorPrice, 39 Part, 12 Vendor, 9 StockTxn opening-balance, 20 historical MaintRecord
    - idempotent (hash-based + unique-key upsert)
  - `tools/import_rm_history.py` — 3 RM History files:
    - `RM History(Wangnoi).xlsx`: 45 Vehicle + 105 MaintRecord (repair log) + 846 StockTxn (Stock อยุธยา)
    - `RM History(LCB).xlsx`: 43 Vehicle + 33 tire StockTxn + 1 part StockTxn
    - `RM History(BigC Thanya).xlsx`: 20 Vehicle (รองรับ layout BigC ที่มีคอลัมน์ จังหวัด คั่นระหว่าง plate/brand)
    - รวมทั้งระบบ: Vehicle 169 (brand-filled 78, old_plate 17), MaintRecord 146, StockTxn 900, Part 660 (tire 30), Vendor 138
    - กันข้อมูลเพี้ยน: strip Excel text-prefix `'` + strip province suffix `อย/ปท/นนท`
- **Dashboard upgrade**: PM widget (overdue/due_soon พร้อมทะเบียน + เหลือกี่วัน/km), recent stock activity (8 รายการล่าสุด), ลิงก์ไปทุก sub-module
- **Smoke test ผ่าน 8 routes**: `/maint`, `/maint/records`, `/maint/pm`, `/maint/tires`, `/maint/parts`, `/maint/vendor-prices`, `/maint/inspections`, `/maint/stock` — 200 OK ทั้งหมด

## 2026-04-08 — Fuel-Adjusted Transport Pricing (schema v11)

- **เพิ่มความสามารถ**: ค่าขนส่ง (revenue_customer) ผันแปรตามราคาน้ำมันรายเดือนได้
- **Design**: Hybrid pricing
  - Track A: ลูกค้าที่คุยรายเดือน ใช้ `RateCard.effective_from/to` (มีอยู่แล้ว) — admin กรอกเรทใหม่แต่ละเดือน
  - Track C: ลูกค้าที่ส่ง fuel surcharge step table ให้ (BigC/LCB) — ใช้ตาราง step table
- **Schema v11** (2 ตารางใหม่):
  - `FuelPriceIndex(month YYYY-MM, region, diesel_price, source, notes)` — อ้างอิงราคาดีเซลต่อเดือน
  - `FuelSurchargeBand(customer_id, trip_type_code, vehicle_kind, fuel_min, fuel_max, surcharge_pct, surcharge_flat, fuel_ref_mode [current/prev1/prev2], region, effective_from/to, priority, status, notes)` — ช่วงราคา → %/บาทบวก
- **Helper (`main.py`)**:
  - `get_fuel_price(month, region)` — lookup ราคาน้ำมัน + fallback region
  - `match_surcharge_band(customer, trip, vehicle, date, diesel_price)` — เลือก band ที่ match best (specific > wildcard, priority สูง > ต่ำ)
  - `compute_effective_rate(base, customer, trip, vehicle, date, region)` → `{base, diesel_price, band_id, pct, flat, effective, explain}`
- **Routes**:
  - `/fuel-index` GET/POST/delete — CRUD ราคาน้ำมันรายเดือน (upsert ถ้า month+region ซ้ำ)
  - `/fuel-surcharge` GET/POST/delete — CRUD Fuel Surcharge Bands ต่อลูกค้า
  - `GET /api/rates/effective?base_rate=X&customer_id=Y&work_date=Z` → preview JSON
- **UI**:
  - `fuel_index_list.html` / `fuel_surcharge_list.html` — table + inline form
  - Daily form (`daily_form.html`): เพิ่ม live preview ข้างช่อง "ค่าขนส่ง" — JS เรียก `/api/rates/effective` แล้วแสดง `⛽ base 1000 × (1 + 2%) = 1020 (น้ำมัน 2026-03=33.50 ฿/L, current)`
  - Nav เพิ่ม link `⛽ Fuel`
- **ตัวอย่าง test ผ่าน**:
  - Mar 2026, น้ำมัน 33.50 ฿/L → band 33.00-34.00 (+2%) → base 1000 → effective **1020**
  - Feb 2026, น้ำมัน 32.00 ฿/L → band 32.00-33.00 (+0%) → base 1000 → effective **1000**
- **URL design note**: ใช้ `/fuel-index` + `/fuel-surcharge` ที่ root (ไม่ใช่ nested `/rates/...`) เพื่อเลี่ยง route-collision กับ `/rates/{card_id:int}` (FastAPI match int จะ error 422 ก่อน)

- **2026-04-27 (BIGC 2026-03 data hygiene):** ทำ surgical reset เฉพาะ BIGC รอบ `2026-03` (backup DB, wipe เฉพาะ source `import_daily`/`bigc_fuel_rate`/`import_petty_mar26`, reimport ใหม่, recompute payroll, preflight duplicate/unlinked = 0)
- **2026-04-27 (Payroll tax withholding):** เพิ่มคำนวณภาษีรายได้แบบขั้นบันไดใน `services/payroll.py` (annualized progressive PIT แล้วหาร 12 ต่อเดือน) และผูกเป็น deduction อัตโนมัติผ่าน `other_deduction` พร้อมรองรับ override รายคนใน `Employee.custom_terms`
- **2026-04-28 (Tax catch-up default + explicit tax field):** ปรับ payroll ให้ default โหมดภาษีเป็น `catch_up` (คำนวณภาษีคาดการณ์ทั้งปีแล้วเฉลี่ยตามเดือนที่เหลือหลังหักยอดที่เคยหักแล้ว) และแยกเก็บ `PayRunItem.income_tax_withholding` พร้อมแสดงในหน้า payroll detail/employee detail
- **2026-04-28 (Monthly tax cap policy):** เพิ่มเพดานหักภาษีรายเดือนใน `services/payroll.py` (`tax_monthly_cap_rate`, default 15%) โดยจำกัดยอดหักทั้งโหมด `catch_up` และ `safe` ที่ระดับ `% ของเงินสุทธิก่อนหักภาษี`
- **2026-04-28 (UI polish #1):** ฟอร์มพนักงานเพิ่ม section ภาษี (โหมด/cap/ลดหย่อนเพิ่ม/ยกเว้น) merge เข้า `custom_terms` JSON, register Jinja filters `dmy`/`dmy_hm` (รูปแบบ `27/04/2026`) และใช้กับหน้า list/detail หลัก, เพิ่ม jump-to-page (input + dropdown) ที่ /petty-cash /daily /fuel
- **2026-04-28 (Petty dedup wave 2):** เพิ่ม alias `AYU: สมัย → สมัย อยุธยา`, ทำ dedup ข้าม source แบบ canonical-name + reassign site=AYU จาก suffix `อยุธยา` 565 แถว ลด unlinked/ซ้ำของรอบเก่า
- **2026-04-28 (Ops context):** บันทึกบริบทธุรกิจพื้นที่เช่าในลาน วาย.เค (เสี่ยงรายได้หาย ~34,000/เดือนหากผู้เช่าย้าย) และกรอบตัดสินใจเน้นผู้เช่าสายงานสะอาด/ไม่แย่ง capacity ลานจอดหลัก
- **2026-04-28 (Ops risk update):** เพิ่มข้อเท็จจริงหน้างานว่าทางเข้า-ออกรถบรรทุกติดข้อพิพาททางกฎหมาย (คดีถนนเข้าออก) ต้องปรับกลยุทธ์ผู้เช่าใหม่เป็น access-first และใช้สัญญาเงื่อนไขความเสี่ยง

## 2026-04-28 (Ad-hoc quote baseline for Direct-to-store)

- ล็อกสมมติฐานคำนวณเสนอราคาแบบแชท: ค่าเสื่อมรถ `700,000/8/365`, เบี้ยประกันจริง `13,500/365`, น้ำมันฐาน `31.5`, maintenance `1.5 บาท/กม.`, back office `12%`
- ตั้งหลักการ conservative สำหรับงาน ad-hoc: `1 เที่ยว = 1 วัน` (จันทร์-ศุกร์) และถ้าวิ่งมากกว่า 1 เที่ยว/วันให้นับเป็น upside
- ปรับคำนวณน้ำมันให้แยกตามประเภทรถในงานเสนอราคา Direct-to-store: 6W `5.5 กม./ลิตร`, 10W `4.5 กม./ลิตร` พร้อมเพิ่มตัวชี้วัด `%น้ำมันต่อค่าขนส่ง` ต่อรูท
- เปลี่ยนเงื่อนไขเจรจาน้ำมันเป็น `1.5% ต่อ 1 บาท` และ reprice ในไฟล์ทำงาน (`_v3_adjusted_only`) ให้ margin ที่ fuel target 50 ยังอยู่ราว 10%
- อัปเดตเงื่อนไขราคาดีล Direct-to-store เพิ่มเติม: 6W consumption = `5.0`, ค่าเที่ยวแบบ distance ladder (`0-200 = 500/600`, แล้ว +100 ต่อทุก 100 กม.), และโซนเชิงกลยุทธ์ `สมุทรปราการ/ฉะเชิงเทรา/ชลบุรี` ใช้ target margin `5%`
- **2026-05-01 (Oatside reports):** 	rips.html/รายเที่ยวต่อทะเบียน — คอลัมน์ ค่าขนส่ง / เสียเวลา+50% / เสียเวลา+100% / ตีเปล่า+50%; No-work recovery รองรับข้ามคืน (irst_no_work_trip_by_plate_recovery_day + synthetic plate_dest_day_rows)
- **2026-05-07 (Forward Insight checklist progress):** เดินเมนู demo แบบรอ loading overlay ทุกคลิกและปิดหมวด `การจัดซื้อ` ครบ 100% (`expense/expense-item/stock/refuel/fuel-card/fuel-station`) เพื่อให้ checklist เข้าใกล้ gap=0 แบบตรวจสอบย้อนกลับได้
- **2026-05-07 (Forward Insight accounting progress):** ปิดเพิ่มฝั่งบัญชีอีก 4 หน้า (`tms-document`, `bill_income`, `invoice_income`, `payment_income`) ด้วย flow `click -> wait overlay gone -> snapshot` เพื่อลดคลิกพลาดและรักษาความน่าเชื่อถือของ checklist
- **2026-05-07 (Forward Insight long-run progress):** เดินต่อเนื่องแบบไม่หยุดหมวดและปิดเพิ่ม `บัญชี` 3 หน้า (`bill_pay`, `invoice_pay`, `payment_pay`) + `บุคคล` 3 หน้า (`saving`, `income-type`, `income-package`) ทำให้ todo ใน checklist ลดเหลือ 41 หน้า
- **2026-05-07 (Forward Insight HR complete):** ปิดหมวด `บุคคล` ครบทั้ง 12 หน้าแล้ว (รวม `sso`, `เอกสารรถ`, `รายการครบกำหนด`, และ master data `employee/site/department/title`) ทำให้ checklist คงเหลือ todo 34 หน้า
- **2026-05-07 (Forward Insight accounting continued):** ปิดเพิ่มในหมวด `บัญชี` อีก 3 หน้า (`account/carrier/invoice`, `account/carrier/bill`, `account/carrier/finance`) โดยรักษากติกา `click -> wait overlay gone -> snapshot` ทุกคลิกเพื่อลดพลาดจาก ref เปลี่ยนระหว่างโหลด
- **2026-05-07 (Forward Insight accounting complete):** ปิดหน้า `[todo]` ที่เหลือของหมวด `บัญชี` ครบทั้งชุด (`expense`, `adjusting_entries`, `monthly_wht`, `vat/monthly_vat`, `vat/tax_sale`, `vat/tax_purchase`, `tax`, `journal`, `new_account`, `report/gl`, `report/trial-balance`, `report/pnl`)
- **2026-05-07 (Forward Insight settings progress):** เริ่มปิดหมวด `ตั้งค่า` ต่อเนื่องแล้ว 5 หน้า (`partner`, `settinginvoice`, `excel`, `core/product`, `core/product-category`) ก่อนเดินต่อ `unit/vehicle` และ master รถที่เหลือ
- **2026-05-07 (Forward Insight settings complete):** ปิดหมวด `ตั้งค่า` ที่เหลือครบ (`uom`, `core/vehicle`, `core/vehicle-model`, `core/vehicle-type`, `core/vehicle-brand`, `core/vehicle-energy`) ด้วย flow `click -> wait overlay gone -> snapshot`
- **2026-05-07 (Forward Insight transport progress):** ปิดหมวด `ขนส่ง` เพิ่ม 4 หน้า (`tms/report/amount_trip`, `tms/product`, `tms/product-type`, `tms/place`) และคงเหลือ 4 หน้าสุดท้าย (`vehicle/work vehicle type/carrier payment/special expense`)
- **2026-05-07 (Forward Insight transport complete):** ปิด 4 หน้าสุดท้ายของหมวด `ขนส่ง` ครบ (`tms/vehicle`, `tms/run-type`, `tms/pay-type`, `tms/extra`) ทำให้ checklist demo ครบ 100% (todo = 0)
- **2026-05-07 (Claude Code token optimization):** เพิ่มแนวทาง `Lean Mode` สำหรับงาน scope เล็กใน `AI_CURSOR_CLAUDE_WORKFLOW.md` + `CLAUDE.md` และเพิ่มเทมเพลตพร้อมใช้ `docs/CLAUDE_CODE_LEAN_PROMPT_TEMPLATE.md` เพื่อลดการอ่าน `.md` เกินจำเป็นก่อนแตะโค้ด
- **2026-05-07 (Claude Code ultra-lean ops):** เพิ่ม `Ultra-Lean 5 lines` + start snippets (`tools/CC_LEAN_START.txt`, `tools/CC_ULTRA_LEAN_5LINES.txt`) และแนวทางทดสอบ skills ภายนอกแบบคุมความเสี่ยง token (หลีกเลี่ยง profile ใหญ่เป็นค่าเริ่มต้น)
- **2026-05-07 (CC benchmark + team default):** เพิ่ม `tools/CC_BENCHMARK_LOG.md` สำหรับวัด 3 ตัวชี้วัด (เวลาเริ่มลงมือ/โทเค็น/รอบถามกลับ) และล็อกค่าเริ่มต้นทีมให้งานเล็กเริ่มจาก `CC_ULTRA_LEAN_5LINES.txt` ก่อน
- **2026-05-07 (BigC unresolved safe reduce):** ปรับ `audit_bigc_manual_vs_system.py` ให้ auto-resolve เฉพาะชื่อที่พิสูจน์ได้แบบ single-prefix (เช่น `บุญชอบ` -> `บุญชอบพูลสวัสดิ์`) และคง unresolved ที่เหลือพร้อม `next_action` รายคน; rerun แล้ว unresolved ลด `8 -> 7`, `missing_in_manual 1 -> 0`
- **2026-05-07 (Night handoff morning pack):** เพิ่ม `docs/NIGHT_HANDOFF_PACK_LATEST_TH.md` เพื่อสรุป checklist เช้า 10 นาที, outstanding queue เรียง `BigC -> LCB -> AYU`, decisions pending, และ 3 คำสั่ง executable สำหรับผู้ใช้ non-coder จากรายงานล่าสุดใน `reports/`
- **2026-05-08 (Night Autopilot x4 loops):** รันลูป `BigC -> LCB -> AYU -> docs/handoff` ครบ 4 รอบแบบ skip-safe ไม่เดา, รีเฟรช preflight + unresolved/morning queues ทุกไซต์ และยืนยัน app runnable ด้วย `run_payroll_test.py`
- **2026-05-08 (Email Inbox + Excel-like Grid POC):** เพิ่ม schema `InboxEmail/InboxSyncRun`, service `services/email_ingest.py` (IMAP sync + rule/Gemini classify with human-review guardrail), หน้า `/email/inbox` read-only workflow และหน้า `/daily/grid` (Tabulator CDN + batch save API) สำหรับแก้ข้อมูลเร็วแบบคล้าย Excel
- **2026-05-08 (Daily Grid UX hardening):** ปรับ `/daily/grid` เป็นก้าวถัดไปของ single-page Daily workflow: quick presets รายไซต์/สถานะเดือนนี้, save เฉพาะ field ที่แก้จริง, unsaved warning/dirty feedback, และลิงก์แก้เต็มรายแถวโดยไม่เปลี่ยน route เดิม
- **2026-05-08 (Oatside latest-price fallback):** ปรับ `Oatside/build_oatside_reports.py` ให้ fallback ราคาน้ำมันเป็น `latest prior day (<=trip_date)` ก่อน, คงกติกา Apr/May เดิมทั้งหมด, เพิ่ม warning traceable (fallback จากวันไหน/ราคาเท่าไร) และพิมพ์ summary usage `exact/carry_forward/base_fallback` หลัง build

- ยืนยัน policy ราคา Oatside จากผู้ใช้: ช่วง `2026-04-12..2026-04-15` ใช้ base trip `8,000` ภายใต้ base fuel band `50.00-50.99` (กัน mapping ย้อนกลับเป็น 7,500)
