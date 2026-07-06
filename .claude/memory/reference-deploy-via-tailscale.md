---
name: reference-deploy-via-tailscale
description: "Deploy to YK server works via Tailscale (yklog@100.97.150.114) even when HOME machine moved to a different LAN — SSH over Tailscale, not LAN .197"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 91ddce0a-48bd-4312-affe-febfb58477d1
---

เครื่อง HOME ("Home" hostname) ย้ายวงแลนได้ — ตอนนั้น LAN IP server (192.168.1.197) จะ unreachable (ping = "Destination host unreachable", คนละ subnet). **แต่ deploy ยังทำได้ผ่าน Tailscale.**

**Tailscale IPs:** home=100.71.13.122, **yk (server)=100.97.150.114**. `tailscale status` ดูได้. SSH: `ssh yklog@100.97.150.114` (user yk\yklog, passwordless key). [[reference-ssh-to-yk-machine]] เดิมพูดถึง LAN .197 — Tailscale คือทางสำรองที่ใช้ได้ข้ามแลน.

**Gotcha SSH→PowerShell (server default shell = PowerShell ไม่ใช่ bash):**
- `&&` ใช้ไม่ได้ (ใช้ `;` หรือ `Set-Location X; & cmd`).
- quote ซ้อน `\\\"Name='python.exe'\\\"` พังเสมอ → **เขียน .ps1/.py ส่ง scp ไปรัน** ด้วย `powershell -NoProfile -ExecutionPolicy Bypass -File X.ps1`. อย่า inline filter ซับซ้อน.
- ⚠️ **env var inline ก็พังเงียบ (เจ็บจริง 6ก.ค.2026):** `\$env:DATABASE_URL='...'` ผ่าน bash→ssh→powershell ตั้งไม่ติดโดยไม่ error → สคริปต์ "จำลอง" ที่นึกว่าชี้ DB สำเนา **commit ลง DB จริง** (โชคดีเป็นตาราง suggestion + idempotent) — **การทดลองที่ต้องเขียน DB: ให้สคริปต์ .py เซ็ต env/path เองข้างในไฟล์ แล้ว scp ไปรัน; ห้ามพึ่ง env จาก command line ข้าม ssh**

**Deploy ครบ (night-run 2026-06-28, สำเร็จ):**
1. backup server DB: `Copy-Item app.db app.db.bak_before_<x>` (กฎเหล็ก).
2. โค้ด: `bash ProjectYK_System/tools/deploy_mvp_to_server.sh` (ส่ง .py+services+templates, **ไม่แตะ DB by design**).
3. ถ้าต้องส่ง DB ด้วย: stop app (.ps1: Stop-ScheduledTask YK_MVP_APP + kill python ที่ CommandLine match YK_MVP/main.py + รอ port 8010 ปลด) → `scp app.db yklog@100.97.150.114:C:/Users/yklog/YK_MVP/app/app.db` → restart (.ps1: Start-ScheduledTask + รอ 12s + เช็ค port 8010).
4. verify: รัน inspect .py บน server (นับ payruns/emps) + `curl https://app.yklogistics.uk/login` = 200, `/payroll` = 303.

server app path: `C:/Users/yklog/YK_MVP/app`. app รันใต้ venv ของ server. ดู [[reference-mvp-deploy-restart-gotcha]] (kill by path กันโค้ดเก่า).
