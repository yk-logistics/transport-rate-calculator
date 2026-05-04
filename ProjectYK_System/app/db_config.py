"""Database URL: local SQLite by default, or PostgreSQL when DATABASE_URL is set (cloud demo)."""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "app.db"


def resolve_database_url() -> tuple[str, bool]:
    """Returns (sqlalchemy_url, is_sqlite)."""
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if not raw:
        return f"sqlite:///{DB_PATH}", True
    url = raw
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url.split("://", 1)[0]:
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url, False
