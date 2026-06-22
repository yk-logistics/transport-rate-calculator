"""Magic-link token codec. Signs a small payload (role) with the app session
secret so links can't be forged; expiry is enforced at read time via
itsdangerous max_age. No DB access here — pure sign/verify."""
import os

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

_SECRET = os.environ.get("YK_SESSION_SECRET", "dev-insecure-secret-change-me")
_SALT = "yk-access-link-v1"
_serializer = URLSafeTimedSerializer(_SECRET, salt=_SALT)


def make_token(role: str, ttl_seconds: int) -> str:
    # ttl_seconds is informational for the caller (used to set AccessLink.expires_at);
    # actual expiry is enforced in read_token via max_age_seconds.
    return _serializer.dumps({"role": role})


def read_token(token: str, max_age_seconds: int) -> dict | None:
    try:
        return _serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
