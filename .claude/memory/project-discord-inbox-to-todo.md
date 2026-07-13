---
name: project-discord-inbox-to-todo
description: 13ก.ค. ช่อง Discord 📌01-inbox-โยนมาก่อน → /todo อัตโนมัติ (โอ forward เอง = เข้าตรง ไม่ผ่านกล่องรอคัด)
metadata: 
  node_type: memory
  type: project
  originSessionId: 0b97dd47-8853-4b98-a192-29808f698a33
---

**13 ก.ค. 2026:** โออยาก forward ข้อความ/รูปเข้าระบบโดยไม่ต้องก็อป/เซฟเอง →
`services/discord_inbox.py` poll ช่อง 📌01-inbox-โยนมาก่อน (channel id
`1458138638213710058`, guild YK) ด้วย **bot token ตัวเดียวกับ line_archiver**
→ สร้าง TodoItem หมวด "inbox" + ดาวน์โหลดรูปเข้า `_todo_media/` ให้เลย

- trigger: admin เปิด /todo แล้วรอบล่าสุดเกิน 5 นาที → thread เบื้องหลัง
  (`main._discord_inbox_maybe_auto` — แพทเทิร์นเดียวกับ auto-scan ไลน์);
  **รายการเข้าบัญชี "oh" ตายตัว** (env `YK_DISCORD_INBOX_USER` override ได้) —
  ห้ามผูกกับคนเปิดหน้า เพราะ admin มี 4 คน (yk1/oh/joe/miw)
- dedupe: watermark AppSetting `discord_inbox_last_id` (snowflake id ขยับทีละ
  ข้อความหลัง commit — พังกลางทางไม่สร้างซ้ำ); พังโชว์ผ่าน `discord_inbox_err`
  แถวเดียวกับ scan_err บน /todo
- **GOTCHA สำคัญ:** bot อ่าน content/attachments ได้ต้องเปิด **Message Content
  Intent** ใน developer portal (เปิดแล้ว 13ก.ค. โดยโอ) — ก่อนเปิด API ตอบ 200
  แต่ content ว่างหมด หลอกว่าใช้ได้
- **เปิดใช้ต้องตั้ง env ชัดๆ**: `YK_DISCORD_TOKEN` หรือ `YK_DISCORD_TOKEN_FILE`
  (รับทั้ง token ดิบและ .env ของ archiver) — **ห้ามใส่ fallback อัตโนมัติไปหา
  line_archiver/.env** ไม่งั้นเทสต์/dev ที่มีไฟล์นั้นแอบยิง Discord จริงตอนเปิด /todo;
  server ชี้ `C:\Users\yklog\YK_LINE_ARCHIVER\.env` ใน start_mvp.bat
- forward ของ Discord แท้ๆ อยู่ใน `message_snapshots[].message` (content+attachments)
  — รองรับแล้ว; ข้อความบอท/ว่าง (sticker) ข้ามแต่ watermark ขยับ
- รอบแรกไม่มี watermark ดึงแค่ 20 ข้อความล่าสุด (`_FIRST_RUN_LIMIT`) กันประวัติทะลัก
- เทสต์ `tests/test_discord_inbox.py` 5 ตัว (httpx.MockTransport); full suite 728 passed
- **deploy + import รอบแรกบน server เสร็จ 13ก.ค. 13:12** (commit 79021c3, push แล้ว):
  20 รายการ (ย้อนถึง 18 มิ.ย.) + รูป 38 ใบ เข้า /todo ของ oh แล้ว; watermark ตั้งแล้ว
  รอบถัดไปได้เฉพาะของใหม่; เซสชันคู่ขนาน (งาน CFO 22ddfc9) เป็นคน commit+deploy
  โค้ดรอบแรกให้ตอน 12:56

ดู [[project-line-to-todo-ai-phases]] · [[reference-line-archiver]]
