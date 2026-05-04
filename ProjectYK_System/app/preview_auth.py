"""Optional HTTP Basic auth for cloud demo (family / internal only)."""
from __future__ import annotations

import base64
import binascii
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class PreviewAuthMiddleware(BaseHTTPMiddleware):
    """When YK_PREVIEW_AUTH=1 and YK_PREVIEW_USER + YK_PREVIEW_PASSWORD are set, require Basic auth."""

    async def dispatch(self, request: Request, call_next):
        if os.getenv("YK_PREVIEW_AUTH", "").lower() not in ("1", "true", "yes"):
            return await call_next(request)
        user = os.getenv("YK_PREVIEW_USER", "").strip()
        password = os.getenv("YK_PREVIEW_PASSWORD", "").strip()
        if not user or not password:
            return await call_next(request)

        path = request.url.path
        if path == "/health" or path.startswith("/static/") or path.startswith("/uploads/"):
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        if not auth.startswith("Basic "):
            return _unauthorized()
        try:
            raw = base64.b64decode(auth[6:].strip()).decode("utf-8")
            u, _, p = raw.partition(":")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return _unauthorized()
        if u != user or p != password:
            return _unauthorized()
        return await call_next(request)


def _unauthorized() -> Response:
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="YK Preview"'},
        content="ต้องล็อกอิน (HTTP Basic) — ใช้ user/password ที่ตั้งใน YK_PREVIEW_USER / YK_PREVIEW_PASSWORD",
        media_type="text/plain; charset=utf-8",
    )
