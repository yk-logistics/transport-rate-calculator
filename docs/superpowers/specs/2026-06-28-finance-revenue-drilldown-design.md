# Spec — หน้าวิเคราะห์รายได้ CFO (drill-down ไซต์→ลูกค้า→รถ)

วันที่: 2026-06-28
ผู้สั่งงาน: โอ (พงษกาญจน์)
ประเภท: read-only analytics page (ไม่แตะ schema / ไม่แตะเงิน)

## เป้าหมาย

ให้ CFO วิเคราะห์ **รายได้ (ค่าขนส่งจริง)** แบบเจาะลึกซ้อนกัน 3 ชั้น: **ไซต์ → ลูกค้า → รถ** เลือกช่วงเวลาเองได้

## ความจริงที่ตรวจแล้ว (ground truth — กำหนดดีไซน์)

- DailyJob มีข้อมูลรายเที่ยว **เฉพาะ LCB** (1,116 แถว) — BIGC/AYU ไม่มี (onboard แบบลอก net เงินเดือนเท่านั้น) → หน้าต้องบอกชัด ไม่โชว์ 0 เงียบ
- **ลูกค้าเก็บใน `status_code`** (KLND/CJ/DHL Overflow/KAO/NHL/WHALE/…) ไม่ใช่ `customer_name_raw` (ว่าง 1116/1116) หรือ `customer_id` (null 1116/1116)
- **รถใช้ `plate_no_raw`** (ครบ 1116) ไม่ใช่ `head_vehicle_id` (ลิงก์แค่ 508 — /finance/vehicles เดิมเห็นไม่ครบครึ่ง)
- รายได้ = `revenue_customer` (ค่าขนส่งจริง ช่อง U) — โอเลือก top-line ล้วน ไม่รวม DailyJobFee
- revenue กรอกครบในรอบ active; ที่ว่าง 259 แถว = ลา 17 + รถจอด/ซ่อม 230 + ลืมจริง ~2 + กำกวม 10 (ทั้งหมดเดือน เม.ย.–พ.ค. ปิดแล้ว) → ไม่กระทบความแม่นรอบปัจจุบัน

## ขอบเขต

### service ใหม่ `revenue_breakdown(session, start, end, site="") -> dict` (finance.py)
- คิวรี DailyJob `where work_date BETWEEN start AND end` (+ site ถ้าระบุ)
- รายได้ต่อแถว = `revenue_customer or 0`
- build โครงซ้อน:
  - **ชั้น 1 ไซต์:** group by `site_code` → {revenue รวม, trips (นับแถว), rows_priced, rows_no_price}
  - **ชั้น 2 ลูกค้า:** group by `status_code` (ค่าว่าง → "(ไม่ระบุ)") → {revenue, trips}
  - **ชั้น 3 รถ:** group by `plate_no_raw` (ค่าว่าง → "(ไม่ระบุ)") → {revenue, trips}
- เรียงทุกชั้น revenue มาก→น้อย
- คืน totals รวม + flag `has_other_sites` (มีไซต์อื่นนอก LCB ที่มี DailyJob ไหม — ปัจจุบัน false)

### หน้า `/finance/revenue` (route + `templates/finance_revenue.html`)
- ฟอร์ม GET: `from`, `to` (date inputs), `site` (dropdown: ทุกไซต์ + LCB/BIGC/AYU), ปุ่มลัด "รอบ LCB เดือนนี้" (เซ็ต 16→15)
- ค่าเริ่มต้นช่วง: 30 วันล่าสุด (หรือรอบ LCB ปัจจุบัน) — เลือก 30 วันล่าสุดเพื่อความตรงไปตรงมา
- ตารางซ้อนกางได้ด้วย `<details>` ฝั่ง client (ไม่ต้อง round-trip):
  - แถวไซต์: ชื่อ, trips, revenue, (ชั้นบนสุดไม่มี %)
  - กาง → ลูกค้า: ชื่อ, trips, revenue, % ของไซต์
  - กาง → รถ: ทะเบียน, trips, revenue, % ของลูกค้า
- ฟอร์แมตเงิน `{:,.0f}`, ใช้ base.html + สไตล์เดียวกับ /finance เดิม

### แถบเตือนความครบ (กันวิเคราะห์ผิด)
- บนสุด banner: "ข้อมูลรายเที่ยวมีเฉพาะ LCB · BIGC/AYU ยังไม่มีข้อมูลรายวัน (ลอกเฉพาะยอดเงินเดือน)"
- ต่อไซต์: ถ้า rows_no_price > 0 → ป้าย "⚠ {n} เที่ยวยังไม่ลงราคา"

## ไม่ทำ (out of scope)
- ไม่แตะ `/finance`, `/finance/vehicles`, `/finance/pnl`, `cost_per_vehicle`, `monthly_pnl` เดิม
- ไม่รวม cost/กำไรต่อรถ (มีใน /finance/vehicles แล้ว) — หน้านี้ revenue ฝั่งเดียว
- ไม่รวม DailyJobFee เป็นรายได้
- ไม่แก้ 12 แถวไม่มีราคา (โอสั่งข้าม)
- ไม่แตะ schema, read-only

## ตรวจย้อนกลับ (verify)
1. ผลรวม revenue ของทุกไซต์ = Σ ทุกลูกค้า = Σ ทุกรถ = `SELECT SUM(revenue_customer) WHERE work_date BETWEEN` (กันตกหล่น/นับซ้ำ)
2. รอบ LCB มิ.ย. (16/5–15/6): revenue รวม + trips ตรงกับที่เห็นใน /daily ช่วงเดียวกัน
3. ลูกค้า top (KLND/CJ/DHL Overflow) ยอดตรงกับ query ตรง
4. unit test: revenue_breakdown บน fixture เล็ก (2 ไซต์ × 2 ลูกค้า × 2 รถ) → โครง+ผลรวมถูก
