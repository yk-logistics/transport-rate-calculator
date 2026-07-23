---
name: reference-claude-usage-widget
description: Widget โชว์ /usage บน desktop Windows — endpoint OAuth usage + วิธีที่ Opus เคยดึงไม่ได้ + gotcha IRM แปลง datetime
metadata: 
  node_type: memory
  type: reference
  originSessionId: bbbb07fb-c63c-47ab-9741-4ce4f560580e
---

Widget "Claude Usage" (11 ก.ค. 2026) — แบบเดียวกับโพสต์ FB (Übersicht/macOS) แต่ทำด้วย PowerShell WPF บน Windows:

- ไฟล์: `C:\Users\guole\.claude\usage-widget\ClaudeUsageWidget.ps1` + `launch.vbs` (เปิดแบบไม่มีหน้าต่างดำ) + shortcut ใน `shell:startup` เปิดเองตอนบูต
- UI อังกฤษล้วน (โอขอ — เลี่ยงปัญหา encoding ไทยใน ps1 ด้วย), รีเฟรชทุก 10 วินาที (โอขอ — GET เบาๆ ไม่กินโควต้า), ไม่มีแถวสถานะล่าง/ปุ่ม ↻ (โอขอตัดออก; error โชว์แทนที่บรรทัด reset ของ session), ลากย้ายได้ (จำตำแหน่งใน widget-state.json), แถบสี น้ำเงิน<70 ส้ม<90 แดง≥90
- v2 (โอขอ): เม้าส์ชี้แล้วจาง (อ่านของข้างหลังได้ เม้าส์ออกกลับมาเอง) + tray icon จุดส้มข้างนาฬิกา (ดับเบิลคลิก=ซ่อน/โชว์, คลิกขวา=Refresh/Exit) + ✕ = ซ่อนลง tray ไม่ใช่ปิด + single-instance mutex + shortcut ใน Start Menu ชื่อ "Claude Usage Widget"
- v3 (13 ก.ค. โอขอ): **กดทะลุถาวร** — ใส่ WS_EX_TRANSPARENT (SetWindowLong GWL_EXSTYLE) คลิก/hover ไปโดนของข้างหลังเลย; เพราะ window ไม่รับ mouse event แล้ว hover-fade เลยเปลี่ยนเป็น poll ตำแหน่งเม้าส์ทุก 250ms (`[Forms.Control]::MousePosition` เทียบ `PointToScreen` rect); ย้ายตำแหน่ง = tray เมนู **"Move widget"** ปลด click-through ชั่วคราว ลากเสร็จปล่อยเม้าส์ล็อกกลับเอง
- **gotcha verify**: `FindWindow(null, 'Claude Usage')` จาก session อื่นหาไม่เจอทั้งที่ window อยู่ — ต้องใช้ EnumWindows + GetWindowThreadProcessId เช็คแทน; และ Start-Job ตายพร้อม session ของ tool call → เทสต์ detached ต้อง Start-Process + log file ในคำสั่งเดียว
- **Endpoint ที่ /usage ใช้จริง**: `GET https://api.anthropic.com/api/oauth/usage` — header ต้องมี `Authorization: Bearer <accessToken>` + `anthropic-beta: oauth-2025-04-20` (จุดที่ Opus เคยพลาด: ใช้ x-api-key หรือไม่ใส่ beta header จะไม่ผ่าน)
- token อ่านจาก `~/.claude/.credentials.json` → `claudeAiOauth.accessToken` (Claude Code ต่ออายุให้เอง; ถ้า 401 = เปิด CC สักครั้ง)
- response: `five_hour`/`seven_day` (.utilization/.resets_at) + `limits[]` มี `weekly_scoped` ราย model (Fable)
- **gotcha**: `Invoke-RestMethod` แปลง ISO date เป็น [datetime] ให้เองแล้ว — ห้าม cast เป็น [string] แล้ว Parse ซ้ำ (culture เครื่องทำวัน/เดือนสลับ 11 ก.ค.→7 พ.ย.)
- **gotcha**: kill process ด้วย filter `CommandLine -like '*ชื่อสคริปต์*'` จะฆ่า shell ตัวเองด้วย (command text ติดมาใน CommandLine) — ต้อง exclude `$PID` + ประกอบสตริง marker
- **gotcha (แก้แล้ว 11 ก.ค. ค่ำ)**: อาการ "hover แล้วไม่จาง" ไม่ใช่บั๊ก event — คือ `Invoke-RestMethod` ยิงแบบ sync บน UI thread แล้ว request แขวนครบ TimeoutSec 20 ทุก tick 10 วิ → หน้าต่างแช่แข็ง ~2/3 ของเวลา; แก้เป็น `HttpClient.SendAsync` + poll timer 250ms เช็ค `IsCompleted` (ห้ามกลับไปใช้ IRM sync ใน DispatcherTimer)
- **gotcha เครือข่ายเครื่องโอ**: เส้น IPv6 ไป api.anthropic.com เงียบ (SYN drop) — .NET ลอง AAAA ก่อนเลยแขวนจน timeout ทั้งที่ IPv4 ต่อได้ 18ms (curl รอดเพราะ happy-eyeballs); แก้ในโปรเซสด้วย `[AppContext]::SetSwitch('System.Net.DisableIPv6', $true)` ก่อนใช้เน็ตครั้งแรก — แอป .NET อื่นบนเครื่องนี้อาจเจออาการเดียวกัน
