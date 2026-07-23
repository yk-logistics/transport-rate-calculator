---
name: project-todo-scan-claude-fallback
description: 9ก.ค. Qwen gateway (9arm) ล่มยาว คืน content ว่างทุก prompt → todo_scan ตก Claude haiku อัตโนมัติ + แบนเนอร์เตือนบน /todo
metadata: 
  node_type: memory
  type: project
  originSessionId: 3323cfdd-942a-44da-bc85-095450412c8b
---

**9 ก.ค. 2026:** `gateway.9arm.co` ตอบ HTTP 200 `finish_reason=stop` แต่ `content=""`
`completion_tokens=1` **ทุก prompt** (แม้ "1+1") ทั้ง chat/completions, /v1/messages, streaming
— gateway ฟรีพัง ไม่ใช่ prompt เรา. เช็คเร็ว: ยิง prompt สั้น ถ้า `completion_tokens<=1` = ล่ม.

**แก้แล้ว (79c3c6f + f42c63d, deploy 12:53):**
- `services/todo_scan.py`: Qwen ล่ม → `ai_assist.chat_claude(..., model="haiku")` จำกัด
  `_MAX_CLAUDE_CHUNKS=8` ก้อน/รอบ (25 ข้อความ/ก้อน) กันโควต้า Max ของโอ
- ก้อนที่ AI ล่ม = ข้าม ไม่ล้มทั้งรอบ; พังทุกก้อนถึง raise พร้อมเหตุจริง
- setting `todo_scan_err` — พังแล้ว auto-scan ลองใหม่ใน **1 ชม.** (เดิมเงียบ 20 ชม.)
  + แบนเนอร์ ⚠️ ค้างบน `/todo` จนสแกนสำเร็จ
- หมวดที่ AI แต่งเอง ("ฝากงาน"/"นัดหมาย") ถูกยุบเป็น "งาน" (สเปคมี 3 หมวด)

**วัดจริง:** 400 ข้อความ/26ชม. → 90 candidates = 4 ก้อน → Claude คัดได้ 60 งาน, ล้ม 0

**gotcha:** `main.py` กรอง `ConnectionResetError` ของ logger `asyncio` ออกจาก `logs/app.log`
(`_DropClientDisconnect`) — เดิม 7 ใน 8 บรรทัดคือ noise บัง error จริงบน /admin/server-health

ดู [[reference-claude-cli-reads-images]] · [[project-line-to-todo-ai-phases]]
