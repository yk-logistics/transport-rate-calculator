---
name: project-cfo-revenue-drilldown
description: "หน้า CFO /finance/revenue: รายได้ drill-down ไซต์→ลูกค้า→รถ. DONE+deployed 2026-06-28"
metadata: 
  node_type: memory
  type: project
  originSessionId: 02c533fb-7a28-4c02-9a0e-8fd0dafab220
---

**DONE + deployed server 2026-06-28** (branch feat/finance-revenue-drilldown → main → deploy code-only). อ่านอย่างเดียว ไม่แตะ schema/เงิน.

**หน้าใหม่ `/finance/revenue`** (+ `templates/finance_revenue.html`, ลิงก์จาก finance_dashboard ปุ่มม่วง "รายได้แยกลูกค้า/รถ"): เลือกช่วงวัน (from/to) + ไซต์ → ตารางกางได้ (`<details>` ซ้อน 3 ชั้น) ไซต์→ลูกค้า→รถ + %ของพาเรนต์ + เตือน coverage.

**service `revenue_breakdown(session,start,end,site)` (finance.py):** nest ไซต์(site_code)→ลูกค้า(**status_code**)→รถ(**plate_no_raw**). รายได้=**revenue_customer** (ค่าขนส่งจริง ช่อง U, โอเลือก top-line ล้วน ไม่รวม DailyJobFee/cost). เรียง revenue มาก→น้อยทุกชั้น. คืน totals + has_other_sites.

**คีย์ดาต้าที่ตรวจมา (สำคัญ):**
- DailyJob มีข้อมูลรายเที่ยว**เฉพาะ LCB** (1,116 แถว) — BIGC/AYU ไม่มี (onboard ลอก net เงินเดือนเท่านั้น). หน้ามี banner เตือน "ข้อมูลรายเที่ยวมีเฉพาะ LCB".
- **ลูกค้าอยู่ใน status_code** (KLND/CJ/DHL Overflow/KAO/NHL/WHALE...) ไม่ใช่ customer_name_raw/customer_id (ว่าง/null 1116/1116).
- **รถใช้ plate_no_raw (ครบ 1116)** ไม่ใช่ head_vehicle_id (ลิงก์แค่ 508 — /finance/vehicles เดิมเห็นไม่ครบครึ่ง! ข้อจำกัดที่ควรรู้).
- ราคาที่ยังไม่กรอก: 259 แถว revenue=0 แต่ส่วนใหญ่ปกติ (ลา17 + รถจอด/ซ่อม230); ลืมจริง ~2 + กำกวม10 = ทั้งหมดเดือน เม.ย.–พ.ค.(ปิดแล้ว), 0 แถวในรอบ มิ.ย. → โอสั่งข้าม. รอบ active ราคาครบ.

**Verify:** total = Σไซต์ = Σลูกค้า = Σรถ = direct SUM(revenue_customer). LCB มิ.ย.(16/5–15/6) = **1,967,425 / 608 เที่ยว** ตรง /daily. Top ลูกค้า: KLND 575k(29.2%)/CJ 302k/KAO 273k/NHL 232k/DHL Overflow 140k. +4 tests. deploy verified บน server (reconcile MATCH=True). ไม่แตะ /finance,/finance/vehicles,/finance/pnl เดิม. ดู [[project-cfo-cycle-vs-calendar]] [[project-driver-pay-breakdown-daily-slip]].
