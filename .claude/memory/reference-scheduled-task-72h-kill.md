---
name: reference-scheduled-task-72h-kill
description: Windows Task Scheduler ฆ่างานที่รันเกิน 72 ชม. โดยดีฟอลต์ (ExecutionTimeLimit=PT72H) — เคยทำ TradeLab ดับ 9ก.ค.; แก้เป็น PT0S แล้ว 3 task
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3323cfdd-942a-44da-bc85-095450412c8b
---

**9 ก.ค. 2026 โอถาม "ทำไมบอทเทรดเข้าไม่ได้":** `trade.yklogistics.uk` = 502
(tunnel ยังอยู่ แต่พอร์ต 8030 ไม่มีใครฟัง)

**root cause:** `YK_TRADELAB` ตั้ง `ExecutionTimeLimit = PT72H` (ค่า **ดีฟอลต์**ของ Task
Scheduler = "Stop the task if it runs longer than 3 days") — task สตาร์ท 6ก.ค. 18:22:37 →
Windows ฆ่าทิ้งเอง 9ก.ค. 18:22 (snapshot สุดท้าย 18:14:59; `LastTaskResult=267014`
= `SCHED_S_TASK_TERMINATED`) **ไม่ใช่บอทพัง**

**แก้แล้ว → `PT0S` (ไม่จำกัด) 3 ตัว:** `YK_TRADELAB`, `YK_MVP_APP`, `YK_CLOUDFLARED_TUNNEL`
(สองตัวหลังเป็นระเบิดเวลาเหมือนกัน — MVP รอดมาเพราะ deploy บ่อย นาฬิกาเลยรีเซ็ตทุกครั้ง)
`YK_LINE_ARCHIVER` / `YK_UPS_Watch` เป็น PT0S อยู่แล้ว

**เช็คเร็ว:**
```powershell
(Get-ScheduledTask -TaskName X).Settings.ExecutionTimeLimit   # ต้องเป็น PT0S
Get-ScheduledTaskInfo -TaskName X | Select LastRunTime,LastTaskResult
```
`267014`=ถูกสั่งหยุด · `267009`=กำลังรัน · `0`=จบปกติ

**gotcha:** TradeLab watchdog (`schtask ทุก 30 นาที`, ปลุกเมื่อ snapshot เก่า >40 นาที)
จะกู้ให้เองแต่ช้า ~50 นาที และเดิมจะโดนฆ่าซ้ำทุก 3 วัน · พอร์ต: MVP 8010 · archiver 8020 ·
TradeLab 8030 (ingress ที่ `C:\Users\yklog\.cloudflared\config.yml`)

ดู [[project-tradelab-paper-bot]] · [[reference-mvp-server-deploy]]
