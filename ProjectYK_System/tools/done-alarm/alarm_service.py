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
