# Claude Done Alarm — เสียงแจ้งเตือนเมื่อ Claude เสร็จ/ถาม

วันที่: 2026-06-29
สถานะ: design approved, รอเขียน plan

## ปัญหา

โอรัน Claude Code โหมด Max แล้วคิดนานมาก ต้องนั่งเฝ้าจอ. ต้องการเสียงเตือน
**ดังจนกว่าจะเดินมาปิด** เมื่อ Claude เสร็จงานหรือต้องถาม/ขออนุญาต และ
**คุมเปิด/ปิดได้ทั้งจากจอบ้านและจากมือถือ** (โอใช้ Remote Control `/rc` ผ่านมือถือด้วย)
— กันหลับแล้วไม่ตื่น หรือเวลานั่งอยู่หน้าจอก็ปิดได้.

## ข้อกำหนด (ยืนยันกับโอแล้ว)

1. เสียงดังทั้งตอน Claude **ทำงานเสร็จ** และตอน **ถาม/ขออนุญาต**.
2. เสียง **ดังวนซ้ำไปเรื่อยๆ** จนกว่าจะถูกสั่งหยุด (ไม่ใช่ดังรอบเดียว).
3. หยุดเสียงได้ทั้งจาก **จอบ้าน** และจาก **มือถือ** — มือถือต้องสั่งดับเสียงบ้านได้จริง (real-time), ยอมให้ซับซ้อนขึ้น.
4. มือถือสั่งหยุดผ่าน **หน้าเว็บปุ่มหยุดแยก** (ไม่ใช่พิมพ์ใน session).
5. เด้งเตือนมือถือด้วย (push notification ครั้งเดียว) — เสริมเสียงบ้าน.
6. เปิด/ปิดทั้งระบบได้ (กันหลับ) ผ่าน **ปุ่มบนหน้าเว็บ** (ไม่ทำ slash command — YAGNI).
7. ไฟล์เสียง: Claude หา/สร้างไฟล์เตือนดังๆ ให้.
8. expose ออกมือถือผ่าน **Tailscale** (มีอยู่แล้ว, IP เครื่องบ้าน = 100.71.13.122).

## ขอบเขตที่ตัดออก (YAGNI)

- ไม่ทำ slash command — ปุ่มเว็บครอบคลุมแล้ว.
- ไม่ expose ออกเน็ตสาธารณะ (ไม่ใช้ Cloudflare tunnel) — Tailscale ปลอดภัยกว่าและพอ.
- ไม่ผูกเข้า LINE archiver (port 8020) — แยก service ใหม่เพื่อ debug ง่าย.
- ไม่มีหลายระดับเสียง / หลายโทน / ตั้งเวลา snooze.

## สถาปัตยกรรม — 3 ชิ้น

ทั้งหมดอยู่นอก app YK (เป็นเครื่องมือส่วน Claude Code) — เสนอวางที่
`_Claude Tools/done-alarm/` (โฟลเดอร์เดียวกันสไตล์ qwen.ps1 ฯลฯ).

### ชิ้นที่ 1 — Alarm service (Python, port 8030)

ไฟล์: `_Claude Tools/done-alarm/alarm_service.py`
ใช้ stdlib เท่านั้น (http.server + winsound) — ไม่เพิ่ม dependency.

สถานะใน memory (ไม่ต้องมี DB):
- `ringing: bool` — กำลังเล่นเสียงวนอยู่ไหม
- `enabled: bool` — ระบบเปิดอยู่ไหม (ค่าเริ่มต้น = เปิด); เก็บลงไฟล์ flag
  `_Claude Tools/done-alarm/enabled.flag` เพื่อให้คงค่าหลัง restart

เสียงวนซ้ำ: thread แยกวน `winsound.PlaySound(wav, SND_FILENAME | SND_ASYNC)`
ทุก N วินาที จนกว่า `ringing` = False. (winsound = stdlib Windows, ไม่ต้องลงอะไร)

Endpoints:
- `POST /ring` — ถ้า `enabled` → ตั้ง `ringing=True` เริ่ม loop; ถ้า `disabled` → ไม่ทำอะไร (200 เงียบ)
- `POST /stop` — ตั้ง `ringing=False` หยุดเสียง
- `POST /toggle` — สลับ `enabled`, เขียนไฟล์ flag; ถ้าปิด → หยุดเสียงด้วย
- `GET /status` — คืน JSON `{ringing, enabled}` (ให้หน้าเว็บ poll)
- `GET /` — เสิร์ฟหน้าเว็บปุ่ม (ชิ้นที่ 2)

bind `0.0.0.0:8030` เพื่อให้ Tailscale เข้าถึงได้.

### ชิ้นที่ 2 — หน้าเว็บปุ่มหยุด

เสิร์ฟจาก service เดียวกันที่ `GET /` (HTML inline, ไม่มี build).
- ปุ่ม **หยุด** ใหญ่เต็มจอ → `POST /stop`
- ปุ่มสลับ **เปิด/ปิดระบบ** → `POST /toggle`
- แสดงสถานะปัจจุบัน (ดังอยู่ 🔴 / เงียบ ⚪ ; ระบบ เปิด/ปิด) — JS poll `GET /status` ทุก ~2 วิ
- รองรับจอมือถือ (viewport meta, ปุ่มใหญ่กดง่าย)

เปิดที่:
- จอบ้าน: `http://localhost:8030`
- มือถือ (Tailscale): `http://100.71.13.122:8030`

### ชิ้นที่ 3 — Claude Code hooks (`~/.claude/settings.json`)

เพิ่ม block `hooks` (ปัจจุบันยังไม่มี):
- `Stop` → ยิง `POST http://localhost:8030/ring` (Claude เสร็จงาน)
- `Notification` → ยิง `POST http://localhost:8030/ring` (Claude ถาม/ขออนุญาต)
- `UserPromptSubmit` → ยิง `POST http://localhost:8030/stop` (โอพิมพ์ที่จอบ้าน = หยุดเสียง)

แต่ละ hook = คำสั่ง curl สั้นๆ, timeout สั้น, `--silent`, ไม่ block UI.
ถ้า service ไม่รัน → curl fail เงียบ ไม่กระทบ Claude.

Push มือถือ: เมื่อ Claude เสร็จ/ถาม Claude เรียก `PushNotification` (มีอยู่แล้ว,
`agentPushNotifEnabled: true`) เด้งมือถือ 1 ครั้ง — เสริมเสียงบ้าน. นี่เป็นพฤติกรรม
ของ Claude เอง ไม่ต้องตั้งค่าเพิ่ม.

## Flow ตอน Claude เสร็จ

1. Claude หยุด → hook `Stop` ยิง `/ring`.
2. service เช็ก `enabled`:
   - เปิด → เริ่มเล่นเสียงวนซ้ำ; (Claude เด้ง push มือถือ 1 ครั้ง)
   - ปิด → เงียบ (กันหลับ).
3. โอหยุดเสียงได้ 3 ทาง:
   - พิมพ์/Enter ที่จอบ้าน → hook `UserPromptSubmit` ยิง `/stop`
   - กดปุ่มหยุดบนเว็บ (จอบ้าน) → `/stop`
   - กดปุ่มหยุดบนเว็บผ่านมือถือ (Tailscale) → `/stop`
4. service ตั้ง `ringing=False` เสียงหยุด.

## รันค้าง (boot-persistent)

Scheduled Task เปิด `alarm_service.py` ตอน boot — แบบเดียวกับ LINE archiver /
UPS watch ที่โอมีอยู่. ตั้งให้รันใต้ user (ต้องเข้าถึงเสียง/ลำโพง).
script ติดตั้ง: `_Claude Tools/done-alarm/install_task.ps1`.

## ไฟล์เสียง

Claude จัดหา/สร้างไฟล์ `.wav` เสียงเตือนดังๆ วางที่
`_Claude Tools/done-alarm/alarm.wav`. ถ้าหาไฟล์สำเร็จรูปไม่ได้ จะสร้าง wav
beep ดังๆ ด้วย Python (stdlib `wave` + sine/square wave) — ไม่พึ่ง external.

## การทดสอบ / ตรวจรับ

ไม่ใช่งานเงิน → ไม่ต้อง preflight payroll. ตรวจด้วยมือ:
1. start service → `GET /status` คืน `{ringing:false, enabled:true}`.
2. `POST /ring` → ได้ยินเสียงวนซ้ำจริงที่ลำโพงบ้าน.
3. `POST /stop` → เสียงหยุด.
4. เปิด `http://100.71.13.122:8030` บนมือถือ (ต่อ Tailscale) → เห็นหน้าปุ่ม,
   กดหยุดแล้วเสียงบ้านหยุดจริง.
5. `POST /toggle` ปิดระบบ → `/ring` แล้วเงียบ.
6. ตั้ง hooks → ให้ Claude จบ turn จริง → เสียงดัง; พิมพ์ตอบ → เสียงหยุด.
7. reboot → service กลับมาเองจาก Scheduled Task.

## ความเสี่ยง / หมายเหตุ

- winsound เป็น Windows-only — ตรงกับเครื่องโอ (Win11). ถ้าย้าย OS ต้องเปลี่ยน
  ตัวเล่นเสียง.
- service bind 0.0.0.0 แต่ Tailscale-only access (ไม่ port-forward ออกเน็ต) —
  คนนอก LAN/Tailnet เข้าไม่ได้.
- ไม่มี auth บนหน้าเว็บ — ยอมรับได้เพราะอยู่หลัง Tailscale (เครือข่ายส่วนตัว).
- ถ้า service ตาย ตอน Claude เสร็จจะไม่มีเสียง (แต่ push มือถือยังเด้ง) —
  Scheduled Task + restart-on-fail ช่วยลดเคสนี้.
