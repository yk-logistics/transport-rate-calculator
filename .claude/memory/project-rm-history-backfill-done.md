---
name: project-rm-history-backfill-done
description: "10ก.ค. ดึงประวัติซ่อม 2018-2026 จาก RM History sheets เข้า production แล้ว 8,237 บิล/16.67M — ตกค้าง 00-0000 + รถป้ายอักษรไทย; ยอดบนชีทเชื่อไม่ได้ (SUBTOTAL ค้าง)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3323cfdd-942a-44da-bc85-095450412c8b
---

**DONE 10 ก.ค. 2026 — apply บน production ครบ 3 ไฟล์** (สเปค `docs/superpowers/specs/
2026-07-09-rm-history-backfill-design.md`, schema v50):
LCB 2,830 บิล = 4.71M · Wangnoi 2,167 = 3.96M · BigC 3,240 = 8.01M
→ รวม **8,237 บิล / 17,442 บรรทัด / 16.67 ล้านบาท**; ข้อสอบเทียบทีละบรรทัดกับสูตรชีท
(net = รวม−ส่วนลด+VAT) **ไม่ตรง 0 บรรทัด**; ยิงซ้ำ = dup ทั้งหมด (idempotent จริง)

**เครื่องมือ:** `tools/import_rm_vehicle_repairs.py` (`--file lcb|wangnoi|bigc|all`,
dry-run default, `--apply`, `--rollback --yes`, `--create-vehicles`) — อยู่บน server ที่
`YK_MVP\tools\` ด้วย; rollback ลบเฉพาะ `import_key LIKE 'rm:<file>:%'` บิลคนคีย์ (key ว่าง) รอด

**ค้นพบเรื่องเงิน (บอกโอแล้ว):** ยอดสรุปบนหน้าชีท RM History **เชื่อไม่ได้** —
`=SUBTOTAL(9, J23:J205)` ล็อกช่วงแถว (ทีมเพิ่มแถวไม่ขยายสูตร) + SUBTOTAL ไม่นับแถวที่ถูก
ซ่อนด้วยฟิลเตอร์ → ค่าซ่อมที่มองไม่เห็น ~6.1M (LCB 2.18/Wangnoi 1.01/BigC 2.91)

**ตกค้าง (โอสั่งต่อได้):** แท็บ `00-0000` ~300 บิลไม่ระบุคัน · รถป้ายอักษรไทย ~24 แท็บ
Wangnoi (`ฏย404`, `บร9785`, หาง DHL) นอก regex `\d{2}-\d{4}` · Vendor ~1,300 ชื่อสะกด
หลากหลายรอ merge · รถ sold 44 คันถูกสร้าง (กรอง active อยู่ทุกจุด ปฏิทินไม่เพี้ยน)

**gotcha:** ก็อป SQLite จาก server ต้องเอา `app.db-wal/-shm` มาด้วย (WAL — ไม่งั้นได้ของเก่า) ·
SQLModel `Field(index=True)` สร้าง `ix_...` ชนชื่อ unique index ที่สร้างเองใน migration →
ตั้ง `ux_maintrecord_import_key` · วันที่ในชีทมี 3 แบบรวม "20 เม.ย. 20"

ต่อยอด: [[project-maint-bill-lines-ocr]] (บิลใหม่เข้าทาง OCR — สเปคกล่องบิล
`2026-07-10-bill-inbox-ocr-queue-design.md` โอเคาะแล้ว ยังไม่ได้เขียนโค้ด)
