"""Shared paths: tools/ lives under ProjectYK_System/tools/."""
from __future__ import annotations

from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
SYSTEM_DIR = TOOLS_DIR.parent
REPO_ROOT = SYSTEM_DIR.parent
APP_DIR = SYSTEM_DIR / "app"

# ข้อมูลธุรกิจ (เงินเดือน / น้ำมัน / บิลลูกค้า) — ย้ายมารวมที่ราก repo ใต้ data/
DATA_DIR = REPO_ROOT / "data"
SALARY_DIR = DATA_DIR / "Salary"
FUEL_DIR = DATA_DIR / "Fuel"
BILLING_DIR = DATA_DIR / "Billing"
