# -*- coding: utf-8 -*-
"""Watchdog MVP (8010) — scheduled task ทุก 5 นาที บน server.

ลอก pattern จาก YK_LINE_ARCHIVER/health_poll.py (แจ้ง Discord เฉพาะตอน "เปลี่ยนสถานะ"
ไม่ spam) + เพิ่ม: ล่มแล้ว **ลองสตาร์ทกลับอัตโนมัติ 1 ครั้งต่อรอบล่ม** ผ่าน
scheduled task YK_MVP_APP แล้วรายงานผลใน alert เดียวกัน.

- ใช้ stdlib ล้วน (urllib) — ไม่ผูก venv ไหน รันด้วย python ตัวไหนก็ได้บนเครื่อง
- token Discord อ่านจาก .env ของ archiver (read-only — ชุดเดียวกับ backup alert)
- ห้ามยุ่ง service 8020 เด็ดขาด

ติดตั้ง (ครั้งเดียว): scp ไฟล์นี้ไป C:/Users/yklog/YK_MVP/ แล้วรัน register_mvp_watchdog.ps1
"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV = Path(r"C:\Users\yklog\YK_LINE_ARCHIVER\.env")   # token ชุดเดียวกับ archiver/backup
STATE = HERE / "mvp_health_state.json"
LOCAL = "http://127.0.0.1:8010/health"
PUBLIC = "https://app.yklogistics.uk/health"
ALERT_CHANNEL_NAME = "yk-mvp-alerts"
API = "https://discord.com/api/v10"


def load_env() -> dict:
    vals = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals


def _http(url: str, token: str = "", payload: dict | None = None) -> dict | list:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "YK-MVP-Watchdog/1.0")   # Discord/CF ต้องมี UA ไม่งั้น 403
    if token:
        req.add_header("Authorization", f"Bot {token}")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode("utf-8")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def probe(url: str) -> bool:
    try:
        # ต้องมี User-Agent ปกติ — Cloudflare บล็อค UA 'Python-urllib' (เจอจริงตอนติดตั้ง)
        req = urllib.request.Request(url, headers={"User-Agent": "YK-MVP-Watchdog/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def alert(env: dict, msg: str) -> None:
    try:
        token, guild = env["DISCORD_BOT_TOKEN"], env["DISCORD_GUILD_ID"]
        cid = None
        for ch in _http(f"{API}/guilds/{guild}/channels", token):
            if ch.get("type") == 0 and ch.get("name") == ALERT_CHANNEL_NAME:
                cid = ch["id"]
                break
        if cid is None:
            cid = _http(f"{API}/guilds/{guild}/channels", token,
                        {"name": ALERT_CHANNEL_NAME, "type": 0})["id"]
        _http(f"{API}/channels/{cid}/messages", token, {"content": msg[:1900]})
    except Exception as e:  # alert พังต้องไม่ทำ watchdog พัง
        print("alert failed:", e)


def try_restart() -> str:
    """สตาร์ท MVP กลับผ่าน scheduled task เดิม — คืนข้อความผลไว้ใส่ alert."""
    try:
        subprocess.run(["schtasks", "/Run", "/TN", "YK_MVP_APP"],
                       capture_output=True, timeout=30, check=True)
        time.sleep(20)
        return "🔁 สั่งสตาร์ทกลับแล้ว → " + ("🟢 ฟื้นแล้ว" if probe(LOCAL) else "🔴 ยังไม่ขึ้น (ต้องคนดู)")
    except Exception as e:
        return f"🔁 สั่งสตาร์ทกลับไม่สำเร็จ: {e}"


def main() -> None:
    env = load_env()
    local_ok = probe(LOCAL)
    public_ok = probe(PUBLIC)
    now_ok = local_ok and public_ok
    prev = None
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text()).get("ok")
        except Exception:
            prev = None
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    detail = f"(local={'OK' if local_ok else 'DOWN'}, public={'OK' if public_ok else 'DOWN'})"

    restart_note = ""
    if not local_ok and prev is not False:
        # เพิ่งล่มรอบนี้ → ลองกู้เอง 1 ครั้ง (ล่มค้าง prev=False จะไม่วนสั่งซ้ำทุก 5 นาที)
        restart_note = " " + try_restart()
        local_ok = probe(LOCAL)
        now_ok = local_ok and probe(PUBLIC)

    if prev is None:
        pass  # รอบแรก: จำสถานะเฉยๆ
    elif prev and not now_ok:
        alert(env, f"🔴 YK MVP (8010) DOWN {ts} {detail}{restart_note}")
    elif (not prev) and now_ok:
        alert(env, f"🟢 YK MVP (8010) RECOVERED {ts} {detail}")

    STATE.write_text(json.dumps({"ok": now_ok, "ts": ts,
                                 "local": local_ok, "public": public_ok}))
    print(f"{ts} ok={now_ok} {detail} (prev={prev}){restart_note}")


if __name__ == "__main__":
    main()
