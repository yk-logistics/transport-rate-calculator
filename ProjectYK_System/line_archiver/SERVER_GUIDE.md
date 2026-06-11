# คู่มือเปิด LINE Archiver บนเครื่อง Server

> เป้าหมาย: ดับเบิลคลิกไฟล์เดียว `start_all.bat` แล้วระบบเก็บข้อความ LINE ทำงานเลย

---

## ครั้งแรกบนเครื่อง Server ใหม่ (ทำครั้งเดียว)

ถ้าย้ายไปเครื่องใหม่ที่ยังไม่เคยตั้งค่า ต้องเตรียม 4 อย่างนี้ก่อน:

1. **มีโฟลเดอร์โปรเจกต์** `Project YK` บนเครื่อง (copy หรือ git clone มา)
2. **venv ของแอป** ต้องมีอยู่ที่ `ProjectYK_System\app\.venv`
   - ถ้ายังไม่มี: รัน `ProjectYK_System\app\start.bat` หนึ่งครั้ง (มันสร้าง venv + ติดตั้ง lib ให้)
   - แล้วติดตั้ง lib เพิ่มของ archiver:
     ```
     ProjectYK_System\app\.venv\Scripts\pip install httpx
     ```
3. **ติดตั้ง cloudflared** (ครั้งเดียว):
   ```
   winget install Cloudflare.cloudflared
   ```
4. **ไฟล์ `.env`** ต้องอยู่ใน `ProjectYK_System\line_archiver\.env` ครบ 4 ค่า
   (ดู `.env.example` / `SETUP_CHECKLIST.md`) — ไฟล์นี้ไม่อยู่ใน git ต้อง copy มาเอง

---

## ทุกครั้งที่เปิดเครื่อง / เปิดใช้งาน

### ขั้นที่ 1 — ดับเบิลคลิก `start_all.bat`

อยู่ที่ `ProjectYK_System\line_archiver\start_all.bat`
จะเปิดให้ 2 หน้าต่าง:
- **"LINE Archiver BOT"** — ตัวบอท (port 8020)
- หน้าต่าง tunnel — cloudflare

> อย่าปิดทั้งสองหน้าต่างระหว่างใช้งาน ปิดเมื่อไหร่ = หยุดเก็บข้อความ

### ขั้นที่ 2 — เฉพาะตอนใช้ QUICK tunnel (URL เปลี่ยนทุกครั้ง)

ในหน้าต่าง tunnel จะมีบรรทัด:
```
https://xxxx-yyyy-zzzz.trycloudflare.com
```
1. copy URL นั้น
2. ไป LINE Developers > channel > Messaging API > **Webhook URL**
3. วาง URL + ต่อท้าย `/line/webhook` เช่น
   `https://xxxx-yyyy-zzzz.trycloudflare.com/line/webhook`
4. กด **Update** แล้วกด **Verify** ให้ขึ้น Success

> ⚠️ ต้องทำขั้นนี้ทุกครั้งที่รีสตาร์ท เพราะ quick tunnel สุ่ม URL ใหม่เสมอ
> **พอตั้ง named tunnel เสร็จ (ดูด้านล่าง) จะข้ามขั้นนี้ได้ตลอดไป**

### ขั้นที่ 3 — เช็คว่าทำงาน

ส่งข้อความทดสอบในกลุ่ม LINE → ต้องเด้งเข้า Discord channel `line-<ชื่อกลุ่ม>`

---

## อัปเกรดเป็น NAMED TUNNEL — `line.yklogistics.uk` (URL คงที่ ทำครั้งเดียวจบ)

> ✅ ใช้โดเมน **yklogistics.uk** (ซื้อผ่าน Cloudflare Registrar — DNS อยู่ Cloudflare แล้ว)
> **แยกจาก yklogistics.com (อีเมล) คนละโดเมน** — ขั้นตอนนี้ไม่แตะอีเมลเลย
> ไม่ต้องย้าย nameserver ไม่ต้องตรวจ MX/SPF อะไรทั้งสิ้น

### ขั้นตอน (รันบนเครื่อง server)

**1. สร้าง tunnel (PowerShell)**
```powershell
$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
& $cf tunnel login                                 # เลือก yklogistics.uk
& $cf tunnel create yk-line                        # จำ <tunnel-id> ที่โชว์
& $cf tunnel route dns yk-line line.yklogistics.uk # สร้าง DNS record ให้อัตโนมัติ
```

**2. สร้าง config** ที่ `C:\Users\<user>\.cloudflared\config.yml`
(แทน `<user>` และ `<tunnel-id>` เป็นของจริง):
```yaml
tunnel: yk-line
credentials-file: C:\Users\<user>\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: line.yklogistics.uk
    service: http://127.0.0.1:8020
  - service: http_status:404
```

**3. แก้ `start_all.bat` บรรทัดเดียว:**
```
set "TUNNEL_NAME=yk-line"
```

**4. ตั้ง LINE Webhook URL ครั้งสุดท้าย:**
`https://line.yklogistics.uk/line/webhook` → Verify → Success

เสร็จ! ต่อจากนี้ดับเบิลคลิก `start_all.bat` อย่างเดียว ไม่ต้องแตะ LINE อีกเลย
URL `line.yklogistics.uk` ไม่เปลี่ยน bandwidth ไม่จำกัด รัน 24 ชม.ได้

---

## เปิดอัตโนมัติเมื่อเครื่องบูต (ไม่บังคับ)

อยากให้ระบบขึ้นเองหลังเครื่องรีสตาร์ท:
1. กด `Win + R` พิมพ์ `shell:startup` แล้ว Enter
2. คลิกขวาในโฟลเดอร์ที่เปิดมา > New > Shortcut
3. ชี้ไปที่ `...\ProjectYK_System\line_archiver\start_all.bat`

> หมายเหตุ: ถ้ายังเป็น quick tunnel ต้องมาอัปเดต Webhook URL ใน LINE เองอยู่ดีหลังบูต
> named tunnel เท่านั้นที่บูตแล้วใช้ได้เลยโดยไม่ต้องแตะอะไร
