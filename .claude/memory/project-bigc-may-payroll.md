---
name: project-bigc-may-payroll
description: "BigC payroll \"เดือน มิ.ย.\" (=วิ่งงาน พ.ค. 1-31, จ่าย 1 ก.ค.) — engine already computes; only import + costing-from-status are new"
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

โอเรียก **"BigC เดือน มิ.ย." = งานที่วิ่งเดือน พ.ค. 1–31, จ่าย 1 ก.ค.** (BigC รอบจ่าย 1→สิ้นเดือน). payrun ในระบบ = #4 cycle_tag `2026-05`, 11 คน, net 110,613.81 (draft, ลอกจากชีท "รวม YK" โอคำนวณมือ, COPY-LOCK).

**โอสั่ง (28มิ.ย. กลางคืน, ก่อนไปนอน):** (1) ให้ระบบคิดค่าขนส่ง(I)เองจากสถานะงาน ไม่ลอกชีท; (2) ให้ engine คำนวณเงินเดือนจากเดลี่จริง (แทน net ที่ลอก) แล้ว reconcile; (3) แยก branch ใหม่; (4) อยากได้หน้ารวม + แยกรายคน.

**ดึงข้อมูลจาก** `Work\Salary\2026\6.Jun\BigC\2564Daily Report (04.21).xlsx` ชีท `เดือน06.21` (อ่านวันที่จริง=พ.ค. ไม่เชื่อชื่อไฟล์). คอลัมน์: A วันที่ B หัวลาก C หาง D ชื่อ **E สถานะงาน** F รหัสสาขา(BH=ไม่มีรหัส) G ที่ส่ง H เลขเอกสาร I ค่าขนส่ง(พี่หวานใส่ ยังไม่เป๊ะ) J ค่าเที่ยวคนขับ(+เงินเดือน9000 หักวันหยุด ผ่อนผันได้-แก้มือ) K ไม่ใช้ L–S น้ำมัน.
**สถานะ E (verified นับจริง พ.ค.):** Oatside 141(=DHL Overflow ของแหลม), 2BigC 78(สาขา ตจว.), 2++ 33(พ่วง), 2BH 29, ABF 18, รับรถ 11, Homepro 2, 1BH 1, 2DV 1. (1BigC=สาขา กทม.; 2++=พ่วง; คิดค่าขนส่ง=สาขาไกลสุด+ค่าพ่วงตามจำนวนพ่วง). **ยังไม่มีตารางเรท** — โอบอก "เดี๋ยวค่อยมาคุยเรื่องกำหนดเรท".
**น้ำมัน:** ตอนนี้เอาเลขจากไฟล์ `เรทน้ำมันเดือนพฤษภาคม69.xlsx` ชีท `รวมเรท` (เรททำได้/จำนวนลิตร/เงินที่ได้ per head-plate) มาโชว์แทน ยังไม่ตรวจ/คำนวณจริง.

**กุญแจสำคัญ (verified ในโค้ด):** engine `payroll.py` **มี `bigc_monthly` อยู่แล้วและคำนวณจาก DailyJob จริง**: base 9000−(9000/days)×missed + `_sum_trip_fees`(อ่าน DailyJob.trip_fee_driver by driver_id) + fuel-rate rebate ฿16/L (`_compute_bigc_fuel_rebate`). แปลว่า "ให้ engine คำนวณจากเดลี่จริง" = ทำได้เลยเมื่อมี DailyJob BigC + link driver_id. **net ไม่ขึ้นกับ revenue(I)** — costing I เป็นฝั่งวางบิล ไม่ใช่ payroll (ต่างจาก lcb_mao ที่ใช้ 60% ของ revenue).

**สถานะตอนเริ่ม:** DailyJob BigC = 0 แถว (LCB 1116). reverse-check r0 ของไฟล์: Σrevenue=31,070.03 Σtrip=136,300.

**COORDINATION (สำคัญ):** มี **อีก session รันคู่ขนานอยู่จริง** บน branch `feat/bigc-daily-import` (ไฟล์ถูกแก้ 00:15 ห่างจากผมเช็ค ~75วิ). เขาสร้าง **import parse layer** `tools/import_bigc_daily.py` (header-merge+column-map+row_to_record TDD ผ่าน) + plan 860 บรรทัด — แต่ `write_cycle` ยังไม่เสร็จ (Task 3) และสเปคเขา **ไม่คิด payroll** (out of scope). งานสองฝั่ง **เติมกัน ไม่ซ้ำ**: เขา=import (prerequisite), payroll engine ฝั่ง BigC **เขียนไว้แล้ว**. → ห้ามแย่งเขียน app.db พร้อมกันตอนโอหลับ. ของใหม่จริงเหลือแค่ **costing-from-status (I, ฝั่งบิล) + ตารางเรท (โอ defer)**.

**BUG พบใน parse layer เขา:** map E(idx4)→`origin`("รับตู้") ผิด — E จริงคือ **สถานะงาน** (Oatside/2BigC/...). header แถวบน idx4="รับตู้" แต่ข้อมูลเป็น status code. ถ้า costing ใช้ E ต้องแก้ตรงนี้ก่อน (แจ้ง/ประสาน session อื่น ไม่ไปแก้ไฟล์เขาชนกัน).

**UPDATE 29มิ.ย. เช้า (import ของ session อื่น merge main แล้ว 2,381 DailyJob):**
- เพิ่มคนใหม่ 3 (โอยืนยัน): **emp162 ชรินทร์ ใยสอาด, emp163 โกสินทร์ สรีกันยา, emp164 วิทัศน์ คงรอด** (full name+plate จากไฟล์ รวมเรท); tool `tools/bigc_add_link_drivers.py` (reuse `_bigc_link_report.first_name` + `import_bigc_daily.make_engine`)
- **ผูก driver_id ครบ 2,272 แถว BigC, unlinked=0** (คนใหม่ 3: 54/42/14 เที่ยว ตรงชีต)
- **⛔ recompute payrun #4 จากเดลี่ = ผิดมหาศาล net 489,043 vs ของจริง 110,613.81 → ไม่เขียนทับ** (payrun draft ไม่ใช่ finalized แต่เป็น copied-net, recompute จะทับได้แต่ผลผิด). **สาเหตุ = เรทน้ำมัน BigC พัง**: `_compute_bigc_fuel_rebate` คิด residual×16฿ จากข้อมูลน้ำมันที่ import ออกมาเป็นหมื่น (เกรียงไกร +37,000 ทั้งที่จริง −1,654). ค่าเที่ยว(ΣJ) เกือบตรง รวม YK (ต่างนิดหน่อย โอบอกพี่หวานใส่ไม่เป๊ะ). **payroll BigC อัตโนมัติยังใช้ไม่ได้จนแก้เรทน้ำมัน** — ถามโอ: เรทน้ำมันใช้สูตร budget−ใช้จริง หรือลอกเลข "เงินที่ได้" จากชีท รวมเรท ต่อคน?
- 3 สงสัยลาออก(109/110/113): พ.ค. 0 trip. **เงินประกัน BigC ทั้งไซต์=0 ในระบบ (ไม่เคย import)** → DB ตัดสินไม่ได้, ต้องดูชีทสดย่อย/SSO; ยังไม่ตัด/ไม่คืน รอโอ
- backup: `app.db.bak_before_bigc_may_payroll_20260629_070454`; branch `feat/bigc-may-payroll`; rollback คนใหม่=delete emp 162/163/164

related: [[project-multisite-payroll-onboard]] [[project-dhl-overflow-rate]] (Oatside=DHL Overflow), [[feedback-keep-working-autonomously]], [[project-deposits-overview-page]] (บทเรียน parallel session git add ดูดโค้ด), [[project-bigc-daily-import]] (prerequisite import)
