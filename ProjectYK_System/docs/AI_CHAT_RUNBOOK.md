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

## Claude บน server — เปิดใช้แล้ว 5 ก.ค. 2026 ✅

ท่าที่ใช้จริง (ดีกว่าแผนเดิม — โอไม่ต้องไปหน้าจอ server เลย):

1. **ติดตั้ง CLI ผ่าน SSH:** `irm https://claude.ai/install.ps1 | iex` →
   `C:\Users\yklog\.local\bin\claude.exe` (v2.1.201; ไม่ต้องแก้ PATH — ชี้ตรงด้วย env)
2. **token แทนการ login บนจอ server:** โอรัน `claude setup-token` บนเครื่อง dev (อนุมัติ
   ในเบราว์เซอร์ด้วยบัญชี Max) → ได้ token `sk-ant-oat...` เก็บไว้ที่
   `_Claude Tools\claude_server.key` (dev, gitignored) — **อย่าก็อป credentials.json
   ข้ามเครื่อง** (refresh token ชนกัน เสี่ยง login เครื่อง dev หลุด)
3. **env ใน `YK_MVP\start_mvp.bat`** (secret #9 ใน SECRETS_INVENTORY.md):
   ```
   set YK_CLAUDE_EXE=C:\Users\yklog\.local\bin\claude.exe
   set CLAUDE_CODE_OAUTH_TOKEN=<token จากข้อ 2>
   set YK_CLAUDE_CONFIG=C:\Users\yklog\.claude_headless
   ```
   token ใน env = ไม่พึ่ง credential ในโปรไฟล์ → รันเป็น SYSTEM ได้;
   `.claude_headless\.claude.json` ต้องมี `hasCompletedOnboarding: true` +
   `projects["C:/Users/yklog/YK_MVP/app"].hasTrustDialogAccepted: true`
   (ไม่งั้น workspace ไม่ trust — สร้างไว้แล้ว)
4. restart task `YK_MVP_APP` → ทดสอบแล้ว: `chat_claude()` บน server ตอบจริง
   (อ่านไฟล์ใน app dir ได้ = trust ทำงาน)

**หมุน token:** `claude setup-token` ใหม่บนเครื่อง dev → แก้ใน start_mvp.bat → restart;
ยกเลิกของเก่า: claude.ai → Settings → Sessions/Apps revoke.

## ขยาย/แก้ทีหลัง (สำหรับโมเดลเล็กทำต่อ)

- เพิ่มโมเดลใหม่: เพิ่ม branch ใน `ai_ask()` (main.py) + ฟังก์ชันใน `ai_assist.py` + option ใน
  `ai.html` — log ลง AiChatLog เหมือนเดิม
- ปรับบริบทที่ AI เห็น: แก้ `_ai_system_prompt()` อย่างเดียว (อย่าใส่ query แพง — โดนเรียกทุกคำถาม)
- เทสต์: `tests/test_ai_page.py` (fake ทั้งสองโมเดลผ่าน monkeypatch — ไม่ยิงเน็ต)
- เฟส 4 (auto-scan ไลน์รายวัน→เสนอ todo) ยังไม่เริ่ม — ดู memory `project-line-to-todo-ai-phases`
