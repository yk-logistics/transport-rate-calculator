# LINE Group Archiver — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI service แยก (port 8020) รับ LINE webhook → เก็บข้อความลง SQLite + ดาวน์โหลดไฟล์สื่อลงเครื่อง → forward เข้า Discord (สร้าง channel อัตโนมัติต่อกลุ่มไลน์)

**Architecture:** service เดี่ยวที่ `ProjectYK_System/line_archiver/` ใช้ venv เดิมของ `app/` แต่ DB แยก (`line_archive.db`, sqlite3 stdlib — ไม่ใช้ SQLModel) คุย LINE/Discord ผ่าน REST ตรงด้วย httpx (ไม่ใช้ SDK) core logic อยู่ใน `Archiver` class ที่รับ client เป็น dependency injection เพื่อให้ทดสอบด้วย fake ได้โดยไม่แตะเน็ตจริง **ห้ามแตะ `app/main.py` และ `app.db` เด็ดขาด**

**Tech Stack:** Python (venv ที่ `ProjectYK_System/app/.venv`), FastAPI, httpx, sqlite3, pytest

**Spec:** `docs/superpowers/specs/2026-06-11-line-archiver-design.md`

**คำสั่งรันทดสอบ (ใช้ทุก task — รันจาก `ProjectYK_System/line_archiver/`):**

```powershell
cd "C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\ProjectYK_System\line_archiver"
..\app\.venv\Scripts\python.exe -m pytest tests -v
```

---

### Task 1: Scaffold + config loader

**Files:**
- Create: `ProjectYK_System/line_archiver/config.py`
- Create: `ProjectYK_System/line_archiver/conftest.py` (ไฟล์ว่าง — ทำให้ pytest หา module ใน dir นี้เจอ)
- Create: `ProjectYK_System/line_archiver/.env.example`
- Create: `ProjectYK_System/line_archiver/requirements.txt`
- Create: `ProjectYK_System/line_archiver/tests/test_config.py`
- Modify: `.gitignore` (รากโปรเจกต์ — เพิ่มบรรทัด)

- [ ] **Step 1: ติดตั้ง dependency เพิ่มใน venv เดิม (additive — ไม่แตะ pin เดิม)**

```powershell
& "C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\ProjectYK_System\app\.venv\Scripts\pip.exe" install "httpx>=0.27,<1" "pytest>=8,<9"
```

Expected: ติดตั้งสำเร็จ ไม่มีการอัปเกรด fastapi/starlette (ถ้า pip ขออัปเกรดตัวที่ pin ไว้ — หยุดและรายงาน)

- [ ] **Step 2: สร้างโฟลเดอร์ + ไฟล์ประกอบ**

`ProjectYK_System/line_archiver/conftest.py` — ไฟล์ว่าง (0 byte)

`ProjectYK_System/line_archiver/requirements.txt`:

```
# line_archiver ใช้ venv เดิมของ app/ — ไฟล์นี้เป็น reference ว่าต้องมีอะไรเพิ่ม
# (fastapi/uvicorn มาจาก app/requirements.txt อยู่แล้ว)
httpx>=0.27,<1
pytest>=8,<9
```

`ProjectYK_System/line_archiver/.env.example`:

```
# คัดลอกไฟล์นี้เป็น .env แล้วใส่ค่าจริง — ห้าม commit .env
LINE_CHANNEL_SECRET=ใส่จาก LINE Developers > channel > Basic settings
LINE_CHANNEL_ACCESS_TOKEN=ใส่จาก LINE Developers > Messaging API > issue token
DISCORD_BOT_TOKEN=ใส่จาก Discord Developer Portal > Bot
DISCORD_GUILD_ID=คลิกขวาชื่อ server ใน Discord > Copy Server ID (ต้องเปิด Developer Mode)
```

เพิ่มท้าย `.gitignore` (รากโปรเจกต์):

```
# line_archiver — ข้อมูลจริง/ความลับ ห้าม commit
ProjectYK_System/line_archiver/.env
ProjectYK_System/line_archiver/line_archive.db
ProjectYK_System/line_archiver/line_media/
```

- [ ] **Step 3: เขียน failing test ของ config**

`ProjectYK_System/line_archiver/tests/test_config.py`:

```python
from config import parse_env


def test_parse_env_basic():
    text = "LINE_CHANNEL_SECRET=abc123\nDISCORD_BOT_TOKEN=tok.en=with=equals\n"
    vals = parse_env(text)
    assert vals["LINE_CHANNEL_SECRET"] == "abc123"
    assert vals["DISCORD_BOT_TOKEN"] == "tok.en=with=equals"


def test_parse_env_skips_comments_and_blanks():
    text = "# comment\n\nKEY = value \nbadline\n"
    vals = parse_env(text)
    assert vals == {"KEY": "value"}
```

- [ ] **Step 4: รัน test ให้เห็นว่า fail**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 5: เขียน config.py**

`ProjectYK_System/line_archiver/config.py`:

```python
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
```

- [ ] **Step 6: รัน test ให้ผ่าน**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```powershell
git add ProjectYK_System/line_archiver .gitignore
git commit -m "feat(line_archiver): scaffold + .env config loader"
```

---

### Task 2: db.py — SQLite schema + helpers

**Files:**
- Create: `ProjectYK_System/line_archiver/db.py`
- Test: `ProjectYK_System/line_archiver/tests/test_db.py`

- [ ] **Step 1: เขียน failing tests**

`ProjectYK_System/line_archiver/tests/test_db.py`:

```python
import db


def make_conn():
    return db.connect(":memory:")


def test_insert_message_and_dedupe():
    conn = make_conn()
    ok = db.insert_message(conn, line_message_id="m1", group_id="g1", user_id="u1",
                           msg_type="text", text="สวัสดี", sent_at="2026-06-11 09:00:00")
    assert ok is True
    dup = db.insert_message(conn, line_message_id="m1", group_id="g1", user_id="u1",
                            msg_type="text", text="สวัสดี", sent_at="2026-06-11 09:00:00")
    assert dup is False
    rows = conn.execute("SELECT * FROM line_message").fetchall()
    assert len(rows) == 1
    assert rows[0]["discord_forwarded"] == 0


def test_pending_and_mark_forwarded():
    conn = make_conn()
    db.insert_message(conn, line_message_id="m1", group_id="g1", user_id="u1",
                      msg_type="text", text="a", sent_at="2026-06-11 09:00:00")
    db.insert_message(conn, line_message_id="m2", group_id="g1", user_id="u1",
                      msg_type="text", text="b", sent_at="2026-06-11 09:01:00")
    assert [r["line_message_id"] for r in db.pending_forwards(conn)] == ["m1", "m2"]
    db.mark_forwarded(conn, "m1")
    assert [r["line_message_id"] for r in db.pending_forwards(conn)] == ["m2"]


def test_ensure_group_and_channel():
    conn = make_conn()
    g = db.ensure_group(conn, "g1", joined_at="2026-06-11 09:00:00")
    assert g["group_id"] == "g1" and g["discord_channel_id"] is None
    db.set_group_name(conn, "g1", "ทีมงาน LCB")
    db.set_group_channel(conn, "g1", "ch99")
    g = db.ensure_group(conn, "g1")  # เรียกซ้ำต้องไม่ทับค่าเดิม
    assert g["name"] == "ทีมงาน LCB" and g["discord_channel_id"] == "ch99"


def test_upsert_user_keeps_alias():
    conn = make_conn()
    db.upsert_user(conn, "u1", "สมชาย")
    conn.execute("UPDATE line_user SET alias='ชายโม่' WHERE user_id='u1'")
    conn.commit()
    db.upsert_user(conn, "u1", "สมชาย ใจดี")  # ชื่อ LINE เปลี่ยน
    row = db.get_user(conn, "u1")
    assert row["display_name"] == "สมชาย ใจดี"
    assert row["alias"] == "ชายโม่"
```

- [ ] **Step 2: รันให้ fail**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: เขียน db.py**

`ProjectYK_System/line_archiver/db.py`:

```python
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
    active INTEGER DEFAULT 1
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
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 6 passed (config 2 + db 4)

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "feat(line_archiver): sqlite schema + storage helpers"
```

---

### Task 3: line_api.py — ตรวจ signature + LINE REST client

**Files:**
- Create: `ProjectYK_System/line_archiver/line_api.py`
- Test: `ProjectYK_System/line_archiver/tests/test_line_api.py`

- [ ] **Step 1: เขียน failing test (เฉพาะส่วน pure — signature)**

`ProjectYK_System/line_archiver/tests/test_line_api.py`:

```python
import base64
import hashlib
import hmac

from line_api import verify_signature

SECRET = "test-secret"
BODY = b'{"events":[]}'


def good_sig(secret: str, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_valid_signature_passes():
    assert verify_signature(SECRET, BODY, good_sig(SECRET, BODY)) is True


def test_bad_signature_fails():
    assert verify_signature(SECRET, BODY, "AAAA") is False
    assert verify_signature(SECRET, BODY, "") is False
    assert verify_signature(SECRET, BODY, None) is False
    assert verify_signature(SECRET, b'{"tampered":1}', good_sig(SECRET, BODY)) is False
```

- [ ] **Step 2: รันให้ fail**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests/test_line_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'line_api'`

- [ ] **Step 3: เขียน line_api.py**

`ProjectYK_System/line_archiver/line_api.py`:

```python
"""LINE Messaging API: ตรวจ webhook signature + ดึง content/ชื่อกลุ่ม/โปรไฟล์"""
import base64
import hashlib
import hmac

import httpx

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"


def verify_signature(channel_secret: str, body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    mac = hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)


class LineClient:
    def __init__(self, access_token: str):
        self._headers = {"Authorization": f"Bearer {access_token}"}

    def get_content(self, message_id: str) -> tuple[bytes, str]:
        """ดาวน์โหลดไฟล์จริงของ message (รูป/วิดีโอ/เสียง/ไฟล์) — ต้องรีบทำก่อนหมดอายุ"""
        r = httpx.get(f"{API_DATA}/message/{message_id}/content",
                      headers=self._headers, timeout=60)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "")

    def get_group_summary(self, group_id: str) -> dict:
        r = httpx.get(f"{API}/group/{group_id}/summary", headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()  # {"groupId":..., "groupName":..., "pictureUrl":...}

    def get_member_profile(self, group_id: str, user_id: str) -> dict:
        r = httpx.get(f"{API}/group/{group_id}/member/{user_id}",
                      headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()  # {"displayName":..., "userId":...}
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "feat(line_archiver): LINE signature verify + REST client"
```

---

### Task 4: discord_api.py — Discord REST client + ตั้งชื่อ channel

**Files:**
- Create: `ProjectYK_System/line_archiver/discord_api.py`
- Test: `ProjectYK_System/line_archiver/tests/test_discord_api.py`

- [ ] **Step 1: เขียน failing test (ส่วน pure — sanitize ชื่อ channel)**

`ProjectYK_System/line_archiver/tests/test_discord_api.py`:

```python
from discord_api import channel_name_for


def test_thai_name_kept_spaces_dashed():
    assert channel_name_for("ทีมงาน LCB") == "line-ทีมงาน-lcb"


def test_strips_forbidden_chars():
    assert channel_name_for("A/B (test)!") == "line-ab-test"


def test_empty_falls_back():
    assert channel_name_for("") == "line-group"
    assert channel_name_for(None) == "line-group"
```

- [ ] **Step 2: รันให้ fail**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests/test_discord_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'discord_api'`

- [ ] **Step 3: เขียน discord_api.py**

`ProjectYK_System/line_archiver/discord_api.py`:

```python
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
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "feat(line_archiver): Discord REST client + channel naming"
```

---

### Task 5: archiver.py — join event + ข้อความ text

**Files:**
- Create: `ProjectYK_System/line_archiver/archiver.py`
- Test: `ProjectYK_System/line_archiver/tests/test_archiver.py`

- [ ] **Step 1: เขียน failing tests + fakes**

`ProjectYK_System/line_archiver/tests/test_archiver.py`:

```python
from pathlib import Path

import db
from archiver import Archiver


class FakeLine:
    def get_content(self, message_id):
        return b"\x89PNG-fake-bytes", "image/png"

    def get_group_summary(self, group_id):
        return {"groupId": group_id, "groupName": "ทีมงาน LCB"}

    def get_member_profile(self, group_id, user_id):
        return {"displayName": "สมชาย", "userId": user_id}


class FakeDiscord:
    def __init__(self):
        self.created = []   # [name, ...]
        self.posts = []     # [("text", channel_id, content) | ("file", channel_id, filename, content)]

    def create_channel(self, name):
        self.created.append(name)
        return f"ch-{len(self.created)}"

    def post_text(self, channel_id, content):
        self.posts.append(("text", channel_id, content))

    def post_file(self, channel_id, filename, data, content=""):
        self.posts.append(("file", channel_id, filename, content))


def make_archiver(tmp_path) -> tuple[Archiver, FakeDiscord]:
    discord = FakeDiscord()
    arch = Archiver(db.connect(":memory:"), FakeLine(), discord, Path(tmp_path))
    return arch, discord


def text_event(mid="m1", text="สวัสดีครับ", gid="g1", uid="u1", ts=1780000000000):
    return {"type": "message", "timestamp": ts,
            "source": {"type": "group", "groupId": gid, "userId": uid},
            "message": {"id": mid, "type": "text", "text": text}}


def test_join_creates_group_and_channel(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event({"type": "join", "timestamp": 1780000000000,
                       "source": {"type": "group", "groupId": "g1"}})
    g = db.ensure_group(arch.conn, "g1")
    assert g["name"] == "ทีมงาน LCB"
    assert g["discord_channel_id"] == "ch-1"
    assert discord.created == ["line-ทีมงาน-lcb"]
    assert discord.posts[0][0] == "text"  # ข้อความแจ้งเริ่มเก็บ


def test_text_message_stored_and_forwarded(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event(text_event())
    row = arch.conn.execute("SELECT * FROM line_message").fetchone()
    assert row["msg_type"] == "text"
    assert row["text"] == "สวัสดีครับ"
    assert row["discord_forwarded"] == 1
    kind, _, content = discord.posts[-1]
    assert kind == "text"
    assert "สมชาย" in content and "สวัสดีครับ" in content


def test_duplicate_event_ignored(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event(text_event())
    arch.handle_event(text_event())  # redelivery เดิมซ้ำ
    rows = arch.conn.execute("SELECT * FROM line_message").fetchall()
    assert len(rows) == 1
    assert len([p for p in discord.posts if p[0] == "text"]) == 1


def test_non_group_event_ignored(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event({"type": "message", "timestamp": 1,
                       "source": {"type": "user", "userId": "u1"},
                       "message": {"id": "m9", "type": "text", "text": "DM"}})
    assert arch.conn.execute("SELECT COUNT(*) c FROM line_message").fetchone()["c"] == 0
```

- [ ] **Step 2: รันให้ fail**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests/test_archiver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'archiver'`

- [ ] **Step 3: เขียน archiver.py (รอบนี้รองรับ join + text ก่อน — media มาใน Task 6)**

`ProjectYK_System/line_archiver/archiver.py`:

```python
"""Core logic: LINE webhook event -> DB + ไฟล์สื่อ + forward Discord

แยกจาก main.py เพื่อให้ทดสอบได้ด้วย fake client (ไม่แตะเน็ตจริง)
หลักการ: บันทึก DB ก่อนเสมอ (source of truth) แล้วค่อย forward —
forward พลาดได้ ไม่เป็นไร เดี๋ยว retry; ข้อมูลห้ามหาย
"""
import datetime
import logging
import mimetypes
from pathlib import Path

import db
from discord_api import MAX_UPLOAD, channel_name_for

log = logging.getLogger("line_archiver")

TZ_BKK = datetime.timezone(datetime.timedelta(hours=7))

EXT_MAP = {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4",
           "audio/m4a": ".m4a", "audio/x-m4a": ".m4a", "application/pdf": ".pdf"}


def _thai_time(ts_ms: int) -> str:
    dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=TZ_BKK)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _ext_for(content_type: str, file_name: str | None) -> str:
    if file_name and "." in file_name:
        return "." + file_name.rsplit(".", 1)[1]
    ct = (content_type or "").split(";")[0].strip()
    return EXT_MAP.get(ct) or mimetypes.guess_extension(ct) or ".bin"


class Archiver:
    def __init__(self, conn, line, discord, media_root: Path):
        self.conn = conn
        self.line = line
        self.discord = discord
        self.media_root = media_root

    # ---- entry point ----

    def handle_event(self, event: dict) -> None:
        src = event.get("source", {})
        if src.get("type") != "group":
            return  # เก็บเฉพาะแชทกลุ่ม
        if event.get("type") == "join":
            self._on_join(src["groupId"], event.get("timestamp"))
        elif event.get("type") == "message":
            self._on_message(event)

    # ---- group / channel ----

    def _ensure_channel(self, group_id: str) -> str | None:
        group = db.ensure_group(self.conn, group_id)
        name = group["name"]
        if not name:
            try:
                name = self.line.get_group_summary(group_id).get("groupName")
                if name:
                    db.set_group_name(self.conn, group_id, name)
            except Exception:
                log.exception("get_group_summary failed for %s", group_id)
        channel_id = group["discord_channel_id"]
        if not channel_id:
            try:
                channel_id = self.discord.create_channel(channel_name_for(name or group_id[:8]))
                db.set_group_channel(self.conn, group_id, channel_id)
            except Exception:
                log.exception("create_channel failed for %s", group_id)
                return None
        return channel_id

    def _on_join(self, group_id: str, ts: int | None) -> None:
        db.ensure_group(self.conn, group_id, joined_at=_thai_time(ts) if ts else None)
        channel_id = self._ensure_channel(group_id)
        if channel_id:
            try:
                self.discord.post_text(channel_id, "บอทเริ่มเก็บข้อความกลุ่มนี้แล้ว")
            except Exception:
                log.exception("join announce failed")

    # ---- sender ----

    def _sender_name(self, group_id: str, user_id: str | None) -> str:
        if not user_id:
            return "ไม่ทราบชื่อ"
        row = db.get_user(self.conn, user_id)
        if row and (row["alias"] or row["display_name"]):
            return row["alias"] or row["display_name"]
        name = None
        try:
            name = self.line.get_member_profile(group_id, user_id).get("displayName")
        except Exception:
            log.exception("get_member_profile failed for %s", user_id)
        db.upsert_user(self.conn, user_id, name)
        return name or user_id[:8]

    # ---- message ----

    def _on_message(self, event: dict) -> None:
        msg = event["message"]
        group_id = event["source"]["groupId"]
        user_id = event["source"].get("userId")
        mid = msg["id"]
        if db.message_exists(self.conn, mid):  # webhook redelivery
            return
        sent_at = _thai_time(event["timestamp"])
        mtype = msg["type"]
        text = None
        media_path = None
        data = None
        filename = None
        if mtype == "text":
            text = msg.get("text", "")
        elif mtype in ("image", "video", "audio", "file"):
            data, content_type = self.line.get_content(mid)
            ext = _ext_for(content_type, msg.get("fileName"))
            filename = msg.get("fileName") or f"{mid}{ext}"
            rel = Path(group_id) / sent_at[:7] / f"{mid}{ext}"
            full = self.media_root / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(data)
            media_path = str(rel)
            text = msg.get("fileName")
        elif mtype == "sticker":
            text = f"[sticker {msg.get('packageId')}/{msg.get('stickerId')}]"
        else:
            text = f"[{mtype}]"
            mtype = "other"
        db.insert_message(self.conn, line_message_id=mid, group_id=group_id,
                          user_id=user_id, msg_type=mtype, text=text,
                          media_path=media_path, sent_at=sent_at)
        self._forward(group_id, mid, user_id, sent_at, text, media_path,
                      data=data, filename=filename)

    # ---- discord forward ----

    def _forward(self, group_id: str, mid: str, user_id: str | None, sent_at: str,
                 text: str | None, media_path: str | None,
                 data: bytes | None = None, filename: str | None = None) -> None:
        channel_id = self._ensure_channel(group_id)
        if not channel_id:
            return  # discord_forwarded ยัง 0 → retry รอบหลัง
        hhmm = sent_at[11:16] if sent_at else "--:--"
        header = f"**{self._sender_name(group_id, user_id)}** ({hhmm})"
        try:
            if media_path:
                if data is None:
                    data = (self.media_root / media_path).read_bytes()
                if len(data) <= MAX_UPLOAD:
                    self.discord.post_file(channel_id, filename or Path(media_path).name,
                                           data, header)
                else:
                    self.discord.post_text(
                        channel_id,
                        f"{header} ส่งไฟล์ใหญ่เกินลิมิตอัปโหลด — เก็บไว้ในเครื่องที่ `{media_path}`")
            else:
                self.discord.post_text(channel_id, f"{header}: {text}")
            db.mark_forwarded(self.conn, mid)
        except Exception:
            log.exception("forward failed for %s (จะ retry)", mid)

    def retry_pending(self) -> None:
        for row in db.pending_forwards(self.conn):
            self._forward(row["group_id"], row["line_message_id"], row["user_id"],
                          row["sent_at"], row["text"], row["media_path"])
```

- [ ] **Step 4: รันให้ผ่าน**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "feat(line_archiver): core archiver - join + text message flow"
```

---

### Task 6: media (รูป/ไฟล์), sticker, ไฟล์ใหญ่

archiver.py รองรับ media แล้วใน Task 5 — task นี้คือ **พิสูจน์ด้วย test** ว่าพฤติกรรมถูกตามเกณฑ์ spec ข้อ 2

**Files:**
- Modify: `ProjectYK_System/line_archiver/tests/test_archiver.py` (เพิ่ม tests)

- [ ] **Step 1: เพิ่ม tests**

เพิ่มท้าย `ProjectYK_System/line_archiver/tests/test_archiver.py`:

```python
def media_event(mid="img1", mtype="image", gid="g1", uid="u1", ts=1780000000000, **extra):
    return {"type": "message", "timestamp": ts,
            "source": {"type": "group", "groupId": gid, "userId": uid},
            "message": {"id": mid, "type": mtype, **extra}}


def test_image_saved_to_disk_and_forwarded(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event(media_event())
    row = arch.conn.execute("SELECT * FROM line_message").fetchone()
    assert row["msg_type"] == "image"
    assert row["media_path"] is not None
    saved = Path(tmp_path) / row["media_path"]
    assert saved.read_bytes() == b"\x89PNG-fake-bytes"
    assert saved.suffix == ".png"
    assert row["discord_forwarded"] == 1
    assert discord.posts[-1][0] == "file"


def test_file_message_uses_filename(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event(media_event(mid="f1", mtype="file", fileName="ใบงาน.pdf"))
    row = arch.conn.execute("SELECT * FROM line_message").fetchone()
    assert row["media_path"].endswith(".pdf")
    assert row["text"] == "ใบงาน.pdf"
    assert discord.posts[-1][2] == "ใบงาน.pdf"  # filename ที่ส่งเข้า Discord


def test_oversize_file_posts_note_instead(tmp_path, monkeypatch):
    arch, discord = make_archiver(tmp_path)
    big = b"x" * (10 * 1024 * 1024 + 1)
    monkeypatch.setattr(arch.line, "get_content", lambda mid: (big, "video/mp4"))
    arch.handle_event(media_event(mid="v1", mtype="video"))
    row = arch.conn.execute("SELECT * FROM line_message").fetchone()
    assert (Path(tmp_path) / row["media_path"]).stat().st_size == len(big)  # ลงเครื่องครบ
    assert row["discord_forwarded"] == 1
    kind, _, content = discord.posts[-1]
    assert kind == "text" and "ไฟล์ใหญ่" in content


def test_sticker_stored_as_text(tmp_path):
    arch, discord = make_archiver(tmp_path)
    arch.handle_event(media_event(mid="s1", mtype="sticker",
                                  packageId="11537", stickerId="52002734"))
    row = arch.conn.execute("SELECT * FROM line_message").fetchone()
    assert row["msg_type"] == "sticker"
    assert row["text"] == "[sticker 11537/52002734]"
    assert row["media_path"] is None
```

- [ ] **Step 2: รันให้ผ่าน (โค้ดมีแล้ว — ถ้า fail แปลว่า Task 5 มีบั๊ก ให้แก้ archiver.py จนผ่าน)**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 19 passed

- [ ] **Step 3: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "test(line_archiver): media download, sticker, oversize file behavior"
```

---

### Task 7: retry เมื่อ Discord ล่ม

**Files:**
- Modify: `ProjectYK_System/line_archiver/tests/test_archiver.py` (เพิ่ม tests)

- [ ] **Step 1: เพิ่ม failing test**

เพิ่มท้าย `ProjectYK_System/line_archiver/tests/test_archiver.py`:

```python
class DownDiscord(FakeDiscord):
    """Discord ล่ม: โพสต์อะไรก็ exception แต่สร้าง channel ได้"""

    def post_text(self, channel_id, content):
        raise RuntimeError("discord down")

    def post_file(self, channel_id, filename, data, content=""):
        raise RuntimeError("discord down")


def test_discord_down_then_retry_recovers(tmp_path):
    discord = DownDiscord()
    arch = Archiver(db.connect(":memory:"), FakeLine(), discord, Path(tmp_path))
    arch.handle_event(text_event(mid="m1", text="ตอน discord ล่ม"))
    arch.handle_event(media_event(mid="img1"))
    rows = arch.conn.execute("SELECT * FROM line_message ORDER BY id").fetchall()
    assert [r["discord_forwarded"] for r in rows] == [0, 0]  # DB ครบ แต่ยังไม่ forward

    # discord ฟื้น (สลับ method กลับเป็นของ FakeDiscord)
    discord.post_text = lambda cid, content: discord.posts.append(("text", cid, content))
    discord.post_file = lambda cid, fn, data, content="": discord.posts.append(("file", cid, fn, content))
    arch.retry_pending()
    rows = arch.conn.execute("SELECT * FROM line_message ORDER BY id").fetchall()
    assert [r["discord_forwarded"] for r in rows] == [1, 1]
    kinds = [p[0] for p in discord.posts]
    assert "text" in kinds and "file" in kinds
```

- [ ] **Step 2: รันให้ผ่าน (logic `retry_pending` + อ่านไฟล์จาก disk ตอน retry มีแล้วใน Task 5 — fail = บั๊ก ให้แก้)**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 20 passed

- [ ] **Step 3: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "test(line_archiver): discord outage -> data kept, retry forwards"
```

---

### Task 8: main.py — FastAPI webhook endpoint + retry loop

**Files:**
- Create: `ProjectYK_System/line_archiver/main.py`

- [ ] **Step 1: เขียน main.py**

`ProjectYK_System/line_archiver/main.py`:

```python
"""line_archiver — FastAPI service (port 8020)

รับ webhook จาก LINE → Archiver จัดการเก็บ + forward
แยกขาดจากแอป MVP (port 8010) โดยสิ้นเชิง
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

import db
from archiver import Archiver
from config import load_config
from discord_api import DiscordClient
from line_api import LineClient, verify_signature

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("line_archiver")

BASE = Path(__file__).parent
MEDIA_ROOT = BASE / "line_media"
RETRY_INTERVAL = 300  # วินาที — กวาดข้อความที่ยังไม่ได้ forward

cfg = load_config(BASE / ".env")
line = LineClient(cfg.line_access_token)
discord = DiscordClient(cfg.discord_bot_token, cfg.discord_guild_id)


def make_archiver() -> Archiver:
    return Archiver(db.connect(), line, discord, MEDIA_ROOT)


def _retry_once() -> None:
    arch = make_archiver()
    try:
        arch.retry_pending()
    finally:
        arch.conn.close()


async def retry_loop() -> None:
    while True:
        await asyncio.sleep(RETRY_INTERVAL)
        try:
            await asyncio.to_thread(_retry_once)
        except Exception:
            log.exception("retry loop error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(retry_loop())
    log.info("line_archiver started, media root: %s", MEDIA_ROOT)
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/line/webhook")
async def line_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")
    if not verify_signature(cfg.line_channel_secret, body, signature):
        raise HTTPException(status_code=403, detail="bad signature")
    payload = json.loads(body)

    def process() -> None:
        arch = make_archiver()
        try:
            for event in payload.get("events", []):
                try:
                    arch.handle_event(event)
                except Exception:
                    # event เดียวพังต้องไม่ทำให้ทั้ง batch fail (LINE จะ redeliver ทั้งก้อน)
                    log.exception("event failed: %s", event.get("type"))
        finally:
            arch.conn.close()

    await asyncio.to_thread(process)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
```

- [ ] **Step 2: Smoke test ด้วยมือ (ยังไม่มี token จริง — ใช้ค่า dummy)**

```powershell
cd "C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\ProjectYK_System\line_archiver"
Copy-Item .env.example .env   # ค่า dummy พอสำหรับ smoke test
Start-Process ..\app\.venv\Scripts\python.exe -ArgumentList "main.py"
Start-Sleep 3
Invoke-RestMethod http://127.0.0.1:8020/health
# คาด: ok=True
Invoke-WebRequest -Method POST http://127.0.0.1:8020/line/webhook -Body '{"events":[]}' -ContentType application/json -SkipHttpErrorCheck | Select-Object StatusCode
# คาด: StatusCode 403 (ไม่มี signature → โดนปัด)
```

Expected: `/health` ตอบ ok, POST ไม่มี signature ได้ 403, แล้วปิด process (`Stop-Process`) และลบ `.env` dummy ทิ้ง

- [ ] **Step 3: รัน test ทั้งชุดอีกรอบกันถดถอย**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 20 passed

- [ ] **Step 4: Commit**

```powershell
git add ProjectYK_System/line_archiver
git commit -m "feat(line_archiver): FastAPI webhook endpoint + retry loop (port 8020)"
```

---

### Task 9: start_archiver.bat + checklist สำหรับโอ + changelog

**Files:**
- Create: `ProjectYK_System/line_archiver/start_archiver.bat`
- Create: `ProjectYK_System/line_archiver/SETUP_CHECKLIST.md`
- Modify: `ProjectYK_System/CHANGELOG_MASTER.md` (เพิ่มหัวข้อบนสุดตาม policy เดิมของไฟล์)

- [ ] **Step 1: เขียน start_archiver.bat**

`ProjectYK_System/line_archiver/start_archiver.bat`:

```bat
@echo off
rem line_archiver — รันบนเครื่อง MVP (เปิดค้างไว้ 24 ชม.)
cd /d "%~dp0"
if not exist .env (
    echo [ERROR] yang mai mee .env — copy .env.example pen .env laew sai token korn
    pause
    exit /b 1
)
echo Starting line_archiver on port 8020 ...
"..\app\.venv\Scripts\python.exe" main.py
pause
```

- [ ] **Step 2: เขียน SETUP_CHECKLIST.md (ขั้นตอนที่โอต้องทำเอง)**

`ProjectYK_System/line_archiver/SETUP_CHECKLIST.md`:

````markdown
# Checklist เปิดใช้ LINE Archiver (โอทำเอง ~20 นาที)

## A. ฝั่ง LINE (ฟรี)

1. เข้า https://developers.line.biz/ → login ด้วยบัญชี LINE
2. Create provider (ชื่ออะไรก็ได้ เช่น `YK Logistics`)
3. Create channel → เลือก **Messaging API** → ตั้งชื่อบอท เช่น `YK เก็บข้อความ`
4. แท็บ **Basic settings** → copy `Channel secret` → ใส่ `.env` บรรทัด `LINE_CHANNEL_SECRET=`
5. แท็บ **Messaging API** → กด Issue `Channel access token (long-lived)` → ใส่ `.env` บรรทัด `LINE_CHANNEL_ACCESS_TOKEN=`
6. ในหน้า LINE Official Account Manager (ลิงก์จากแท็บเดียวกัน):
   - **เปิด** "Allow bot to join group chats" (ตั้งค่า > ตอบกลับ > แชทกลุ่ม)
   - **ปิด** auto-reply / greeting message (ไม่งั้นบอทจะตอบสแปมในกลุ่ม)
7. แท็บ **Messaging API** → Webhook settings → **เปิด Use webhook** + **เปิด Webhook redelivery**
   (URL จะมาใส่ในข้อ C)

## B. ฝั่ง Discord (ฟรี)

1. เข้า https://discord.com/developers/applications → New Application ชื่อ `YK Line Archiver`
2. เมนู **Bot** → Reset Token → copy → ใส่ `.env` บรรทัด `DISCORD_BOT_TOKEN=`
3. เมนู **OAuth2 > URL Generator**:
   - Scopes: เลือก `bot`
   - Bot Permissions: เลือก `Manage Channels`, `Send Messages`, `Attach Files`
   - copy URL ที่ได้ → เปิดในเบราว์เซอร์ → เลือก server ของโอ → Authorize
4. ใน Discord app: User Settings > Advanced > เปิด **Developer Mode**
   แล้วคลิกขวาชื่อ server > **Copy Server ID** → ใส่ `.env` บรรทัด `DISCORD_GUILD_ID=`

## C. ฝั่งเครื่อง MVP

1. ติดตั้ง cloudflared (ครั้งเดียว): `winget install Cloudflare.cloudflared`
2. คัดลอก `.env.example` เป็น `.env` แล้วใส่ค่าครบ 4 ตัวจากข้อ A/B
3. รัน `start_archiver.bat` (ค้างไว้)
4. เปิดอีกหน้าต่าง: `cloudflared tunnel --url http://127.0.0.1:8020` (ค้างไว้)
   → จะได้ URL แบบ `https://xxxx.trycloudflare.com`
5. เอา URL นั้น + `/line/webhook` ไปใส่ใน LINE Developers > Messaging API > Webhook URL
   เช่น `https://xxxx.trycloudflare.com/line/webhook` → กด **Verify** ต้องขึ้น Success
   ⚠️ URL เปลี่ยนทุกครั้งที่รีสตาร์ท cloudflared — รีสตาร์ทเมื่อไหร่ต้องมาอัปเดต+Verify ใหม่

## D. ทดสอบจริง

1. เชิญบอท (เพิ่มเพื่อนด้วย QR จากแท็บ Messaging API ก่อน แล้วเชิญเข้ากลุ่มทดสอบ)
2. เช็คว่า Discord มี channel ใหม่ `line-<ชื่อกลุ่ม>` + ข้อความ "บอทเริ่มเก็บข้อความกลุ่มนี้แล้ว"
3. พิมพ์ข้อความ + ส่งรูปในกลุ่ม → ต้องเด้งใน Discord ภายในไม่กี่วินาที
   และไฟล์รูปอยู่ใน `line_media/<group_id>/<YYYY-MM>/`
````

- [ ] **Step 3: เพิ่ม changelog ตามรูปแบบหัวข้อ `##` ล่าสุดของ `ProjectYK_System/CHANGELOG_MASTER.md`**

อ่านหัวข้อบนสุดของไฟล์ก่อนเพื่อเลียนแบบ format แล้วเพิ่มหัวข้อใหม่บนสุด ใจความ:

```markdown
## 2026-06-11 — line_archiver: บอทเก็บข้อความ+รูปจากกลุ่ม LINE ลง SQLite/Discord

- service ใหม่แยกขาด `ProjectYK_System/line_archiver/` (port 8020, DB แยก line_archive.db)
- LINE Messaging API webhook → เก็บ text/รูป/ไฟล์ลงเครื่อง → forward Discord (auto-create channel ต่อกลุ่ม)
- ไม่แตะ app/main.py, app.db; spec: docs/superpowers/specs/2026-06-11-line-archiver-design.md
- เปิดใช้ตาม line_archiver/SETUP_CHECKLIST.md
```

- [ ] **Step 4: รัน test ทั้งชุดปิดท้าย**

Run: `..\app\.venv\Scripts\python.exe -m pytest tests -v`
Expected: 20 passed

- [ ] **Step 5: เช็คว่าแอปหลักไม่ถูกแตะ**

```powershell
git status --short ProjectYK_System/app
```

Expected: ว่างเปล่า (ไม่มีไฟล์ใต้ app/ เปลี่ยน)

- [ ] **Step 6: Commit**

```powershell
git add ProjectYK_System/line_archiver ProjectYK_System/CHANGELOG_MASTER.md
git commit -m "feat(line_archiver): start script + setup checklist + changelog"
```

---

## หลังจบทุก task — เกณฑ์ความสำเร็จจาก spec (ทวนกับโอ)

ข้อ 1–4 ของ spec ต้องทดสอบกับ **token จริง + กลุ่มจริง** หลังโอทำ `SETUP_CHECKLIST.md` เสร็จ:

1. ข้อความ text → ลง DB + เด้ง Discord
2. รูป → ไฟล์อยู่ `line_media/` + เด้ง Discord
3. เชิญเข้ากลุ่มใหม่ → channel ใหม่อัตโนมัติ
4. ปิดบอทชั่วคราว + redelivery → ไม่หาย ไม่ซ้ำ
5. `git log --stat` ยืนยันไม่มี diff ใต้ `ProjectYK_System/app/` ✓ (เช็คแล้วใน Task 9)
