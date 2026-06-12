"""จัดหมวด Discord ย้อนหลังให้ channel เดิมทั้งหมด

  python backfill_categories.py            # dry-run (default) — แค่พิมพ์ตาราง ไม่แตะ Discord
  python backfill_categories.py --apply    # จัดจริง: ensure category + move channel + เขียน DB

dry-run เขียนตาราง 'ชื่อกลุ่ม -> category' ลง backfill_preview.txt (UTF-8) + สรุปนับต่อหมวด
ให้โอรีวิวก่อน apply เสมอ (กฎ ห้ามเดา — เดาชื่อกลุ่มผิดได้)
"""
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

import db
from categories import category_for
from config import load_config
from discord_api import DiscordClient

BASE = Path(__file__).parent
PREVIEW_FILE = BASE / "backfill_preview.txt"


def load_groups(conn):
    """กลุ่มที่มี channel แล้ว (จัดได้) — เรียงตาม category แล้วชื่อ"""
    rows = conn.execute(
        "SELECT group_id, name, discord_channel_id, category FROM line_group "
        "WHERE discord_channel_id IS NOT NULL"
    ).fetchall()
    items = [(r["group_id"], r["name"], r["discord_channel_id"], category_for(r["name"]),
              r["category"]) for r in rows]
    items.sort(key=lambda x: (x[3], (x[1] or "")))
    return items


def dry_run(conn) -> None:
    items = load_groups(conn)
    counts = Counter(target for *_ , target, _current in items)
    lines = []
    for _gid, name, _ch, target, current in items:
        mark = "" if current == target else "  <-- เปลี่ยน" if current else "  (ใหม่)"
        lines.append(f"{target:<14} | {name or '(ไม่มีชื่อ)'}{mark}")
    summary = ["สรุปต่อหมวด:"] + [f"  {cat:<14} {n}" for cat, n in sorted(counts.items())]
    summary.append(f"  {'รวม':<14} {len(items)}")
    body = "\n".join(["= dry-run: ยังไม่แตะ Discord =", "", *lines, "", *summary]) + "\n"
    PREVIEW_FILE.write_text(body, encoding="utf-8")
    footer = (f"\n-> เขียนตารางลง {PREVIEW_FILE.name} แล้ว ({len(items)} กลุ่ม) "
              f"รีวิวก่อน --apply\n")
    # console: ปลอดภัยกับ codepage เพี้ยน (Windows cp1252) — เขียน bytes ตรง
    sys.stdout.buffer.write((body + footer).encode("utf-8", "replace"))
    sys.stdout.buffer.flush()


def apply(conn, discord: DiscordClient) -> None:
    items = load_groups(conn)
    moved = 0
    for gid, name, channel_id, target, current in items:
        try:
            parent_id = discord.ensure_category(target)
            _move_with_retry(discord, channel_id, parent_id)
            db.set_group_category(conn, gid, target)
            moved += 1
        except Exception as e:
            print(f"FAIL {name!r}: {e}", flush=True)
    print(f"apply เสร็จ: จัดสำเร็จ {moved}/{len(items)} channel", flush=True)


def _move_with_retry(discord: DiscordClient, channel_id: str, parent_id: str) -> None:
    while True:
        try:
            discord.move_channel(channel_id, parent_id)
            return
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = float(e.response.headers.get("retry-after", 1))
                time.sleep(wait)
                continue
            raise


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="จัดจริง (default = dry-run)")
    args = ap.parse_args()

    conn = db.connect()
    try:
        if args.apply:
            cfg = load_config(BASE / ".env")
            discord = DiscordClient(cfg.discord_bot_token, cfg.discord_guild_id)
            apply(conn, discord)
        else:
            dry_run(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
