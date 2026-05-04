# DEPLOYMENT FREE WINDOWS (TAILSCALE)

เป้าหมาย: ให้ 2 ไซท์เข้าใช้งานระบบเดียวกันผ่านอินเทอร์เน็ตอย่างปลอดภัย โดยไม่ต้องซื้อโครงสร้าง cloud แพง

แนวทางหลัก: รันเว็บแอปบน PC เซิร์ฟเวอร์ของคุณ + ใช้ `Tailscale` เชื่อม private network

## 1) Architecture

- Frontend: Web app
- Backend API: รันบนเครื่อง Windows server
- Database: PostgreSQL บนเครื่องเดียวกัน
- File storage: โฟลเดอร์ในเครื่อง (แนบรูป/สแกน)
- Backup: dump DB + zip uploads + sync cloud drive
- Access network: Tailscale (แทนการเปิด public port)

## 2) ทำไมเลือก Tailscale

- ฟรีสำหรับทีมขนาดเล็ก
- ไม่ต้องพึ่ง Global IP หรือ port forwarding
- เลี่ยงปัญหา CGNAT
- ปลอดภัยกว่าการเปิดระบบออกอินเทอร์เน็ตตรงๆ

## 3) เครื่องมือฟรีที่ใช้

- Python + FastAPI
- PostgreSQL
- Node.js (build frontend)
- Caddy (reverse proxy)
- Tailscale
- Windows Task Scheduler (งาน backup)

## 4) ขั้นตอนติดตั้ง (High-level)

### Step A: เตรียมเครื่องเซิร์ฟเวอร์
- ติดตั้ง PostgreSQL
- สร้าง database เช่น `yk_ops`
- ตั้งโฟลเดอร์:
  - `C:\yk-system\apps`
  - `C:\yk-system\data\uploads`
  - `C:\yk-system\data\backups`

### Step B: ติดตั้งและเชื่อม Tailscale
- ติดตั้ง Tailscale บนเครื่องเซิร์ฟเวอร์
- login ด้วยบัญชีหลักบริษัท
- ติดตั้ง Tailscale บนเครื่องผู้ใช้ทั้งสองไซต์
- ทดสอบ ping ผ่านชื่อเครื่องใน tailnet

### Step C: รันแอป
- Backend listen ที่ `127.0.0.1:8000`
- Frontend build เป็น static files
- Caddy serve frontend + proxy `/api` ไป backend

### Step D: เปิดใช้ภายใน tailnet
- เข้าใช้งานผ่านชื่อเครื่อง tailscale เช่น
  - `http://server-name:8080` (หรือโดเมน tailnet ที่ตั้งไว้)

## 5) Security baseline

- ใช้บัญชีผู้ใช้แยก role
- บังคับรหัสผ่านแข็งแรง
- จำกัดสิทธิ์ตาม ROLE_MATRIX
- ปิดพอร์ตสาธารณะจาก internet
- เปิดเฉพาะใน tailnet

## 6) Backup/Restore (บังคับทำ)

### รายวัน (อัตโนมัติ)
- `pg_dump` ฐานข้อมูล
- zip โฟลเดอร์ uploads
- เก็บไฟล์ลง `data\backups\YYYYMMDD`
- sync สำเนาไป OneDrive/Google Drive

### รายสัปดาห์
- ทดสอบ restore จริงในเครื่องทดสอบ 1 ครั้ง

## 7) Monitoring ขั้นต่ำ

- ตรวจสถานะ service ทุกเช้า
- ตรวจพื้นที่ disk คงเหลือ
- ตรวจ backup success/fail logs

## 8) แผนสำรอง

- ถ้าเครื่องเซิร์ฟเวอร์เสีย:
  - restore DB ล่าสุด
  - restore uploads
  - ชี้ Tailscale ไปเครื่องสำรอง

## 9) ทางเลือกสำรอง (ไม่แนะนำเป็นหลัก)

- Global IP + DDNS (เช่น no-ip) ทำได้ แต่ต้องรับภาระ:
  - port forwarding
  - firewall hardening
  - security exposure สูงขึ้น

สรุป: สำหรับระบบธุรกรรมจริงของคุณ ใช้ Tailscale เป็นมาตรฐานหลักเหมาะกว่า

