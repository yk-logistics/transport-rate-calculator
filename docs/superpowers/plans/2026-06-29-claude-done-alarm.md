# Claude Done Alarm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เสียงเตือนวนซ้ำเมื่อ Claude Code เสร็จงาน/ถาม จนกว่าจะกดหยุด, คุมเปิด/ปิด+หยุดได้ทั้งจากจอบ้านและมือถือผ่าน Tailscale.

**Architecture:** Python stdlib HTTP service (port 8030) บนเครื่องบ้าน เล่นเสียง `.wav` วนซ้ำใน thread แยก, เสิร์ฟหน้าเว็บปุ่มหยุดหน้าเดียว, เปิด/ปิดผ่าน flag file. Claude Code hooks (Stop/Notification → /ring, UserPromptSubmit → /stop) ยิง curl ไป service. Scheduled Task เปิด service ตอน boot.

**Tech Stack:** Python 3.12 stdlib เท่านั้น (`http.server`, `winsound`, `wave`, `struct`, `threading`, `json`), PowerShell (installer/scheduled task), Claude Code settings.json hooks, Tailscale (มีอยู่).

## Global Constraints

- Python stdlib เท่านั้น — ห้ามเพิ่ม dependency (`pip install` ใดๆ).
- Windows-only (winsound) — ตรงเครื่องโอ Win11.
- Port = **8030** (เลี่ยง 8010 app, 8020 LINE archiver).
- วางที่ `_Claude Tools/done-alarm/` (นอก app YK, ไม่แตะ ProjectYK_System).
- bind `0.0.0.0:8030`; access จาก Tailscale เท่านั้น (ไม่ port-forward ออกเน็ต).
- Tailscale IP เครื่องบ้าน = `100.71.13.122`.
- ไม่แตะเงิน/payroll/DB — ไม่ต้อง preflight.
- ไม่ทำ slash command (YAGNI). ไม่ผูกเข้า LINE archiver.

---

### Task 1: สร้างไฟล์เสียงเตือน (alarm.wav)

**Files:**
- Create: `_Claude Tools/done-alarm/make_wav.py`
- Output: `_Claude Tools/done-alarm/alarm.wav`

**Interfaces:**
- Produces: ไฟล์ `_Claude Tools/done-alarm/alarm.wav` — mono 16-bit PCM, ~1.5 วินาที, เสียงบี๊บดังสองโทนสลับ (ดังพอปลุก). Task 2 เล่นไฟล์นี้.

- [ ] **Step 1: เขียนสคริปต์สร้าง wav ด้วย stdlib**

`_Claude Tools/done-alarm/make_wav.py`:

```python
"""สร้าง alarm.wav (stdlib only) — เสียงบี๊บสองโทนสลับ ดังพอปลุก."""
import wave
import struct
import math
import os

SAMPLE_RATE = 44100
AMPLITUDE = 26000  # /32767 — ดังแต่ไม่ clip
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")


def tone(freq, dur):
    n = int(SAMPLE_RATE * dur)
    for i in range(n):
        # square-ish ผ่าน sign(sin) ทำให้แสบหู/ปลุกง่ายกว่า sine ล้วน
        s = math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
        val = AMPLITUDE if s >= 0 else -AMPLITUDE
        yield struct.pack("<h", val)


def silence(dur):
    for _ in range(int(SAMPLE_RATE * dur)):
        yield struct.pack("<h", 0)


def main():
    frames = []
    # บี๊บ-บี๊บ: 880Hz / เงียบ / 1175Hz / เงียบ
    for chunk in (tone(880, 0.35), silence(0.12),
                  tone(1175, 0.35), silence(0.12),
                  tone(880, 0.35), silence(0.20)):
        frames.extend(chunk)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"".join(frames))
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: รันสร้างไฟล์**

Run: `python "_Claude Tools/done-alarm/make_wav.py"`
Expected: `wrote ...alarm.wav <N> bytes` (N > 100000)

- [ ] **Step 3: ตรวจว่าเล่นได้ + ได้ยินจริง**

Run: `python -c "import winsound; winsound.PlaySound(r'_Claude Tools/done-alarm/alarm.wav', winsound.SND_FILENAME)"`
Expected: ได้ยินเสียงบี๊บสองโทนสลับ ~1.5 วิ (verify ด้วยหูจากเครื่องบ้าน)

- [ ] **Step 4: Commit**

```bash
git add "_Claude Tools/done-alarm/make_wav.py" "_Claude Tools/done-alarm/alarm.wav"
git commit -m "feat(alarm): generate alarm.wav (stdlib two-tone beep)"
```

---

### Task 2: Alarm service (เล่นเสียงวนซ้ำ + endpoints + หน้าเว็บ)

**Files:**
- Create: `_Claude Tools/done-alarm/alarm_service.py`
- Runtime: `_Claude Tools/done-alarm/enabled.flag` (สร้างอัตโนมัติตอนรัน)

**Interfaces:**
- Consumes: `alarm.wav` จาก Task 1 (path เดียวกับสคริปต์).
- Produces: HTTP service บน `0.0.0.0:8030` พร้อม endpoints:
  - `POST /ring` → ถ้า enabled เริ่มเสียงวนซ้ำ, คืน `{"ok":true,"ringing":<bool>}`
  - `POST /stop` → หยุดเสียง, คืน `{"ok":true,"ringing":false}`
  - `POST /toggle` → สลับ enabled (เขียน flag), ถ้าปิดก็หยุดเสียง, คืน `{"ok":true,"enabled":<bool>}`
  - `GET /status` → `{"ringing":<bool>,"enabled":<bool>}`
  - `GET /` → หน้าเว็บ HTML ปุ่มหยุด (Task 3 ฝังใน service นี้)
  Task 4 (hooks) ยิง `/ring` และ `/stop`. Task 5 (installer) รันไฟล์นี้.

- [ ] **Step 1: เขียน service โครงหลัก (state + winsound loop + endpoints)**

`_Claude Tools/done-alarm/alarm_service.py`:

```python
"""Claude done-alarm service — เล่นเสียงวนซ้ำจนกดหยุด, คุมจากเว็บ (จอบ้าน+มือถือ Tailscale).
stdlib only. Windows (winsound). Port 8030.
"""
import json
import os
import threading
import time
import winsound
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "alarm.wav")
FLAG = os.path.join(HERE, "enabled.flag")
PORT = 8030
LOOP_GAP = 0.2  # วินาทีพักระหว่างรอบเล่นซ้ำ

_state_lock = threading.Lock()
_ringing = False


def _load_enabled():
    # ไม่มีไฟล์ = เปิด (default on); "0" = ปิด
    try:
        with open(FLAG, "r", encoding="utf-8") as f:
            return f.read().strip() != "0"
    except FileNotFoundError:
        return True


def _save_enabled(value):
    with open(FLAG, "w", encoding="utf-8") as f:
        f.write("1" if value else "0")


_enabled = _load_enabled()


def _alarm_loop():
    """เล่น wav วนซ้ำตราบที่ _ringing เป็น True."""
    while True:
        with _state_lock:
            ring = _ringing
        if ring:
            # SND_FILENAME แบบ sync (บล็อกจนจบไฟล์) แล้ววนใหม่ → ดังต่อเนื่อง
            try:
                winsound.PlaySound(WAV, winsound.SND_FILENAME)
            except RuntimeError:
                time.sleep(0.5)
            time.sleep(LOOP_GAP)
        else:
            time.sleep(0.15)


def start_ring():
    global _ringing
    with _state_lock:
        if not _enabled:
            return False
        _ringing = True
        return True


def stop_ring():
    global _ringing
    with _state_lock:
        _ringing = False


def toggle_enabled():
    global _enabled, _ringing
    with _state_lock:
        _enabled = not _enabled
        _save_enabled(_enabled)
        if not _enabled:
            _ringing = False
        return _enabled


def status():
    with _state_lock:
        return {"ringing": _ringing, "enabled": _enabled}
```

- [ ] **Step 2: เพิ่ม HTML page + request handler + main**

ต่อท้ายไฟล์เดิม:

```python
PAGE = """<!doctype html><html lang="th"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Alarm</title>
<style>
 *{box-sizing:border-box} body{margin:0;font-family:system-ui,sans-serif;background:#111;color:#eee;
  display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;gap:24px;padding:20px}
 #stop{width:80vw;max-width:480px;height:38vh;font-size:13vw;font-weight:800;border:none;border-radius:24px;
  background:#e11;color:#fff;cursor:pointer} #stop:active{background:#a00}
 .row{display:flex;gap:16px;align-items:center}
 #toggle{font-size:1.2rem;padding:14px 22px;border-radius:14px;border:2px solid #888;background:#222;color:#eee;cursor:pointer}
 #state{font-size:1.4rem;text-align:center;min-height:1.6em}
 .dot{font-size:2rem}
</style></head><body>
 <div id="state">…</div>
 <button id="stop">หยุด</button>
 <div class="row"><button id="toggle">…</button></div>
<script>
 async function post(p){await fetch(p,{method:'POST'});refresh();}
 async function refresh(){
   const r=await fetch('/status');const s=await r.json();
   document.getElementById('state').innerHTML=
     (s.ringing?'<span class=dot>🔴</span> กำลังดัง':'<span class=dot>⚪</span> เงียบ');
   document.getElementById('toggle').textContent= s.enabled?'ปิดเสียงทั้งระบบ (กันหลับ)':'เปิดเสียงทั้งระบบ';
   document.getElementById('toggle').style.borderColor= s.enabled?'#3a3':'#a33';
 }
 document.getElementById('stop').onclick=()=>post('/stop');
 document.getElementById('toggle').onclick=()=>post('/toggle');
 refresh();setInterval(refresh,2000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, PAGE, "text/html")
        elif self.path == "/status":
            self._send(200, json.dumps(status()))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if self.path == "/ring":
            r = start_ring()
            self._send(200, json.dumps({"ok": True, "ringing": status()["ringing"], "started": r}))
        elif self.path == "/stop":
            stop_ring()
            self._send(200, json.dumps({"ok": True, "ringing": False}))
        elif self.path == "/toggle":
            en = toggle_enabled()
            self._send(200, json.dumps({"ok": True, "enabled": en}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, *a):
        pass  # เงียบ log


def main():
    threading.Thread(target=_alarm_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"alarm service on http://0.0.0.0:{PORT} (wav={WAV}, enabled={_enabled})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: รัน service ใน background แล้วทดสอบ status**

Run (terminal แยก / background):
```
python "_Claude Tools/done-alarm/alarm_service.py"
```
แล้วอีก terminal:
```
curl -s -X GET http://localhost:8030/status
```
Expected: `{"ringing": false, "enabled": true}`

- [ ] **Step 4: ทดสอบ ring → ได้ยินเสียงวนซ้ำจริง**

Run: `curl -s -X POST http://localhost:8030/ring`
Expected: คืน `{"ok": true, "ringing": true, "started": true}` **และได้ยินเสียงบี๊บวนซ้ำต่อเนื่อง** (ไม่หยุดเอง) — verify ด้วยหู

- [ ] **Step 5: ทดสอบ stop → เสียงหยุด**

Run: `curl -s -X POST http://localhost:8030/stop`
Expected: คืน `{"ok": true, "ringing": false}` และเสียงหยุดภายใน ~1.5 วิ (จบรอบที่เล่นค้าง)

- [ ] **Step 6: ทดสอบ toggle ปิดระบบ → ring แล้วเงียบ**

Run:
```
curl -s -X POST http://localhost:8030/toggle
curl -s -X POST http://localhost:8030/ring
```
Expected: toggle คืน `{"ok":true,"enabled":false}`; ring คืน `started:false` และ **ไม่มีเสียง**. แล้ว `curl -s -X POST http://localhost:8030/toggle` กลับมา enabled=true. หยุด service (Ctrl-C / kill background).

- [ ] **Step 7: Commit**

```bash
git add "_Claude Tools/done-alarm/alarm_service.py"
git commit -m "feat(alarm): service port 8030 — looping winsound + ring/stop/toggle/status + web page"
```

---

### Task 3: ทดสอบหน้าเว็บปุ่มหยุดผ่านมือถือ (Tailscale)

หมายเหตุ: HTML ฝังใน service แล้ว (Task 2 Step 2) — task นี้คือ **verify การเข้าถึงจากมือถือ** ซึ่งเป็นข้อกำหนดหลักของโอ (สั่งหยุดเสียงบ้านจากมือถือได้จริง).

**Files:** ไม่มีไฟล์ใหม่ (verify อย่างเดียว)

**Interfaces:**
- Consumes: service ที่รันจาก Task 2.

- [ ] **Step 1: เปิด service ค้าง + ยืนยัน Tailscale IP**

Run:
```
python "_Claude Tools/done-alarm/alarm_service.py"
"/c/Program Files/Tailscale/tailscale" ip -4
```
Expected: service รัน; IP = `100.71.13.122` (ถ้าต่างให้ใช้ค่าจริงในขั้นต่อไป)

- [ ] **Step 2: เปิดหน้าเว็บบนจอบ้าน**

เปิด browser → `http://localhost:8030`
Expected: เห็นปุ่ม "หยุด" สีแดงเต็มจอ + สถานะ "⚪ เงียบ" + ปุ่ม "ปิดเสียงทั้งระบบ (กันหลับ)"

- [ ] **Step 3: ทดสอบหยุดจากเว็บ**

`curl -s -X POST http://localhost:8030/ring` (ให้เสียงดัง) → กดปุ่ม "หยุด" บนหน้าเว็บจอบ้าน
Expected: เสียงหยุด, สถานะหน้าเว็บเปลี่ยนเป็น "⚪ เงียบ" ภายใน ~2 วิ

- [ ] **Step 4: ทดสอบจากมือถือผ่าน Tailscale**

บนมือถือ (ต่อ Tailscale อยู่) เปิด `http://100.71.13.122:8030` → `curl ... /ring` จากเครื่องบ้านให้เสียงดัง → กด "หยุด" บนมือถือ
Expected: **เสียงที่ลำโพงเครื่องบ้านหยุดจริง** เมื่อกดจากมือถือ. (ถ้าเข้าไม่ได้: เช็ก Tailscale มือถือ online + Windows Firewall ปล่อย inbound port 8030 บน Tailscale interface — เพิ่ม rule ใน Step 5)

- [ ] **Step 5: (ถ้า Step 4 เข้าไม่ได้) เพิ่ม firewall rule แล้วทดสอบซ้ำ**

Run (PowerShell, ครั้งเดียว):
```powershell
New-NetFirewallRule -DisplayName "Claude Alarm 8030" -Direction Inbound -Protocol TCP -LocalPort 8030 -Action Allow
```
แล้วทำ Step 4 ซ้ำจนผ่าน. หยุด service.

- [ ] **Step 6: Commit (บันทึกผลทดสอบใน design ถ้าต้องแก้ port/firewall)**

ถ้าไม่มีไฟล์เปลี่ยน ข้าม commit. ถ้าเพิ่ม firewall ลง runbook (Task 5) ค่อย commit ที่ Task 5.

---

### Task 4: Claude Code hooks (settings.json)

**Files:**
- Modify: `C:/Users/guole/.claude/settings.json`

**Interfaces:**
- Consumes: endpoints `/ring`, `/stop` จาก Task 2.
- Produces: พฤติกรรม — Claude เสร็จ/ถาม → เสียงดัง; โอพิมพ์ → เสียงหยุด.

หมายเหตุ: settings.json ปัจจุบัน **ไม่มี** key `hooks`. ใช้ `curl --silent --max-time 2` เพื่อไม่ block UI และ fail เงียบถ้า service ไม่รัน. Windows มี `curl.exe` ติดมากับ OS.

- [ ] **Step 1: อ่าน settings.json ปัจจุบัน (ยืนยันโครงสร้าง)**

Run: อ่าน `C:/Users/guole/.claude/settings.json`
Expected: เห็น JSON ที่ไม่มี key `hooks` (ยืนยันก่อนแก้)

- [ ] **Step 2: เพิ่ม block `hooks` (ผ่าน update-config skill หรือแก้ JSON ตรง)**

เพิ่ม key `"hooks"` ระดับบนสุดของ settings.json (เคียงกับ `"permissions"`):

```json
"hooks": {
  "Stop": [
    { "hooks": [ { "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/ring" } ] }
  ],
  "Notification": [
    { "hooks": [ { "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/ring" } ] }
  ],
  "UserPromptSubmit": [
    { "hooks": [ { "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/stop" } ] }
  ]
}
```

- [ ] **Step 3: ตรวจ JSON ยัง valid**

Run: `python -c "import json;json.load(open(r'C:/Users/guole/.claude/settings.json',encoding='utf-8'));print('ok')"`
Expected: `ok`

- [ ] **Step 4: ทดสอบ end-to-end ด้วย session จริง**

เปิด service (Task 2) → ใน Claude Code session ใหม่ ให้ Claude จบ turn (Stop hook ยิง)
Expected: ได้ยินเสียงดังวนซ้ำเมื่อ Claude เสร็จ; พิมพ์ข้อความตอบ (UserPromptSubmit) → เสียงหยุด

หมายเหตุ: hooks โหลดตอนเริ่ม session — ต้องเปิด session ใหม่หลังแก้ settings.json.

- [ ] **Step 5: Commit (settings.json อยู่นอก repo — ไม่ commit; บันทึก snippet ลง runbook Task 5)**

settings.json อยู่ที่ `~/.claude/` ไม่ใช่ใน repo. ไม่ commit. snippet hooks จะถูกบันทึกใน runbook (Task 5) เพื่อกู้คืนหลัง format เครื่อง.

---

### Task 5: Boot persistence (Scheduled Task) + runbook

**Files:**
- Create: `_Claude Tools/done-alarm/install_task.ps1`
- Create: `_Claude Tools/done-alarm/RUNBOOK.md`

**Interfaces:**
- Consumes: `alarm_service.py` (Task 2).
- Produces: Scheduled Task `Claude_Done_Alarm` รัน service ตอน logon; runbook อธิบายติดตั้ง/แก้ปัญหา + เก็บ hooks snippet (กู้หลัง format).

- [ ] **Step 1: เขียน installer PowerShell**

`_Claude Tools/done-alarm/install_task.ps1`:

```powershell
# ติดตั้ง Scheduled Task เปิด alarm service ตอน logon (รันใต้ user เพื่อให้เข้าถึงเสียง)
$ErrorActionPreference = "Stop"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$py     = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$script = Join-Path $here "alarm_service.py"
if (-not (Test-Path $py))     { throw "python not found: $py" }
if (-not (Test-Path $script)) { throw "service not found: $script" }

$action  = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -AtLogOn
$set     = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
             -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$set.ExecutionTimeLimit = "PT0S"  # ไม่จำกัดเวลา (service รันยาว)

Register-ScheduledTask -TaskName "Claude_Done_Alarm" -Action $action -Trigger $trigger `
  -Settings $set -RunLevel Limited -Force | Out-Null
Write-Host "registered Claude_Done_Alarm; starting now..."
Start-ScheduledTask -TaskName "Claude_Done_Alarm"
```

- [ ] **Step 2: รัน installer**

Run (PowerShell): `& "_Claude Tools/done-alarm/install_task.ps1"`
Expected: `registered Claude_Done_Alarm; starting now...` ไม่มี error

- [ ] **Step 3: ตรวจ task รัน + service ตอบ**

Run:
```powershell
Get-ScheduledTask -TaskName "Claude_Done_Alarm" | Select-Object State
```
แล้ว: `curl -s http://localhost:8030/status`
Expected: State = Running; status คืน JSON ปกติ

- [ ] **Step 4: ทดสอบ reboot-persistence (sign-out/in หรือ restart task)**

Run: `Stop-ScheduledTask -TaskName "Claude_Done_Alarm"; Start-ScheduledTask -TaskName "Claude_Done_Alarm"`
แล้ว `curl -s http://localhost:8030/status`
Expected: service กลับมาตอบเอง (จำลองการ start ตอน logon)

- [ ] **Step 5: เขียน runbook**

`_Claude Tools/done-alarm/RUNBOOK.md`:

```markdown
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

## ติดตั้งใหม่หลัง format เครื่อง
1. `python make_wav.py`  (สร้าง alarm.wav)
2. `& .\install_task.ps1`  (ติดตั้ง + start)
3. ถ้ามือถือเข้าไม่ได้: `New-NetFirewallRule -DisplayName "Claude Alarm 8030" -Direction Inbound -Protocol TCP -LocalPort 8030 -Action Allow`
4. ใส่ hooks snippet ลง ~/.claude/settings.json แล้วเปิด Claude Code session ใหม่

## hooks snippet (~/.claude/settings.json — key ระดับบนสุด)
\`\`\`json
"hooks": {
  "Stop": [{ "hooks": [{ "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/ring" }] }],
  "Notification": [{ "hooks": [{ "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/ring" }] }],
  "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "curl --silent --max-time 2 -X POST http://localhost:8030/stop" }] }]
}
\`\`\`

## แก้ปัญหา
- ไม่มีเสียง: เช็ก `Get-ScheduledTask Claude_Done_Alarm` State=Running; `curl http://localhost:8030/status`
- ดังไม่หยุด: `curl -X POST http://localhost:8030/stop` หรือกดเว็บ
- เงียบหมด (ไม่ดังเลย): อาจ enabled=false → กด "เปิดเสียงทั้งระบบ" บนเว็บ
- มือถือเข้าไม่ได้: Tailscale online? firewall port 8030?
```

- [ ] **Step 6: Commit**

```bash
git add "_Claude Tools/done-alarm/install_task.ps1" "_Claude Tools/done-alarm/RUNBOOK.md"
git commit -m "feat(alarm): boot-persistent scheduled task + runbook (recover after format)"
```

---

## Self-Review

**Spec coverage:**
- เสียงตอนเสร็จ + ตอนถาม → Task 4 (Stop + Notification hooks) ✓
- ดังวนซ้ำจนกดปิด → Task 2 (_alarm_loop) ✓
- หยุดจากจอบ้าน + มือถือ → Task 2 (/stop) + Task 3 (Tailscale verify) ✓
- มือถือสั่งดับเสียงบ้าน real-time → Task 3 Step 4 ✓
- push มือถือ → พฤติกรรม Claude (PushNotification, agentPushNotifEnabled=true แล้ว) — ไม่ต้อง task โค้ด ✓
- เปิด/ปิดทั้งระบบ (กันหลับ) → Task 2 (/toggle + enabled.flag) + หน้าเว็บปุ่ม ✓
- ไฟล์เสียง Claude หาให้ → Task 1 ✓
- Tailscale → Task 3 ✓
- boot-persistent → Task 5 ✓

**Placeholder scan:** ไม่มี TBD/TODO; ทุก step มีโค้ด/คำสั่งจริง.

**Type consistency:** endpoint paths (/ring /stop /toggle /status) ตรงกันระหว่าง Task 2 (นิยาม), Task 3 (เว็บ), Task 4 (hooks), Task 5 (runbook). ฟังก์ชัน start_ring/stop_ring/toggle_enabled/status ใช้ชื่อเดียวกันทั้งไฟล์.

**Note ต่างจาก plan template:** ส่วน `_Claude Tools/` ไม่มี pytest harness — verification เป็น manual (ฟังเสียง/curl/มือถือ) ตามธรรมชาติของเครื่องมือนี้ ไม่ฝืนสร้าง test framework ที่ไม่มีอยู่.
