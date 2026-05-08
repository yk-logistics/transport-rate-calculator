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
