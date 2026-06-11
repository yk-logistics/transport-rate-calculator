"""Discord REST API (bot token): สร้าง channel + โพสต์ข้อความ/ไฟล์"""
import re

import httpx

API = "https://discord.com/api/v10"
MAX_UPLOAD = 10 * 1024 * 1024  # ลิมิตอัปโหลด bot ~10MB — เกินนี้โพสต์เป็นข้อความแจ้ง path แทน
MAX_CONTENT = 1900  # Discord จำกัด 2000 ตัวอักษร เผื่อ margin


def channel_name_for(group_name: str | None) -> str:
    name = (group_name or "").strip().lower()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^a-z0-9฀-๿\-_]", "", name)
    name = name.strip("-")
    if not name:
        return "line-group"
    return ("line-" + name)[:90]


class DiscordClient:
    def __init__(self, bot_token: str, guild_id: str):
        self._headers = {"Authorization": f"Bot {bot_token}"}
        self.guild_id = guild_id

    def create_channel(self, name: str) -> str:
        r = httpx.post(f"{API}/guilds/{self.guild_id}/channels",
                       headers=self._headers,
                       json={"name": name, "type": 0}, timeout=30)
        r.raise_for_status()
        return r.json()["id"]

    def post_text(self, channel_id: str, content: str) -> None:
        r = httpx.post(f"{API}/channels/{channel_id}/messages",
                       headers=self._headers,
                       json={"content": content[:MAX_CONTENT]}, timeout=30)
        r.raise_for_status()

    def post_file(self, channel_id: str, filename: str, data: bytes,
                  content: str = "") -> None:
        r = httpx.post(f"{API}/channels/{channel_id}/messages",
                       headers=self._headers,
                       data={"content": content[:MAX_CONTENT]},
                       files={"files[0]": (filename, data)}, timeout=60)
        r.raise_for_status()
