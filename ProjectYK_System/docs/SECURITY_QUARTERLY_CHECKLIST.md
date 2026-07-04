# Checklist ตรวจเจาะรายไตรมาส (S5) — runbook ให้โมเดลเด็ก/คนรันได้

> รันทุก 3 เดือน (ม.ค./เม.ย./ก.ค./ต.ค.) บนเครื่อง server ผ่าน SSH
> (`ssh yklog@100.97.150.114` — passwordless จากเครื่อง Dev) — ทุกข้อ read-only
> ยกเว้นข้อที่เขียนว่า "แก้"; ผลตรวจสรุปส่งโอ + จดวันที่รันท้ายไฟล์นี้

## 1. พอร์ตเปิด / บริการแปลก (บน server)
```powershell
netstat -ano | findstr LISTENING
Get-Service | Where-Object {$_.Status -eq 'Running'} | Sort-Object DisplayName
```
- ที่ควรเปิด: 8010 (MVP), 8020 (LINE archiver), 443/80 (reverse proxy ถ้ามี), Tailscale
- เจอพอร์ต/บริการที่ไม่รู้จัก → จดชื่อ+PID ถามก่อนปิด (`tasklist /svc /FI "PID eq <pid>"`)
- RDP ต้องปิดอยู่ (3389 ห้ามโผล่), XAMPP ห้ามกลับมา

## 2. บัญชีผู้ใช้
- /admin/users: ไล่รายชื่อกับโอ — คนออกแล้วต้อง disabled ทุกคน
- ตรวจ role: ใครถือ admin เกินจำเป็นไหม; office/accountant ตรงหน้าที่จริงไหม
- /admin/permissions: override รายคนตกค้างจากคนที่ย้ายหน้าที่แล้วไหม
- /admin/audit ย้อน 90 วัน: มีการแก้เงินนอกเวลางานผิดปกติไหม

## 3. Dependency เก่า / ช่องโหว่
```powershell
cd C:\...\ProjectYK_System\app
.venv\Scripts\pip list --outdated
.venv\Scripts\pip install pip-audit && .venv\Scripts\pip-audit
```
- เทียบ CVE ที่ขึ้น HIGH/CRITICAL — **ห้ามอัปเกรด fastapi/starlette เกิน pin**
  (fastapi<0.115, starlette<0.40 — Jinja2 globals พัง ดู CLAUDE.md) นอกนั้นอัปได้หลังเทสต์

## 4. ไฟล์/สิทธิ์/ของลับ
- ตรวจว่าไม่มี secret ใหม่หลุดเข้า git: `git log --diff-filter=A --name-only -20`
  ไล่หาไฟล์ .env/.json key ที่เผลอ commit
- สิทธิ์โฟลเดอร์ app: มีแต่ user ระบบที่ต้องใช้; ไฟล์ key Google อ่านได้เฉพาะ service user
- token LINE/Discord อายุเกิน 1 ปี → rotate (S3 — จดวันที่ rotate ล่าสุดด้วย)

## 5. Backup ยังหายใจ (ผูกกับ S1)
- /admin/server-health: backup ล่าสุดต้องไม่เกิน 24 ชม.; External ไม่เกิน 10 วัน
- เครื่อง Dev: `C:\Users\guole\YK_BACKUPS_MIRROR` มี zip ล่าสุดไหม
- **ซ้อมกู้จริง 1 ครั้งต่อไตรมาส** ตาม docs/BACKUP_RUNBOOK.md (กู้ลงโฟลเดอร์ทดสอบ
  แล้วเปิดด้วย sqlite ดูจำนวนแถว dailyjob — ห้ามทับของจริง)

## 6. HTTPS / โดเมน
- เปิด https://app.yklogistics.uk ดู cert หมดอายุเมื่อไหร่ (ต่ออัตโนมัติทำงานไหม)
- DNS yklogistics.com: A/MX/SPF ครบตาม memory reference-yklogistics-dns

## 7. ทดสอบเจาะเบา ๆ (จากเครื่องนอก Tailscale)
- `ssh yklog@<public ip>` ต้องเข้าไม่ได้ (SSH จำกัดวง Tailscale)
- เปิด /admin/* โดยไม่ล็อกอิน → ต้องเด้ง /login
- ล็อกอินผิด 5 ครั้งติด → ต้องโดนล็อก (login_guard)
- role viewer: ลอง POST แก้ข้อมูล → ต้อง 403; เปิด /api/daily/grid-data → ต้องไม่มี kb_amount

## ประวัติการรัน
| วันที่ | ผู้รัน | ผล/ประเด็น |
|-------|-------|-----------|
| 4 ก.ค. 2569 | Claude (Fable) | **รอบแรก — ผ่าน 5/7 ข้อ, แก้จริง 1 เรื่อง:** ①พอร์ต: ครบตามคาด ไม่มี RDP/XAMPP; ⚠ พบ MSI.TerminalServer/CentralServer (ซอฟต์แวร์เมนบอร์ด MSI เปิดพอร์ตฟัง) + OneDrive — โอพิจารณาปิดถ้าไม่ใช้ ③pip-audit: **python-multipart 0.0.29 มี 3 CVE → อัป 0.0.32 + เทสต์ 424 ผ่าน + deploy server แล้ววันเดียวกัน**; starlette 0.38.6 มี CVE หลายตัวแต่ติด pin (<0.40) — ต้องวางแผน migration fastapi/starlette แยกงาน (Jinja2 globals พัง); pytest CVE = dev-only ④ไม่มี secret ใน git ⑤ชั้น1 03:00 วันนี้ ✓ / ชั้น3 dev ดูดวันนี้ ✓ / Drive ติด SA quota (รอ OAuth โอ) / ซ้อมกู้ทำแล้ว 3 ก.ค. (S1) ⑥cert หมด 9 ก.ย. 2026 (Cloudflare ต่อเอง) ⑦/admin ไม่ล็อกอิน→303 ✓, login ผิด 5 ครั้ง→429 ✓, SSH public IP→timeout ✓ · **ค้างให้โอ:** ②ไล่รายชื่อ user/role กับโอ + ⑦ทดสอบ role viewer (ไม่มีรหัส viewer ให้ทดสอบ) |
