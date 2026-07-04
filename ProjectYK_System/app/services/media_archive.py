# -*- coding: utf-8 -*-
"""G2: ย้ายรูปไลน์เก่าลงแผ่น External — copy → เช็ค hash → ค่อยลบต้นทาง.

นโยบาย (โอเคาะ 3ก.ค.): เก็บรูปบนเครื่อง 2 ปี; ดิสก์เหลือ <25% = เตือนเสนอย้าย
ของเก่าสุดก่อนครบกำหนด. ตำแหน่งใหม่จดลงตาราง MediaArchive ฝั่ง app.db เท่านั้น
(**ห้ามเขียน line_archive.db ของ service 8020**) — ไฟล์บนแผ่นวางที่
<แผ่น>/YK_MEDIA/<YYYY>/<MM>/<msgid>_<ชื่อเดิม>. แผ่นถูกจำด้วย marker
YK_ARCHIVE.txt ที่รากแผ่น (บรรทัด "label: EXT-01").
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from services import line_archive as la

RETENTION_DAYS = 730          # เก็บบนเครื่อง 2 ปี
DISK_WARN_FREE_PCT = 25.0     # ต่ำกว่านี้ = เสนอย้ายของเก่าสุดก่อนครบกำหนด
MARKER = "YK_ARCHIVE.txt"
_LABEL_RE = re.compile(r"label:\s*(\S+)")


def read_label(target: str | Path) -> str | None:
    """label ของแผ่น (จาก marker ที่รากแผ่น) — ไม่มี marker = None."""
    try:
        txt = (Path(target) / MARKER).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = _LABEL_RE.search(txt)
    return m.group(1) if m else None


def ensure_label(target: str | Path, seq: int) -> str:
    """อ่าน label เดิม หรือสร้าง marker ใหม่เป็น EXT-<seq> (ครั้งแรกของแผ่นนี้)."""
    lb = read_label(target)
    if lb:
        return lb
    lb = f"EXT-{seq:02d}"
    (Path(target) / MARKER).write_text(
        f"YK archive disk - do not delete\nlabel: {lb}\ncreated: {datetime.now():%Y-%m-%d %H:%M}\n",
        encoding="utf-8")
    return lb


def find_disk(label: str, targets: list[str]) -> Path | None:
    """หาแผ่นที่ label ตรงในไดรฟ์ที่เสียบอยู่ — ไม่เจอ = แผ่นไม่ได้เสียบ."""
    for t in targets:
        if read_label(t) == label:
            return Path(t)
    return None


def _resolve_media(root: Path, media_path: str) -> Path | None:
    p = Path(media_path)
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    if not str(p).startswith(str(root.resolve())) or not p.exists():
        return None
    return p


def scan_photos(archived_ids: set[int], before: date | None = None,
                limit: int = 5000) -> list[dict]:
    """รูปในคลังที่ยังไม่ถูกย้าย (เก่าสุดก่อน) — before=None คือทั้งหมด (ไว้หาวันเก่าสุด)."""
    p = la.db_path()
    root = la.media_root()
    if p is None or root is None:
        return []
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        q = """SELECT id, media_path, sent_at FROM line_message
               WHERE media_path IS NOT NULL AND media_path != ''"""
        args: list = []
        if before is not None:
            q += " AND substr(sent_at, 1, 10) < ?"
            args.append(before.isoformat())
        q += " ORDER BY sent_at LIMIT ?"
        args.append(limit)
        out = []
        for r in con.execute(q, args):
            if r["id"] in archived_ids:
                continue
            f = _resolve_media(root, r["media_path"])
            if f is None:
                continue
            out.append({"msg_id": r["id"], "path": f, "sent": str(r["sent_at"])[:10]})
        return out
    finally:
        con.close()


def due_date_of(oldest_sent: str) -> date:
    return date.fromisoformat(oldest_sent) + timedelta(days=RETENTION_DAYS)


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def move_files(session, target: str | Path, label: str, photos: list[dict],
               by_user: str = "") -> dict:
    """ย้ายทีละไฟล์: copy → hash ตรง → ลบต้นทาง → จด MediaArchive.
    hash ไม่ตรง = ลบสำเนา เก็บต้นทางไว้ ไม่จดแถว (ไฟล์นั้น fail)."""
    import models

    dest_root = Path(target) / "YK_MEDIA"
    n_ok = n_fail = bytes_moved = 0
    errors: list[str] = []
    for ph in photos:
        src: Path = ph["path"]
        try:
            y, m = ph["sent"][:4], ph["sent"][5:7]
            dest_dir = dest_root / y / m
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{ph['msg_id']}_{src.name}"
            h_src = _sha256(src)
            shutil.copy2(src, dest)
            if _sha256(dest) != h_src:
                dest.unlink(missing_ok=True)
                n_fail += 1
                errors.append(f"msg {ph['msg_id']}: hash ไม่ตรง — ไม่ลบต้นทาง")
                continue
            size = src.stat().st_size
            session.add(models.MediaArchive(
                line_message_pk=ph["msg_id"], disk_label=label,
                archive_path=str(dest), orig_path=str(src),
                size_bytes=size, sha256=h_src, by_user=by_user))
            session.commit()
            src.unlink()          # ลบต้นทางหลังจดแถวแล้ว — พังกลางคันก็ยังหาไฟล์เจอ
            n_ok += 1
            bytes_moved += size
        except OSError as e:
            session.rollback()
            n_fail += 1
            errors.append(f"msg {ph['msg_id']}: {e}")
    return {"ok": n_ok, "fail": n_fail, "gb": round(bytes_moved / 1e9, 2),
            "errors": errors[:10]}
