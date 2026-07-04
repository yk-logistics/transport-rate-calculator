---
name: project-bigc-holiday-anuloom
description: BigC วันหยุด หัก + (อนุโลม) ไม่หัก — _count_work_days อ่าน destination substring; re-import ลบ driver link ต้อง relink
metadata: 
  node_type: memory
  type: project
  originSessionId: d3a84270-2e17-48a4-abad-f3b07a41a33f
---

DONE+**deployed** 30 มิ.ย. (committed main `6435913`; live บน server net 126,859 verified public 200): BigC คีย์สถานะวันหยุดลงช่อง "ที่ส่งสินค้า" (= `DailyJob.destination`):
- `ลาหยุด` = วันหยุด **หักเงิน** (290฿/วัน = 9000÷31)
- `ลาหยุด (อนุโลม)` = **ไม่หัก** นับเหมือนทำงานเต็มวัน (โอยืนยัน: อนุโลม = ได้ฐานเต็ม)

**บั๊กที่เจอ (สำคัญ):** เดิม `_count_work_days` (services/payroll.py) **ไม่อ่าน `destination` เลย** (อ่านแค่ leave_status+status_code+remark) → วันหยุด BigC **ไม่เคยถูกหัก**. สมัย/สมประสงค์/ณัชพน ได้ฐานเต็ม 31 วันผิด (worked=31, leave=0). ความจำเก่า [[project-jun-payroll-ayu-bigc-status]] เขียน "DailyJob ตรงไฟล์ → ไม่ต้อง re-import" = จริงเฉพาะ trip total แต่พลาดเรื่องวันหยุด.

**กฎ token ไทย (จำไว้):** tokenizer แตกคำด้วย space/punct เท่านั้น → `ลาหยุด` เป็น **token เดียว** ไม่แตกเป็น ลา+หยุด ฉะนั้น `"หยุด" in tokens` = False เสมอกับ `ลาหยุด`. ต้องใช้ **substring match** (`"หยุด" in full_blob`). destination **ยังไม่เข้า token set** (กันชื่อสถานที่ ลาดพร้าว/ตลาด ทริปกฎ ลา/ขาด/ป่วย) — ใช้ destination เฉพาะ substring marker `หยุด`/`อนุโลม`.

**โค้ด (TDD 4 เทสต์ test_bigc_holiday_exempt.py):**
- เพิ่ม `full_blob` = blob+dest ต่อวัน; `is_exempt = "อนุโลม" in full_blob` (อนุโลมชนะเสมอ → `continue` ข้าม = นับ worked); `is_holiday = (not exempt) and "หยุด" in full_blob` → fold เข้า `is_leave`.
- **forward-ready:** อ่าน `leave_status` ด้วย (อยู่ใน full_blob) → อนาคตคนคีย์ย้ายไปกรอกช่องสถานะแยกแทน destination ไม่ต้องแก้โค้ด.
- safety: scan DB ทุกไซต์ — `หยุด` ใน destination มีแต่ BIGC (64 แถว, **0 มี revenue**) → ไม่มีวันงานจริงโดน misclassify; `อนุโลม` ไม่มีที่ไหนเลยก่อน re-import.

**ข้อมูล (โอสั่ง re-import + recompute):** re-import `import_bigc_daily.py --cycle 2026-05 --wipe-prior` (venv python ไม่ใช่ system) → restore `(อนุโลม)` 6 แถว + plain ลาหยุด 18 แถว. recompute payrun #4 (draft, ไม่มี net_override ใน payrunadjust — มีแต่ fuel_rate_override_thb).

**GOTCHA ใหญ่: re-import ลบ driver_id link!** `_wipe_source` ลบ DailyJob source=bigc_2026-05 + เขียนใหม่ `driver_id=NULL` → recompute รอบแรกได้ **0 items** (activity filter ตัดคน dj_count=0). แก้: รัน `bigc_add_link_drivers.py` (idempotent, ลิงก์ตาม first-name, ไม่สร้าง emp ใหม่ซ้ำ) → relink, 0 unlinked → recompute ได้ 11 items.

**ผล (net_guard after --allow 4 ยืนยัน เฉพาะ run 4 ขยับ):** net **131,856.29 → 126,859.00 (Δ −4,997.29)**, รอบอื่นนิ่งหมด. leave ตรง Excel: ณัชพน 2, สมประสงค์ 6, สมัย 7, เกศศักดิ์ 3 (อนุโลม 2+2+2=6 นับ worked). 2 คน inactive (สมพร145/อภิรักษ์146) 0 daily พ.ค. → engine ตัดถูก (เดิม copied มา).

**ยังค้าง รอโอ (ตามเดิม):** เกศศักดิ์107 net −4,092 (6 วันจริง + petty>gross) + ธนวัฒน์105 net 1,854 (6 วัน) → โอต้องยืนยันวันทำงาน. เรทน้ำมัน BigC สูตรไหน (defer).

GOTCHA branch: ระหว่าง session branch flip เอง (main↔feat/slip-merge-fuel-same-fill) — commit ลงจริงบน main (verify `git log main`, 2 files only) ดู [[reference-branch-switch-during-session]]. งานเงินยัง gate deploy ตาม [[feedback-merge-and-deploy-without-preview]].

**DEPLOY GOTCHA (30มิ.ย. ยืนยัน 3 อัน):** (1) **scheduled task ชื่อ `YK_MVP_APP`** (รัน start_mvp.bat) **ไม่ใช่ `YK_MVP`** — `schtasks /Run /TN YK_MVP` = "cannot find file". restart ด้วย `schtasks /Run /TN YK_MVP_APP`. (2) **kill 8010 ต้อง match by PORT-owner PID ไม่ใช่ cmdline** — server python.exe อยู่ใต้ `AppData\Local\Python\...` cmdline=`"...python.exe" main.py` **ไม่มีคำ YK_MVP** (working-dir เป็น YK_MVP แต่ไม่อยู่ใน CommandLine) → filter `*YK_MVP*`+`*main.py*` พลาด; ใช้ `Get-NetTCPConnection -LocalPort 8010 -State Listen` → `.OwningProcess` → Stop-Process (แม่นกว่า ไม่โดน 8020). (3) **`Move-Item -Force` ทับ app.db ที่ยัง lock = "Cannot create a file when that file already exists"** → ต้อง stop 8010 ก่อน + `Remove-Item app.db` แล้วค่อย Move (ไม่พึ่ง -Force ทับ). DB push ใช้ backup-API clean copy → scp app_incoming.db → integrity บน server → swap (ตาม [[reference-deploy-mvp-selfverify]] WAL rule). marker check ของ deploy_mvp.sh scan แค่ main.py+templates **ไม่เห็น services/payroll.py** → verify payroll.py ด้วย Select-String 'is_exempt' บน server แยกเอง.

related: [[project-jun-payroll-ayu-bigc-status]], [[project-bigc-may-payroll]], [[reference-net-guard]], [[reference-branch-switch-during-session]]
