"""Scripts ใต้ ProjectYK_System/dev_scripts/ — ชี้ไปที่ app/ เดียวกับแอปหลัก."""
from __future__ import annotations

from pathlib import Path

DEV_DIR = Path(__file__).resolve().parent
SYSTEM_DIR = DEV_DIR.parent
APP_DIR = SYSTEM_DIR / "app"
REPO_ROOT = SYSTEM_DIR.parent
DATA_DIR = REPO_ROOT / "data"
SALARY_DIR = DATA_DIR / "Salary"
