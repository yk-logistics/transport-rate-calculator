---
name: project-line-to-todo-ai-phases
description: แผน 4 เฟส LINE→todo + AI ผู้ช่วยในเว็บ — เฟส 1+2 deploy แล้ว 5ก.ค.; เฟส 3-4 ค้าง (หน้า /ai + claude -p / auto-scan)
metadata: 
  node_type: memory
  type: project
  originSessionId: 8e5308e0-979d-42e2-93cb-cde3cf077211
---

โอเคาะ 5 ก.ค. 2026: ทำ 4 เฟสเรียงลำดับ (AI ช่วยงานในเว็บ MVP)

**เฟส 1 — DONE + deploy 5ก.ค.** ปุ่ม ➕ บนหน้า /line ส่งข้อความ+รูปทั้งชุดเข้า /todo
- `line_archive.bundle_for_todo(msg_id)`: ข้อความที่กด + รูป **คนส่งเดียวกัน ±20 นาที** (ข้อสมมติ window — ปรับได้), read-only เช่นเดิม
- `POST /line/{id}/to-todo` (main.py หลัง todo_media): TodoItem หมวด "ไลน์", ก็อปรูปเข้า `_todo_media/<id>/`; รูปที่ย้ายลงแผ่น External (G2) ใส่โน้ตเตือนแทน
- เทสต์: `tests/test_line_to_todo.py` (fake archive ผ่าน env `YK_LINE_DB`) — 4 ตัวผ่าน
- commit a3fcfd3 บน fix/slip-trip-fee-kb-display (branch นี้ ahead main 141 — คือเส้นทำงานจริง)
- **GOTCHA ตอน deploy:** working tree main.py มี hunk PWA `/sw.js` ของ session อื่นค้าง (ยังไม่ commit, ยังไม่อยู่บน server) — ต้อง stage แบบกรอง hunk (git apply --cached) และ scp เวอร์ชัน `git show HEAD:` ไม่ใช่ working tree

**เฟส 2 — DONE + deploy 5ก.ค. (commit 48beeb5):** ปุ่ม ✨ เรียบเรียง ต่อรายการบนหน้า /todo
- `services/ai_assist.py` เรียก 9arm ตรงด้วย urllib (ไม่ผ่าน claude CLI): **ต้องใช้ท่า OpenAI `/v1/chat/completions`** — ท่า Anthropic `/v1/messages` บน gateway นี้คืน `content: []` (LiteLLM แปลงแล้วข้อความหาย, พิสูจน์สด); **ต้องตั้ง user-agent เอง** ไม่งั้น WAF ตอบ 403 กับ UA ของ Python; temperature 0 (จูนแล้ว — เคยเปลี่ยน 'พรุ่งนี้'→'บ่ายนี้' เพี้ยนความหมาย); กันบรรทัดที่มา 📱/(⚠️ หายฝั่ง server
- draft ไม่เก็บ DB (ไม่แตะ schema): `POST /todo/{id}/ai-draft` คืน fragment htmx (`todo_ai_draft.html`) → โอแก้ต่อ/กด "ใช้ตามนี้" ยิง `/todo/{id}/update` ตัวเดิม
- คีย์: env `YK_QWEN_KEY` (server ใส่ใน `YK_MVP\start_mvp.bat` แล้ว) หรือ `YK_QWEN_KEY_FILE`; dev ชี้ไฟล์ `_Claude Tools/9arm.key`
- เทสต์ `tests/test_todo_ai_draft.py` 7 ตัว (fake AI) + smoke จริงผ่านทั้ง dev และบน server
**เฟส 3:** หน้า /ai เฉพาะโอ (admin) — แชทถามระบบ read-only + model picker; Claude ผ่าน **`claude -p` headless บนเครื่อง server login ด้วย Max ของโอ** (เอา token Max ยิง API ตรง = ผิด ToS; claude -p ได้; โควต้าแชร์กับเซสชันทำงาน) + log การใช้
**เฟส 4:** สแกนข้อความไลน์รายวัน → เสนอ todo เข้ากล่องรอคัด (ต่อยอด [[project-f4-fuel-line-compare]] pattern parse)

กฎยืนทุกเฟส: AI read-only — สร้างอะไรเป็น draft ให้โอยืนยัน ห้ามเขียน DB เอง โดยเฉพาะเงิน
