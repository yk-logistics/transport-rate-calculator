---
name: reference-test-claude-as-system
description: แอป YK บน server รันเป็น SYSTEM — ทดสอบ claude/subprocess ในสิทธิ์ yklog แล้วผ่าน ไม่ได้แปลว่าแอปทำได้
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3323cfdd-942a-44da-bc85-095450412c8b
---

**บทเรียน 9 ก.ค. 2026 (เสียเวลาไปครึ่งวัน):** ผมทดสอบ `ai_assist.chat_claude()` ผ่าน
`ssh yklog` แล้วได้ `OK` เลยบอกโอว่า Claude fallback ใช้ได้ — **ผิด** เพราะแอปจริงรันเป็น
**SYSTEM** (`Get-CimInstance Win32_Process` → GetOwner = SYSTEM)

- claude บน Windows ต้องมี **Git bash หรือ PowerShell 7**
- `yklog` มี `C:\WINDOWS\system32\bash.exe` = **WSL** (distro ผูกกับ user) → ผ่าน
- SYSTEM ไม่มี distro → claude ตายใน 0.4 วิ: *"Claude Code on Windows requires either
  Git for Windows (for bash) or PowerShell"* → หน้าเว็บขึ้นแบนเนอร์แดง ไม่มีร่องรอยใน log

**แก้แล้ว:** ติดตั้ง Git for Windows ระดับเครื่อง (`winget install --id Git.Git -e
--scope machine --silent`) + `ai_assist._claude_env()` เซ็ต `CLAUDE_CODE_GIT_BASH_PATH` เอง

**วิธีทดสอบในสิทธิ์ SYSTEM (ใช้ซ้ำได้):**
```
schtasks /Create /TN TMP /TR "powershell -File C:\...\inner.ps1" /SC ONCE /ST 23:59 /RU SYSTEM /F
schtasks /Run /TN TMP     # inner.ps1 เขียนผลลงไฟล์ แล้วอ่านไฟล์
schtasks /Delete /TN TMP /F
```

**gotcha ประกอบ:** ไฟล์ `.ps1` ที่ scp ไป **ห้ามมีภาษาไทย** (PowerShell parse พังเป็น
"string is missing the terminator"); `claude -p` เป็น blocking ~40 วิ → route async ต้องใช้
`run_in_threadpool`

ดู [[reference-claude-cli-reads-images]] · [[project-maint-bill-lines-ocr]]
