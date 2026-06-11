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

## อัปเกรดเป็น NAMED TUNNEL — `line.yklogistics.com` (URL คงที่ ทำครั้งเดียวจบ)

> ⚠️ **อีเมล @yklogistics.com ใช้งานจริง — ขั้นตอนนี้ออกแบบมาไม่ให้อีเมลล่ม**
> โดเมนนี้ DNS อยู่ที่ hosting (24webhost) การทำ named tunnel ฟรีต้องย้าย
> nameserver มา Cloudflare เราจะย้ายแบบ "ตรวจ DNS ให้ครบก่อนสลับ"

### DNS records เดิมที่ "ห้ามหาย" (จดไว้ก่อนเริ่ม)

| Type | Name | Value | หน้าที่ |
|------|------|-------|--------|
| A | yklogistics.com | `5.223.56.39` | เว็บ + mail server |
| MX | yklogistics.com | `0 yklogistics.com` | **รับอีเมล** |
| TXT | yklogistics.com | `v=spf1 +a +mx +ip4:5.223.56.39 ~all` | **SPF** |

(ถ้ามี record อื่นใน cPanel > Zone Editor เช่น DKIM, autodiscover, www — จดเพิ่มให้หมดก่อน)

### ขั้นตอน (ทำตามลำดับ ห้ามข้าม)

**1. เพิ่มโดเมนเข้า Cloudflare (ยังไม่สลับ NS)**
- สมัคร cloudflare.com (ฟรี) > Add a site > `yklogistics.com` > เลือก **Free plan**
- Cloudflare จะสแกน DNS เดิมให้อัตโนมัติ

**2. ⭐ ตรวจ DNS ที่ Cloudflare สแกนมา — จุดชี้เป็นชี้ตายของอีเมล**
- ในหน้า DNS ของ Cloudflare เทียบกับตาราง "ห้ามหาย" ข้างบน
- **A, MX, TXT(SPF) ต้องมาครบทั้ง 3** — ถ้าขาด **เพิ่มเองด้วยมือ** ให้ตรงเป๊ะ
- MX/อีเมล records ตั้งเป็น **DNS only (เมฆเทา)** ไม่ใช่ Proxied (เมฆส้ม)

**3. ค่อยสลับ nameserver ที่ผู้ให้บริการโดเมน**
- Cloudflare จะให้ NS 2 ตัว (เช่น `xxx.ns.cloudflare.com`)
- เข้าที่จดทะเบียนโดเมน/24webhost > เปลี่ยน nameserver เป็นของ Cloudflare
- รอ propagate (ไม่กี่นาที — ไม่กี่ชั่วโมง)

**4. ✅ ตรวจว่าอีเมลยังทำงาน (ก่อนทำ tunnel)**
- ลองส่งอีเมลเข้า @yklogistics.com จากเมลอื่น → ต้องเข้าได้ปกติ
- ถ้าเข้าไม่ได้ → กลับไปเช็คข้อ 2 (MX/SPF หาย) **อย่าไปต่อจนกว่าอีเมลปกติ**

**5. สร้าง tunnel (รันใน PowerShell บนเครื่อง server)**
```powershell
$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
& $cf tunnel login                                   # เลือก yklogistics.com
& $cf tunnel create yk-line                          # จำ <tunnel-id> ที่โชว์
& $cf tunnel route dns yk-line line.yklogistics.com  # สร้าง CNAME ให้อัตโนมัติ
```

**6. สร้าง config** ที่ `C:\Users\<user>\.cloudflared\config.yml`
(แทน `<user>` และ `<tunnel-id>` เป็นของจริง):
```yaml
tunnel: yk-line
credentials-file: C:\Users\<user>\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: line.yklogistics.com
    service: http://127.0.0.1:8020
  - service: http_status:404
```

**7. แก้ `start_all.bat` บรรทัดเดียว:**
```
set "TUNNEL_NAME=yk-line"
```

**8. ตั้ง LINE Webhook URL ครั้งสุดท้าย:**
`https://line.yklogistics.com/line/webhook` → Verify → Success

เสร็จ! ต่อจากนี้ดับเบิลคลิก `start_all.bat` อย่างเดียว ไม่ต้องแตะ LINE อีกเลย
URL `line.yklogistics.com` ไม่เปลี่ยน bandwidth ไม่จำกัด รัน 24 ชม.ได้

---

## เปิดอัตโนมัติเมื่อเครื่องบูต (ไม่บังคับ)

อยากให้ระบบขึ้นเองหลังเครื่องรีสตาร์ท:
1. กด `Win + R` พิมพ์ `shell:startup` แล้ว Enter
2. คลิกขวาในโฟลเดอร์ที่เปิดมา > New > Shortcut
3. ชี้ไปที่ `...\ProjectYK_System\line_archiver\start_all.bat`

> หมายเหตุ: ถ้ายังเป็น quick tunnel ต้องมาอัปเดต Webhook URL ใน LINE เองอยู่ดีหลังบูต
> named tunnel เท่านั้นที่บูตแล้วใช้ได้เลยโดยไม่ต้องแตะอะไร
