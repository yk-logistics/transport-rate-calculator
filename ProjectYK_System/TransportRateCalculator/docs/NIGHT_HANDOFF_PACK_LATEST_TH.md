# Night Handoff Pack (เช้า)

อัปเดตล่าสุด: 2026-05-08 (Night UX bar + checklist)  
ฐานข้อมูลอ้างอิงจากรายงานล่าสุดใน `reports/` ของ repo นี้

---

## 1) Checklist เช้าแบบ 10 นาที

1. เปิดไฟล์สรุปหลัก 2 ไฟล์:
   - `reports/audit_bigc_2026-03_recheck_mminus1_after_unresolved_safe/summary.json`
   - `reports/preflight_payrun_LCB_2026-03_run9.json`
2. เข้าหน้า payroll ของรันที่มีความเสี่ยง:
   - BIGC `run_id=10` (`/payroll/10`)
   - LCB `run_id=9` (`/payroll/9`)
3. เช็ก blocker ก่อนกด finalize (ต้องเป็นศูนย์หรือเคลียร์เหตุผลแล้ว):
   - `cycle-date drift`
   - `unlinked pending`
   - (UX) บนหน้า `/payroll/{run_id}` ใช้แถบ **Ops** ลัดไปสดย่อย/เดลี่/น้ำมัน/บิล + copy คำสั่ง `preflight_payrun.py` ได้ทันที
4. เคลียร์คิวชื่อ BigC ที่ยังไม่ match master จำนวน 7 รายชื่อ (ดูหัวข้อ Outstanding Queue)
5. ตัดสินใจเคสคงค้างมูลค่าสูงก่อน:
   - `สมพร` net diff `-9,999.99` (manual-net rule)
   - `BigC drift` 7 รายการ `4,150.00` บาท (กันปิดรอบผิดเดือน)
6. หลังแก้แล้ว rerun audit/preflight 1 รอบ และบันทึกผลใหม่ใน `reports/`

---

## 2) Outstanding Queue (เรียง BigC -> LCB -> AYU)

### BIGC (สูงสุด)
- **Unresolved name mapping: 7 เคส** (repeat แล้ว 1 รอบ): `แบ็งค์`, `ใหม่`, `อภิรักษ์`, `ไวพจน์`, `ธีระวัฒน์`, `สุพนธ์`, `นันทวัฒน์`
- **Residual financial mismatch:**
  - รวมทั้งรอบ: `net_diff_total = -9,074.28`, `trip_fee_diff_total = 0.00`, `fuel_rate_diff_total = +0.26`
  - เคสหนัก: `สมพร` (`net_diff=-9,999.99`) — รอยืนยันนิยาม net manual
- **Preflight blocker ล่าสุด (`run_id=10`):**
  - `cycle-date drift = 7 รายการ / 4,150.00 บาท`
  - `unlinked = 33 รายการ / 23,716.00 บาท`
- **สถานะ run:** `run_id=10` ยังเป็น `draft`
- **ไฟล์เช้าอ้างอิง:** `reports/audit_bigc_2026-03_recheck_mminus1_after_unresolved_safe/PENDING_MORNING_UNRESOLVED.md`

### LCB (สูง)
- **Preflight risk = HIGH** สำหรับ `run_id=9`, `tag=2026-03`
- `unlinked = 33 รายการ / 23,716.00 บาท`
- `cycle-date drift = 23 รายการ / 14,616.00 บาท`
- `cross-site collision indicator = 4 คน` (ต้องตรวจเชิงลึกว่าเข้ายอดรอบนี้จริงหรือไม่)
- **ไฟล์เช้าอ้างอิง:** `reports/preflight_morning_queue/PENDING_MORNING_preflight_LCB_2026-03_run9.md`

### AYU (สูง)
- **Preflight risk = HIGH** สำหรับ `run_id=7`, `tag=2026-03`
- `unlinked = 33 รายการ / 23,716.00 บาท`
- `cycle-date drift = 33 รายการ / 24,430.00 บาท`
- **ไฟล์เช้าอ้างอิง:** `reports/preflight_morning_queue/PENDING_MORNING_preflight_AYU_2026-03_run7.md`

---

## 3) Critical Decisions Pending (ไม่เกิน 5)

1. **ล็อกนิยาม manual net (BigC/สมพร):** จะใช้ช่องใดในชีท `Book1.xlsx` เป็นยอดจ่ายจริงมาตรฐาน
2. **อนุมัติ mapping ชื่อ 7 เคส BigC:** เพิ่ม master/alias อย่างไรเพื่อปิด unresolved แบบตรวจสอบย้อนกลับได้
3. **นโยบายแก้ drift LCB/AYU:** จะให้แก้ที่ `txn_date` หรือแก้ `pay_cycle_tag` เป็นหลัก (เพื่อ consistency ทั้งระบบ)
4. **cross-site collision LCB 4 คน:** ให้ถือเป็น warning อย่างเดียวหรือเพิ่มเป็น hard gate ก่อน finalize
5. **นโยบาย finalize AYU:** จะคง flow เดิม (unlinked-first) หรือเปิด drift-first block แบบ BIGC/LCB

---

## 4) Next 3 Executable Commands/Steps (สำหรับผู้ใช้ non-coder)

1. รัน preflight LCB รอบล่าสุด
   - `python ProjectYK_System/tools/preflight_payrun.py --site LCB --run-id 9`
2. รัน preflight BIGC รอบล่าสุด
   - `python ProjectYK_System/tools/preflight_payrun.py --site BIGC --run-id 10`
3. รัน preflight AYU รอบล่าสุด
   - `python ProjectYK_System/tools/preflight_payrun.py --site AYU --run-id 7`

> หมายเหตุ: ถ้ารันข้อ 3 แล้ว unresolved ยังซ้ำ ให้หยุด loop และใช้ไฟล์ `PENDING_MORNING_UNRESOLVED.md` เป็นคิวแก้รายคนก่อน rerun รอบถัดไป
