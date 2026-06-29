# Claude Done Alarm — runbook

เสียงเตือนเมื่อ Claude Code เสร็จ/ถาม ดังวนซ้ำจนกดหยุด. คุมจากจอบ้าน+มือถือ.

## ส่วนประกอบ
- `alarm_service.py` — HTTP service port 8030 (stdlib + winsound), เล่น `alarm.wav` วนซ้ำ
- `make_wav.py` — สร้าง alarm.wav ใหม่ถ้าหาย
- `install_task.ps1` — ติดตั้ง Scheduled Task `Claude_Done_Alarm` (เปิด service ตอน logon)
- hooks ใน `~/.claude/settings.json` (ดู snippet ด้านล่าง)

## เปิด/ปิด + หยุด
- จอบ้าน: http://localhost:8030
- มือถือ (ต่อ Tailscale): http://100.71.13.122:8030
- ปุ่ม "หยุด" = ดับเสียงรอบนี้; ปุ่ม "ปิดเสียงทั้งระบบ" = กันหลับ (ไม่ดังจนกว่าจะเปิดใหม่)
- state เปิด/ปิด เก็บที่ `enabled.flag` (คงค่าหลัง restart)

## พฤติกรรม hooks (สำคัญ)
- `Stop` ยิงทุกครั้งที่ Claude จบ turn — รวมตอนคุยกันสดๆ ด้วย ไม่ใช่แค่ตอนรัน Max ยาวจบ
  → ตอนนั่งอยู่หน้าจอคุยกัน เสียงจะดังบ่อย: กด "ปิดเสียงทั้งระบบ" บนเว็บไว้
  → ตอนจะเดินจากไป: กด "เปิดเสียงทั้งระบบ"
- `UserPromptSubmit` ยิง /stop ทุกครั้งที่พิมพ์ส่ง → เดินมาพิมพ์ตอบ = เสียงหยุดเอง
- hooks โหลดตอน **เริ่ม session** — แก้ settings.json แล้วต้องเปิด Claude Code session ใหม่

## มือถือเปิดหน้าเว็บไม่ขึ้น (เคยเจอ)
สาเหตุที่เจอจริง: **มือถือไม่ได้อยู่ใน Tailnet** (ไม่ใช่ firewall/service).
1. เปิดแอป Tailscale บนมือถือ, login บัญชีเดียวกับเครื่องบ้าน (pongsakan@), Connected = เปิด
2. เช็กจากเครื่องบ้านว่ามือถือเข้าวงแล้ว: `& "C:\Program Files\Tailscale\tailscale" status`
   ต้องเห็นบรรทัดมือถือ (เช่น `iphone-... 100.96.x.x ... iOS active`)
3. บนมือถือพิมพ์เต็ม `http://100.71.13.122:8030` (อย่าให้เด้งเป็น https/ค้นหา)

## ติดตั้งใหม่หลัง format เครื่อง
1. `python make_wav.py`  (สร้าง alarm.wav)
2. `powershell -ExecutionPolicy Bypass -File .\install_task.ps1`  (ติดตั้ง + start)
3. เปิด firewall ให้มือถือเข้าได้ (ครั้งเดียว):
   `New-NetFirewallRule -DisplayName "Claude Alarm 8030" -Direction Inbound -Protocol TCP -LocalPort 8030 -Action Allow`
4. ใส่ hooks snippet ลง ~/.claude/settings.json แล้วเปิด Claude Code session ใหม่

## hooks snippet (~/.claude/settings.json — key ระดับบนสุด)
```json
"hooks": {
  "Stop": [{ "hooks": [{ "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/ring" }] }],
  "Notification": [{ "hooks": [{ "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/ring" }] }],
  "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/stop" }] }]
}
```

## แก้ปัญหา
- ไม่มีเสียง: `Get-ScheduledTask Claude_Done_Alarm` State=Running? `curl http://localhost:8030/status`
- ดังไม่หยุด: `curl -X POST http://localhost:8030/stop` หรือกดเว็บ
- เงียบหมด (ไม่ดังเลย): อาจ enabled=false → กด "เปิดเสียงทั้งระบบ" บนเว็บ
- มือถือเข้าไม่ได้: ดูหัวข้อ "มือถือเปิดหน้าเว็บไม่ขึ้น" ด้านบน
- restart service: `Stop-ScheduledTask Claude_Done_Alarm; Start-ScheduledTask Claude_Done_Alarm`
