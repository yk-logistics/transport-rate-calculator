---
name: project-s1-backup-3tier
description: "S1 สำรอง 3 ชั้น DONE 3ก.ค. — nightly zip→D: + ปุ่ม External + Dev mirror + Discord; GOTCHA ใหญ่: Google ตัดโควต้า service account = SA อัปโหลด Drive ไม่ได้อีกถาวร"
metadata: 
  node_type: memory
  type: project
  originSessionId: 742a8c2c-bba6-475f-bb99-ce05aba9b6ba
---

**S1 DONE 3 ก.ค. 2026 (ซ้อมกู้จริงผ่าน integrity ok ทั้ง 2 DB; runbook docs/BACKUP_RUNBOOK.md):**
- **ชั้น 1**: task `YK_MVP_HOT_BACKUP` (server, SYSTEM, 03:00) รัน `C:\Users\yklog\YK_MVP\backup_tier1.py` (ต้นทาง repo: tools/server_backup/) — snapshot app.db+line_archive.db ด้วย **sqlite backup API** (ห้าม copy ดิบขณะแอปรัน) + .env×2 + start bats + oatside config (**อยู่ app\oatside\ ไม่ใช่ app\**) + key → zip ~16MB ลง `D:\YK_BACKUPS\daily` เก็บ 14 / weekly (อาทิตย์) เก็บ 8; เขียน `last_run.json` ให้การ์ด G1 (แดงเมื่อ fail หรือ >26 ชม.)
- **ชั้น 2**: ปุ่ม "💾 Backup ลงแผ่นนี้" บน /admin/server-health (robocopy line_media+zips ลง `<แผ่น>:\YK_BACKUP` ใน thread, AppSetting external_backup_last, เตือน >10 วัน) — โอยังไม่เคยกดจริง (รอมีแผ่น)
- **ชั้น 3**: task `YK_PULL_BACKUP` (เครื่อง Dev โอ, 09:30) รัน tools/server_backup/pull_backup_dev.ps1 ดูด zip ล่าสุดผ่าน Tailscale → `C:\Users\guole\YK_BACKUPS_MIRROR` เก็บ 14 — **นี่คือสำเนานอกเครื่อง server ตัวหลักตอนนี้**

**GOTCHA:**
1. **Google ตัดโควต้า storage ของ service account (นโยบาย 2025) — SA สร้าง/อัปโหลดไฟล์ Drive ไม่ได้อีกถาวร** (403 storageQuotaExceeded แม้อัปเข้าโฟลเดอร์คนอื่น เพราะไฟล์ owner=SA); ข้อสมมติ "SA อัปได้เลย" ในสเปคเดิมผิด; ทางเดียว = OAuth บัญชีโอ (มี plumbing ใน services/email_oauth.py แต่ client id/secret ยังไม่ตั้งบน server) — **รอโอเคาะค่อยทำ**; สคริปต์เขียนแบบ Drive พัง=ธงเหลือง ไม่ล้มงาน พร้อมเปิดใช้เมื่อมี OAuth
2. Discord ผ่าน urllib ต้องตั้ง **User-Agent** เอง (Cloudflare 403 UA default) + บอทไม่มีสิทธิ์สร้าง channel → post เข้า line-archiver-alerts เดิม; ทดสอบ alert จริงแล้ว (ข้อความ 🔴 3ก.ค. ~15:31 คือเทสต์)
3. คอนโซล Windows: สคริปต์ standalone ที่ log ไทยต้อง sys.stdout.reconfigure(utf-8) ไม่งั้นตายทั้งตัว

verified: รันจริงบน server 2 รอบ + force-fail ทดสอบ alert + restore drill จาก zip จริง (48 ตาราง/170 คน/18 payruns/quotation v35) + pytest tests/test_server_health_backup.py 3 ตัว

related: [[project-master-plan-jul26]] [[reference-mvp-server-deploy]]
