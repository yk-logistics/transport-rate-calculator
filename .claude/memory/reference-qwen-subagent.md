---
name: reference-qwen-subagent
description: Delegate read-only recon/summarize work to a cheap Qwen subagent via _Claude Tools/qwen.ps1 (9arm gateway) to save Opus tokens
metadata: 
  node_type: memory
  type: reference
  originSessionId: 768861b2-a0c9-47cb-ae87-3a101a0dbce6
---

Opus can offload bulky **read-only** work (grep across many files, digest long logs, "list files + what each does" recon, summarize) to a cheap Qwen model so Opus pays only for the short summary, not the raw tool output.

**How to call** (from a Bash/PowerShell tool in an Opus session):
```
powershell -ExecutionPolicy Bypass -File "_Claude Tools\qwen.ps1" "<task prompt>"
```
stdout = Qwen's final answer. Full guide: `_Claude Tools/QWEN_SUBAGENT.md`.

**Saves tokens only for "read a lot → return a short summary."** If Qwen has to *think/decide*, Opus pays again to verify it → net loss. Keep judgment in Opus.

**SAFETY — there is NO technical guardrail, by design.** The wrapper runs `--permission-mode bypassPermissions` (the old `--allowedTools '*'` was removed 2026-06-09 — claude ≥2.1.16x rejects the `*` wildcard in allow rules with a warning; bypassPermissions alone already grants every tool), and Qwen hallucinates. Control is by discipline, enforced by Opus when it writes the prompt:
- Delegate **read-only recon/summarize only**. Never money/payroll/billing, never file writes, never SQL migrations, never design decisions (CLAUDE.md money rule: ห้ามเดาเรื่องเงิน).
- **Make the git working tree clean (commit/stash) before delegating** — if Qwen goes off-script and writes/deletes, `git` is the undo. This is the cheap safety net that keeps Qwen full-powered.
- Each call is a **fresh session** — pack needed context into the prompt; Qwen remembers nothing between calls.

Key lives in `_Claude Tools/9arm.key` (gitignored via `*.key`), not hardcoded in the script. 9arm is a free gateway — no rate-limit or uptime guarantee.

## Gotcha: claude ส่ง OAuth token แทนคีย์ 9arm (แก้แล้ว 2026-06-08)

ถ้า `claude` login ด้วย subscription (มี `~/.claude/.credentials.json`) มันจะ **prefer OAuth token ก่อน `ANTHROPIC_API_KEY` env เสมอ** → ส่ง token ของบัญชีไป 9arm → **401 Invalid token ทุกครั้ง ไม่ว่าคีย์ในไฟล์จะเป็นอะไร**. อาการชี้ชัด: error แสดง `Received API Key = sk-...XXXX` ที่ **ท้ายไม่ตรงกับคีย์ในไฟล์** + key hash เปลี่ยนทุก run (= OAuth refresh). แก้คีย์ในไฟล์ไม่ช่วยเด็ดขาด.

**Fix (baked เข้า `qwen.ps1` + `qwen-readonly.ps1` แล้ว):** subprocess ตั้ง `CLAUDE_CONFIG_DIR` เป็น dir แยกที่ไม่มี credential → claude fallback ไปใช้ env key → 9arm ยอมรับ. ยืนยันด้วย `AUTH_OK` + recon จริงคืนเลขถูก.

## qwen-readonly.ps1 (read-only variant)

เหมือน qwen.ps1 แต่ `--allowedTools 'Read,Grep,Glob'` → เขียน/ลบ/รัน shell ไม่ได้ทางเทคนิค (guard จริง ไม่ใช่ discipline). ใช้กับงาน recon/propose ที่อยากให้ qwen "ดูแต่ไม่แตะ" แล้ว Opus เอาผลมา apply เอง.
