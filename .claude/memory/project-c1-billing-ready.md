---
name: project-c1-billing-ready
description: "C1 แถบ \"พร้อมวางบิล?\" ใน /billing DONE+deployed 3ก.ค. — ราคาว่าง/ไม่มีเลขใบงาน/ตู้ซ้ำ ต่อลูกค้า + helper _daily_row_kind ใช้ร่วมปฏิทิน"
metadata: 
  node_type: memory
  type: project
  originSessionId: 742a8c2c-bba6-475f-bb99-ce05aba9b6ba
---

**C1 DONE+deployed 3 ก.ค. 2026 (commit d509223, surgical scp main.py+billing_page.html, RESULT OK):**
หน้า /billing มีแถบ "พร้อมวางบิล?" ต่อลูกค้า+เดือน: นับจาก**แถวเดลี่ทั้งหมด**ในช่วง (หน้าเดิมกรอง revenue>0 เลยมองไม่เห็นแถวราคาขาด) — 3 เกณฑ์: ราคาว่าง (job จริง revenue<=0) / ไม่มีเลขใบงาน (doc_no+invoice_no+job_ref+receive_inv_no ว่างหมด) / ตู้ซ้ำ (วัน+ทะเบียน+ตู้ เฉพาะ container ไม่ว่าง); แต่ละแถว deep-link ไปแก้ /daily?site&d_from&d_to&q=ทะเบียน; เขียว "พร้อมวางบิล" เมื่อไม่มีปัญหา; เกณฑ์ที่ 4 (ราคา≠ใบเสนอ) รอ B3

**Refactor:** ตัวแยกชนิดแถวเดลี่จาก B4 ยกเป็น helper `_daily_row_kind(r)` → job/idle/leave/repair ใช้ร่วม ปฏิทินรถ + billing (ตรรกะเดียวกับ payroll _count_work_days)

**ผลจริง (ตรงเกณฑ์ผ่านสเปค):** BigC พ.ค. จับราคาว่าง 340 แถว (เคส "ลงราคา 9%" ที่รู้กัน — โผล่กลุ่ม "(ไม่ระบุ)" เพราะ BigC ลูกค้าอยู่คอลัมน์ E ไม่ได้ map เข้า customer_name_raw — งานข้อมูล D1); LCB มิ.ย. ราคาครบ (สอดคล้อง audit) เหลือ Nippon 4 + PX19 2 แถวไม่มีเลขใบงาน; AYU มิ.ย. ราคาว่าง 179 (Oatside 126 = วางบิลทาง GPS แยกอยู่แล้ว)

verified: pytest 2 ตัว (tests/test_billing_ready.py) + suite 324 pass + smoke ข้อมูลจริง 3 ไซท์

related: [[project-b4-fleet-calendar]] [[project-master-plan-jul26]]
