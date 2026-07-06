# BACKUP_RUNBOOK — สำรอง 3 ชั้น + วิธีกู้ (S1)

> ทำเมื่อ 3 ก.ค. 2026 · เขียนให้คน/โมเดลเด็กทำตามได้โดยไม่ต้องเดา
> หลักคิด: **ของร้อน** (ฐานข้อมูลเงิน+ตั้งค่า ~16MB zip) สำรองถี่อัตโนมัติ / **ของเย็น** (รูปไลน์ ~4GB) ลงแผ่นรายสัปดาห์

## ภาพรวม 3 ชั้น (สถานะดูได้ที่ /admin/server-health การ์ด "สำรองข้อมูล 3 ชั้น")

| ชั้น | อะไร | เมื่อไหร่ | อยู่ที่ไหน | ใครทำ |
|---|---|---|---|---|
| 1 | zip ของร้อน: app.db + line_archive.db (snapshot ปลอดภัยขณะแอปรัน) + .env archiver/slip_reader + start_mvp.bat/start.bat + oatside config 2 ไฟล์ + key Google | ทุกคืน 03:00 (task `YK_MVP_HOT_BACKUP` บน server, รันเป็น SYSTEM) | `D:\YK_BACKUPS\daily` (เก็บ 14) + `weekly` (อาทิตย์ละชุด เก็บ 8) | อัตโนมัติ |
| 2 | ของเย็น: รูปไลน์ทั้งหมด (`line_media`) + zip ชั้น 1 ทุกชุด | รายสัปดาห์ — โอเสียบ External ที่**เครื่อง server** → /admin/server-health → ปุ่ม "💾 Backup ลงแผ่นนี้" (robocopy incremental ครั้งแรก ~10 นาที ครั้งถัดไป ~2-3 นาที) | `<แผ่น>:\YK_BACKUP\` | โอ (การ์ดเตือนถ้าเกิน 10 วัน) |
| 3 | สำเนา zip ชั้น 1 คืนล่าสุด **นอกเครื่อง server** | ทุกวัน 09:30 เมื่อเครื่อง Dev โอเปิดอยู่ (task `YK_PULL_BACKUP` บนเครื่อง Dev, ดูดผ่าน Tailscale) | เครื่อง Dev: `C:\Users\guole\YK_BACKUPS_MIRROR` (เก็บ 14) | อัตโนมัติ |

- backup พังคืนไหน → เด้ง **Discord** (channel line-archiver-alerts / yk-backup-alerts) + การ์ด G1 แดง (แดงเองด้วยถ้าชุดล่าสุดเก่ากว่า 26 ชม.)
- ⚠️ gotcha ชั้น 3 (เจอ+แก้แล้ว 6 ก.ค. 2026): เครื่อง Dev เป็นโน้ตบุ๊ก — task scheduler default **ไม่ยอมเริ่มงานตอนใช้แบต** ทำ pull เงียบหายวันที่ไม่เสียบสาย (code 0x800710E0) → ตั้ง AllowStartIfOnBatteries + StartWhenAvailable (รันย้อนถ้าพลาดเวลา) แล้ว; ถ้าสร้าง task ใหม่บนโน้ตบุ๊กต้องตั้ง 2 ตัวนี้เสมอ
- สคริปต์ต้นทางอยู่ใน repo: `ProjectYK_System/tools/server_backup/backup_tier1.py` (server: `C:\Users\yklog\YK_MVP\backup_tier1.py`) + `pull_backup_dev.ps1` (Dev)
- ✅ **ชั้น Google Drive ทำงานแล้ว (6 ก.ค. 2026)**: โอ consent OAuth (สถานะ In production) + ทดสอบจริงผ่าน `drive_ok=true` — zip ขึ้นโฟลเดอร์ `YK_BACKUPS_HOT/daily` ใน Drive โอทุกคืน; token = secret #10 (server: `YK_MVP/app/gdrive_token.json`, dev: รากโปรเจกต์ gitignored); §Drive ด้านล่างเก็บไว้เผื่อต้อง re-setup

## §Drive — เปิดชั้น Google Drive (โอทำครั้งเดียว ~5 นาที; โค้ดพร้อมหมดแล้ว)

1. เปิด https://console.cloud.google.com/apis/credentials (โปรเจกต์ **noble-history-446303** เดิมของ SA)
2. ถ้ายังไม่เคยตั้ง OAuth consent screen: เมนู "OAuth consent screen" → External → กรอกชื่อแอป `yk-backup` + อีเมลโอ → Save ผ่านทุกหน้า → **สำคัญ: กด "PUBLISH APP" ให้สถานะเป็น In production** (ถ้าปล่อยเป็น Testing → refresh token **หมดอายุทุก 7 วัน** = backup Drive ตายเงียบ; แอป unverified ไม่เป็นไร ใช้เอง)
3. Credentials → **+ CREATE CREDENTIALS → OAuth client ID → Application type: Desktop app** ชื่อ `yk-backup` → Create → **Download JSON** (ได้ไฟล์ `client_secret_….json`)
4. บนเครื่อง Dev (เครื่องโอ) เปิด terminal ที่ราก repo:
   ```powershell
   pip install google-auth-oauthlib   # ใช้เฉพาะตอน setup; server ไม่ต้องลง
   python ProjectYK_System/tools/server_backup/gdrive_oauth.py setup --client-secret "<path ไฟล์ที่โหลด>"
   ```
   → browser เด้งให้เลือกบัญชี guolekung → หน้าเตือน unverified กด Advanced → Go to yk-backup → Allow
   → สคริปต์เขียน `gdrive_token.json` + **ทดสอบสร้างโฟลเดอร์ YK_BACKUPS_HOT ใน Drive ทันที** + พิมพ์คำสั่ง scp ให้
5. รันคำสั่ง scp ที่สคริปต์พิมพ์ (ส่ง token ขึ้น server) — จบ. คืนนั้น 03:00 backup จะอัป Drive เอง
6. ตรวจผล: เช้าวันถัดไปดู `D:\YK_BACKUPS\last_run.json` → `"drive_ok": true` หรือการ์ดบน /admin/server-health; ทดสอบทันทีก็ได้: `ssh yklog@100.97.150.114` แล้ว `python C:\Users\yklog\YK_MVP\gdrive_oauth.py test`

- scope ที่ขอ = `drive.file` (เห็น/แก้เฉพาะไฟล์ที่ตัวเองสร้าง) — ปลอดภัยต่อไฟล์อื่นใน Drive โอ; พื้นที่ ~350MB (14 daily + 8 weekly × 16MB)
- token = secret #10 ใน `SECRETS_INVENTORY.md` (วิธีหมุน/ถอนสิทธิ์อยู่ที่นั่น)

## วิธีกู้ (restore) — ซ้อมจริงแล้ว 3 ก.ค. 2026 (integrity ok ทั้ง 2 DB)

### กู้ฐานข้อมูลระบบ (app.db) — เคสดิสก์พัง/ransomware/ไฟล์เสีย
1. หา zip ล่าสุด: `D:\YK_BACKUPS\daily\yk_hot_*.zip` (server) — ถ้าเครื่อง server ตายทั้งเครื่อง ใช้สำเนาบนเครื่อง Dev `C:\Users\guole\YK_BACKUPS_MIRROR` หรือแผ่น External `\YK_BACKUP\hot_zips`
2. แตก zip → ได้ `db/app.db`, `db/line_archive.db`, `config/...`
3. เช็คก่อนใช้: `python -c "import sqlite3; print(sqlite3.connect(r'db/app.db').execute('pragma integrity_check').fetchone())"` ต้องได้ `ok`
4. หยุดแอป: `Stop-ScheduledTask YK_MVP_APP` + ปิด process พอร์ต 8010 (ดู §0.1 ใน MVP_TASK_SPECS)
5. เก็บของเดิมไว้ก่อน: rename `app.db` → `app.db.broken_<วันที่>` (อย่าลบ)
6. วาง `db/app.db` จาก zip แทนที่ `C:\Users\yklog\YK_MVP\app\app.db`
7. `Start-ScheduledTask YK_MVP_APP` → เปิด https://app.yklogistics.uk เช็ค /health + เปิดรอบ payroll ล่าสุดดูยอดตรง
8. ⚠️ รหัสผ่านผู้ใช้อยู่ใน app.db — กู้จาก zip เก่า = รหัสถอยไปวันนั้นด้วย (ถ้าโอเพิ่งเปลี่ยนรหัส ใช้ RESET_PASSWORD.bat ตั้งใหม่ — ดู MVP_ADMIN_RECOVERY_RUNBOOK)

### กู้ฐานแชทไลน์ (line_archive.db)
เหมือนกันแต่: หยุด service บอทไลน์ (พอร์ต 8020) → วาง `db/line_archive.db` ที่ `C:\Users\yklog\YK_LINE_ARCHIVER\` → start ใหม่; รูปเก่าอยู่ `line_media` (กู้จากแผ่น External `\YK_BACKUP\line_media` ถ้าหาย)

### กู้ config/ตั้งค่า
ไฟล์ใน zip โฟลเดอร์ `config/` ตั้งชื่อ `<โฟลเดอร์แม่>__<ชื่อไฟล์>` เช่น `oatside__oatside_config.json` → วางกลับที่เดิมตามตาราง:
`YK_LINE_ARCHIVER__.env → C:\Users\yklog\YK_LINE_ARCHIVER\.env` · `YK_MVP__start_mvp.bat → C:\Users\yklog\YK_MVP\` · `app__start.bat, app__noble-history-*.json → YK_MVP\app\` · `oatside__*.json → YK_MVP\app\oatside\` · `slip_reader__.env → YK_MVP\slip_reader\`

## ตรวจสุขภาพ backup (ทำเดือนละครั้ง / เมื่อสงสัย)
1. เปิด /admin/server-health — การ์ดชั้น 1 ต้องเขียว + ไม่เกิน 26 ชม.
2. `D:\YK_BACKUPS\last_run.json` ต้อง `"ok": true`
3. ซ้อมกู้: รันคำสั่งเดียว `python ProjectYK_System/tools/server_backup/restore_drill.py` (หา zip ล่าสุดเอง mirror→D:, แตกลง temp, integrity_check ทั้ง 2 DB, นับแถวเทียบขั้นต่ำ, ลบ temp เอง — read-only ทั้งหมด; รันจริงผ่านแล้ว 4 ก.ค. 2026) — **backup ที่ไม่เคยซ้อมกู้ = ไม่มี backup**
4. เครื่อง Dev: `C:\Users\guole\YK_BACKUPS_MIRROR\pull.log` ต้องมี OK ล่าสุดไม่เกิน ~2-3 วัน (เครื่องปิด = ข้ามได้ ไม่ผิด)

## แก้ปัญหา
- **Discord เด้ง 🔴 backup พัง** → ssh เข้า server รัน `C:\Users\yklog\YK_MVP\app\.venv\Scripts\python.exe C:\Users\yklog\YK_MVP\backup_tier1.py` ดู error ตรงๆ (ไทยอ่านได้ — สคริปต์ตั้ง UTF-8 เอง)
- **การ์ดชั้น 1 = "ยังไม่เคยรัน"** → task หาย: รัน `ProjectYK_System/tools/server_backup/` ส่วน install ใหม่ (Register-ScheduledTask YK_MVP_HOT_BACKUP 03:00 SYSTEM)
- **ปุ่มลงแผ่นไม่โผล่** → แผ่นต้องเสียบที่เครื่อง server (ไม่ใช่เครื่องโอ) แล้วรีเฟรช; ไดรฟ์ E:-Z: เท่านั้น
- **อยากเพิ่มไฟล์เข้า backup** → แก้ list `SERVER["extras"]` ใน backup_tier1.py แล้ว scp ทับ (ไม่ต้อง restart อะไร — task อ่านไฟล์ใหม่คืนถัดไป)
