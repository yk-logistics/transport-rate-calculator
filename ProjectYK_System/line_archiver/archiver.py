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
