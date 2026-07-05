# AI Chat (/ai) Runbook — เฟส 3 LINE→todo+AI

หน้า `/ai` = แชทถามระบบ เฉพาะ admin (RBAC เมนู `ai`) — AI **อ่านอย่างเดียว** ตอบคำถาม
ไม่มีทางเขียน DB (กฎยืนทุกเฟส). ทุกคำถาม-คำตอบลงตาราง `AiChatLog` (ดูท้ายหน้า /ai).

## สถาปัตยกรรม (ใครทำอะไร)

| ชิ้น | ที่อยู่ | หน้าที่ |
|------|---------|---------|
| `services/ai_assist.py` | app | `chat_qwen()` REST ไป 9arm · `chat_claude()` subprocess `claude -p` · `rewrite_todo()` (เฟส 2) |
| `POST /ai/ask` | main.py | รับ {q, model, history} → เรียกโมเดล → ลง `AiChatLog` → คืน JSON |
| `_ai_system_prompt()` | main.py | บริบทระบบ + ตัวเลขสดจาก DB (count เท่านั้น — ถูก) |
| `templates/ai.html` | app | หน้าแชท (JS fetch, history เก็บฝั่ง browser ส่งกลับทุกคำถาม) |

## โมเดล

- **Qwen (ฟรี)** — ใช้ได้ทันที: REST `gateway.9arm.co/v1/chat/completions` คีย์ `YK_QWEN_KEY`
  (secret #8 ใน `SECRETS_INVENTORY.md`). Gotcha: ต้องตั้ง `user-agent` เอง (WAF บล็อก UA Python)
  และห้ามใช้ท่า `/v1/messages` (คืน content ว่าง).
- **Claude (Max ของโอ)** — ผ่าน `claude -p` headless เท่านั้น (เอา token Max ยิง API ตรง =
  ผิด ToS; `claude -p` ได้; **โควต้าแชร์กับเซสชันทำงานของโอ**). จำกัดเครื่องมือ
  `--allowedTools Read,Grep,Glob` = guard อ่านอย่างเดียวจริง ระดับเทคนิค.

## เปิดใช้ Claude บน server (ยังไม่ได้ทำ — รอโอ)

สถานะ 5 ก.ค. 2026: server (yklog@100.97.150.114) **ยังไม่มี claude CLI** → หน้า /ai
โชว์ตัวเลือก Claude เป็นสีเทา "ยังไม่ติดตั้งบนเครื่องนี้" และถ้าเรียกจะได้ข้อความแนะนำ ไม่พัง.

ขั้นตอนเปิดใช้ (โอทำบนจอ server ครั้งเดียว):

1. ติดตั้ง Claude Code บน server (PowerShell): `irm https://claude.ai/install.ps1 | iex`
   (หรือ npm ตามคู่มือทางการ) — ได้ `claude.exe` ใน `%USERPROFILE%\.local\bin`
2. login ด้วยบัญชี Max ของโอ: รัน `claude` แล้วทำ OAuth ในเบราว์เซอร์ (เครื่อง server มีจอ/AnyDesk)
3. เพิ่ม 2 บรรทัดใน `C:\Users\yklog\YK_MVP\start_mvp.bat` (ก่อนบรรทัด cd):
   ```
   set YK_CLAUDE_EXE=C:\Users\yklog\.local\bin\claude.exe
   set YK_CLAUDE_CONFIG=C:\Users\yklog\.claude
   ```
   `YK_CLAUDE_CONFIG` **จำเป็น** — แอปรันเป็น SYSTEM ผ่าน scheduled task แต่ credential
   Max อยู่โปรไฟล์ yklog; ตัวแปรนี้ทำให้ subprocess หา login เจอ.
4. restart task `YK_MVP_APP` (Stop-ScheduledTask → เช็ค PID 8010 → Start-ScheduledTask
   — ดู MVP_SERVER_DEPLOY.md) แล้วเปิด /ai → ตัวเลือก Claude ต้องหายเทา

## ขยาย/แก้ทีหลัง (สำหรับโมเดลเล็กทำต่อ)

- เพิ่มโมเดลใหม่: เพิ่ม branch ใน `ai_ask()` (main.py) + ฟังก์ชันใน `ai_assist.py` + option ใน
  `ai.html` — log ลง AiChatLog เหมือนเดิม
- ปรับบริบทที่ AI เห็น: แก้ `_ai_system_prompt()` อย่างเดียว (อย่าใส่ query แพง — โดนเรียกทุกคำถาม)
- เทสต์: `tests/test_ai_page.py` (fake ทั้งสองโมเดลผ่าน monkeypatch — ไม่ยิงเน็ต)
- เฟส 4 (auto-scan ไลน์รายวัน→เสนอ todo) ยังไม่เริ่ม — ดู memory `project-line-to-todo-ai-phases`
