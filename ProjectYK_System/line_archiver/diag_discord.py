"""เทียบ DB <-> Discord จริง (read-only): หา channel ที่ DB ชี้แต่ Discord ไม่มี
รันบน server:  .venv\Scripts\python.exe diag_discord.py
"""
import sqlite3
import sys
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")
base = Path(__file__).parent

# โหลด .env
from config import load_config
cfg = load_config(base / ".env")

API = "https://discord.com/api/v10"
headers = {"Authorization": f"Bot {cfg.discord_bot_token}"}
r = httpx.get(f"{API}/guilds/{cfg.discord_guild_id}/channels", headers=headers, timeout=30)
r.raise_for_status()
chans = r.json()
text_ch = {ch["id"]: ch["name"] for ch in chans if ch.get("type") == 0}
print(f"Discord มี text channel ทั้งหมด: {len(text_ch)}")

c = sqlite3.connect(base / "line_archive.db")
c.row_factory = sqlite3.Row
groups = c.execute("SELECT group_id, name, discord_channel_id AS ch FROM line_group").fetchall()
print(f"DB มีกลุ่มทั้งหมด: {len(groups)}")
print()

dangling = []   # DB ชี้ channel ที่ Discord ไม่มีแล้ว
no_ch = []      # DB ไม่มี channel_id
ok = 0
for g in groups:
    if not g["ch"]:
        no_ch.append(g)
    elif g["ch"] not in text_ch:
        dangling.append(g)
    else:
        ok += 1

print("=" * 70)
print(f">>> กลุ่มที่ DB ชี้ channel ที่ Discord ลบไปแล้ว (forward 404!): {len(dangling)} <<<")
print("=" * 70)
for g in dangling:
    print(f"  - {g['name'] or '(no name)'}   (ch_id={g['ch']})")

print()
print(f">>> กลุ่มที่ไม่มี channel_id ใน DB: {len(no_ch)} <<<")
for g in no_ch:
    print(f"  - {g['name'] or '(no name)'}")

print()
print("=" * 70)
print(f"สรุป: ปกติ {ok} | channel หาย {len(dangling)} | ไม่มี ch_id {len(no_ch)}")
print("=" * 70)
