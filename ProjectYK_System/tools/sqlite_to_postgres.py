"""
One-shot copy: local SQLite app.db → PostgreSQL (Neon / Render Postgres).

Usage (จากราก repo Project YK, PowerShell):
  $env:DATABASE_URL="postgresql+psycopg2://USER:PASS@HOST/DB?sslmode=require"
  python ProjectYK_System/tools/sqlite_to_postgres.py --wipe

Requires: pip install -r ProjectYK_System/app/requirements.txt (รวม psycopg2-binary)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
APP_DIR = TOOLS_DIR.parent / "app"

sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)

# noqa: F401 — register all tables on SQLModel.metadata
import models  # type: ignore  # pylint: disable=unused-import

from sqlalchemy import create_engine, insert, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel


def _normalize_pg_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url.split("://", 1)[0]:
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def _row_for_table(table, rowdict: dict) -> dict:
    cols = set(table.c.keys())
    return {k: v for k, v in rowdict.items() if k in cols}


def _copy_rows(sqlite_engine: Engine, pg_engine: Engine) -> None:
    meta = SQLModel.metadata
    with sqlite_engine.connect() as src, pg_engine.begin() as dst:
        dst.execute(text("SET session_replication_role = replica"))
        try:
            for table in meta.sorted_tables:
                rows = src.execute(table.select()).mappings().all()
                if not rows:
                    continue
                dicts = [_row_for_table(table, dict(r)) for r in rows]
                chunk = 400
                for i in range(0, len(dicts), chunk):
                    part = dicts[i : i + chunk]
                    dst.execute(insert(table), part)
        finally:
            dst.execute(text("SET session_replication_role = DEFAULT"))

        for table in meta.sorted_tables:
            if "id" not in table.c:
                continue
            tname = table.name
            if not tname.replace("_", "").isalnum():
                continue
            try:
                dst.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{tname}', 'id'), "
                        f'COALESCE((SELECT MAX(id) FROM "{tname}"), 1), true)'
                    )
                )
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy Project YK SQLite → Postgres")
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=APP_DIR / "app.db",
        help="Path to app.db (default: ProjectYK_System/app/app.db)",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="DROP ALL tables บน Postgres ก่อน (บังคับ — กันซ้ำ)",
    )
    args = parser.parse_args()
    if not args.wipe:
        print("Required: --wipe (drops all app tables on target Postgres before copy).", file=sys.stderr)
        sys.exit(1)

    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        print("Set DATABASE_URL to PostgreSQL connection string.", file=sys.stderr)
        sys.exit(1)
    pg_url = _normalize_pg_url(raw_url)
    if "sqlite" in pg_url.lower():
        print("DATABASE_URL must be PostgreSQL, not sqlite.", file=sys.stderr)
        sys.exit(1)

    if not args.sqlite.exists():
        print(f"SQLite file not found: {args.sqlite}", file=sys.stderr)
        sys.exit(1)

    sqlite_engine = create_engine(f"sqlite:///{args.sqlite}", echo=False)
    pg_engine = create_engine(pg_url, echo=False, pool_pre_ping=True)

    if args.wipe:
        SQLModel.metadata.drop_all(pg_engine)
    SQLModel.metadata.create_all(pg_engine)

    _copy_rows(sqlite_engine, pg_engine)
    print("Done: copied all tables from", args.sqlite, "→ Postgres")


if __name__ == "__main__":
    main()
