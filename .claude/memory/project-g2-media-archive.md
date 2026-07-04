---
name: project-g2-media-archive
description: "G2 done 4ก.ค.: ย้ายรูปไลน์เก่าลงแผ่น External (v44 MediaArchive) — copy→hash→ลบ + ป้าย EXT-xx; เหลือโอเสียบแผ่นจริงครั้งแรก"
metadata: 
  node_type: memory
  type: project
  originSessionId: d4a29959-9dce-4e25-82a7-9d031c3c20be
---

G2 เสร็จ 4ก.ค. 2026 (v44 deploy บน server แล้ว):

- ตาราง `MediaArchive` (app.db — ห้ามเขียน line_archive.db) + `services/media_archive.py`: RETENTION_DAYS=730, ดิสก์ <25% เตือนย้ายเดือนเก่าสุด
- การ์ดบน /admin/server-health: รูปเก่าสุด/วันครบกำหนด + ปุ่มย้าย 2 โหมด (due / oldest-month) รันใน thread (`_MEDIA_ARCH` state) — ย้ายต่อไฟล์ copy→sha256 ตรง→จดแถว→ค่อยลบต้นทาง
- แผ่นจำด้วย `YK_ARCHIVE.txt` รากแผ่น (label EXT-01.. seq เก็บใน AppSetting `media_archive_disk_seq`); `/line/media/{id}` fallback เสิร์ฟจากแผ่น (หา label แม้อักษรไดรฟ์เปลี่ยน) → ไม่เสียบ = ป้าย SVG ไม่พัง; ZIP /billing/evidence fallback ด้วย
- **GOTCHA:** ปุ่ม Backup ชั้น 2 (S1) เขียน YK_ARCHIVE.txt ของตัวเองที่ `<แผ่น>/YK_BACKUP/YK_ARCHIVE.txt` (ไม่มี label) — คนละไฟล์กับ marker G2 ที่รากแผ่น ไม่ชนกัน
- เทสต์ tests/test_media_archive.py 4 ตัว (100 ไฟล์ hash ตรง/unplug/idempotent/การ์ด) — ชุดเต็ม 421 ผ่าน

**Why:** ดิสก์ server โดนรูปไลน์กิน ~5GB/เดือน นโยบายโอ = เก็บ 2 ปีแล้วย้ายลงแผ่น

**How to apply:** โอเสียบ External ที่เครื่อง server → เปิด /admin/server-health → ปุ่มโผล่เอง; ตอนนี้ยังไม่มีไฟล์ครบกำหนด (archive เริ่ม มิ.ย. 2026 → ครบกำหนดแรก มิ.ย. 2028) ปุ่มโหมดเดือนเก่าสุดใช้ได้เมื่อดิสก์ตึง ดู [[project-s1-backup-3tier]]
