# CFO — มุมมองเทียบทุกไซท์ (compare view)

วันที่: 2026-06-28

## ปัญหา / เป้าหมาย

หน้า `/finance` (CFO) ตอนนี้เลือกได้ทีละไซท์ หรือ "ทั้งหมด" (รวมทุกไซท์เป็นก้อนเดียว).
โออยากเห็น **ทุกไซท์พร้อมกัน แต่แยกรายการต่อไซท์** เป็นตารางเทียบ เพื่อดูว่า
ไซท์ไหน/รอบไหนเป็นยังไง โดยเห็นพร้อมกันในจอเดียว.

## ขอบเขต (จากการถามโอ)

- รูปแบบ: **ตารางเทียบไซท์** (แถว = ไซท์ + แถวรวม)
- โหมดเวลา: **สลับได้ทั้งสองแบบ**
  - `calendar` — ทุกไซท์ใช้เดือนปฏิทินเดียวกัน (1–สิ้นเดือน)
  - `cycle` — anchor ด้วยเดือนปฏิทิน (เช่น 2026-06) แล้ว **แต่ละไซท์ map ไปรอบจ่ายของตัวที่จบในเดือนนั้น**
    (BIGC=ปฏิทิน, LCB=16/5–15/6, AYU=26/5–25/6) — ใช้ `_cycle_period_for_tag(site, tag)` เดิม
- ในมุมมอง compare: ซ่อน KPI cards / trend 6 เดือน / vehicle list เดิม (พวกนั้นออกแบบมาเพื่อไซท์เดียว) — โชว์แค่ตารางเทียบ
- แต่ละแถวไซท์กดลิงก์เข้าไปดูมุมมอง single ของไซท์นั้นได้

## สิ่งที่ไม่ทำ (YAGNI)

- ไม่แตะ `monthly_pnl()` (มันรับ `site` + `period` อยู่แล้ว)
- ไม่ทำ drill-down / กราฟใหม่ / export
- ไม่แตะ loans / health / cashflow / pnl / vehicles routes

## สถาปัตยกรรม

### Route `/finance` (main.py:finance_dashboard)

เพิ่ม query param `view`:
- `view=single` (default) — โค้ดเดิมเป๊ะ ไม่กระทบ
- `view=compare` — สาขาใหม่:
  - loop `SITES = ['AYU','BIGC','LCB']`
  - แต่ละไซท์เรียก `finance_svc.monthly_pnl(s, y, m, site, include_other_petty=flag, period=...)`
    - `calendar` → `period=None`
    - `cycle` → `period=_cycle_period_for_tag(site, month)` (anchor = เดือนที่เลือก)
  - รวมแถว total = ผลรวมฟิลด์ตัวเลขของทุกไซท์
  - ส่ง `rows` (list per-site dict) + `totals` ไป template

โหมด `cycle` ในมุมมอง compare **ไม่ต้องเลือกไซท์ก่อน** (ต่างจาก single) — เพราะ anchor เป็นเดือน
แล้วแต่ละไซท์ map รอบเอง. ถ้าไซท์ไหน map ไม่ได้ → fallback period=None (ปฏิทิน) สำหรับไซท์นั้น.

### Template `finance_dashboard.html`

- เพิ่ม toggle `view` (ไซท์เดียว ↔ เทียบทุกไซท์) ในฟอร์ม filter
- `{% if view == 'compare' %}` → render ตารางเทียบ, else → เนื้อหาเดิมทั้งหมด
- ตารางคอลัมน์: ไซท์ · ช่วงวันที่จริง · เที่ยว · รายรับ · น้ำมัน · payroll · สดย่อย(net) · ซ่อม · กำไรสุทธิ · margin%
- แถวสุดท้าย = รวม (เว้นช่วงวันที่จริง เพราะแต่ละไซท์คนละช่วงในโหมด cycle)
- ชื่อไซท์ลิงก์ไป `/finance?view=single&site=<S>&mode=<mode>&month=<month>`

## วิธีตรวจย้อนกลับ

- ตัวเลขแต่ละแถวต้องตรงกับเปิด single ของไซท์นั้นในเดือน/รอบเดียวกัน (เพราะเรียกฟังก์ชันเดียวกัน)
- แถวรวม (compare/calendar) ต้องตรงกับ single `site=""` (ทั้งหมด) เดือนเดียวกัน — verify ด้วยสคริปต์
- `view=single` ต้องเหมือนเดิมเป๊ะ (regression)
