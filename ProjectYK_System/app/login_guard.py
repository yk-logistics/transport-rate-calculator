"""In-memory brute-force protection for /login.

Two independent layers:
  1. Per-username lockout: after MAX_USER_FAILS bad passwords, that username is
     locked for USER_LOCK_SECONDS (protects a specific account from guessing).
  2. Per-IP rate limit: after MAX_IP_ATTEMPTS login hits from one IP within
     IP_WINDOW_SECONDS, that IP is blocked for IP_BLOCK_SECONDS — this throttles
     an attacker spraying many different usernames from one IP.

State is process-local (single app process). Good enough for the MVP; if we ever
run multiple workers, move this to a shared store (Redis).
"""
from __future__ import annotations

import time

MAX_USER_FAILS = 5
USER_LOCK_SECONDS = 15 * 60          # 15 minutes

MAX_IP_ATTEMPTS = 20
IP_WINDOW_SECONDS = 60               # counting window
IP_BLOCK_SECONDS = 10 * 60          # 10 minutes

# username -> list of failure timestamps (within the lock window)
_user_fails: dict[str, list[float]] = {}
# username -> unix time the lock expires
_user_locked_until: dict[str, float] = {}
# ip -> list of attempt timestamps (within the IP window)
_ip_attempts: dict[str, list[float]] = {}
# ip -> unix time the block expires
_ip_blocked_until: dict[str, float] = {}


def reset_all() -> None:
    _user_fails.clear()
    _user_locked_until.clear()
    _ip_attempts.clear()
    _ip_blocked_until.clear()


# ---- per-username ----

def record_failure(username: str, ip: str) -> None:
    now = time.time()
    fails = [t for t in _user_fails.get(username, []) if now - t < USER_LOCK_SECONDS]
    fails.append(now)
    _user_fails[username] = fails
    if len(fails) >= MAX_USER_FAILS:
        _user_locked_until[username] = now + USER_LOCK_SECONDS
    record_attempt(ip)


def record_success(username: str, ip: str) -> None:
    _user_fails.pop(username, None)
    _user_locked_until.pop(username, None)


def is_username_locked(username: str) -> bool:
    until = _user_locked_until.get(username)
    if until is None:
        return False
    if time.time() >= until:
        _user_locked_until.pop(username, None)
        _user_fails.pop(username, None)
        return False
    return True


# ---- per-IP ----

def record_attempt(ip: str) -> None:
    now = time.time()
    hits = [t for t in _ip_attempts.get(ip, []) if now - t < IP_WINDOW_SECONDS]
    hits.append(now)
    _ip_attempts[ip] = hits
    if len(hits) >= MAX_IP_ATTEMPTS:
        _ip_blocked_until[ip] = now + IP_BLOCK_SECONDS


def is_ip_blocked(ip: str) -> bool:
    until = _ip_blocked_until.get(ip)
    if until is None:
        return False
    if time.time() >= until:
        _ip_blocked_until.pop(ip, None)
        _ip_attempts.pop(ip, None)
        return False
    return True
