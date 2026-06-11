# Checklist เปิดใช้ LINE Archiver (โอทำเอง ~20 นาที)

## A. ฝั่ง LINE (ฟรี)

1. เข้า https://developers.line.biz/ → login ด้วยบัญชี LINE
2. Create provider (ชื่ออะไรก็ได้ เช่น `YK Logistics`)
3. Create channel → เลือก **Messaging API** → ตั้งชื่อบอท เช่น `YK เก็บข้อความ`
4. แท็บ **Basic settings** → copy `Channel secret` → ใส่ `.env` บรรทัด `LINE_CHANNEL_SECRET=`
5. แท็บ **Messaging API** → กด Issue `Channel access token (long-lived)` → ใส่ `.env` บรรทัด `LINE_CHANNEL_ACCESS_TOKEN=`
6. ใน LINE Official Account Manager (ลิงก์จากแท็บเดียวกัน):
   - **เปิด** "Allow bot to join group chats" (ตั้งค่า > ตอบกลับ > แชทกลุ่ม)
   - **ปิด** auto-reply / greeting message (ไม่งั้นบอทจะตอบสแปมในกลุ่ม)
7. แท็บ **Messaging API** → Webhook settings → **เปิด Use webhook** + **เปิด Webhook redelivery**
   (URL จะมาใส่ในข้อ C)

## B. ฝั่ง Discord (ฟรี)

1. เข้า https://discord.com/developers/applications → New Application ชื่อ `YK Line Archiver`
2. เมนู **Bot** → Reset Token → copy → ใส่ `.env` บรรทัด `DISCORD_BOT_TOKEN=`
3. เมนู **OAuth2 > URL Generator**:
   - Scopes: เลือก `bot`
   - Bot Permissions: เลือก `Manage Channels`, `Send Messages`, `Attach Files`
   - copy URL ที่ได้ → เปิดในเบราว์เซอร์ → เลือก server ของโอ → Authorize
4. ใน Discord app: User Settings > Advanced > เปิด **Developer Mode**
   แล้วคลิกขวาชื่อ server > **Copy Server ID** → ใส่ `.env` บรรทัด `DISCORD_GUILD_ID=`

## C. ฝั่งเครื่อง MVP

1. ติดตั้ง cloudflared (ครั้งเดียว):
   ```
   winget install Cloudflare.cloudflared
   ```
2. คัดลอก `.env.example` เป็น `.env` แล้วใส่ค่าครบ 4 ตัวจากข้อ A/B
3. รัน `start_archiver.bat` (ค้างไว้)
4. เปิด PowerShell อีกหน้าต่าง:
   ```
   cloudflared tunnel --url http://127.0.0.1:8020
   ```
   ค้างไว้ — จะได้ URL แบบ `https://xxxx.trycloudflare.com`
5. เอา URL นั้น + `/line/webhook` ไปใส่ใน LINE Developers > Messaging API > Webhook URL:
   ```
   https://xxxx.trycloudflare.com/line/webhook
   ```
   กด **Verify** ต้องขึ้น Success

> ⚠️ URL เปลี่ยนทุกครั้งที่รีสตาร์ท cloudflared
> รีสตาร์ทเมื่อไหร่ต้องมาอัปเดต Webhook URL ใหม่ด้วย
> ถ้ารำคาญให้ใช้ named tunnel (ต้องมีโดเมน ~300-400 บาท/ปี)

## D. ทดสอบจริง

1. เพิ่มบอทเป็นเพื่อนก่อน (QR จากแท็บ Messaging API) แล้วเชิญเข้ากลุ่มทดสอบ
2. เช็คว่า Discord มี channel ใหม่ `line-<ชื่อกลุ่ม>` + ข้อความ "บอทเริ่มเก็บข้อความกลุ่มนี้แล้ว"
3. พิมพ์ข้อความ + ส่งรูปในกลุ่ม → ต้องเด้งใน Discord ภายในไม่กี่วินาที
4. ไฟล์รูปอยู่ใน `line_media/<group_id>/<YYYY-MM>/` บนเครื่อง
