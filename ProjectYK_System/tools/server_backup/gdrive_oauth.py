# -*- coding: utf-8 -*-
"""S1 ชั้น Drive ผ่าน OAuth บัญชีโอ — แทน service account ที่ Google ตัดโควต้า (2025).

2 โหมด:
  setup   (รันบนเครื่อง Dev ที่มี browser — ครั้งเดียว):
            python gdrive_oauth.py setup --client-secret <client_secret_xxx.json>
          → เปิด browser ให้โอกดยินยอม → เขียน gdrive_token.json (refresh token)
          → พิมพ์คำสั่ง scp ส่ง token ขึ้น server ให้เสร็จสรรพ
  upload  (server เรียกจาก backup_tier1 — ไม่ต้องมี lib google ใดๆ, stdlib ล้วน):
            ใช้ผ่าน import: upload_and_rotate(token_path, zip_path, weekly)

scope = drive.file (เห็น/ลบเฉพาะไฟล์ที่แอปนี้สร้างเอง — ปลอดภัยต่อ Drive โอ).
โฟลเดอร์ปลายทาง: YK_BACKUPS_HOT/daily + /weekly ใน My Drive ของโอ (โควต้าโอ ~15GB,
zip ~16MB × (14+8) ≈ 350MB — เหลือเฟือ). หมุนเวียนตามชื่อไฟล์ (timestamp ในชื่อ).
"""
from __future__ import annotations

import json
import mimetypes
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCOPE = "https://www.googleapis.com/auth/drive.file"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
ROOT_NAME = "YK_BACKUPS_HOT"
SERVER_TOKEN_PATH = r"C:\Users\yklog\YK_MVP\app\gdrive_token.json"


# ---------------- token ----------------
def _access_token(token_path: str) -> str:
    """แลก refresh_token → access token (อายุ ~1 ชม. ขอใหม่ทุกครั้งที่รัน backup)."""
    tok = json.loads(Path(token_path).read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({
        "client_id": tok["client_id"],
        "client_secret": tok["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["access_token"]


def _req(access: str, method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Authorization": f"Bearer {access}"}
    if data is not None:
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


# ---------------- Drive ops (REST ล้วน) ----------------
def _ensure_folder(access: str, name: str, parent: str | None) -> str:
    q = (f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"
         " and trashed = false")
    if parent:
        q += f" and '{parent}' in parents"
    url = f"{API}/files?q={urllib.parse.quote(q)}&fields=files(id)"
    res = _req(access, "GET", url).get("files", [])
    if res:
        return res[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent:
        meta["parents"] = [parent]
    return _req(access, "POST", f"{API}/files?fields=id", meta)["id"]


def _upload(access: str, path: Path, folder_id: str) -> str:
    """multipart upload (ไฟล์ ~16MB ก้อนเดียวพอ ไม่ต้อง resumable)."""
    boundary = uuid.uuid4().hex
    meta = json.dumps({"name": path.name, "parents": [folder_id]}).encode()
    mime = mimetypes.guess_type(path.name)[0] or "application/zip"
    body = (b"--" + boundary.encode() + b"\r\n"
            b"Content-Type: application/json; charset=UTF-8\r\n\r\n" + meta +
            b"\r\n--" + boundary.encode() + b"\r\n"
            b"Content-Type: " + mime.encode() + b"\r\n\r\n" + path.read_bytes() +
            b"\r\n--" + boundary.encode() + b"--")
    req = urllib.request.Request(
        f"{UPLOAD_API}/files?uploadType=multipart&fields=id",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {access}",
                 "Content-Type": f"multipart/related; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())["id"]


def upload_and_rotate(token_path: str, zip_path: Path, weekly: bool,
                      keep_daily: int = 14, keep_weekly: int = 8) -> dict:
    """อัป zip เข้า daily (+weekly ถ้าวันอาทิตย์) แล้วลบชุดเก่าเกิน keep — คืน {sub: file_id}."""
    access = _access_token(token_path)
    root = _ensure_folder(access, ROOT_NAME, None)
    out = {}
    for sub, keep, do in (("daily", keep_daily, True), ("weekly", keep_weekly, weekly)):
        if not do:
            continue
        folder = _ensure_folder(access, sub, root)
        out[sub] = _upload(access, zip_path, folder)
        q = f"'{folder}' in parents and trashed = false"
        kids = _req(access, "GET",
                    f"{API}/files?q={urllib.parse.quote(q)}"
                    "&fields=files(id,name)&pageSize=200").get("files", [])
        for k in sorted(kids, key=lambda x: x["name"])[:-keep]:
            _req(access, "DELETE", f"{API}/files/{k['id']}")
    return out


# ---------------- setup (Dev เท่านั้น — ต้องมี browser) ----------------
def setup(client_secret_path: str, out_path: str) -> int:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ยังไม่มี lib สำหรับ setup — รันก่อน:\n"
              "  pip install google-auth-oauthlib\n"
              "(ใช้เฉพาะตอน setup บนเครื่อง Dev; server ไม่ต้องลง)")
        return 2
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, [SCOPE])
    creds = flow.run_local_server(port=0, prompt="consent")
    if not creds.refresh_token:
        print("FAIL ไม่ได้ refresh_token — ลองใหม่ (ต้องมี prompt=consent)")
        return 1
    tok = {"client_id": creds.client_id, "client_secret": creds.client_secret,
           "refresh_token": creds.refresh_token,
           "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    Path(out_path).write_text(json.dumps(tok, indent=1), encoding="utf-8")
    print(f"OK เขียน {out_path}")
    # ทดสอบทันทีด้วยเส้นทางเดียวกับ server (REST ล้วน)
    access = _access_token(out_path)
    root = _ensure_folder(access, ROOT_NAME, None)
    print(f"OK ทดสอบ token ผ่าน — โฟลเดอร์ {ROOT_NAME} id={root}")
    print("\nขั้นต่อไป (ส่ง token ขึ้น server):")
    print(f'  scp "{out_path}" yklog@100.97.150.114:{SERVER_TOKEN_PATH}')
    print("คืนถัดไป backup_tier1 จะเห็น token แล้วอัป Drive เอง (ดู drive_ok ใน last_run.json)")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="ครั้งเดียวบน Dev: OAuth consent → token file")
    s.add_argument("--client-secret", required=True,
                   help="ไฟล์ client_secret_*.json ที่โอโหลดจาก Google console")
    s.add_argument("--out", default="gdrive_token.json")
    t = sub.add_parser("test", help="ทดสอบ token + list โฟลเดอร์ (ใช้ได้ทั้ง Dev/server)")
    t.add_argument("--token", default=SERVER_TOKEN_PATH)
    a = ap.parse_args()
    if a.cmd == "setup":
        sys.exit(setup(a.client_secret, a.out))
    access = _access_token(a.token)
    root = _ensure_folder(access, ROOT_NAME, None)
    print(f"OK token ใช้ได้ — {ROOT_NAME} id={root}")
    sys.exit(0)
