"""Auth helpers: password hashing + session access."""
from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


from sqlmodel import Session, select  # noqa: E402

from db_config import engine  # noqa: E402
from models import AppUser  # noqa: E402


def get_user_by_username(username: str):
    with Session(engine) as s:
        return s.exec(select(AppUser).where(AppUser.username == username)).first()


def get_user_by_id(user_id: int):
    with Session(engine) as s:
        return s.get(AppUser, user_id)


def login_session(request, user) -> None:
    request.session["uid"] = user.id
    request.session["role"] = user.role


def logout_session(request) -> None:
    request.session.clear()


def current_user(request):
    uid = request.session.get("uid")
    if uid is None:
        return None
    u = get_user_by_id(uid)
    if u is None or u.status != "active":
        return None
    return u
