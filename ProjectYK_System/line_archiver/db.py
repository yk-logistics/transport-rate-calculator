"""SQLite storage ของ line_archiver — DB แยกจาก app.db โดยสิ้นเชิง"""
import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "line_archive.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS line_group (
    group_id TEXT PRIMARY KEY,
    name TEXT,
    discord_channel_id TEXT,
    joined_at TEXT,
    active INTEGER DEFAULT 1,
    category TEXT
);
CREATE TABLE IF NOT EXISTS line_user (
    user_id TEXT PRIMARY KEY,
    display_name TEXT,
    alias TEXT
);
CREATE TABLE IF NOT EXISTS line_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_message_id TEXT UNIQUE,
    group_id TEXT,
    user_id TEXT,
    msg_type TEXT,
    text TEXT,
    media_path TEXT,
    sent_at TEXT,
    received_at TEXT,
    discord_forwarded INTEGER DEFAULT 0
);
"""


def connect(db_path=DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # idempotent migration สำหรับ DB เก่าที่สร้างก่อนมีคอลัมน์ category
    try:
        conn.execute("ALTER TABLE line_group ADD COLUMN category TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # คอลัมน์มีอยู่แล้ว
    return conn


def ensure_group(conn, group_id: str, joined_at: str | None = None) -> sqlite3.Row:
    conn.execute("INSERT OR IGNORE INTO line_group (group_id, joined_at) VALUES (?, ?)",
                 (group_id, joined_at))
    conn.commit()
    return conn.execute("SELECT * FROM line_group WHERE group_id=?", (group_id,)).fetchone()


def set_group_name(conn, group_id: str, name: str) -> None:
    conn.execute("UPDATE line_group SET name=? WHERE group_id=?", (name, group_id))
    conn.commit()


def set_group_channel(conn, group_id: str, channel_id: str) -> None:
    conn.execute("UPDATE line_group SET discord_channel_id=? WHERE group_id=?",
                 (channel_id, group_id))
    conn.commit()


def set_group_category(conn, group_id: str, category: str) -> None:
    conn.execute("UPDATE line_group SET category=? WHERE group_id=?",
                 (category, group_id))
    conn.commit()


def get_user(conn, user_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM line_user WHERE user_id=?", (user_id,)).fetchone()


def upsert_user(conn, user_id: str, display_name: str | None) -> None:
    conn.execute(
        "INSERT INTO line_user (user_id, display_name) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name",
        (user_id, display_name))
    conn.commit()


def message_exists(conn, line_message_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM line_message WHERE line_message_id=?",
                       (line_message_id,)).fetchone()
    return row is not None


def insert_message(conn, *, line_message_id: str, group_id: str, user_id: str | None,
                   msg_type: str, text: str | None = None, media_path: str | None = None,
                   sent_at: str | None = None) -> bool:
    received_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.execute(
            "INSERT INTO line_message (line_message_id, group_id, user_id, msg_type, "
            "text, media_path, sent_at, received_at) VALUES (?,?,?,?,?,?,?,?)",
            (line_message_id, group_id, user_id, msg_type, text, media_path,
             sent_at, received_at))
        conn.commit()
        return True
    except sqlite3.IntegrityError:  # ซ้ำจาก webhook redelivery
        return False


def mark_forwarded(conn, line_message_id: str) -> None:
    conn.execute("UPDATE line_message SET discord_forwarded=1 WHERE line_message_id=?",
                 (line_message_id,))
    conn.commit()


def pending_forwards(conn, limit: int = 20):
    return conn.execute(
        "SELECT * FROM line_message WHERE discord_forwarded=0 ORDER BY id LIMIT ?",
        (limit,)).fetchall()
