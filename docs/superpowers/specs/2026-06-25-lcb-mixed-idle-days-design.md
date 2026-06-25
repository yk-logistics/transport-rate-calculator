# LCB ลูกผสม — นับวันรถจอดเข้าฐาน + เตือนวันรอลงราคา

วันที่: 2026-06-25
Branch: `fix/lcb-mixed-idle-days`
สถานะ: design approved (โอ ยืนยัน 2026-06-25)

## ปัญหา

ขณะตรวจเงินเดือน LCB รอบ มิ.ย. 2569 (16/05–15/06, payrun #2, tag 2026-06) พบว่า
pay_mode `lcb_mixed` คิดเงินฐาน/ค่าดูแลของฝั่งเที่ยวด้วยตัวหารผิด และมีวันทำงาน
บางประเภทตกหล่นจากการคิดเงิน รวม 3 จุด:

1. **ตัวหารฐานผิด** — branch `lcb_mixed` ใน `payroll.py` คิด
   `base × (n_trip / days_in_month)` ใช้แค่ "วันเที่ยว" เป็นตัวหาร ทั้งที่
   "วันรถจอด" (บริษัทไม่มีงาน คนขับมาแต่ไม่มีงานวิ่ง) ก็ต้องได้เงินฐานด้วย
   ตาม policy ของโอ → คนขับ mixed ได้ฐานน้อยกว่าที่ควร

2. **`_count_work_days` จับ "รถจอด" ไม่ครบ** — `is_company_no_work` ปัจจุบันจับแค่
   token `รถจอด / รองาน / ไม่มีงาน / idle` แต่ในข้อมูลจริงมี status อื่นที่โอ
   ยืนยันว่าเป็น "รถจอด/วันทำงาน" เช่นกัน: `รถอุบัติเหตุ` (15), `รถซ่อม` (3),
   `DHL Overflow` (19, เป็นชื่อลูกค้า) → วันพวกนี้ตอนนี้ไม่ถูกนับเป็นอะไรเลย

3. **วันรอลงราคา ตกหล่นเงียบ** — 25 วันที่ status_code เป็นรหัสลูกค้า
   (KAO/KLND/NHL/Nippon ฯลฯ) แต่ revenue=0 เพราะพี่ตาลยังไม่ได้ลงราคา
   วันพวกนี้ revenue=0 → ระบบมองข้าม → เงินวันนั้นหาย ทั้งที่คนขับน่าจะวิ่งจริง
   ต้อง "เตือน" ให้ไปเติมราคา ไม่ใช่เดาแทน

### ground truth (จาก app.db, LCB cycle 2026-06, 609 แถว)

status_code ของวัน revenue==0:
```
190  รถจอด          → company_no_work (ได้ฐาน)
 19  DHL Overflow   → ชื่อลูกค้า = วันทำงาน (ได้ฐาน)   [เพิ่มใหม่]
 15  ลา / ไม่พร้อม   → leave (ไม่ได้ฐาน)
 15  รถอุบัติเหตุ    → company_no_work (ได้ฐาน)        [เพิ่มใหม่]
  3  รถซ่อม         → company_no_work (ได้ฐาน)        [เพิ่มใหม่]
 25  KAO/KLND/NHL/Nippon (รหัสลูกค้า) → "รอลงราคา" = warning  [จุด 3]
```

## นโยบายที่โอยืนยัน

- วันรถจอด/อุบัติเหตุ/ซ่อม/DHL Overflow = **ได้เงินฐาน** (นับเข้าตัวหาร)
- วันลา / ไม่พร้อม = **ไม่ได้ฐาน** (เดิมถูกอยู่แล้ว)
- ตัวหารฐานใหม่ = `(วันเที่ยว + วันรถจอด) / จำนวนวันใน cycle`
- 25 วันรหัสลูกค้า revenue=0 = **นับเป็นวันทำงานที่รอลงราคา** → ไม่เดาราคา
  แต่ทำ warning ฝังใน **หน้าเงินเดือนจริงใน MVP** ให้พี่ตาลไล่เติม
- NET ของแต่ละคนจะขยับ — ต้องเทียบเก่า/ใหม่ก่อน finalize

## ขอบเขต

### จุด 1 — ตัวหารฐาน/ค่าดูแล ใน branch `lcb_mixed`
ไฟล์: `app/services/payroll.py` (branch `lcb_mixed`)
- เดิม: `n_trip / days_in_month`
- ใหม่: `(n_trip + n_idle) / days_in_month` โดย `n_idle = calc.days_company_no_work`
- ทั้ง `base_salary_earned` และ `care_allowance_earned`
- อัปเดตข้อความ `calc.note` ให้สะท้อนตัวหารใหม่

### จุด 2 — ขยาย `is_company_no_work` ใน `_count_work_days`
ไฟล์: `app/services/payroll.py` (`_count_work_days`)
- เพิ่ม token จับเป็น company_no_work: `อุบัติเหตุ`, `ซ่อม`, `dhl overflow`
  (คง `รถจอด/รองาน/ไม่มีงาน/idle` เดิมไว้)
- "dhl overflow" ต้อง match แบบวลี (มีช่องว่าง) — ตรวจจาก status_code ทั้งสตริง
  ไม่ใช่ token เดี่ยว เพราะ tokenizer แตก "dhl" กับ "overflow" แยกกัน

**impact จริง (เช็คแล้วกับ app.db):** คนที่มีวัน อุบัติเหตุ/ซ่อม/DHL-Overflow
revenue=0 ในรอบ payrun#2 = 4 คน ทุกคน LCB:
emp94 สันติพงษ (lcb_trip, 15 วันอุบัติเหตุ), emp87 เนื้อ (lcb_trip, 2 ซ่อม),
emp100 สุภาพ (lcb_trip, 1 ซ่อม), emp85 รัฐภูมิ (lcb_mao, 0 ในรอบ).

**ทำไม net ไม่ควรเปลี่ยนสำหรับ lcb_trip/lcb_mao/lcb_monthly:** branch พวกนี้คิดฐาน
แบบ `base − (base/days)×missed` โดย `missed = leave + absent + not_employed`
**ไม่รวม company_no_work** → สลับวันจาก worked↔idle ไม่กระทบฐาน. แต่ต้องพิสูจน์
ด้วย regression test (snapshot net 18 คนเป็น golden — ดูภาคผนวก).

- ⚠️ `_count_work_days` ใช้ร่วมทุก pay_mode → regression ต้องครอบทุก site:
  net ทุกคน (ยกเว้น mixed) คงเดิม. ถ้ามีคนเปลี่ยน = เจอ logic อื่นที่พึ่ง
  `days_worked` ทางอ้อม → หยุดแล้วรายงานโอ ไม่ปล่อยผ่าน

### จุด 3 — เตือนวันรอลงราคา ในหน้าเงินเดือน MVP
- helper `find_pending_price_days(session, emp_id, start, end, site)` คืน list ของ
  DailyJob ที่: `revenue_customer<=0 AND trip_fee_driver<=0 AND` status ไม่เข้า
  leave/absent/company_no_work (= มี status เป็นรหัสลูกค้า/อื่นที่ไม่ใช่หยุด)
- แสดงในหน้า payrun detail (template MVP) เป็นแถบเตือนสีส้มต่อคน:
  "⚠ รอลงราคา N วัน: <วันที่> (<status_code>)"
- ไม่คิดเงินวันพวกนี้ ไม่เดาราคา — เป็น read-only guard

## การตรวจย้อนกลับ (preflight / กฎเงิน)

- **TDD**: เขียน test ก่อนเขียน implementation
  - พชร(86): net ใหม่ = net เก่า + (base+care)×(n_idle/31)
  - สุรเดช(91): เช่นเดียวกัน
  - regression: คน LCB อื่น 16 คน — net คงเดิม (snapshot ก่อน/หลัง)
- **Backup** `app.db` ก่อน recompute payrun #2
- **เทียบตาราง** net เก่า/ใหม่ทุกคนในรอบ ก่อน finalize — โอเป็นคนกด finalize
- หน้าเว็บเทียบมือ (`reports/lcb_mixed_compare_2026-06.html`) regen ด้วยเลขใหม่

## ไม่ทำรอบนี้ (YAGNI)

- ไม่ทำ UI กรอกราคาในตัว warning — พี่ตาลเติมในหน้า daily เดิม
- ไม่แตะ site อื่น (BIGC/AYU) — เปลี่ยน `_count_work_days` กระทบ logic ร่วม แต่
  token ที่เพิ่มเป็นคำเฉพาะ LCB; ยังต้อง regression ครอบทุก site
- ไม่ finalize ในงานนี้ — แค่ recompute draft + เทียบเลข

## ภาคผนวก — snapshot net ก่อนแก้ (golden สำหรับ regression)

payrun #2 (2026-06), 18 คน, net ปัจจุบัน:
```
emp 84 พัฒิยะ   lcb_mao      -1,478.10   (worked22 idle12)
emp 85 รัฐภูมิ   lcb_mao       7,921.27   (31 16)
emp 86 พชร      lcb_mixed    12,092.10   (31 11)  ← จะเพิ่ม
emp 87 เนื้อ     lcb_trip     14,040.00   (31  5)
emp 88 นันท     lcb_trip     13,178.00   (31  8)
emp 89 ประจ     lcb_trip     12,728.00   (31  9)
emp 90 สุวิ     lcb_trip     19,757.75   (31 11)
emp 91 สุรเดช    lcb_mixed    13,119.57   (31 10)  ← จะเพิ่ม
emp 92 ปกรณ์    lcb_mao      19,518.00   (31  8)
emp 93 พิชิ     lcb_mao       6,129.68   (28  9)
emp 94 สันติพงษ  lcb_trip      6,128.00   (31 11)
emp 95 ชยุต     lcb_trip      9,850.32   (29 12)
emp 96 อภิช     lcb_trip      8,647.17   (30 12)
emp 97 นิพล     lcb_mao       7,894.80   (31 11)
emp 98 ณัฐว     lcb_mao      14,747.88   (31 11)
emp 99 วิโรจน์   lcb_mao      19,926.12   (31  8)
emp100 สุภาพ    lcb_trip     62,261.15   (31 12)
emp101 วราวุฒิ   lcb_mao      22,049.96   (24  7)
```
หลังแก้: เฉพาะ emp86, emp91 (mixed) เปลี่ยน. ที่เหลือต้องเท่าเดิมเป๊ะ.
