---
name: project-receivables-page
description: หน้ารอรับเงินลูกค้า /finance/receivables อ่านทะเบียนรับเช็ค AYU/LCB จาก Drive — deployed 2ก.ค. รอโอแชร์ไฟล์ 2 ตัวให้ service account
metadata: 
  node_type: memory
  type: project
  originSessionId: e43bba19-d298-4881-8117-b08646b56d9b
---

**DONE+deployed 2 ก.ค. 2026** — โอส่งไฟล์ "รายการรับเช็ค AYU/LCB 2025-2026.xlsx" (ทะเบียนวางบิล-รอเก็บเงิน ทีมบัญชีทำมือ แท็บรายเดือน) ให้ต่อยอด "ออโต้ดึงจาก Drive" ผมตัดสินใจทำเป็นหน้า **/finance/receivables** (สิทธิ์ตามเมนู finance: admin edit / accountant view):

- **ทีมบัญชีไม่เปลี่ยน workflow** — กรอก Excel ใน Drive เดิม ระบบอ่านเอง (หาไฟล์จากชื่อ "รายการรับเช็ค AYU/LCB", cache ตาม modifiedTime, รองรับทั้ง xlsx และ Google Sheet)
- **กติกาสี (โอยืนยัน):** ไฮไลท์ทั้งแถว=รับแล้ว (เขียว FF92D050=รอบปกติ / เหลือง FFFFC000=รับแล้วคนละรอบโอน) ไม่มีสี=ค้างรับ — **ตัดสินจากช่อง C ชื่อบริษัท** (สีเฉพาะช่อง F หัก ณ ที่จ่าย ไม่นับ; theme color อ่าน rgb ไม่ได้ = นับว่ามีสี; เทียบสีเฉพาะ 6 หลักท้าย ตัด alpha)
- โครงแท็บ: A วันที่/B INV/C บริษัท/D จำนวน/E VAT/F หัก ณ ที่จ่าย/G เงินหน้าเช็ค/H DUE รับเช็ค/I หมายเหตุ/J เลข RC; หลาย section ต่อแท็บ ข้ามหัวซ้ำ+แถว "รวมเป็นเงิน"+แถวยอด 0 (รอออกบิล); **INV ซ้ำหลายแท็บ dedupe เอาแท็บล่าสุด** (แถวไม่มี INV เสี่ยงนับซ้ำถ้าพิมพ์หลายแท็บ)
- สรุป: ค้างรับรวม/เลยกำหนด(แดง)/ครบใน 7 วัน + ตารางเรียง DUE + ค้างรายลูกค้า; ยอดรอรับ = G (บิล−WHT)
- **อ่านเฉพาะแท็บปี 2026+ (MIN_YEAR, โอสั่ง — แท็บปีเก่าไฮไลท์ไม่อัปเดต=ค้างปลอม)**; verified ไฟล์จริง 2ก.ค.: 2,645 แถว → **ค้างรับ 247 ใบ = 3,316,751.90 / เลยกำหนด 17 ใบ = 1,053,875.35** (top: HAIER 682k, BJC DHL 677k, CONTINENTAL 311k)
- code: services/receivables.py + templates/finance_receivables.html + เมนู เงิน→💵; runbook docs/RECEIVABLES_RUNBOOK.md; เทสต์ workbook จำลอง 3 ตัว

**✅ Drive ต่อสำเร็จ 2ก.ค.:** โอแชร์เป็น**ลิงก์โฟลเดอร์** "Project YK" (`1mcXEjbG93b-fhs7bwtqN2itLQjMehmBa`, anyone-with-link Viewer) แทนการแชร์ตรงให้ service account — **GOTCHA: ของที่แชร์แบบลิงก์ `files.list` ค้นหาด้วยชื่อไม่เจอ ต้องเปิดจากรหัสโฟลเดอร์ตรง** (`AR_FOLDER` ใน services/receivables.py, มี fallback ค้นทั้ง Drive); ไฟล์เป็น Google Sheet → export xlsx; **verified end-to-end บน server: 2,645 แถว ค้างรับ 247 = 3,316,751.90 ตรง local เป๊ะ** — หน้าใช้งานจริงเต็มรูปแบบแล้ว; ห้ามเปลี่ยนชื่อไฟล์ให้หลุดคำ "รายการรับเช็ค AYU/LCB" และห้ามปิดแชร์ลิงก์โฟลเดอร์

related: [[reference-google-drive-access]] [[project-cy-kb-payout-calculator]] [[feedback-handoff-for-smaller-models]]
