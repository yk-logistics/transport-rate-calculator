"""Role-based permission matrix. Edit MENUS / MATRIX to adjust who sees what.

check(role, path, method) -> "edit" | "view" | "deny"
- "edit": full access (GET + write methods)
- "view": GET allowed, write methods (POST/PUT/PATCH/DELETE) denied
- "deny": no access at all
"""
from __future__ import annotations

ROLES = ["admin", "office", "accountant", "viewer"]

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Logical menu key -> list of URL prefixes that belong to it.
# /api/* endpoints are mapped to the menu they serve so AJAX calls inherit the
# same permission as the page that makes them.
MENUS = {
    "daily": ["/daily", "/api/daily", "/api/daily-jobs", "/api/cycle-tag"],
    "petty": ["/petty-cash", "/petty/review", "/api/petty"],
    "payroll": ["/payroll"],
    "finance": ["/finance"],
    "maint": ["/maint"],
    "master": ["/employees", "/vehicles"],
    "billing": ["/billing"],
    "rates": ["/rates", "/api/rates"],
    "customers": ["/customers"],
    "fuel": ["/fuel", "/fuel-index", "/fuel-surcharge", "/api/fuel"],
    "dispatch": ["/dispatch", "/ops/lcb-fuel-dispatch"],
    "email": ["/email"],
    "import": ["/import"],
    "admin": ["/admin"],
    # KB จ่ายคืนเจ้าของงาน = ข้อมูลลับ — เฉพาะ admin
    "kb": ["/kb-payout"],
    # สมุดโน้ตส่วนตัว (ของใครของมัน แยกด้วย username) — ทุก role ใช้ได้
    "todo": ["/todo"],
    # เครื่องคิดราคา + รายงาน Oatside (มีต้นทุน/เรทภายใน) — admin ก่อน รอโอสั่งขยาย
    "quote": ["/quote", "/oatside"],
    # คลังแชทไลน์ (อ่านย้อนหลัง/ค้นหา) — ออฟฟิศ/บัญชีดูได้ (ใช้หาหลักฐานงาน)
    "line": ["/line"],
}

# menu -> role -> "edit" | "view" | "deny"
MATRIX = {
    "daily":     {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "petty":     {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "payroll":   {"admin": "edit", "office": "deny", "accountant": "edit", "viewer": "deny"},
    "finance":   {"admin": "edit", "office": "deny", "accountant": "view", "viewer": "deny"},
    "maint":     {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "master":    {"admin": "edit", "office": "view", "accountant": "view", "viewer": "view"},
    "billing":   {"admin": "edit", "office": "edit", "accountant": "edit", "viewer": "view"},
    "rates":     {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "customers": {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "fuel":      {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "dispatch":  {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "email":     {"admin": "edit", "office": "deny", "accountant": "view", "viewer": "deny"},
    "import":    {"admin": "edit", "office": "deny", "accountant": "deny", "viewer": "deny"},
    "admin":     {"admin": "edit", "office": "deny", "accountant": "deny", "viewer": "deny"},
    "kb":        {"admin": "edit", "office": "deny", "accountant": "deny", "viewer": "deny"},
    "todo":      {"admin": "edit", "office": "edit", "accountant": "edit", "viewer": "edit"},
    "quote":     {"admin": "edit", "office": "deny", "accountant": "deny", "viewer": "deny"},
    "line":      {"admin": "edit", "office": "view", "accountant": "view", "viewer": "deny"},
}


def _menu_for_path(path: str) -> str | None:
    best = None
    best_len = -1
    for menu, prefixes in MENUS.items():
        for p in prefixes:
            if (path == p or path.startswith(p + "/")) and len(p) > best_len:
                best, best_len = menu, len(p)
    return best


def check(role: str, path: str, method: str) -> str:
    menu = _menu_for_path(path)
    if menu is None:
        # Unmapped route -> admin-only (fail closed). Flag to โอ if a real menu lands here.
        return "edit" if role == "admin" else "deny"
    level = MATRIX.get(menu, {}).get(role, "deny")
    if level == "deny":
        return "deny"
    if level == "view" and method.upper() in WRITE_METHODS:
        return "deny"
    return level
