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
        self.categories = {}  # {name: cat_id}
        self.moves = []     # [(channel_id, parent_id), ...]

    def create_channel(self, name):
        self.created.append(name)
        return f"ch-{len(self.created)}"

    def post_text(self, channel_id, content):
        self.posts.append(("text", channel_id, content))

    def post_file(self, channel_id, filename, data, content=""):
        self.posts.append(("file", channel_id, filename, content))

    def ensure_category(self, name):
        return self.categories.setdefault(name, f"cat-{len(self.categories) + 1}")

    def move_channel(self, channel_id, parent_id):
        self.moves.append((channel_id, parent_id))


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


class GarageLine(FakeLine):
    def get_group_summary(self, group_id):
        return {"groupId": group_id, "groupName": "อู่ช่างไสว & YK"}


def test_new_channel_moved_into_category(tmp_path):
    discord = FakeDiscord()
    arch = Archiver(db.connect(":memory:"), GarageLine(), discord, Path(tmp_path))
    arch.handle_event({"type": "join", "timestamp": 1780000000000,
                       "source": {"type": "group", "groupId": "g1"}})
    assert discord.moves == [("ch-1", "cat-1")]
    assert discord.categories == {"ซ่อมบำรุง": "cat-1"}
    g = db.ensure_group(arch.conn, "g1")
    assert g["category"] == "ซ่อมบำรุง"


def test_category_failure_does_not_block_forward(tmp_path):
    class FailCategory(FakeDiscord):
        def ensure_category(self, name):
            raise RuntimeError("discord category down")

    discord = FailCategory()
    arch = Archiver(db.connect(":memory:"), GarageLine(), discord, Path(tmp_path))
    arch.handle_event(text_event(text="ยังต้อง forward ได้"))
    row = arch.conn.execute("SELECT * FROM line_message").fetchone()
    assert row["discord_forwarded"] == 1  # ข้อความยังไปถึง Discord แม้จัด category พลาด


def test_existing_channel_not_re_moved(tmp_path):
    discord = FakeDiscord()
    arch = Archiver(db.connect(":memory:"), GarageLine(), discord, Path(tmp_path))
    db.ensure_group(arch.conn, "g1")
    db.set_group_channel(arch.conn, "g1", "ch-existing")  # มี channel แล้ว
    arch.handle_event(text_event(text="ข้อความใหม่"))
    assert discord.moves == []  # ไม่ย้ายซ้ำ — โอย้ายเองทีหลังได้ ไม่ดึงกลับ


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
