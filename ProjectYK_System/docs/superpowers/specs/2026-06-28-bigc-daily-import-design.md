# BIGC Daily Import — Design Spec

วันที่: 2026-06-28 · เจ้าของงาน: โอ (พงษกาญจน์) · ผู้ทำ: Claude Code (Opus 4.8)
Repo: `Project YK` · branch งานนี้: (สร้างใหม่ก่อนเริ่ม — ห้ามทำบน main)

## 1. เป้าหมาย (scope แคบ ชัด)

นำข้อมูล **เดลี่รายเที่ยวของ BIGC** เข้าระบบเป็น `DailyJob` ทีละแถว (เหมือนที่ LCB มีอยู่แล้ว) เพื่อให้
หน้า `/daily` และ CFO `/finance/revenue` เห็นข้อมูล BIGC ได้

**นี่คือ "ข้อ 2" ของ handoff เท่านั้น** — ไม่รวม "ข้อ 1" (ให้ engine คิดเงินเดือน BIGC เอง)

### อยู่นอก scope (จะไม่ทำในงานนี้)
- ❌ ไม่คิด/ไม่แก้สูตรเงินเดือน BIGC — payrun BIGC 6 รอบที่ลอก net จากแบงค์ไว้ (COPY-LOCK) **คงเดิมทุกบาท**
- ❌ ไม่แตะ LCB และ AYU
- ❌ ไม่ยุ่ง petty/สดย่อย, ไม่ทำ fuel cross-check กับ Caltex
- ❌ ไม่เปลี่ยน schema (ทุกคอลัมน์ที่ต้องใช้มีใน `DailyJob`/`FuelTxn`/`DailyJobFee` อยู่แล้ว)

## 2. สถานะปัจจุบัน (verified จาก app.db, 2026-06-28)

- `DailyJob` มีเฉพาะ **LCB** = 1116 แถว (source: `lcb_may-jun2026` 608, `reimport_lcb_daily` 508). **BIGC = 0 แถว**
- payrun BIGC ที่มีอยู่ (ทั้งหมด status=draft, net ลอกจากแบงค์):
  | run | cycle_tag | items | net |
  |-----|-----------|-------|-----|
  | #10 | 2025-12 | 8 | 116,187.48 |
  | #11 | 2026-01 | 8 | 127,003.76 |
  | #12 | 2026-02 | 9 | 134,236.04 |
  | #17 | 2026-03 | 9 | 115,918.99 |
  | #3  | 2026-04 | 11 | 118,136.94 |
  | #4  | 2026-05 | 11 | 110,613.81 |

  → งานนี้ **ไม่แตะตารางนี้เลย** (import ลง DailyJob คนละตาราง)

## 3. ไฟล์ต้นทาง (verified — อ่านวันที่จริงในเซลล์ ไม่เชื่อชื่อไฟล์)

โครง BIGC = **ไฟล์ละเดือน**, primary file ชื่อ `2564Daily Report (04.21).xlsx` ในแต่ละโฟลเดอร์เดือน
**เก็บข้อมูลของเดือนก่อนหน้า** (BIGC รอบจ่าย = 1 → สิ้นเดือน, cycle_tag = YYYY-MM ของเดือนนั้น)

| โฟลเดอร์ | ไฟล์ | ชีต | ช่วงวันที่จริง | cycle_tag | source tag |
|---|---|---|---|---|---|
| `2026/1.Jan/BigC` | `2564Daily Report (04.21).xlsx` | `เดือน06.21` | 2025-12-01..31 | 2025-12 | `bigc_2025-12` |
| `2026/2.Feb/BigC` | เดียวกัน | `เดือน06.21` | 2026-01-01..31 | 2026-01 | `bigc_2026-01` |
| `2026/3.Mar/BigC` | เดียวกัน | `เดือน06.21` | 2026-02 (มีแถวหลง 01-31) | 2026-02 | `bigc_2026-02` |
| `2026/4.Apr/BigC` | เดียวกัน | `เดือน06.21` | 2026-03-01..31 | 2026-03 | `bigc_2026-03` |
| `2026/5.May/BigC` | เดียวกัน | `เดือน06.21` | 2026-04-01..30 | 2026-04 | `bigc_2026-04` |
| `2026/6.Jun/BigC` | เดียวกัน | `เดือน06.21` | 2026-05-01..31 | 2026-05 | `bigc_2026-05` |

**มิ.ย. (2026-06): ยังไม่มีไฟล์** — เดลี่ BIGC ล่าสุดจบ 31 พ.ค. (ไฟล์ มิ.ย.จะอยู่ในโฟลเดอร์ `7.Jul` ที่ยังไม่ถูกสร้าง
เพราะเดือน มิ.ย.ยังไม่จบ). โอยืนยัน: **import 6 เดือนที่มีก่อน รอ มิ.ย.ไว้ทีหลัง**

> หมายเหตุ filter: importer กรองตามช่วง **วันที่ 1 → วันสุดท้ายของเดือน cycle_tag** เสมอ → แถวหลงถูกตัดทิ้ง
> อัตโนมัติ ไม่ปนรอบ. ตรวจแล้ว: ไฟล์ 3.Mar มี 2026-02 = 373 แถว (เนื้อ) + 2026-01-31 = 2 แถวหลง → cycle_tag
> `2026-02` ถูกต้อง, 2 แถวหลงถูกตัด

## 4. โครงสร้างชีต BIGC (ต่างจาก LCB — หัวตาราง 2 แถว)

- **r0** = แถวยอดรวม ("Transport Daily Report 2569", "ยอดเงิน", ผลรวม ค่าขนส่ง/ค่าเที่ยว) — ใช้เป็นตัวเทียบ reverse-check
- **r1 + r2** = หัวตาราง **2 แถวซ้อน** (merged cell) — ต้องรวม top+bottom เป็นชื่อคอลัมน์เดียว
- **r3+** = ข้อมูล

### column map (verified, index 0-based)

| col | หัวรวม (top / bottom) | → DailyJob field | หมายเหตุ |
|----:|---|---|---|
| 0 | วันที่ / รับงาน | `work_date` | กรองให้อยู่ในรอบ |
| 1 | ทะเบียน / รถหัวลาก | `plate_no_raw` | |
| 2 | ทะเบียน / หางลาก | `tail_plate_raw` | |
| 3 | ชื่อ-นามสกุล | `driver_raw_name` | ชื่อต้นอย่างเดียว |
| 4 | รับตู้ / สถานที่ | `origin` | |
| 5 | รหัส / สาขา | `store_code` | |
| 6 | ที่ส่งสินค้า / สถานที่ | `destination` | |
| 7 | เลขที่ / เอกสาร | `doc_no` | |
| 8 | ค่าขนส่ง / โดยประมาณ | `revenue_customer` | **รายได้** |
| 9 | ค่าเที่ยวพขร / จุดพ่วง-BH | `trip_fee_driver` | **เงินคนขับ** |
| 10 | เงินเดือน | (ไม่ import ลงแถว) | salaried marker; รายแถวว่าง |
| 11 | น้ำมันที่ / กำหนด | (ข้าม) | ข้อความกำหนดน้ำมัน |
| 12 | เลขไมล์ / ตอนเติม | `mile_snapshot` | |
| 13 | จำนวน / น้ำมันลิตร | `fuel_liter` | → FuelTxn |
| 14 | ราคาน้ำมัน / ฿ per L | (คำนวณ price_per_liter) | |
| 15 | จำนวน / เงินบาท | `fuel_amount` | → FuelTxn |
| 16 | เรท / น้ำมัน | `fuel_rate_km_per_l` | เรท กม/ล |
| 17 | จำนวน / น้ำมันทำได้ | (ข้าม) | derived ในชีต |
| 18 | หมายเหตุ | `remark` | |

หาคอลัมน์ด้วย **ข้อความหัว** (เลียน `find()` ของ LCB importer) ไม่ผูก index ตายตัว → กันไฟล์ที่คอลัมน์เลื่อน
critical columns ที่ต้องเจอ ไม่งั้น block: `work_date`, `plate`, `driver`, `revenue`, `trip_fee`

## 5. การเขียนลง DB (ต่อแถวข้อมูล)

1. **DailyJob** (`site_code="BIGC"`, `source=bigc_<cycle_tag>`) — ทุกแถวที่มี `work_date` ในรอบ
   (รวมแถวรถจอด rev=0/trip=0 — เป็นบันทึกรายวันจริง เหมือน LCB)
2. **FuelTxn** — สร้างเมื่อ `fuel_liter>0` หรือ `fuel_amount>0`:
   - `site_code="BIGC"`, `txn_date=work_date`, `plate_no_raw`, `driver_raw_name`, `liter`, `amount`,
     `price_per_liter = amount/liter`, `daily_job_id`, `source=bigc_<cycle_tag>`
   - **`exclude_from_driver=True`** เสมอ — BIGC จ่ายเงินเดือน ไม่หักน้ำมันรายเที่ยว (ทำให้เจตนา "ไม่หักคนขับ"
     ชัดและตรวจสอบได้)
3. **DailyJobFee** — BIGC ไม่มีคอลัมน์ค่าธรรมเนียมแยก (ยกตู้/ผ่านลาน/OT ฯลฯ) ในชีตนี้ → ปกติจะไม่สร้าง
   (เผื่ออนาคตเจอคอลัมน์ค่าธรรมเนียม ค่อยเพิ่ม)

ค่าตัวเลขทำความสะอาด: `#DIV/0!`, `#N/A`, `-`, `,` → 0 / "" (เลียน `_float`/`_str` ของ LCB importer)

## 6. ชื่อคนขับ → emp_id (ทำหลัง import, ไม่เดา)

- เก็บ `driver_raw_name` ดิบทุกแถวเสมอ → หน้า/CFO ใช้ได้ทันทีโดยไม่ต้องรอ link
- การผูก `driver_id`: ทำ first-name → emp_id map **เฉพาะพนักงาน site=BIGC** (กันชนชื่อต้นซ้ำข้ามไซต์)
- หลัง import: รายงานรายชื่อ **unlinked** ให้โอยืนยันตัวสะกด/ตัวซ้ำ ก่อนผูกจริง — **ไม่เดาการ map**
- 11 ชื่อในเดือน พ.ค.: ชรินทร์, ณัชพน, ธนวัฒน์, มานพ, วิทัศน์, สมประสงค์, สมัย, เกรียงไกร, เกศศักดิ์,
  เสกสรร, โกสินทร์ (เดือนอื่นอาจต่างเล็กน้อย)

## 7. ลำดับรัน (ปลอดภัย + กันซ้ำ + reverse-check)

1. **branch ใหม่** ก่อนเริ่ม (ห้ามบน main)
2. **backup `app.db`** ก่อนเขียนใด ๆ
3. **dry-run ทุกเดือน** → นับแถว + ผลรวม ค่าขนส่ง/ค่าเที่ยว ต่อ cycle (ยังไม่เขียน DB)
4. เทียบ reverse-check ต่อเดือน — ต้องตรงยอดในแถว r0 ของไฟล์. ตัวอย่าง **พ.ค. (2026-05)**:
   - `SUM revenue_customer` ต้อง = **31,070.03**
   - `SUM trip_fee_driver` ต้อง = **136,300**
5. โอดูตัวเลข dry-run โอเค → เขียนจริงทีละเดือน (`--wipe-prior` ลบเฉพาะ source tag เดือนนั้น)
6. verify: `/daily` เลือก BIGC เห็นแถว, `/finance/revenue` เห็นรายได้ BIGC
7. deploy (Tailscale; restart kill by 8010-PID + YK_MVP path — อย่าใช้ `\.venv` filter กว้าง)

### กันซ้ำ (idempotent)
- source tag 1 ตัว/เดือน (`bigc_<cycle_tag>`)
- `--wipe-prior` ลบเฉพาะ `source = tag เดือนนั้น` (+ DailyJobFee/FuelTxn ที่ผูก daily_job_id) ก่อนเขียนใหม่
- **ลบด้วย source tag เท่านั้น** ไม่ลบด้วย work_date/site (บทเรียนเก่า: filter กว้างเคยลบงานจริง)
- คนละ source + คนละ site → **ไม่กระทบ LCB เด็ดขาด**

## 8. โครงโค้ด

- ไฟล์ใหม่: `ProjectYK_System/tools/import_bigc_daily.py`
  - เลียน `import_lcb_may_jun2026_xlsx.py` (column-map by header, `_date/_float/_str`, `--dry-run/--wipe-prior`)
  - ต่าง: รวมหัว 2 แถว, รับ `--cycle YYYY-MM` (เลือกเดือน) → map ไป folder/cycle window/source tag,
    set `FuelTxn.exclude_from_driver=True`
- ไม่แตะ `models.py`, `main.py`, services, templates (ไม่มี schema change)

## 9. เกณฑ์ว่าเสร็จ (verifiable)

- [ ] dry-run 6 เดือน: ผลรวม revenue/trip ตรงยอดในไฟล์ทุกเดือน
- [ ] เขียนจริง: `DailyJob` BIGC > 0 ต่อ cycle, นับแถวตรง dry-run
- [ ] payrun BIGC 6 รอบ net **ไม่เปลี่ยน** (เทียบก่อน/หลัง = เท่าเดิมทุกบาท)
- [ ] LCB DailyJob ยัง = 1116 (ไม่ถูกแตะ)
- [ ] `/daily` + `/finance/revenue` แสดง BIGC
- [ ] รายงาน unlinked driver names ให้โอ
