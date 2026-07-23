---
name: reference-claude-cli-reads-images
description: claude -p อ่านรูปจากไฟล์ได้ (ใส่ path ใน prompt + Read tool) — ใช้ทำ OCR ในแอปได้ Qwen gateway ทำไม่ได้
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3323cfdd-942a-44da-bc85-095450412c8b
---

`ai_assist.chat_claude(f"อ่านรูปนี้: {path} ...", model="sonnet")` → Claude Code CLI
เปิดรูปผ่าน Read tool (`--allowedTools Read,Grep,Glob` ที่ตั้งไว้อยู่แล้ว) แล้วตอบได้จริง

**พิสูจน์ 9 ก.ค. 2026 บน server:**
- รูปหน้าปัดรถ → อ่านเลขไมล์ 291,095 ถูก (~11 วินาที, sonnet)
- บิลปั๊ม Caltex → ร้าน/วันที่/ทะเบียน 71-9627/DIESEL_B20 30L×29.96=898.80 ครบ
- haiku ใช้คัดหยาบได้ (บิลใช่/ไม่ใช่) เร็วและถูกกว่า

**ข้อจำกัด:** Qwen ผ่าน 9arm gateway รับแต่ text — งานรูปต้องใช้ Claude เท่านั้น
(กินโควต้า Max ของโอ → งานปริมาณมากต้องมีเพดาน เช่น `_MAX_CLAUDE_CHUNKS`)

ใช้จริงที่ `services/bill_ocr.py` ([[project-maint-bill-lines-ocr]])
