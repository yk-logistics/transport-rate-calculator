---
name: project-slip-ktag-mixed-table
description: "งานสลิปค้างข้ามเซสชันปิดแล้ว 5ก.ค. — ตาราง mixed ถอดคอลัมน์ \"ฝั่ง\" เป็นป้าย k-tag + พิเศษ/OT เรียงตรง; commit 20b32b0 deploy เขียว; บล็อก \"ห้ามทับ template สลิป\" ยกเลิก"
metadata: 
  node_type: memory
  type: project
  originSessionId: 701a5a18-481b-4f29-9892-135e2950f72e
---

**ปิด 5 ก.ค. 2026** — งาน branch `fix/slip-trip-fee-kb-display` ที่ค้าง working tree ข้ามเซสชันมาตั้งแต่ ~1 ก.ค. เสร็จแล้ว:

- **ตาราง mixed (LCB ลูกผสม) ใน `_slip_body.html`**: ถอดคอลัมน์ "ฝั่ง" → ป้าย `k-tag` หน้า route (`k-mao`=เขียว เหมา, `k-trip`=น้ำเงิน เที่ยว, `k-idle`=เทา รถจอด) เหลือ 6 คอลัมน์ — route ได้ที่เพิ่ม; แถววัดถัง + tfoot colspan ปรับตาม
- **คอลัมน์พิเศษ/OT** (`.c-extra .fnum/.fk` กว้างคงที่): เลขหลายบรรทัด (พิเศษ/OT/รับตู้) เรียงตรงเป็นคอลัมน์; `.fline` เปิด flex-wrap กันป้ายล้นช่องน้ำมันหลายบิล
- **CSS ต้องแก้คู่ขนาน 2 surface เสมอ**: `payroll_slip.html` (รายคน/ZIP) + `payroll_print_all.html` (/print) — ดู [[project-slip-surfaces-consistency]]
- ตรวจ: เรนเดอร์จริง LCB#2 พชร (mixed) + รัฐภูมิ (mao) ผ่าน Chrome headless screenshot; ตารางเที่ยวปกติไม่โดนกระทบ
- **git**: commit `20b32b0` บน branch → main ff ด้วย `git fetch . branch:main` (checkout ไม่ได้เพราะ oatside ค้าง); deploy `deploy_mvp.sh --markers "k-mao"` เขียวครบ; **ไม่ push origin** (norm repo นี้ origin ตามหลังไกล deploy ผ่าน scp)
- **บล็อกเก่า "สลิป template uncommitted ห้ามทับ/ห้าม deploy ทั้ง dir" ยกเลิกแล้ว** — ที่ค้างใน working tree เหลือแค่ `app/oatside/` (build_oatside_reports.py + oatside_config.json ของ session Oatside) ซึ่ง deploy_mvp.sh ไม่ลากอยู่แล้ว (copy แค่ root *.py + services/static/templates)

related: [[project-jul1-session-close]], [[project-jul4-day-run]], [[reference-deploy-mvp-selfverify]]
