# LINE Group Archiver — Design Spec

**วันที่:** 2026-06-11
**สถานะ:** รออนุมัติ spec → เขียน implementation plan
**เจ้าของ:** โอ (ตัดสินใจโดเมน) / Claude Code (implement)

## 1. ปัญหาและเป้าหมาย

ปัญหาปัจจุบันของกลุ่มงานใน LINE:
- รูป/ไฟล์หมดอายุ ดาวน์โหลดย้อนหลังไม่ได้
- ค้นหาข้อความเก่าไม่เจอ

เป้าหมาย: บอท LINE ทางการ (Messaging API) เข้ากลุ่มงาน เก็บ **ทุกข้อความ + ไฟล์สื่อใหม่** ลงเครื่อง (DB + ไฟล์) และ forward เข้า Discord เพื่อใช้ดู/ค้นหาได้ทันที — เป็นฐานข้อมูลให้ระบบ MVP ต่อยอดในอนาคต (ผูก DailyJob, OCR สลิป, หน้า search) และเป็นบัญชี LINE OA ฐานเดียวกับเฟสลูกค้าใน `AGENTS.md`

## 2. การตัดสินใจที่ล็อกแล้ว (จากการ brainstorm 2026-06-11)

| ประเด็น | ตัดสินใจ |
|---------|----------|
| ประวัติย้อนหลัง | **ไม่ดึง** — เริ่มเก็บตั้งแต่วันที่บอทเข้ากลุ่ม (LINE ไม่มี API ย้อนหลัง) |
| ชนิดบอท | **LINE Official Account + Messaging API** เท่านั้น (ไม่ใช้ selfbot — ผิด TOS) |
| ปลายทาง | **ทั้งคู่:** SQLite + ไฟล์ลงเครื่อง (หลัก) และ forward เข้า Discord (หน้าจอดู/ค้นหา) |
| โฮสต์ | เครื่อง MVP ที่เปิด 24 ชม. + **Cloudflare Tunnel** (ฟรี) |
| จำนวนกลุ่ม | หลายกลุ่ม — บอทตัวเดียว, **1 กลุ่มไลน์ = 1 Discord channel** |
| Discord | ใช้ **Discord Bot token** (ไม่ใช่ webhook ต่อห้อง) → สร้าง channel อัตโนมัติเมื่อเจอกลุ่มไลน์ใหม่; โอมี server อยู่แล้ว |
| สถาปัตยกรรม | **service แยก** (แนวทางที่ 1) — ไม่ฝังใน `app/main.py` |

## 3. สถาปัตยกรรม

```
LINE กลุ่ม A,B,C…
   │ webhook (HTTPS ผ่าน Cloudflare Tunnel)
   ▼
line_archiver  (FastAPI, port 8020, เครื่อง MVP)
   ├─ ตรวจ X-Line-Signature (HMAC-SHA256 ด้วย channel secret) — ปัดทุก request ที่ลายเซ็นไม่ผ่าน
   ├─ text → INSERT line_message
   ├─ image/file/video/audio → GET /v2/bot/message/{id}/content ทันที
   │       → เซฟ line_media/<group>/<YYYY-MM>/<msgid>.<ext> → INSERT line_message (media_path)
   └─ forward → Discord REST API (bot token)
           └─ channel ต่อกลุ่ม: ถ้ายังไม่มี → สร้างอัตโนมัติ ตั้งชื่อตามชื่อกลุ่มไลน์
```

**แยกขาดจากระบบเงิน:** Cloudflare Tunnel ชี้เฉพาะ port 8020 — แอป MVP (8010) และ `app.db` ไม่ถูกเปิดสู่อินเทอร์เน็ต บอทพัง/รีสตาร์ทไม่กระทบแอปหลัก

## 4. โครงไฟล์

```
ProjectYK_System/line_archiver/
  main.py            — FastAPI: POST /line/webhook + ตัวประมวลผล event
  line_api.py        — LINE: verify signature, get content, get profile
  discord_api.py     — Discord REST: ensure channel, post message/file
  db.py              — SQLite schema + helpers (DB แยก: line_archive.db)
  .env               — LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN,
                       DISCORD_BOT_TOKEN, DISCORD_GUILD_ID  (ห้าม commit)
  start_archiver.bat — รัน uvicorn + cloudflared
  line_archive.db    — (สร้างตอนรัน, ห้าม commit)
  line_media/        — ไฟล์สื่อ (ห้าม commit)
```

- ใช้ venv เดิมของ `app/` (มี fastapi/uvicorn อยู่แล้ว) + เพิ่ม `httpx` ถ้ายังไม่มี
- ไม่ใช้ line-bot-sdk / discord.py — คุย REST ตรงด้วย httpx (ลด dependency, ตรวจสอบง่าย)
- เพิ่ม `.gitignore`: `line_archive.db`, `line_media/`, `line_archiver/.env`

## 5. Schema (`line_archive.db`)

```sql
line_group   (group_id TEXT PK, name TEXT, discord_channel_id TEXT,
              joined_at TEXT, active INTEGER DEFAULT 1)

line_user    (user_id TEXT PK, display_name TEXT, alias TEXT)
             -- display_name จาก LINE profile API (cache);
             -- alias = ชื่อที่ทีมตั้งเองทีหลัง (สไตล์ alias_map.py)

line_message (id INTEGER PK AUTOINCREMENT,
              line_message_id TEXT UNIQUE,   -- กัน insert ซ้ำจาก redelivery
              group_id TEXT, user_id TEXT,
              msg_type TEXT,                 -- text|image|video|audio|file|sticker|other
              text TEXT,                     -- เนื้อความ (ถ้ามี)
              media_path TEXT,               -- path ไฟล์ที่เซฟ (ถ้ามี)
              sent_at TEXT,                  -- เวลาจริงจาก LINE (ISO, เวลาไทย)
              received_at TEXT,
              discord_forwarded INTEGER DEFAULT 0)
```

## 6. การจัดการ error / เคสขอบ

- **เครื่องดับ/เน็ตหลุดสั้น ๆ:** เปิด *webhook redelivery* ใน LINE Developers console — LINE ยิงซ้ำให้; `line_message_id UNIQUE` กันบันทึกซ้ำ
- **Discord ล่ม/ติด rate limit:** บันทึก DB ก่อนเสมอ (source of truth) แล้วค่อย forward; ถ้า forward พลาด → `discord_forwarded=0` และ retry รอบหลัง (background task ทุก ~5 นาที) — ข้อมูลไม่หายแม้ Discord มีปัญหา
- **ดึงชื่อคนส่งไม่ได้:** เก็บ `user_id` ไว้ก่อน แสดงเป็น id ย่อ จนกว่าจะตั้ง alias
- **sticker:** เก็บ sticker id เป็น text (ไม่ดาวน์โหลดภาพ sticker)
- **ไฟล์ใหญ่ (วิดีโอ):** เซฟลงเครื่องเสมอ; ฝั่ง Discord ถ้าเกินลิมิตอัปโหลด (~10MB) ส่งเป็นข้อความแจ้งชื่อไฟล์+path แทนตัวไฟล์

## 7. สิ่งที่โอต้องทำเอง (จะมี checklist ละเอียดตอน implement)

1. สมัคร LINE Developers (ฟรี) → สร้าง provider + Messaging API channel → เปิด "Allow bot to join group chats" → เอา channel secret / access token มาใส่ `.env`
2. สร้าง Discord Application + Bot (ฟรี) → เชิญเข้า server ตัวเอง พร้อมสิทธิ์ Manage Channels + Send Messages + Attach Files → เอา bot token + guild id ใส่ `.env`
3. เชิญบอทไลน์เข้ากลุ่มที่ต้องการเก็บ

**หมายเหตุ Cloudflare Tunnel:** quick tunnel (ฟรี ไม่ต้องมีโดเมน) URL จะเปลี่ยนทุกครั้งที่รีสตาร์ท tunnel → ต้องอัปเดต webhook URL ใน LINE console ตาม ถ้ารีสตาร์ทบ่อยจนรำคาญ ค่อยอัปเกรดเป็น named tunnel (ต้องมีโดเมนของตัวเอง ~300–400 บาท/ปี) — เริ่มจาก quick tunnel ก่อน

## 8. นอกขอบเขต (รอบนี้ไม่ทำ)

- ดึงประวัติย้อนหลัง (LINE ไม่มี API)
- UI ค้นหาในแอป MVP (เฟสถัดไป — อ่านจาก `line_archive.db` ได้เลย)
- OCR / ผูก DailyJob / ตอบกลับอัตโนมัติในกลุ่ม (เฟสถัดไป)
- บอทส่งข้อความเข้ากลุ่มไลน์ (รับอย่างเดียว)

## 9. เกณฑ์ความสำเร็จ

1. ส่งข้อความ text ในกลุ่มทดสอบ → ปรากฏใน `line_message` และเด้งใน Discord channel ของกลุ่มนั้น ภายในไม่กี่วินาที
2. ส่งรูปในกลุ่ม → ไฟล์จริงอยู่ใน `line_media/...` เปิดดูได้ + รูปโผล่ใน Discord
3. เชิญบอทเข้ากลุ่มใหม่ → Discord channel ใหม่ถูกสร้างอัตโนมัติ
4. ปิด process บอทชั่วคราวแล้วส่งข้อความ → เปิดกลับมา + LINE redelivery → ข้อความไม่หาย ไม่ซ้ำ
5. แอป MVP หลัก (port 8010) ไม่ถูกแตะต้องเลยใน diff
