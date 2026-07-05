---
name: project-line-to-todo-ai-phases
description: แผน 4 เฟส LINE→todo + AI ผู้ช่วยในเว็บ — จบครบ 4 เฟส 5ก.ค. (➕/✨/หน้า /ai/กล่องรอคัด) deploy v46; Claude เปิดใช้แล้วเลือกรุ่นได้
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
**เฟส 3 — DONE + deploy 5ก.ค. (commit f0c9317, schema v45):** หน้า /ai เฉพาะ admin
- RBAC เมนู `ai` (permissions.py) — office/accountant/viewer = deny; ลิงก์ในเมนูผู้บริหาร
- Qwen = `ai_assist.chat_qwen()` (refactor ใช้ร่วม rewrite_todo); Claude = `chat_claude()` subprocess `claude -p --allowedTools Read,Grep,Glob` (guard อ่านอย่างเดียวจริง); log ทุกคำถามลง `AiChatLog`
- **Claude บน server เปิดใช้แล้ว 5ก.ค.** — CLI v2.1.201 ติดตั้งผ่าน SSH; auth ด้วย `CLAUDE_CODE_OAUTH_TOKEN` จาก `claude setup-token` ที่โอรันบนเครื่อง dev (token = secret #9, dev copy ที่ `_Claude Tools/claude_server.key`) → ไม่ต้อง login บนจอ server, รันเป็น SYSTEM ได้; ต้องมี `.claude_headless/.claude.json` ใส่ hasCompletedOnboarding+hasTrustDialogAccepted ของ `C:/Users/yklog/YK_MVP/app` ไม่งั้น workspace ไม่ trust; ยืนยันแล้ว chat_claude ตอบจริงบน server; วิธีหมุน/รายละเอียดใน `docs/AI_CHAT_RUNBOOK.md`
- ระหว่างทำ: session PWA อื่น commit 542e806 แทรก branch เดียวกัน → hunk /sw.js ที่เคยค้างเข้า HEAD แล้ว, working tree main.py สะอาด (ตอนนี้ stage ตรงได้ ไม่ต้องกรอง hunk แล้ว)
**เฟส 4 — DONE + deploy 5ก.ค. (8314163+cf97e5c, schema v46):** กล่องรอคัดจากไลน์
- `TodoSuggest` + `services/todo_scan.py`: prefilter → Qwen คัดก้อนละ 25; **AI สร้างได้แค่ pending** โอกดรับถึงเกิด TodoItem (รูปตามมาผ่าน `_todo_from_line_bundle` — refactor ใช้ร่วมเฟส 1)
- auto-scan: admin เปิด /todo + รอบล่าสุด >20 ชม. → thread; ปุ่มสแกนเองได้; กล่อง/สแกน admin-only
- จูนจากวัดจริง (400 ข้อความ→58→49): ตัดฟอร์แมต "แจ้งเติม"+น้ำมัน (F4 ดูแยกแล้ว [[project-f4-fuel-line-compare]]) + dedupe (who,text) ข้ามกลุ่ม; คีย์เวิร์ด "ขอ" จับ "ขอบคุณ" ได้ = ตั้งใจ (AI คัดชั้นสุดท้าย)
- /ai เลือกรุ่น Claude ได้: claude:haiku|sonnet|opus → `chat_claude(model=...)` → `--model`; Qwen มีตัวเดียว qwen3.6-35b-a3b

**ค้าง/ไอเดียถัดไป:** AI ตอบเรื่องเงินรายคน (เช่น "เรวัตรได้เท่าไหร่") ยังไม่ได้ — ตั้งใจ (system prompt มีแค่ count, ห้ามเดาเลขเงิน); ถ้าโออยากได้ต้องออกแบบช่องข้อมูล read-only เพิ่มอย่างระวัง

กฎยืนทุกเฟส: AI read-only — สร้างอะไรเป็น draft ให้โอยืนยัน ห้ามเขียน DB เอง โดยเฉพาะเงิน
