"""
Driver PWA authentication (Phase 4).

Simple phone + PIN login. PIN is 4-6 digits, hashed with salt+scrypt (stdlib).
Session stored in signed cookie 'drv_session'.

Design choices:
- No passwords (drivers aren't used to them). Phone number = username.
- PIN rate limiting: after 5 failed attempts, lockout 10 min (in-memory).
- Session = 30-day rolling (reset on every authenticated request).
- Uses stdlib only (no bcrypt/argon2 dependency) — scrypt is good enough
  for 4-6 digit PINs when combined with rate limiting.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, Response
from sqlmodel import Session, select

from models import DriverSession, Employee


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

COOKIE_NAME = "drv_session"
SESSION_DAYS = 30
PIN_MIN_LEN = 4
PIN_MAX_LEN = 6
LOCKOUT_AFTER_FAILS = 5
LOCKOUT_MINUTES = 10


# ---------------------------------------------------------------------------
# PIN HASHING (scrypt, stdlib)
# ---------------------------------------------------------------------------

def hash_pin(pin: str) -> str:
    """Return 'scrypt$<hex_salt>$<hex_hash>' string."""
    if not pin or not pin.isdigit() or not (PIN_MIN_LEN <= len(pin) <= PIN_MAX_LEN):
        raise ValueError(f"PIN ต้องเป็นตัวเลข {PIN_MIN_LEN}-{PIN_MAX_LEN} หลัก")
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_pin(pin: str, hash_str: str) -> bool:
    if not hash_str or not hash_str.startswith("scrypt$"):
        return False
    try:
        _, salt_hex, hash_hex = hash_str.split("$", 2)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False
    h = hashlib.scrypt(pin.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(h, expected)


# ---------------------------------------------------------------------------
# RATE LIMITING (in-memory, per-process — fine for 1 FastAPI process)
# ---------------------------------------------------------------------------

_fail_counts: dict[str, tuple[int, datetime]] = {}


def _record_fail(key: str) -> None:
    count, first_at = _fail_counts.get(key, (0, datetime.utcnow()))
    if datetime.utcnow() - first_at > timedelta(minutes=LOCKOUT_MINUTES):
        count, first_at = 0, datetime.utcnow()
    _fail_counts[key] = (count + 1, first_at)


def _is_locked(key: str) -> bool:
    count, first_at = _fail_counts.get(key, (0, datetime.utcnow()))
    if datetime.utcnow() - first_at > timedelta(minutes=LOCKOUT_MINUTES):
        _fail_counts.pop(key, None)
        return False
    return count >= LOCKOUT_AFTER_FAILS


def _clear_fails(key: str) -> None:
    _fail_counts.pop(key, None)


# ---------------------------------------------------------------------------
# PHONE NORMALIZATION
# ---------------------------------------------------------------------------

def normalize_phone(raw: str) -> str:
    """Keep digits only. '081-234 5678' → '0812345678'. '+66 81 234 5678' → '66812345678'."""
    if not raw:
        return ""
    return re.sub(r"\D", "", raw)


# ---------------------------------------------------------------------------
# SESSION MANAGEMENT
# ---------------------------------------------------------------------------

def create_session(session: Session, emp: Employee, device_info: str = "") -> str:
    token = secrets.token_urlsafe(32)
    row = DriverSession(
        employee_id=emp.id,
        token=token,
        device_info=(device_info or "")[:300],
        expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
    )
    session.add(row)
    session.commit()
    return token


def revoke_session(session: Session, token: str) -> None:
    row = session.exec(select(DriverSession).where(DriverSession.token == token)).first()
    if row:
        row.revoked = True
        session.add(row)
        session.commit()


def get_current_driver(request: Request, session: Session) -> Optional[Employee]:
    """Return the Employee for the request's session cookie, or None."""
    token = request.cookies.get(COOKIE_NAME, "")
    if not token:
        return None
    row = session.exec(
        select(DriverSession).where(
            DriverSession.token == token,
            DriverSession.revoked == False,  # noqa: E712
        )
    ).first()
    if not row:
        return None
    if row.expires_at < datetime.utcnow():
        return None
    emp = session.get(Employee, row.employee_id)
    if not emp or emp.status != "active":
        return None
    # Touch last_seen_at + rolling expiration (throttled — only every ~5 min
    # to avoid detaching attributes on every request via commit/expire cycle)
    now = datetime.utcnow()
    if (now - row.last_seen_at) > timedelta(minutes=5):
        row.last_seen_at = now
        row.expires_at = now + timedelta(days=SESSION_DAYS)
        session.add(row)
        session.commit()
        # Re-load emp attributes (commit expired them)
        session.refresh(emp)
    return emp


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # TODO: True when HTTPS
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


# ---------------------------------------------------------------------------
# LOGIN FLOW
# ---------------------------------------------------------------------------

class LoginResult:
    def __init__(self, ok: bool, employee: Optional[Employee] = None, error: str = ""):
        self.ok = ok
        self.employee = employee
        self.error = error


def attempt_login(session: Session, phone_raw: str, pin: str) -> LoginResult:
    phone = normalize_phone(phone_raw)
    if not phone:
        return LoginResult(False, error="กรอกเบอร์โทร")
    if not pin or not pin.isdigit():
        return LoginResult(False, error="กรอก PIN เป็นตัวเลข")

    rate_key = f"phone:{phone}"
    if _is_locked(rate_key):
        return LoginResult(False, error=f"ล็อค {LOCKOUT_MINUTES} นาที (ลองผิดเกิน {LOCKOUT_AFTER_FAILS} ครั้ง)")

    # Find employee by normalized phone (strip dashes/spaces in DB or match loosely)
    candidates = session.exec(
        select(Employee).where(Employee.status == "active")
    ).all()
    match = None
    for e in candidates:
        if normalize_phone(e.phone) == phone and e.pin_hash:
            match = e
            break

    if not match:
        _record_fail(rate_key)
        return LoginResult(False, error="ไม่พบเบอร์นี้ในระบบ หรือยังไม่ได้ตั้ง PIN")

    if not verify_pin(pin, match.pin_hash):
        _record_fail(rate_key)
        return LoginResult(False, error="PIN ไม่ถูกต้อง")

    _clear_fails(rate_key)
    return LoginResult(True, employee=match)


# ---------------------------------------------------------------------------
# PHOTO STORAGE
# ---------------------------------------------------------------------------

UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "driver")


def save_photo(emp_id: int, kind: str, file_bytes: bytes, ext: str = "jpg") -> str:
    """Save photo bytes to uploads/driver/<emp>/<YYYY-MM-DD>/<kind>/<ts>.<ext>.
    Return relative path (from uploads root) for storing in DB."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    folder = os.path.join(UPLOAD_ROOT, str(emp_id), today, kind)
    os.makedirs(folder, exist_ok=True)
    ts = datetime.utcnow().strftime("%H%M%S_%f")
    ext = (ext or "jpg").lower().lstrip(".")
    filename = f"{ts}.{ext}"
    full = os.path.join(folder, filename)
    with open(full, "wb") as f:
        f.write(file_bytes)
    rel = os.path.relpath(full, os.path.dirname(UPLOAD_ROOT)).replace("\\", "/")
    return rel  # e.g. "driver/12/2026-04-08/vehicle_check/123456_000000.jpg"
