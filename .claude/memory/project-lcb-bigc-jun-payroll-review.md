---
name: project-lcb-bigc-jun-payroll-review
description: "30 มิ.ย. full review of LCB#2 + BigC#4 before โอ finalizes — both reconcile to source files; open items are HR decisions not bugs + LCB slip fuel-date design"
metadata: 
  node_type: memory
  type: project
  originSessionId: a7be03e9-a1b6-49f9-babb-fcf28b790466
---

**30 มิ.ย. (โอ ไปอาบน้ำ สั่ง "ตรวจทาน LCB+BigC เงินเดือนทั้งหมด"):** read-only audit ทั้ง 2 ไซต์ vs ground-truth ไฟล์ มิ.ย. ใน `Work/Salary/2026/6.Jun/`. **ไม่แตะ DB/เงิน** — รายงานให้โอตัดสิน.

**สถานะ DB จริง (verified live local app.db; net เคลื่อนตั้งแต่ memory เก่า เพราะ commit fbb4830 LCB per-trip + 5812d9e KB-before-60%):**
- **LCB#2** (cycle 2026-06, 16/5–15/6, draft, 18 คน) net **271,074.17** (เก่า 266,057 → +5,016 จาก 2 commit นั้น, ถูกต้อง).
- **BigC#4** (cycle 2026-05, "เดือน มิ.ย." วิ่ง พ.ค.1–31, draft, 11 คน) net **126,859.00**.

**BigC#4 — reconcile เป๊ะ:**
- ค่าเที่ยว(J) ตรงไฟล์ `2564Daily Report (04.21).xlsx` ชีท `เดือน06.21` **ทั้ง 11 คน** (สมประสงค์18,350/ชรินทร์18,300/เกรียงไกร18,000/ณัชพน17,600/เสกสรร15,400/มานพ15,200/สมัย14,000/โกสินทร์13,850/ธนวัฒน์2,200/วิทัศน์2,200/เกศศักดิ์1,200).
- **เรทน้ำมัน(fuel_rate_income) = "เงินที่ได้" คอลัมน์ G ชีท `รวมเรท` (เรทน้ำมันเดือนพฤษภาคม69.xlsx) เป๊ะทั้ง 11** → ยืนยันสูตร = ลอกเลข G ต่อหัว ไม่ใช่ budget−ใช้จริง (RESOLVED open item เก่า). ติดลบได้ (สมประสงค์−265, เกศศักดิ์−155 = เรททำได้ต่ำกว่าเกณฑ์16).
- petty ตรงชีท `สดย่อยวังน้อย.xlsx` ชีท `MAY 26` คอลัมน์ O ทั้งหมด (มานพ12,000/เกรียงไกร9,000/สมประสงค์9,500/...เกศศักดิ์4,925/ธนวัฒน์1,000).
- **11 ชื่อในชีท = 11 คนใน payrun, unlinked=0**.
- **2 open = HR ไม่ใช่บั๊ก:** (1) **ธนวัฒน์105 net 1,853.90** — ชีทมี 6 วัน (วิ่งจริง 1–3/5 ค่าเที่ยว, 4–6/5 รองาน/ต่อเนื่อง) DB d=6 ตรงชีท. (2) **เกศศักดิ์107 net −4,091.80** — ชีทมี 6 วันแต่ 3 วันแรก(1–3/5)="ลาหยุด", วิ่งจริงวันเดียว 4/5 (4 เที่ยว 1,200), 5–6/5 ส่งต่อ/รองาน; DB d=3/lv3/ab25 → gross เล็ก petty 4,925>gross = ติดลบ. **โอต้องตัดสิน: จ่าย prorate ตามจริง (ปัจจุบัน) หรือผ่อนผัน/ยกยอด petty เกศศักดิ์**. ทั้งคู่เลขสืบจากชีทได้หมด ไม่มีบั๊กคำนวณ.

**LCB#2 — reconcile เป๊ะ:**
- trip driver (ค่าเที่ยว/พิเศษ/OT เข้าเงินตรง): ชยุต/นันทสิทธิ์/ประจัก/สันติพงษ์/สุวิทย์/อภิชาติ/เนื้อ ตรงชีท `วางบิล YK VOLVO.xlsx` ชีท `Daily` (AD/AF/AG) **ทั้งหมด**. mixed (พชร/สุรเดช) trip-day portion + special/OT ตรง; mao-day → fuel_share (60%×rev−KB).
- petty ตรงชีท `JUN 26` คอลัมน์ O ทั้งหมด (พิชิต17,879/เนื้อ10,500/พัฒิยะ10,270/...). **วันชัย 2,000 ในชีทแต่ไม่อยู่ payrun = carry ถูกต้อง** (ลาออก 1/5, หักรอบหน้า).
- mao day-count DB ต่างจากชีท (ชีททุกคน 31) เพราะ engine นับลา/รถจอด (พัฒิยะ22/พิชิต28/วราวุฒิ24) — ยังไม่ตรวจรายวันลึก แต่ trip/petty/fuel ตรง.

**LCB SLIP FUEL-DATE (โอสั่งแก้ + เป็น design — รอ approve):** โออยากให้สลิปโชว์น้ำมัน "วันที่เติมจริง" อ้าง `Y2026-น้ำมันคาลเท็ก(-).xlsx`. ปัจจุบัน `_slip_body.html` โชว์น้ำมันใต้แถว **DailyJob.work_date** (บรรทัด r.fuel_amount). พบ: **74/384 บิล (19%) fuel `FuelTxn.txn_date` = work_date − 1 วัน เป๊ะ** (ที่เหลือ delta=0); `DailyJob.fuel_date`(AC) ว่าง 0/384 → real fill date เชื่อได้ตัวเดียว = `FuelTxn.txn_date`. ไม่มี txn หลุดนอกรอบ. **feature เก่า [[project-slip-merge-fuel-same-fill]] (cb18b37, บน main) รวม B7+B20 ตาม txn_date อยู่แล้ว แต่ยังโชว์ใต้ work_date ของ DailyJob** → ต้องแก้ให้ key การแสดงผลตาม txn_date จริง. display-only ไม่แตะเงิน (fuel_cost_self คงเดิม).

**⚠️ SERVER LCB#2 ahead of local (พบตอน probe ก่อน deploy) — local STALE:** server net **276,871.37** vs local 271,074.17. ต่างที่ **ปกรณ์92 (+2,898.60 net→23,734.40) + ณัฐวุฒิ98 (+2,898.60→19,948.50)** = +5,797.20; ทั้งคู่ gross เพิ่ม (revenue +4,831 ×0.6) จาก session อื่น/โอ เติม revenue บน server. **server ตรง source sheet** (ณัฐวุฒิ rev−KB 131,677 = ชีท Daily เป๊ะ, ปกรณ์ 121,538 = 122,418−KB880). → local เก่า, **ห้าม push local DB ทับ server** (จะ revert 5,797). LCB reconcile ยังจริง แค่ที่เลข server ที่สูงกว่า. live LCB#2 ที่โอจะ finalize = 276,871.37.

**DONE 30มิ.ย. คืน — 3 งาน deploy แล้ว (โอสั่งช่วงตรวจทาน):**
1. **ลบ นาย/นาง/นางสาว ออกจากชื่อคนขับทุกคนทุกไซต์** (โอเลือก "ลบหมด"): 100/170 ชื่อ, run บน server DB ตรงๆ (ไม่ push local กัน clobber LCB#2), net guard NONE moved, backup app.db.bak_before_strip_title_*; tool scratchpad strip_name_prefix.py (arg=db path). ปกรณ์ เดิมไม่มีนาย → ตอนนี้ทุกคนเหมือนกัน.
2. **สลิปโชว์น้ำมันตามวันเติมจริง** (commit main df75121) — ดู [[project-slip-fuel-fill-date]] (สร้างใหม่).
3. **fix grid header-filter ไม่ apply เมื่อเปลี่ยนชุดไม่ล้างก่อน** (commit main b8a4d2f) — ดู [[project-grid-header-filter-fix]] (สร้างใหม่).
deploy: code ผ่าน deploy_mvp.sh --markers "refreshFilter,fuel_lines_by_job" (ไม่ --with-db, DB ไม่แตะ), verified live pid fresh+archiver+200; name-strip รันบน server DB แยก.

related: [[project-jun-payroll-ayu-bigc-status]], [[project-slip-fuel-fill-date]], [[project-grid-header-filter-fix]], [[project-lcb-jun-audit-round2]], [[project-bigc-may-payroll]], [[feedback-slip-fuel-must-reconcile]]
