# -*- coding: utf-8 -*-
"""S1 ชั้น 1 — สำรอง "ของร้อน" ทุกคืน (แบบธนาคาร ไม่ต้องมีใครอยู่).

ของร้อน = ฐานข้อมูลเงิน + ตั้งค่า (เล็ก <100MB): app.db, line_archive.db,
.env archiver/slip_reader, start_mvp.bat, oatside config, key Google.
รูปไลน์ 3.8GB = ของเย็น อยู่ชั้น 2 (ปุ่ม External ใน /admin/server-health).

ทำอะไร (ตามลำดับ — พังขั้นไหนแจ้ง Discord + เขียน last_run.json ให้การ์ด G1 เตือน):
 1. snapshot ฐานข้อมูลด้วย sqlite backup API (ปลอดภัยขณะแอปเขียนอยู่ — ห้าม copy ดิบ)
 2. zip ลง <out>/daily/yk_hot_YYYYMMDD_HHMMSS.zip  (หมุนเวียนเก็บ 14 ชุด)
 3. วันอาทิตย์ copy เข้า <out>/weekly ด้วย (เก็บ 8 ชุด)
 4. อัปโหลดขึ้น Google Drive ของ service account (โฟลเดอร์ YK_BACKUPS_HOT
    แชร์ให้อีเมลโอแบบ viewer) + หมุนเวียนบน Drive เท่ากัน — ไม่ใช้พื้นที่ Drive โอ
 5. เขียนสถานะลง <out>/last_run.json (การ์ด G1 อ่านไฟล์นี้ — เกิน 26 ชม. = แดง)

รันบนเซิร์ฟเวอร์ (scheduled task YK_MVP_HOT_BACKUP 03:00):
  C:\\Users\\yklog\\YK_MVP\\app\\.venv\\Scripts\\python.exe C:\\Users\\yklog\\YK_MVP\\backup_tier1.py
ทดสอบบนเครื่อง Dev:
  python backup_tier1.py --app-db <path> --line-db "" --out <dir> --key <key.json> --no-discord

restore: ดู docs/BACKUP_RUNBOOK.md (unzip → วาง app.db/line_archive.db กลับ → restart)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import urllib.request
import zipfile
from datetime import date, datetime
from pathlib import Path

# console Windows เป็น cp1252/cp874 — ไทยใน log ทำสคริปต์ตายทั้งตัว (GOTCHA เดิม)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

KEEP_DAILY = 14
KEEP_WEEKLY = 8
DRIVE_ROOT_NAME = "YK_BACKUPS_HOT"

SERVER = {
    "app_db": r"C:\Users\yklog\YK_MVP\app\app.db",
    "line_db": r"C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db",
    "extras": [
        r"C:\Users\yklog\YK_LINE_ARCHIVER\.env",
        r"C:\Users\yklog\YK_MVP\start_mvp.bat",
        r"C:\Users\yklog\YK_MVP\app\start.bat",
        # config Oatside ตัวจริง (โอแก้ผ่านเว็บ /oatside/settings — ห้ามหลุดจาก backup)
        r"C:\Users\yklog\YK_MVP\app\oatside\oatside_config.json",
        r"C:\Users\yklog\YK_MVP\app\oatside\oatside_billing_overrides.json",
        r"C:\Users\yklog\YK_MVP\slip_reader\.env",
        r"C:\Users\yklog\YK_MVP\app\noble-history-446303-e4-c36409a0122c.json",
    ],
    "out": r"D:\YK_BACKUPS",
    "key": r"C:\Users\yklog\YK_MVP\app\noble-history-446303-e4-c36409a0122c.json",
    # OAuth token ของโอ (สร้างด้วย gdrive_oauth.py setup บน Dev) — ถ้าไฟล์นี้มี
    # จะใช้แทน service account (ที่ Google ตัดโควต้าแล้ว)
    "oauth_token": r"C:\Users\yklog\YK_MVP\app\gdrive_token.json",
    "share_email": "guolekung@gmail.com",
    "archiver_env": r"C:\Users\yklog\YK_LINE_ARCHIVER\.env",
}


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def snapshot_sqlite(src: Path, dst: Path) -> None:
    """สำเนา DB แบบ transaction-safe ขณะแอปยังเขียนอยู่ (sqlite backup API)."""
    con = sqlite3.connect(str(src))
    try:
        dcon = sqlite3.connect(str(dst))
        try:
            con.backup(dcon)
        finally:
            dcon.close()
    finally:
        con.close()


def build_zip(app_db: str, line_db: str, extras: list[str], zip_path: Path) -> list[str]:
    manifest: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for label, dbp in (("app.db", app_db), ("line_archive.db", line_db)):
                if not dbp:
                    continue
                src = Path(dbp)
                if not src.exists():
                    raise FileNotFoundError(f"ไม่พบฐานข้อมูล {src}")
                snap = tdp / label
                snapshot_sqlite(src, snap)
                zf.write(snap, f"db/{label}")
                manifest.append(f"db/{label} ({snap.stat().st_size / 1e6:.1f}MB)")
            for ex in extras:
                p = Path(ex)
                if p.exists():
                    arc = f"config/{p.parent.name}__{p.name}"
                    zf.write(p, arc)
                    manifest.append(arc)
                else:
                    manifest.append(f"(ข้าม ไม่พบ: {ex})")
            zf.writestr("MANIFEST.txt",
                        f"yk_hot backup {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                        + "\n".join(manifest) + "\n")
    return manifest


def rotate_local(dir_: Path, keep: int) -> int:
    files = sorted(dir_.glob("yk_hot_*.zip"))
    n = 0
    for f in files[:-keep] if keep else files:
        f.unlink()
        n += 1
    return n


# ---------------- Google Drive (service account เป็นเจ้าของ — ไม่กินโควต้าโอ) ---
def drive_service(key_path: str):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _ensure_folder(svc, name: str, parent: str | None, share_email: str = "") -> str:
    q = (f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"
         " and trashed = false")
    if parent:
        q += f" and '{parent}' in parents"
    res = svc.files().list(q=q, fields="files(id)").execute().get("files", [])
    if res:
        return res[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent:
        meta["parents"] = [parent]
    fid = svc.files().create(body=meta, fields="id").execute()["id"]
    if share_email:
        try:
            svc.permissions().create(
                fileId=fid,
                body={"type": "user", "role": "reader", "emailAddress": share_email},
                sendNotificationEmail=False,
            ).execute()
        except Exception as e:  # แชร์พลาดไม่ใช่เหตุให้ backup fail
            log(f"WARN share to {share_email} failed: {e}")
    return fid


def drive_upload_and_rotate(key_path: str, share_email: str, zip_path: Path,
                            weekly: bool) -> dict:
    from googleapiclient.http import MediaFileUpload
    svc = drive_service(key_path)
    root = _ensure_folder(svc, DRIVE_ROOT_NAME, None, share_email)
    out = {}
    for sub, keep, do in (("daily", KEEP_DAILY, True), ("weekly", KEEP_WEEKLY, weekly)):
        if not do:
            continue
        folder = _ensure_folder(svc, sub, root)
        media = MediaFileUpload(str(zip_path), mimetype="application/zip",
                                resumable=True)
        f = svc.files().create(
            body={"name": zip_path.name, "parents": [folder]},
            media_body=media, fields="id, size").execute()
        out[sub] = f["id"]
        # หมุนเวียน: ชื่อไฟล์มี timestamp → เรียงชื่อ = เรียงเวลา
        kids = svc.files().list(
            q=f"'{folder}' in parents and trashed = false",
            fields="files(id, name)", pageSize=200,
        ).execute().get("files", [])
        for k in sorted(kids, key=lambda x: x["name"])[:-keep]:
            svc.files().delete(fileId=k["id"]).execute()
    return out


# ---------------- Discord (ลอก pattern health_poll ของ archiver) ---------------
def _read_env(path: str) -> dict:
    env = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def discord_alert(archiver_env: str, msg: str) -> None:
    env = _read_env(archiver_env)
    token, guild = env.get("DISCORD_BOT_TOKEN"), env.get("DISCORD_GUILD_ID")
    if not (token and guild):
        log("WARN no discord creds — skip alert")
        return
    api = "https://discord.com/api/v10"
    # Cloudflare ของ Discord บล็อค UA default ของ urllib — ต้องตั้งเอง
    hdr = {"Authorization": f"Bot {token}", "Content-Type": "application/json",
           "User-Agent": "DiscordBot (yk-backup, 1.0)"}

    def _req(method: str, url: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=hdr, method=method)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    chans = _req("GET", f"{api}/guilds/{guild}/channels")
    by_name = {c.get("name"): c["id"] for c in chans if c.get("type") == 0}
    # บอทไม่มีสิทธิ์สร้าง channel (403) → ใช้ channel แจ้งเตือนเดิมของ archiver แทน
    cid = by_name.get("yk-backup-alerts") or by_name.get("line-archiver-alerts")
    if not cid:
        cid = _req("POST", f"{api}/guilds/{guild}/channels",
                   {"name": "yk-backup-alerts", "type": 0})["id"]
    _req("POST", f"{api}/channels/{cid}/messages", {"content": msg})


# ------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--app-db", default=SERVER["app_db"])
    ap.add_argument("--line-db", default=SERVER["line_db"])
    ap.add_argument("--extra", action="append", default=None,
                    help="ไฟล์ config เพิ่ม (default = ชุดเซิร์ฟเวอร์)")
    ap.add_argument("--out", default=SERVER["out"])
    ap.add_argument("--key", default=SERVER["key"])
    ap.add_argument("--share-email", default=SERVER["share_email"])
    ap.add_argument("--oauth-token", default=SERVER["oauth_token"])
    ap.add_argument("--archiver-env", default=SERVER["archiver_env"])
    ap.add_argument("--no-drive", action="store_true")
    ap.add_argument("--no-discord", action="store_true")
    a = ap.parse_args()
    extras = a.extra if a.extra is not None else SERVER["extras"]

    out_root = Path(a.out)
    daily = out_root / "daily"
    weekly_dir = out_root / "weekly"
    daily.mkdir(parents=True, exist_ok=True)
    weekly_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_root / "last_run.json"
    stamp = datetime.now()
    zip_path = daily / f"yk_hot_{stamp:%Y%m%d_%H%M%S}.zip"
    is_weekly = date.today().weekday() == 6  # อาทิตย์
    status = {"ok": False, "ts": stamp.isoformat(timespec="seconds"),
              "zip": zip_path.name, "size_mb": None,
              "drive_ok": None, "drive_error": None, "error": None}
    try:
        manifest = build_zip(a.app_db, a.line_db, extras, zip_path)
        status["size_mb"] = round(zip_path.stat().st_size / 1e6, 1)
        log(f"zip OK {zip_path.name} {status['size_mb']}MB ({len(manifest)} รายการ)")
        if is_weekly:
            shutil.copy2(zip_path, weekly_dir / zip_path.name)
        n1 = rotate_local(daily, KEEP_DAILY)
        n2 = rotate_local(weekly_dir, KEEP_WEEKLY)
        if n1 or n2:
            log(f"rotate local: ลบ daily {n1} / weekly {n2}")
        # Drive = layer เสริม: Google ตัดโควต้า service account (2025) → อัปไม่ได้
        # จนกว่าจะมี OAuth ของโอ. พัง = ติดธงเหลืองบนการ์ด G1 ไม่ล้มงานหลัก
        # (สำเนานอกเครื่องตัวจริงตอนนี้ = ชั้น 3 เครื่อง Dev ดูดผ่าน Tailscale)
        if not a.no_drive:
            try:
                if Path(a.oauth_token).exists():
                    # ทาง OAuth (โควต้าโอ) — stdlib ล้วน ไม่ต้องมี lib google บน server
                    from gdrive_oauth import upload_and_rotate as _oauth_up
                    fid = _oauth_up(a.oauth_token, zip_path, is_weekly,
                                    KEEP_DAILY, KEEP_WEEKLY)
                else:
                    fid = drive_upload_and_rotate(a.key, a.share_email, zip_path,
                                                  is_weekly)
                status["drive_ok"] = True
                log(f"Drive OK {fid}")
            except Exception as de:  # noqa: BLE001
                status["drive_ok"] = False
                status["drive_error"] = f"{type(de).__name__}: {de}"[:300]
                log(f"WARN Drive upload failed (ไม่ล้มงาน): {status['drive_error']}")
        status["ok"] = True
        return 0
    except Exception as e:  # noqa: BLE001 — จุดรวมทุกความพัง: จดสถานะ+แจ้งเตือน
        status["error"] = f"{type(e).__name__}: {e}"
        log(f"FAIL {status['error']}")
        if not a.no_discord:
            try:
                discord_alert(a.archiver_env,
                              f"🔴 YK backup คืนนี้พัง {stamp:%d/%m %H:%M} — "
                              f"{status['error']} (ดู {status_path})")
            except Exception as de:  # noqa: BLE001
                log(f"WARN discord alert failed: {de}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=1),
                               encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
