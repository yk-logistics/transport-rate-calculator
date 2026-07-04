---
name: project-jun-payroll-ayu-bigc-status
description: "Jun-30 night: AYU+BIGC payroll status — both draft on server, blocked on โอ's data not code; AYU re-pull from gsheet pending"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4b67c665-cf02-4e41-ab42-b175c44a9cb7
---

คืน 30 มิ.ย. โอง่วงมาก สั่ง "เร่งทำเงินเดือน AYU ก่อน แล้ว BIGC" จากไฟล์ `Work\Salary\2026\6.Jun\{AYU,BigC}`.

**สรุปหลังตรวจ DB จริง (ไม่เชื่อความจำอย่างเดียว):**

**AYU มิ.ย. = payrun #18, cycle 2026-06 (26พ.ค.-25มิ.ย.), draft, ✅ DONE+deployed 30มิ.ย. net 205,892 → 310,486.61, 24 คน, บน server แล้ว (verified).**
- **gsheet re-import แก้เหมาติดลบสำเร็จ:** โอแปลงไฟล์ AYU เป็น Google Sheet แท้ id `1F5eJlYsNAGi1zzm1Ej-dlk7Jcp6EEUz8cq1Om4n5VnQ` (sheet "Jun 26") share ให้ service account. gsheet **อัปเดตกว่า Desktop จริง**: ค่าขนส่ง 445,330 → **1,115,026**, ค่าเที่ยว 226,612 → **331,206** (ราคา+ค่าเที่ยวครบขึ้น). โครงคอลัมน์ตรง Desktop เป๊ะ (16 col, 841 แถว match 0 diff).
- **ผลลัพธ์ (หลัง gsheet):** นิวัติ139 **−14,350 → +35,195** (60%×rev 82,825), เรวัตร140 5,956 → 61,005, เสรี/office/ayu_trip เท่าเดิม. net 310,486.

**UPDATE 30มิ.ย. รอบ 2 — โอสั่ง "หักน้ำมันคนเหมา" → DONE+deployed net 310,486 → 192,200.61:**
- ปัญหา: FuelTxn เหมา 4 คน **ทุกบิล exclude_from_driver=1 + driver_id=NULL** → `_sum_fuel_cost` (เงื่อนไข driver_id==emp + exclude==False) คืน 0 → ไม่หักเลย. importer ตั้ง exclude=True ทุกบิลตอน import.
- แก้: link driver_id + set exclude_from_driver=0 ให้ **47 บิล** ของ 4 คน (match `driver_raw_name LIKE '%firstname%'` + site=AYU + in-cycle; sanity: distinct raw name=1/คน ไม่หลุด). **match by full_name ไม่ได้** (employee.full_name="นิวัติ" สั้น แต่ FuelTxn.driver_raw_name="นายนิวัติ รัตนเจียมรังษี" เต็ม → ใช้ LIKE).
- recompute (+ office snapshot/restore เหมือนเดิม). **โอเลือก "หักทุกบิลเต็มจำนวน" + "บิลที่ไม่หัก (ถังแรก) จะติ๊กแก้มือเอง"** (ข้อ 1). ผล: นิวัติ 35,195→**6,139** (หัก 29,056), เรวัตร 61,005→**16,333** (หัก 44,672), ธัชชนพล −4,304→**−37,468** (หัก 33,164), เสรี 5,952→**−5,442** (หัก 11,394). office+เที่ยวเท่าเดิมเป๊ะ.
- **ธัชชนพล/เสรี ติดลบหนัก = ตั้งใจชั่วคราว** เพราะหักรวมถังเต็มถังแรก — **โอจะติ๊กบิลถังแรกไม่หักเอง** ผ่าน UI /payroll/18/employee/{id} ปุ่ม toggle-exclude (ดู [[project-fuel-exclude-from-driver]] กฎ first-tank: ลิตรเศษ >80=ถังเต็ม). 47 บิลมีถังเต็มหลายใบต่อคน (ธัชชนพล 267-279ล. 3 ใบ).
- deploy: scp→app_incoming.db→swap.ps1 (integrity ok)→restart. net server 192,200.61 verified, 17 payrun อื่นเท่าเดิม (sum 4,026,576). backup server app.db.bak_before_maofuel_*, local app.db.bak_before_ayu_mao_fuel_20260630_072314.
- **บทเรียนสำคัญ (gsheet→re-import flow):** (1) gsheet เป็น .xlsx-uploaded เปิด gspread ไม่ได้ ("must not be an Office file") + Drive API ปิด → **โอต้อง File→Save as Google Sheets เป็นไฟล์ใหม่ id ใหม่** ก่อน. (2) read gsheet → save เป็น .xlsx (NUMCOLS 9-14 แปลง float) → patch `import_ayu_daily.CYCLES["2026-06"]["file"]` → parse_cycle. (3) **เหมา AYU 4 คน (นิวัติ/เรวัตร/ธัชชนพล/เสรี) = pay_mode `ayu_mao`** (60%×revenue), share=None→0.60. มี tool `set_ayu_self_fuel.py` (self_fuel) แต่ DB ใช้ ayu_mao — โออัปเดตค่าเที่ยวในชีท ≈ 60%×rev อยู่แล้ว แต่ engine ใช้ revenue ตรง. (4) **GOTCHA ยืนยัน 2 อัน:** [a] `petty_itemize --site AYU` recompute → **office 12 คน base=0 → net −1,450 ทุกคน** ต้อง **snapshot office net ก่อน + restore หลัง** (office=copied-net คงที่ รัตนาวดี 40k... รวม 181,400; restore set base/gross/net=snap, zero SS/ded). [b] `import_ayu_daily` wipe ลบเฉพาะ `source==ayu_2026-06` **ไม่ลบ `_xsite`** → 162 แถว xsite เก่าค้าง = DailyJob บวม 1003; ต้องลบ leftover `source=ayu_2026-06_xsite AND created_at<importtime` (g- by created_at split). (5) verify สลิป: เรียก `main.payroll_employee_slip(18,eid,fakereq)` + `payroll_print_all` ตรง (เลี่ยง auth) — render OK ทุกคน 29k-47k chars, print-all 343k (จุดเคยพัง print-all 500 ผ่าน).
- **deploy GOTCHA (ยืนยัน):** `deploy_mvp.sh --with-db` scp app.db ดิบ fail "dest open Failure" (lock) + ยังไม่ทำ wal_checkpoint. วิธีที่ work: [1] local `PRAGMA wal_checkpoint(TRUNCATE)` + `integrity_check`. [2] **scp ไป `app_incoming.db` (ชื่ออื่น) สำเร็จ แม้ทับ app.db ตรงๆ fail.** [3] swap.ps1: integrity_check incoming บน server (ใช้ `"$ok".Trim() -ne "ok"` ไม่ใช่ array -notmatch ที่ buggy) → stop task → rm -wal/-shm → Move-Item ทับ. [4] start task → 8010 UP fresh PID + 8020 archiver UP + public 200. **PS gotcha: `COUNT(*)` ใน inline -Command โดน PS ขยาย glob `*` → เขียน .py แยก scp ไปรัน เสมอ.**

**BIGC "เดือน มิ.ย." = วิ่งงาน พ.ค.1-31 จ่าย 1ก.ค. = payrun #4, cycle 2026-05, draft, net 131,856.29, 11 คน, server.**
- ไฟล์ `6.Jun\BigC\2564Daily Report (04.21).xlsx` ชีท `เดือน06.21` = ข้อมูลวันที่ **พ.ค. (ครบ 1-31, 462 แถว in-cycle)** ไม่ใช่ มิ.ย. (อ่านวันจริง ไม่เชื่อชื่อไฟล์). E(col5)=สถานะงาน (Oatside 141/2BigC 78/2++ 33/2BH 29/ABF 18/รับรถ 11/Homepro 2...) ไม่เชื่อ header "รับตู้/สถานที่".
- **DailyJob BIGC ใน DB = ตรงไฟล์เป๊ะทุกคน** (11 คน trip ตรง; trip รวม 136,300, fuel 18,505.6L/674,911฿) → **ไม่ต้อง re-import**.
- net ในระบบ = **131,856** (ไม่ใช่ 145,356 ที่ความจำเก่าบางไฟล์เขียน — petty itemize 29มิ.ย. แก้ลงเป็น 131,856; เชื่อ DB). คิดด้วย `bigc_monthly` recompute จากเดลี่ (เรทน้ำมัน note "งบ XL − ใช้จริง").
- **ค้าง (รอโอ ตามไฟล์ _BIGC_MAY_FINDINGS):** (1) **เกศศักดิ์107 net −3,226** (d=6 วัน, petty 4,925 > gross 2,787) + **ธนวัฒน์105 net 1,854** (d=6 วัน) → โอต้องบอกว่าทำ 6 วันจริง (เลขถูก) หรือผ่อนผันเต็มเดือน (แก้ days_worked). (2) เรทน้ำมัน BIGC สูตรไหนกันแน่ — โอเคยสั่งให้ลอก "เงินที่ได้" จากชีท รวมเรท แต่ DB ตอนนี้ note เป็น "งบ−ใช้จริง" → ตรวจก่อน recompute. (3) costing ช่อง I จากสถานะงาน = ฝั่งบิล ไม่กระทบ payroll, โอ defer เรท.

**กฎที่ยึด:** ไม่เดาราคา/รอบ/วันทำงาน (กฎเงิน). ทั้ง AYU+BIGC draft ไม่ finalize. DailyJob ทั้งสองไซต์ตรงไฟล์แล้ว = งานที่เหลือเป็นการตัดสิน/ใส่ข้อมูลของโอ ล้วนๆ.

related: [[project-ayu-jun-payroll]], [[project-ayu-daily-import]], [[project-bigc-may-payroll]], [[reference-google-sheets-access]], [[feedback-keep-working-autonomously]]
