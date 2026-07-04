---
name: project-jul4-day-run
description: "เซสชันกลางวัน 4ก.ค.: F3 วัด+จูน, G2 done v44, S3 done+rotate token, F0 จบจริง, S5 checklist รอบแรก+อุด CVE, doc_no clean 208 แถว — แพลน 34/38"
metadata: 
  node_type: memory
  type: project
  originSessionId: d4a29959-9dce-4e25-82a7-9d031c3c20be
---

เซสชันกลางวัน 4 ก.ค. 2026 (โอสั่ง "ทำต่อเรื่อยๆ ไม่ต้องหยุด อนุมัติทุกอย่าง"):

1. **F3** วัดจริง+จูน reverse-match ([[project-f3-pod-measured-tuned]]) — ยัง doing รอเดลี่ ก.ค.
2. **G2 done** v44 ([[project-g2-media-archive]])
3. **S3 done** — SECRETS_INVENTORY.md + rotate YK_SLIP_INGEST_TOKEN จริง (ค่าเก่าตาย ยืนยัน fetch_config 200)
4. **F0 จบจริง** — deploy จัดหมวด Discord ไป archiver + จัดห้องค้าง 44/44 (ต้นตอ: backfill 12มิ.ย. จัดห้องชุด dev แต่ server สร้างห้องใหม่); `fix_orphan_channels.py` อยู่ใน repo+server
5. **doc_no สะอาด** — ขยาย /admin/data-clean ครอบ doc_no + ล้างจริงบน server 208 แถว (audit "claude-autoclean")
6. **S5 checklist รอบแรก** — ผ่าน 5/7; **อุด CVE จริง: python-multipart 0.0.29→0.0.32 บน server** (form parser รับจากเน็ตตรง); จดค้าง: **starlette 0.38.6 มี CVE หลายตัวแต่ติด pin <0.40 → ต้องวางแผน migration fastapi/starlette เป็นงานแยก**; MSI.TerminalServer/OneDrive เปิดพอร์ตบน server (โอพิจารณาปิด); ข้อ 2 (ไล่ user/role) + ทดสอบ viewer role รอโอ
7. **LineGroupMap 38 กลุ่ม** ลง server DB (19 customer data-backed) — โอแก้ได้ที่ /line/inbox

**ข้อค้นพบสำคัญ:** สลิป template บน **server = HEAD (874261d) แล้ว** — ที่ค้างคือแก้ใน **working tree local** ของ session สลิปเก่า (payroll_slip.html + payroll_print_all.html มี .k-tag/.c-extra ยังไม่ commit) → ห้าม commit/checkout ทับ จนกว่า session นั้นปิดงาน; deploy แบบ surgical ปลอดภัยแล้วสำหรับไฟล์อื่น

**Why:** เก็บสถานะรวมเซสชันนี้กันหลงว่าใครทำอะไร deploy อะไรไปแล้ว

**How to apply:** งานแพลนที่เหลือ: A5 (รอ session สลิป), D1 (ทีมเติมราคา), F3 (รอ import เดลี่ ก.ค.), F4 (รอโอเคาะ OCR); server อยู่ v44 ทุก commit ถึง S5 deploy ครบ
