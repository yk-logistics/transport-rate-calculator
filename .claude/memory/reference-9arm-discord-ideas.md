---
name: reference-9arm-discord-ideas
description: "ไอเดีย/เครื่องมือคัดแล้วจาก Discord หลังบ้านนายอาร์ม (มิ.ย.-ก.ค. 2026) ที่เอามาต่อยอด Project YK ได้ — slip-verify API, OCR ไทย, anti-hallucination เงิน, LLM failover, monitoring"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 066fdd67-822a-4537-b2af-341f28a573ef
---

สรุปจากการอ่าน Discord export 2 ห้อง (แชทททท 1,033 ข้อความ + อวด-project-ai 129 ข้อความ, 1 มิ.ย.–4 ก.ค. 2026) — อ่านโดย Qwen 4 ก้อน + ตัวหลักตรวจทาน 5 ก.ค. 2026. **Gotcha ที่เจอ: qwen-readonly.ps1 รันใน repo เรา → มันแอบปนความจำ Project YK เข้าไปในคำตอบ (เช่นอ้างว่าในแชทมี "KB payout") — ต้อง grep transcript ยืนยันก่อนเชื่อทุกครั้ง.**

## โอเคาะแล้ว 5 ก.ค. 2026 (ตอบทีละข้อ)

- ข้อ 1-2 (เช็คสลิป API + QR พร้อมเพย์): **ไม่เอา** — "ส่วนใหญ่เราเป็นฝ่ายโอน" ไม่ใช่ฝ่ายรับ
- ข้อ 3 (calculator-enforce): ยังไม่ต้อง — ตัวเลขเงินทั้งระบบคำนวณด้วย Python อยู่แล้ว AI ไม่บวกเอง; เก็บแนวคิดไว้ใช้ถ้าเฟส 4 auto-scan ให้ AI สรุปยอด
- ข้อ 4 (OCR): พอถึงงาน OCR จริง (NHL POD) **ให้ทำเป็นตัวเลือก 2 เจ้า**: Qwen ผ่าน 9arm (ฟรี) vs Google Cloud Vision (ฟรี 1,000 หน้าแรก/เดือน แล้ว ~$1.5/1,000)
- ข้อ 5 (LLM failover): **ทำแล้ว 5 ก.ค. commit b25d1a9 + deploy เขียว** — ปุ่ม ✨ fallback Qwen→Claude อัตโนมัติ + ตั้งค่า ⚙️ บนหน้า /ai (AppSetting `ai_draft_provider`: auto/qwen/claude); draft ติดป้าย "Claude สำรอง" ตอน fallback ทำงาน
- ข้อ 6 (Uptime Kuma): ไม่เร่ง — มี watchdog+UPS alert บนเครื่องแล้ว; ที่ขาดคือ "คนเฝ้านอกเครื่อง" (ทั้งเครื่องดับ = ตัวแจ้งตายด้วย) ทำเองได้ด้วย cron จากเครื่อง dev ไว้โอสั่งค่อยทำ
- ข้อ 7 (เครื่องมือจุกจิก): ส่วนใหญ่ซ้ำของที่มี (headroom≈บีบไฟล์ก่อนส่ง Qwen ที่ทำอยู่, /teach≈memory, /to-issues≈runbook) — ไม่ลงเพิ่ม

## ใช้ได้ตรงงาน YK (เรียงตามความคุ้ม)

1. **เช็คสลิปโอนด้วย API** — slipok (ฟรี 100 สลิป/เดือน) หรือ EasySlip (~30บ./1,000 ครั้ง): สแกน QR บนสลิป→ยืนยัน transaction จริงกับธนาคาร. ใช้กับ [[project-cy-kb-payout-calculator]] (จับคู่ยอดโอน 4 เจ้า) + [[feedback-slip-fuel-must-reconcile]] — ตอนนี้เรา match ยอดเอง ยังไม่ได้พิสูจน์ว่าสลิปจริง. **งานเงิน → ต้องให้โอเคาะก่อนทำ.**
2. **QR พร้อมเพย์พร้อมยอด gen ได้ฟรี** (มาตรฐาน EMV/PromptPay ไม่ต้องใช้ API) — ฝัง QR ยอดจ่ายลงสลิปเงินเดือน/ใบ KB payout ให้กดสแกนจ่ายได้เลย.
3. **OCR ไทยสำหรับเอกสาร** — ชุมชนยืนยัน: Google Cloud Vision ถูกสุดสำหรับเอกสารบัญชี, Qwen3.6 อ่าน OCR ไทยจากรูปได้ดี, pdfplumber ใช้ได้เฉพาะ PDF digital (scan ไม่ผ่าน). เกี่ยว: NHL POD ที่ต้อง OCR ([[project-f3-pod-measured-tuned]]) + F4 OCR ที่โอยังไม่เคาะ.
4. **บังคับ AI เรียกเครื่องคิดเลขก่อนตอบตัวเลข** (เว็บ KineticV) — มีโค้ดตรวจ ถ้า AI ไม่เรียก calculator tool ตอนมีการคำนวณ → reject แล้ว gen ใหม่. เอาใช้กับเฟส 3-4 LINE→AI ([[project-line-to-todo-ai-phases]]) ทุกจุดที่ AI แตะตัวเลขเงิน — เข้ากฎเงิน YK ตรงๆ.
5. **LLM failover หลายชั้น** (คนในกลุ่มทำ 9arm→local→DeepSeek) — ปุ่ม ✨ AI เรียบเรียงของเราพึ่ง 9arm เจ้าเดียว (ฟรี ไม่การันตี uptime); ชั้นสำรองของเราควรเป็น Haiku API (server ไม่มี GPU — [[reference-server-no-gpu-llm]]).
6. **headroom** (github.com/chopratejas/headroom) — compress tool outputs/logs ก่อนเข้า LLM ลด token 60-95% — เสริม pipeline Qwen subagent ของเรา ([[reference-qwen-subagent]]).
7. **Uptime Kuma** (ฟรี self-host) + webhook — monitor app.yklogistics.uk + LINE archiver + nightly backup; ต่อยอดจาก UPS alert เดิม ([[project-ups-power-alert]]).
8. **Email AI triage** — ดึงเมล→AI วิเคราะห์→assign งาน — เรามี email_ingest อยู่แล้ว ต่อยอดได้ถ้าโอต้องการ.

## ยืนยันแนวทางที่เราทำอยู่แล้วว่ามาถูก (ไม่ต้องทำอะไร)

- Model routing "ผู้ใหญ่คิด เด็กเขียน" = ท่ามาตรฐานของชุมชน (Opus วางแผน + Qwen mechanical)
- Warm-window ping ตอนเช้า = มีคนทำแจก (narze/claude-morning) ตรงกับ [[reference-window-warm-routines]]
- Qwen3.6 เขียนโค้ดตรงๆ bug เยอะ (เคส Battle City ต้องให้ Opus ตบ) = ตรงกับกฎเรา "Qwen recon/summarize เท่านั้น"
- Qwen ทำ JSON classification ได้ดี (เคส spam detector→blacklist) = ยืนยันแนว F2/ปุ่ม ✨
- Fable แพง ~2 เท่า Opus + ฟรีถึง 7 ก.ค. = ตรง [[project-fable-deadline-and-phase-p]]

## เผื่ออนาคต

- **xenodeve/xeno-skills** — multi-agent brainstorm (Delphi + adversarial round) สำหรับงานออกแบบสำคัญมาก — กิน token หนัก ใช้เฉพาะเคสใหญ่
- **Orca (onorca.dev)** — รันหลาย coding agents ขนานใน worktrees + ดู terminal จากมือถือ
- **mattpocock/skills** — /teach (สอน domain knowledge), /to-issues (แตก plan เป็น issues ให้ subagent)
- Typhoon ASR = speech-to-text ไทยแม่นสุด (เผื่อทีมส่งเสียงแทนพิมพ์ใน LINE)

เกร็ด: โอโพสต์เล่าใน #แชทททท (5 มิ.ย.) เรื่องจ้างฟรีแลนซ์ 60k ทำระบบขนส่งแล้วโดนทิ้งงานงวดสุดท้าย จึงมา vibe coding เอง — คนในกลุ่มรู้จักเคสนี้แล้ว.
