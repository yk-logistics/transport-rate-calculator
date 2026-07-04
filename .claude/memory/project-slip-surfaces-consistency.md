---
name: project-slip-surfaces-consistency
description: สลิป 3 surface (รายคน/ZIP ใช้ payroll_slip.html ; /print ใช้ payroll_print_all.html) ต้องเหมือนกัน — เจอ /print ลืมส่ง fuel_only_info + แยกคอลัมน์ พิเศษ/OT
metadata: 
  node_type: memory
  type: project
  originSessionId: e4915bf4-d6d9-461e-b875-baa8077934cf
---

1ก.ค. โอ: (1) สลิป สุรเดช/พชร (lcb_mixed) แถวจัดไม่ดี ช่อง "ค่าแรง" เบียด (ค่าเที่ยว+พิเศษ/OT ซ้อนกัน); (2) ไฟล์ ZIP ที่แตกต่อคน ≠ หน้า /print (+/print?for=boss).

**สถาปัตยกรรม 3 surface (สำคัญ):** หน้าสลิปรายคน `/payroll/{id}/employee/{eid}/slip` **และ** ปุ่ม ZIP (`/payroll/{id}/export-zip` → `services/payroll_zip_pdf.py` render ด้วย headless Chrome) **ใช้ `payroll_slip.html` ตัวเดียวกัน** (build_payroll_slip_context) → เหมือนกันเสมอ. ส่วน `/payroll/{id}/print` ใช้ **`payroll_print_all.html`** (คนละไฟล์ มี `<style>` + JS zoom ของตัวเอง) ที่ `{% with %}`-include `_slip_body.html`. ตารางเดลี่จริงมาจาก `_slip_body.html` ตัวเดียว (ทั้ง 3 surface) แต่ wrapper/CSS ต่างกัน → พิสูจน์แล้ว CSS `.daily` เหมือนกันเป๊ะ (diff เหลือแค่ `.th-sub` + rule ของ `table.run`/boss สรุป).

**บั๊กที่เจอ (root cause ของ /print ≠ ZIP):** `payroll_print_all.html` `{% with %}` **ลืมส่ง `fuel_only_info`** (ตัวเดียวที่ขาด จาก 29 keys) → วัน "เติมน้ำมัน" (มีน้ำมันแต่ไม่มีงาน) หลุดไปโชว์เป็น "รถจอด" บน /print ทั้งที่หน้าสลิปรายคนถูก. `_slip_body` guard ด้วย `|default({})` เลยไม่ 500 แต่ misrender เงียบ. **แก้=เติม `fuel_only_info=r.ctx.fuel_only_info` 1 บรรทัด.** (คลาสเดียวกับ GOTCHA print-all เดิม — {% with %} ลืม var). marker ตรวจ: `🛢 เติมน้ำมัน` (คำว่า "เติมน้ำมัน" เฉยๆ โผล่ใน footer note เสมอ ใช้แยกไม่ได้).

**แยกคอลัมน์ พิเศษ/OT (โอเลือก):** เดิม พิเศษ/OT/รับตู้ = `.fline.sub` ซ้อนใต้ค่าเที่ยว (macro `feelines`) → เบียด. เปลี่ยนเป็น **คอลัมน์ "พิเศษ/OT" แยก** (macro เปลี่ยนชื่อ `feecol`, ออก `<td class="num c-extra">`). แก้ทั้ง 2 ตารางใน `_slip_body.html` (normal + mixed) + boss variant: header เพิ่ม th, data row ย้าย feecol ออกจาก c-trip, **tank rows + footer colspan/`<td>` ต้องเพิ่มให้ตรง** (normal footer colspan คงที่ +1 empty td ก่อน boss cells ; mixed footer colspan 4→5, tank +1 td). CSS `.c-extra .fline.sub` เพิ่มใน **ทั้ง 2 ไฟล์** (payroll_slip.html + payroll_print_all.html มี style คนละก้อน). เลข number-first + label muted เล็ก (กันคำ "พิเศษ" ล้นทับ ค่าแรง — เจอตอนแรก label-first ล้น). แสดงผลล้วน special_income/gross ไม่เปลี่ยน.

**verified:** สุรเดช(mixed) ค่าแรง/พิเศษ/OT แยกคอลัมน์สะอาด, ปกรณ์ boss view ทุกคอลัมน์ตรง (ค่าเที่ยว 1,380 KB-adj + พิเศษ/OT "200 OT" + KB 110), /print driver+boss render ไม่ 500 (c-extra 607 rows). tests: test_print_fuelonly_matches_slip.py + test_slip_extra_fee_column.py.

**ยังค้าง (โอสั่งแยกทำทีหลัง):** วันเที่ยวของ lcb_mixed (สุรเดช/พชร) ยังไม่หัก KB (mixed path `_slip_body:70` โชว์ `revenue×0.60` ไม่ผ่าน trip_fee_show) — ดู [[project-slip-mao-kb-reconcile]].
related: [[project-payroll-slip-zip-per-driver]] [[reference-chrome-headless-pdf]] [[project-slip-mao-kb-reconcile]]
