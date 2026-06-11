"""โหลดค่า .env ของ line_archiver (ไม่พึ่ง python-dotenv)"""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    line_channel_secret: str
    line_access_token: str
    discord_bot_token: str
    discord_guild_id: str


def parse_env(text: str) -> dict:
    vals = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        vals[key.strip()] = val.strip()
    return vals


def load_config(path: Path) -> Config:
    vals = parse_env(path.read_text(encoding="utf-8"))
    return Config(
        line_channel_secret=vals["LINE_CHANNEL_SECRET"],
        line_access_token=vals["LINE_CHANNEL_ACCESS_TOKEN"],
        discord_bot_token=vals["DISCORD_BOT_TOKEN"],
        discord_guild_id=vals["DISCORD_GUILD_ID"],
    )
