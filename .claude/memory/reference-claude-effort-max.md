---
name: reference-claude-effort-max
description: effort level ของ Claude Code — default ปัจจุบัน = high ผ่าน settings.json; profile inject max ถูกถอดแล้ว 21 ก.ค.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7efc79a4-ad88-42c7-94ab-4f7dde34d4e5
  modified: 2026-07-21T02:48:41.792Z
---

Claude Code effort level:

**สถานะปัจจุบัน (โอสั่ง 21 ก.ค. 2026): default = `high`**
- `~/.claude/settings.json` → `effortLevel: "high"` — persist ได้ ใช้ทุกทางเปิด (claude.exe, cc.cmd, ClaudeCode.exe)
- function `claude` ใน `~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1` ที่เคย inject `--effort max` **ถอดออกแล้ว** (ไฟล์ว่าง) — มันมีไว้เพราะ max เซฟลงไฟล์ไม่ได้เท่านั้น
- อยากได้ max ชั่วคราว: เปิดด้วย `claude --effort max` ตรงๆ หรือ `/model` ในเซสชัน (มีผลเฉพาะเซสชันนั้น)

ข้อเท็จจริงจาก binary 2.1.205 (วัด 9 ก.ค. 2026):
- **เช็คว่าตอนนี้รัน effort อะไร:** `echo $CLAUDE_EFFORT` ใน Bash tool (`/status` ไม่โชว์ effort)
- **`effortLevel` ใน settings.json รับได้แค่ `low|medium|high|xhigh`** — ไม่มี `max`; เขียน `"max"` ลงไปโดน `.catch()` ทิ้งเงียบๆ
- **ลำดับความสำคัญ:** `--effort` flag ตอนเปิด > `ultracode: true` (ได้แค่ xhigh) > `effortLevel` ในไฟล์
- **`--effort` ใช้กับ subcommand ไม่ได้** — `claude mcp list --effort max` → error
