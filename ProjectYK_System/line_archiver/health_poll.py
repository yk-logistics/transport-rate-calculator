"""Health-poll + Discord alert for the LINE archiver.

Run on a 5-min Scheduled Task. Checks the bot /health (local) and the public
tunnel. Alerts Discord on state CHANGE only (ok->down, down->ok), not every
tick, so it does not spam. Reads tokens from .env. Does NOT touch the bot
pipeline.
"""
import json
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ENV = HERE / ".env"
STATE = HERE / "health_state.json"
LOCAL = "http://127.0.0.1:8020/health"
PUBLIC = "https://line.yklogistics.uk/health"
ALERT_CHANNEL_NAME = "line-archiver-alerts"
API = "https://discord.com/api/v10"


def load_env():
    vals = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals


def probe(url):
    try:
        return httpx.get(url, timeout=10).status_code == 200
    except Exception:
        return False


def discord_channel_id(http, token, guild):
    h = {"Authorization": f"Bot {token}"}
    r = http.get(f"{API}/guilds/{guild}/channels", headers=h, timeout=20)
    r.raise_for_status()
    for ch in r.json():
        if ch.get("type") == 0 and ch.get("name") == ALERT_CHANNEL_NAME:
            return ch["id"]
    r = http.post(f"{API}/guilds/{guild}/channels", headers=h,
                  json={"name": ALERT_CHANNEL_NAME, "type": 0}, timeout=20)
    r.raise_for_status()
    return r.json()["id"]


def alert(env, msg):
    with httpx.Client() as http:
        cid = discord_channel_id(http, env["DISCORD_BOT_TOKEN"], env["DISCORD_GUILD_ID"])
        http.post(f"{API}/channels/{cid}/messages",
                  headers={"Authorization": f"Bot {env['DISCORD_BOT_TOKEN']}"},
                  json={"content": msg[:1900]}, timeout=20)


def main():
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
    if prev is None:
        pass  # first run: seed state, no alert
    elif prev and not now_ok:
        alert(env, f"\U0001F534 LINE archiver DOWN {ts} {detail}")
    elif (not prev) and now_ok:
        alert(env, f"\U0001F7E2 LINE archiver RECOVERED {ts} {detail}")
    STATE.write_text(json.dumps({"ok": now_ok, "ts": ts, "local": local_ok, "public": public_ok}))
    print(f"{ts} ok={now_ok} {detail} (prev={prev})")


if __name__ == "__main__":
    main()
