# Handoff: OAuth2 Gmail IMAP + Draft Daily จาก Inbox + Daily Grid เต็มฟอร์ม

> สร้างเมื่อ 2026-05-08 — ใช้เมื่อสลับเป็น **Agent mode** แล้วลงมือ apply ทีเดียว หรือ copy ไปวางเอง

## สิ่งที่โอขอ

1. **OAuth2 Gmail/Workspace** แทน app password (พร้อม production มากขึ้น)
2. **Inbox → สร้างร่าง Daily** (human confirm ก่อน save) + preflight guardrail
3. **`/daily/grid`** ให้คอลัมน์ครบเหมือนหน้า Daily ทุกไซต์ในตารางเดียว + **ซ่อนคอลัมน์** แบบคล้าย Excel (localStorage)

---

## ไฟล์ใหม่: `app/services/email_oauth.py`

สร้างไฟล์นี้จากเนื้อหาด้านล่าง (import `db_config.APP_DIR` เหมือน service อื่น)

<details>
<summary>คลิกเพื่อขยายโค้ดเต็ม (ยาว)</summary>

```python
"""Google OAuth2 helpers for Gmail IMAP (XOAUTH2)."""
from __future__ import annotations

import base64
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from db_config import APP_DIR

DATA_DIR = APP_DIR / "data"
TOKEN_FILE = DATA_DIR / "email_google_refresh.token"

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GMAIL_IMAP_SCOPE = "https://mail.google.com/"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_google_refresh_token() -> str:
    raw = (os.environ.get("EMAIL_GOOGLE_REFRESH_TOKEN", "") or "").strip()
    if raw:
        return raw
    if TOKEN_FILE.exists():
        try:
            return TOKEN_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


def save_google_refresh_token(token: str) -> Path:
    _ensure_data_dir()
    TOKEN_FILE.write_text(token.strip(), encoding="utf-8")
    return TOKEN_FILE


def oauth_client_config() -> tuple[str, str, str]:
    cid = (os.environ.get("EMAIL_GOOGLE_CLIENT_ID", "") or "").strip()
    csec = (os.environ.get("EMAIL_GOOGLE_CLIENT_SECRET", "") or "").strip()
    redir = (os.environ.get("EMAIL_GOOGLE_REDIRECT_URI", "") or "").strip()
    if not redir:
        redir = "http://localhost:8000/email/oauth/callback"
    return cid, csec, redir


def build_authorize_url(state: str) -> str:
    cid, _, redir = oauth_client_config()
    if not cid:
        raise RuntimeError("EMAIL_GOOGLE_CLIENT_ID not set")
    q = urllib.parse.urlencode(
        {
            "client_id": cid,
            "redirect_uri": redir,
            "response_type": "code",
            "scope": GMAIL_IMAP_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH}?{q}"


def exchange_code_for_tokens(code: str) -> dict:
    cid, csec, redir = oauth_client_config()
    if not cid or not csec:
        raise RuntimeError(
            "EMAIL_GOOGLE_CLIENT_ID / EMAIL_GOOGLE_CLIENT_SECRET required for callback"
        )
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": cid,
            "client_secret": csec,
            "redirect_uri": redir,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_TOKEN,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def refresh_access_token(refresh_token: str) -> str:
    cid, csec, _ = oauth_client_config()
    body = urllib.parse.urlencode(
        {
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_TOKEN,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"token refresh HTTP {e.code}: {err}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("token response missing access_token")
    return str(token)


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def build_xoauth2_string(user_email: str, access_token: str) -> bytes:
    return f"user={user_email}\1auth=Bearer {access_token}\1\1".encode("utf-8")


def encode_xoauth2_for_imap(user_email: str, access_token: str) -> str:
    return base64.b64encode(build_xoauth2_string(user_email, access_token)).decode("ascii")
```

</details>

---

## แก้ `app/services/email_ingest.py`

### 1) ขยาย `InboxScope`

เพิ่มฟิลด์:

- `auth_mode: str`  # `password` | `oauth2`

### 2) `get_inbox_scope()`

- อ่าน `EMAIL_IMAP_AUTH` default `password` — ถ้าเป็น `oauth2` ใช้ OAuth
- เมื่อ oauth2 **ไม่**ต้องบังคับ `password`; ใช้ `EMAIL_IMAP_USERNAME` เป็น email บัญชี Gmail

### 3) ฟังก์ชันใหม่ `_imap_connect_login(scope)`

- ถ้า `password`: `client.login(username, password)` เหมือนเดิม
- ถ้า `oauth2`:
  - `rt = email_oauth.load_google_refresh_token()`
  - `at = refresh_access_token(rt)`
  - `imap.authenticate("XOAUTH2", lambda x: encode_xoauth2_for_imap(username, at))`

(ใช้ `imaplib.IMAP4_SSL` เหมือนเดิม)

### 4) `sync_inbox()` — เช็ก credential

- `password`: ต้องมี username + password
- `oauth2`: ต้องมี username + refresh token (env หรือไฟล์) + client id/secret สำหรับ refresh

ข้อความ error เป็นภาษาอังกฤhariสั้นๆ พอ

---

## แก้ `app/main.py`

### Imports

```python
from services.email_oauth import (
    build_authorize_url,
    exchange_code_for_tokens,
    load_google_refresh_token,
    new_oauth_state,
    oauth_client_config,
    save_google_refresh_token,
)
```

### Routes OAuth (cookie state ง่ายๆ)

- `GET /email/oauth/start`
  - สร้าง `state = new_oauth_state()`
  - `RedirectResponse` ไป `build_authorize_url(state)`
  - `set_cookie("email_oauth_state", state, max_age=600, ...)` (httponly=True, samesite=lax)

- `GET /email/oauth/callback?code=&state=`
  - เทียบ `state` กับ cookie
  - `exchange_code_for_tokens(code)` → `refresh_token`
  - `save_google_refresh_token(refresh_token)` ถ้ามีใน response (Google ให้ครั้งแรกหลัง consent)
  - แสดง `HTMLResponse` สั้นๆ ว่าบันทึกแล้ว + path ไฟล์ + ให้ตั้ง `EMAIL_IMAP_AUTH=oauth2`

**หมายเหตุ Google Console**: Redirect URI ต้องตรง `EMAIL_GOOGLE_REDIRECT_URI` (default localhost callback)

### ขยาย `get_inbox_scope` display บน inbox template

ส่งฟิลด์ `auth_mode` เข้า template (expose จาก scope object)

### Draft Daily + preflight

- `GET /email/inbox/{mail_id}/draft-daily`
  - โหลด `InboxEmail`, masters
  - สร้าง `DailyJob` **ในหน่วยความจำ** (ไม่ commit) เติมฟิลด์เริ่มต้น:
    - `work_date` = mail.sent_at.date() ถ้าไม่มีใช้วันนี้
    - `site_code` = mail.suggested_site_code ถ้าว่างใช้ `BIGC`
    - `remark` = `[จากอีเมล inbox #{id}]\nหัวข้อ: …\n---\nbody ตัดความยาว …`
    - `customer_name_raw` = mail.suggested_customer
  - **preflight_warnings** list[str] เช่น:
    - ยังไม่มี driver master (driver_id ว่าง — ธรรมดา)
    - ยังไม่มี customer_id
    - มีแต่ไฟล์แนบ / body สั้นผิดปกติ
    - เตือนให้เปิด `/payroll`/preflight ถ้ากระทบรอบ (ข้อความทั่วไป ไม่ต้อง query DB heavy)
  - render `daily_form.html` พร้อม `row=draft_job`, `inbox_mail_id=mail.id`, `preflight_warnings=...`

### แก้ `daily_form.html`

ที่ต้นฟอร์ม:

- ถ้ามี `preflight_warnings`: แสดงกล่องเหลืองรายการ
- ซ่อนฟิลด์: `<input type="hidden" name="inbox_mail_id" value="{{ inbox_mail_id }}" />` ถ้ามี

### แก้ `daily_save`

เพิ่ม `inbox_mail_id: str = Form("")`

หลัง `s.commit()` + `s.refresh(row)` สำหรับโหมด new:

ถ้ามี `_parse_int(inbox_mail_id)`:

- โหลด `InboxEmail`, ตั้ง `linked_daily_job_id=row.id`, `status='linked'`, commit

Redirect เดิม `/daily`

### แก้ `daily_grid` + API

#### Query

เพิ่ม `limit: int` query param default 400, max 800

#### `_daily_grid_filters`

เพิ่มฟิลเตอร์ `status=` (optional) แบบเดียวกับ `/daily` list ถ้าต้องการ — optional

#### `/api/daily/grid-data`

ส่งคืนฟิลด์ DailyJob **ทั้งหมด**ที่มีในฟอร์ม + `invoice_date` ISO string + float fields

#### `/api/daily/grid-save`

-  расширить `editable` ให้ครบทุกคอลัมน์ที่แก้ในฟอร์ม (ไม่รวม `id`, `created_at`)
- **`status_code`** อย่าจำกัดแค่ idle/placeholder/leave/real — ฟอร์มบอกว่าเป็น text อิสระแล้ว
- **`leave_status`**: validate กับ `LEAVE_STATUS_CHOICES`
- FK: `driver_id`, `customer_id`, `head_vehicle_id`, `tail_vehicle_id` — `_parse_int` ได้ None
- `work_date`: parse ISO date
- `invoice_date`: empty → None else parse
- หลัง save ให้เรียก `rate_record_from_daily` เหมือน `daily_save` (อยู่ใน try/rollback)

---

## แก้ `daily_grid.html`

- Tabulator columns: array จากทุก field + `{title, field, editor, visible:true}` เฉพาะ `id/source/created_at` ใช้ `editor:false` read-only (หรือไม่ให้ซ่อนคอลัมน์ id เท่านั้น)
- ปุ่ม **"คอลัมน์"** เปิด `<dialog>` checklist จากรายการ `ALL_FIELDS` sync กับ `table.hideColumn/showColumn`
- เก็บ hidden list ใน `localStorage['yk_daily_grid_hidden_v1']` (array of field names)
- เพิ่ม `ตัวกรอง status` และ `จำนวนแถว` ในฟอร์ม get

---

## แก้ `email_inbox.html`

- บรรทัด scope แสดง `auth: password | oauth2`
- ลิงก์ `<a href="/email/oauth/start">ตั้งค่า OAuth Google</a>` (เมื่อใช้ oauth2 / หรือแสดงเสมอ)
- ต่อคอลัมน์ action: `<a href="/email/inbox/{{ r.id }}/draft-daily">สร้างร่าง Daily</a>`

---

## `.gitignore` (ที่ราก repo หรือ app)

เพิ่ม:

```
ProjectYK_System/app/data/email_google_refresh.token
```

---

## ENV ที่โอใช้

| Variable | ค่า |
|----------|-----|
| `EMAIL_INGEST_ENABLED` | `1` |
| `EMAIL_IMAP_AUTH` | `oauth2` หรือ `password` |
| `EMAIL_IMAP_USERNAME` | `user@gmail.com` |
| `EMAIL_IMAP_PASSWORD` | (ถ้า password) |
| `EMAIL_GOOGLE_CLIENT_ID` | จาก GCP |
| `EMAIL_GOOGLE_CLIENT_SECRET` | จาก GCP |
| `EMAIL_GOOGLE_REDIRECT_URI` | `http://localhost:8000/email/oauth/callback` |
| `EMAIL_GOOGLE_REFRESH_TOKEN` | (optional — ถ้าไม่ใส่ใช้ไฟล์จาก callback) |

---

## Verify หลัง apply

```bash
python -m py_compile ProjectYK_System/app/main.py ProjectYK_System/app/services/email_ingest.py ProjectYK_System/app/services/email_oauth.py
python ProjectYK_System/tools/run_payroll_test.py
```

ทดสอบมือ:

1. `/email/oauth/start` → Login Google → callback → มีไฟล์ token  
2. `EMAIL_IMAP_AUTH=oauth2` + Sync  
3. Inbox → สร้างร่าง Daily → เช็ความเตือน → ติ๊กยืนยัน → Save → Inbox เชื่อม `linked_daily_job_id`  
4. `/daily/grid` ซ่อน/โชว์คอลัมน์ + Save

---

เมื่อให้ Cursor **Agent mode** กลับมา ให้ชี้อ้างไฟล์นี้แล้วบอกว่า "apply EMAIL_OAUTH_DRAFT_DAILY_GRID_V2_TH.md ให้ครบ"
