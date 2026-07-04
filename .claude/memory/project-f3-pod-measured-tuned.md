---
name: project-f3-pod-measured-tuned
description: F3 POD วัดจริงบน server 4ก.ค. + จูน reverse-match เลข Job แล้ว — เหลือรอเดลี่ ก.ค. import ถึงวัดรอบเต็ม ≥90% ได้; LineGroupMap 38 กลุ่มลง server DB แล้ว
metadata: 
  node_type: memory
  type: project
  originSessionId: d4a29959-9dce-4e25-82a7-9d031c3c20be
---

F3 (ชุดหลักฐานวางบิล POD) วัดจริงบน server 4ก.ค. 2026:

- **Archive LINE เริ่มเก็บ ~12 มิ.ย. / เดลี่บน server จบ 15 มิ.ย. (LCB) - 25 มิ.ย. (อื่น)** → หน้าต่างวัดมีแค่ 12-15 มิ.ย.; เกณฑ์ ≥90% ต่อรอบเต็มต้องรอเดลี่ ก.ค. import ก่อน — วัดซ้ำ: `python measure_pod2.py 2026-07-01 2026-07-31` จาก `C:\Users\yklog\YK_MVP\app` (venv python, สคริปต์ read-only ทิ้งไว้บน server แล้ว)
- **จูนที่ได้ผล (commit 4484175, deploy แล้ว):** reverse-match — เอา job_ref/doc_no ของแถวเดลี่ไปหาในข้อความ ±10 นาทีรอบรูป (score 4) เพราะ KLND โพสต์ "Job. KLND26-015737" ตรง job_ref เดลี่ 100% ส่วนเลขตู้อยู่ในตัวรูป; ผล strong match 57→80/340, KLND 0→22
- **NHL = กลุ่มรูปเยอะสุด (127 รูป/4วัน) แต่ text ไม่มีเลขอ้างอิงเลย** — เลขงาน TNC อยู่ในตัวรูป ต้อง OCR (โยง F4); DHL doc_no ใน DB มี `"` นำหน้า (dirty data — /admin/data-clean ยัง normalize แค่ invoice_no)
- **LineGroupMap:** ผมตัดสินใจแทนโอ (โอมอบอำนาจ 4ก.ค.) mark 38 กลุ่มลง server DB — 19 customer (อิงชื่อกลุ่ม + status_code มีจริงในเดลี่), 2 station, 17 internal; กลุ่มกำกวม (P&W, เรียกรถ, บอสรับเบอร์, ไทร์มาร์ท, ออโต้เทคนิค, อ.ยนต์) เว้นไว้; โอแก้ได้ที่ /line/inbox
- **site_code แก้แล้วตามเดลี่จริง (4ก.ค. เย็น):** DHL BPD/ABF/Conti/HomePro/Wonder/Yusen → **AYU** (เดิมเดา LCB ผิด — DHL 222 แถวอยู่ AYU); DHL Overflow + DHL Carrier = LCB ถูกอยู่แล้ว

**Why:** ปลดบล็อค /line/pod + /line/inbox บน server (เดิม mapping ว่างเปล่า ฟีเจอร์ไม่ทำงานเลย) และบันทึกว่าทำไมวัด ≥90% ยังไม่ได้

**How to apply:** หลัง import เดลี่ ก.ค. → รัน measure_pod2.py ช่วง ก.ค. → ถ้า strong/coverage ดีพอ mark F3 done; ถ้าจะดัน NHL ต้องทำ OCR รูป (คุยโอเรื่องค่าใช้จ่ายพร้อม F4) ดู [[project-jul4-night-run]]
