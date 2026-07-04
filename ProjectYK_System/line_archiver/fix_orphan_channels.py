# -*- coding: utf-8 -*-
"""Categorize ONLY Discord channels that have no category (parent) yet.

Surgical version of backfill_categories: never touches channels already in a
category, so manual moves by โอ are preserved. Run on server from
C:\\Users\\yklog\\YK_LINE_ARCHIVER.  Default = dry-run; pass --apply to move.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import sqlite3
from pathlib import Path

import db
from categories import category_for
from config import load_config
from discord_api import DiscordClient

APPLY = "--apply" in sys.argv

conn = sqlite3.connect(Path(__file__).parent / "line_archive.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT group_id, name, discord_channel_id FROM line_group "
    "WHERE discord_channel_id IS NOT NULL AND discord_channel_id != ''").fetchall()
by_channel = {r["discord_channel_id"]: r for r in rows}

cfg = load_config(Path(__file__).parent / ".env")
discord = DiscordClient(cfg.discord_bot_token, cfg.discord_guild_id)
channels = discord.list_channels()

orphans = [c for c in channels
           if c.get("type") == 0 and not c.get("parent_id")
           and c["id"] in by_channel]
print(f"text channels: {sum(1 for c in channels if c.get('type') == 0)} | "
      f"tracked-in-db: {len(by_channel)} | uncategorized+tracked: {len(orphans)}")

n = 0
for c in orphans:
    g = by_channel[c["id"]]
    target = category_for(g["name"] or "")
    print(f"  {'MOVE' if APPLY else 'would-move'}: #{c['name']} ({g['name']}) -> {target}")
    if APPLY:
        parent_id = discord.ensure_category(target)
        discord.move_channel(c["id"], parent_id)
        db.set_group_category(conn, g["group_id"], target)
        conn.commit()
        n += 1
print(f"done (moved {n})" if APPLY else "dry-run only — รัน --apply เพื่อย้ายจริง")
