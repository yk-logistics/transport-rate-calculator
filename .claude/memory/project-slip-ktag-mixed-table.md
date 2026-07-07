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

**ต่อยอดทันที (เซสชันเดียวกัน):** หางงาน E2 "ธงบนสลิป" ที่รอ template ว่าง — เสร็จแล้ว commit `10e80f6` deploy marker `tag-anom` เขียว: ⚠ ธง R1/R2/R3 ในช่องน้ำมัน **เฉพาะชุดผู้บริหาร** (is_boss — สลิปคนขับไม่โชว์); **R1 บนสลิปเกณฑ์ ≥3 บิล/วัน** (คู่ B7+B20 ปกติ = 2 บิล ไม่ธง — เกณฑ์ ≥2 เดิมธง 190/รอบ ไร้ความหมาย) ส่วนหน้า /fuel/anomaly เกณฑ์เดิม; fuel_anomaly.scan แนบ `n` ใน flag R1 ให้ผู้เรียกกรอง

**รอบเก็บงาน 7 ก.ค. (โอส่ง screenshot ติ Mix):** commit `fe1acac` → main ff → surgical scp 3 ไฟล์ + restart เขียว (RESULT OK + /login 200):
- ช่องน้ำมัน ฿ ตาราง mixed: **เลขบรรทัดบน / ป้ายคู่ [เกรด][สถานะ] บรรทัดล่าง** — `.tag-st` กว้างคงที่ 32px (หัก/บริษัท/ไม่หัก) เรียงตรงคอลัมน์ทุกแถว; บิลเดียวใช้โครง `.fline` เดียวกับหลายบิล (เลิกตัวใหญ่ 11px ปน)
- เหตุที่ต้อง 2 บรรทัด: คอลัมน์กว้าง 70px ใส่ fnum32+เกรด20+สถานะ32 บรรทัดเดียวไม่พอ → flex-wrap เดิมห่อเองเลยเหลื่อม
- หัวตาราง mixed "ค่าแรง" → **"ค่าเที่ยว"** + foot note ตาม; `.c-extra` ถอด `border-left` (เส้นตั้งหลังคอลัมน์ค่าเที่ยว) ทั้ง 2 surface
- โอบอก "เหลือแค่ Mix นอกนั้นโอเคหมดแล้ว" → รอบนี้น่าจะปิดชุดสลิปทั้งหมด

related: [[project-jul1-session-close]], [[project-jul4-day-run]], [[reference-deploy-mvp-selfverify]]
