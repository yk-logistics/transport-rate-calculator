# ทะเบียนรหัสลับ (S3) — อยู่ไหน ใครใช้ หมุนยังไง

> อัปเดตล่าสุด: 4 ก.ค. 2026 · กติกา: **หมุนปีละครั้ง** (หรือทันทีเมื่อสงสัยรั่ว) · ห้าม commit ค่า secret ลง git เด็ดขาด
> ตรวจแล้ว 4 ก.ค.: **ไม่มี secret ฝังในโค้ด repo** — ทุกตัวอ่านจากไฟล์บน server ตอนรัน

## ทะเบียน (บนเครื่อง server — C:\Users\yklog)

| # | ไฟล์ | key | ใครใช้ | วิธีหมุน (rotate) | หมุนล่าสุด |
|---|------|-----|--------|-------------------|------------|
| 1 | `YK_MVP\start_mvp.bat` | `YK_SESSION_SECRET` | แอป MVP (คุกกี้ login) | สร้าง hex ใหม่ 48 ตัว แก้ในไฟล์ → restart task `YK_MVP_APP` — **ทุกคนหลุด login ต้องเข้าใหม่** (ทำนอกเวลางาน) | มิ.ย. 2026 (ตั้งครั้งแรก) |
| 2 | `YK_MVP\start_mvp.bat` + `YK_MVP\slip_reader\.env` | `YK_SLIP_INGEST_TOKEN` | slip reader → MVP (`X-Service-Token`) | สคริปต์เดียวจบ: สร้าง hex ใหม่บน server แก้ **2 ไฟล์พร้อมกัน** → restart `YK_MVP_APP` → ทดสอบ `fetch_config()` ต้องได้ 200 (ดูท้ายไฟล์นี้) | **4 ก.ค. 2026** ✅ |
| 3 | `YK_MVP\slip_reader\.env` | `ANTHROPIC_API_KEY` | slip reader (อ่านสลิปด้วย Haiku) | console.anthropic.com → สร้าง key ใหม่ → แก้ .env → ปิด key เก่า (**บัญชีโอ**) | มิ.ย. 2026 |
| 4 | `YK_LINE_ARCHIVER\.env` | `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN` | บอทเก็บไลน์ (8020) | LINE Developers console → reissue → แก้ .env → `nssm restart YKLineBot` (**บัญชีโอ**) | ยังไม่เคย |
| 5 | `YK_LINE_ARCHIVER\.env` | `DISCORD_BOT_TOKEN` | บอทเก็บไลน์ + backup_tier1.py + mvp_health_poll.py (อ่านไฟล์นี้ตอนรันเพื่อแจ้งเตือน) | Discord Developer Portal → Reset Token → แก้ .env → restart YKLineBot (**บัญชีโอ**) | ยังไม่เคย |
| 6 | `.cloudflared\741eef82-….json` | tunnel credential | cloudflared (task `YK_CLOUDFLARED_TUNNEL`) | `cloudflared tunnel token`/สร้าง tunnel ใหม่ — แทบไม่ต้องหมุนถ้าไม่รั่ว | — |
| 7 | `YK_MVP\app\noble-history-….json` | Google service account key (yk-sheets-editor) | อ่าน Google Sheets/Drive (AR, quote sync) | Google Cloud console → สร้าง key ใหม่ → วางแทน → ลบ key เก่า (**บัญชีโอ**); ตรวจ scope: SA ควรเห็นเฉพาะไฟล์ที่แชร์ให้เท่านั้น | มิ.ย. 2026 (ตั้งครั้งแรก) |
| 8 | `YK_MVP\start_mvp.bat` | `YK_QWEN_KEY` | ปุ่ม ✨ AI เรียบเรียงบน /todo (`services/ai_assist.py` → gateway.9arm.co) | 9arm ออกคีย์ใหม่ → แก้ในไฟล์ (dev: `_Claude Tools\9arm.key` ตัวเดียวกัน) → restart `YK_MVP_APP`; คีย์ฟรี ไม่ผูกเงิน — รั่วแล้วแค่คนอื่นใช้โควต้าฟรีแทน | ก.ค. 2026 (ตั้งครั้งแรก) |
| 9 | `YK_MVP\start_mvp.bat` | `CLAUDE_CODE_OAUTH_TOKEN` | Claude บนหน้า /ai (`claude -p` — โควต้า Max ของโอ) | `claude setup-token` บนเครื่อง dev (**บัญชีโอ อนุมัติในเบราว์เซอร์**) → แก้ในไฟล์ + `_Claude Tools\claude_server.key` (dev) → restart `YK_MVP_APP` → revoke ตัวเก่าใน claude.ai Settings; ดู AI_CHAT_RUNBOOK.md | **5 ก.ค. 2026** (ตั้งครั้งแรก) |

| 10 | `YK_MVP\app\gdrive_token.json` *(ยังไม่มี — รอโอ setup)* | Google OAuth refresh token (scope drive.file) | backup ชั้น Drive (`gdrive_oauth.py` ← backup_tier1) | รัน `gdrive_oauth.py setup` ใหม่บน Dev (**บัญชีโอ ยินยอมในเบราว์เซอร์**) → scp ทับบน server; ถอนสิทธิ์เก่า: myaccount.google.com → Security → Third-party access | — (รอตั้งครั้งแรก — ดู BACKUP_RUNBOOK §Drive) |

ฝั่งเครื่อง Dev (เครื่องโอ): มี SA json ตัวเดียวกัน + `.env` ของ tools บางตัว — ไม่ expose ออกเน็ต ความเสี่ยงต่ำกว่า แต่หมุนพร้อมกันเมื่อหมุน #7

## หมายเหตุความปลอดภัย

- ไฟล์ทั้งหมดอยู่ใต้โปรไฟล์ `yklog` (เครื่องเข้าได้เฉพาะ SSH key + Tailscale) — ไม่มี secret ใน git ✓
- `YK_ADMIN_TEMP_PW=changeme1` ใน start_mvp.bat ใช้เฉพาะ seed ครั้งแรก — รหัสจริงเปลี่ยนแล้ว ไม่ใช่ secret
- rotate #2 ทำ 4 ก.ค. เพราะค่าเก่าเคยโผล่ในหน้าจอ session ทำงาน — ถือเป็นซ้อมหมุนจริงรอบแรกด้วย

## วิธีหมุน YK_SLIP_INGEST_TOKEN (ซ้อมแล้ว 4 ก.ค. — ใช้ได้จริง)

```powershell
# รันบน server (สร้าง token ใหม่ในเครื่อง ไม่ผ่านหน้าจอ):
$bytes = New-Object byte[] 24
(New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
$new = ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''
# แก้ 2 ไฟล์: start_mvp.bat (set YK_SLIP_INGEST_TOKEN=...) + slip_reader\.env (YK_SLIP_INGEST_TOKEN=...)
# → Stop/Start-ScheduledTask YK_MVP_APP
# → ทดสอบ: โหลด .env แล้วรัน python -c "from slip_reader import mvp_config; print(mvp_config.fetch_config())"
#   ต้องไม่มี key "error" ในผลลัพธ์ (enabled true/false ตาม setting ไม่เกี่ยว)
```

## ตารางหมุนประจำปี

| รอบ | ทำอะไร | ใคร |
|-----|--------|-----|
| ก.ค. ของทุกปี | หมุน #1 #2 (ทำเองบน server ได้เลย) | Claude + โอกดยืนยัน |
| ก.ค. ของทุกปี | หมุน #3 #4 #5 #7 (ต้อง console บัญชีโอ — Claude เตรียมขั้นตอน โอคลิก) | โอ |
| ทุกไตรมาส | เช็คตาม `SECURITY_QUARTERLY_CHECKLIST.md` หมวดของลับ | Claude |
