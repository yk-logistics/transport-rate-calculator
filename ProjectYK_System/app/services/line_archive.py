# -*- coding: utf-8 -*-
"""อ่านคลังแชทไลน์ (line_archiver) สำหรับหน้า /line — READ-ONLY เท่านั้น (F1).

DB ของ service เก็บแชท (port 8020) — **ห้ามเขียนเด็ดขาด**: เปิดด้วย sqlite mode=ro.
ตาราง: line_group(group_id,name,discord_channel_id,joined_at,active)
       line_user(user_id,display_name,alias)
       line_message(id,line_message_id,group_id,user_id,msg_type,text,media_path,
                    sent_at,received_at,discord_forwarded)
media_path = path ไฟล์ใน line_media/ (รูป/ไฟล์ที่ดาวน์โหลดเก็บถาวรแล้ว).
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

def db_path() -> Path | None:
    candidates = (
        os.environ.get("YK_LINE_DB", ""),  # อ่านสดทุกครั้ง (เทสต์/ย้ายเครื่อง override ได้)
        r"C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db",  # server
        str(Path(__file__).resolve().parents[2] / "line_archiver" / "line_archive.db"),  # dev (ถ้ามี)
    )
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return None


def media_root() -> Path | None:
    p = db_path()
    return (p.parent / "line_media") if p else None


def _conn() -> sqlite3.Connection:
    p = db_path()
    if p is None:
        raise FileNotFoundError("ไม่พบ line_archive.db บนเครื่องนี้")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def groups_by_activity() -> list[dict]:
    """ทุกกลุ่ม เรียงข้อความล่าสุดก่อน — กลุ่มเงียบนานตกไปท้าย (มองเห็นทันทีว่าใครหาย)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT g.group_id, g.name, COUNT(m.id) AS n_msg,
                   MAX(m.sent_at) AS last_at,
                   SUM(CASE WHEN m.media_path IS NOT NULL AND m.media_path != '' THEN 1 ELSE 0 END) AS n_media
            FROM line_group g LEFT JOIN line_message m ON m.group_id = g.group_id
            WHERE COALESCE(g.active, 1) = 1
            GROUP BY g.group_id ORDER BY last_at DESC NULLS LAST""").fetchall()
    return [dict(r) for r in rows]


def search(q: str = "", group_id: str = "", msg_type: str = "",
           limit: int = 100, offset: int = 0) -> list[dict]:
    """ค้นข้อความทุกกลุ่ม: คำในข้อความ/ชื่อคนส่ง — ล่าสุดก่อน."""
    where, args = ["1=1"], []
    if q.strip():
        where.append("(m.text LIKE ? OR u.display_name LIKE ? OR u.alias LIKE ?)")
        pat = f"%{q.strip()}%"
        args += [pat, pat, pat]
    if group_id:
        where.append("m.group_id = ?")
        args.append(group_id)
    if msg_type:
        where.append("m.msg_type = ?")
        args.append(msg_type)
    with _conn() as c:
        rows = c.execute(f"""
            SELECT m.id, m.msg_type, m.text, m.media_path, m.sent_at,
                   g.name AS group_name, COALESCE(u.alias, u.display_name) AS who
            FROM line_message m
            LEFT JOIN line_group g ON g.group_id = m.group_id
            LEFT JOIN line_user u ON u.user_id = m.user_id
            WHERE {' AND '.join(where)}
            ORDER BY m.sent_at DESC LIMIT ? OFFSET ?""", args + [limit, offset]).fetchall()
    return [dict(r) for r in rows]


def daily_digest(day_iso: str, today_iso: str) -> dict:
    """F5: สรุปต่อกลุ่มของวัน day_iso (YYYY-MM-DD) + กลุ่มเงียบ >3 วันเทียบ today_iso.

    sent_at ใน DB เป็น TEXT ขึ้นต้นด้วยวันที่ — เทียบด้วย substr เพื่อรองรับทั้ง
    'YYYY-MM-DD HH:MM' และ ISO 'T'.
    """
    with _conn() as c:
        active = {r["group_id"]: dict(r) for r in c.execute(
            "SELECT group_id, name FROM line_group WHERE COALESCE(active,1)=1")}
        rows = c.execute("""
            SELECT m.group_id, m.msg_type, m.text, m.media_path, m.sent_at,
                   COALESCE(u.alias, u.display_name) AS who
            FROM line_message m LEFT JOIN line_user u ON u.user_id = m.user_id
            WHERE substr(m.sent_at, 1, 10) = ?
            ORDER BY m.sent_at""", (day_iso,)).fetchall()
        last_at = {r["group_id"]: r["last_at"] for r in c.execute(
            "SELECT group_id, MAX(sent_at) AS last_at FROM line_message GROUP BY group_id")}

    per: dict[str, dict] = {}
    for r in rows:
        gid = r["group_id"]
        if gid not in active:
            continue
        g = per.setdefault(gid, {
            "group_id": gid, "name": active[gid]["name"],
            "n_msg": 0, "n_media": 0, "first": None, "last": None})
        g["n_msg"] += 1
        if r["media_path"]:
            g["n_media"] += 1
        item = {"who": r["who"] or "", "text": (r["text"] or "")[:120],
                "at": str(r["sent_at"])[11:16], "msg_type": r["msg_type"]}
        if g["first"] is None:
            g["first"] = item
        g["last"] = item

    # เงียบ >3 วัน: ข้อความล่าสุดเก่ากว่า (today − 3 วัน) — string compare พอ (ISO)
    from datetime import date as _date, timedelta as _td
    cutoff = (_date.fromisoformat(today_iso) - _td(days=3)).isoformat()
    silent = []
    for gid, g in active.items():
        la_ = last_at.get(gid)
        if la_ is None or str(la_)[:10] < cutoff:
            silent.append({"group_id": gid, "name": g["name"],
                           "last_at": str(la_ or "")[:16] or "ไม่เคยมีข้อความ"})
    silent.sort(key=lambda x: x["last_at"])
    return {
        "groups": sorted(per.values(), key=lambda g: -g["n_msg"]),
        "silent": silent,
        "total_msg": sum(g["n_msg"] for g in per.values()),
        "total_media": sum(g["n_media"] for g in per.values()),
    }


def media_file(msg_id: int) -> Path | None:
    """ไฟล์ media ของข้อความ (ตรวจอยู่ใต้ line_media จริง กัน path traversal)."""
    root = media_root()
    if root is None:
        return None
    with _conn() as c:
        r = c.execute("SELECT media_path FROM line_message WHERE id = ?", (msg_id,)).fetchone()
    if not r or not r["media_path"]:
        return None
    p = Path(r["media_path"])
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    if not str(p).startswith(str(root.resolve())) or not p.exists():
        return None
    return p
