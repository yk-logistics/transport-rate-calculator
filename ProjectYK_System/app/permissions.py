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
MENUS = {
    "daily": ["/daily"],
    "petty": ["/petty-cash"],
    "payroll": ["/payroll"],
    "finance": ["/finance"],
    "maint": ["/maint"],
    "master": ["/employees", "/vehicles"],
    "admin": ["/admin"],
}

# menu -> role -> "edit" | "view" | "deny"
MATRIX = {
    "daily":   {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "petty":   {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "payroll": {"admin": "edit", "office": "deny", "accountant": "edit", "viewer": "deny"},
    "finance": {"admin": "edit", "office": "deny", "accountant": "view", "viewer": "deny"},
    "maint":   {"admin": "edit", "office": "edit", "accountant": "view", "viewer": "view"},
    "master":  {"admin": "edit", "office": "view", "accountant": "view", "viewer": "view"},
    "admin":   {"admin": "edit", "office": "deny", "accountant": "deny", "viewer": "deny"},
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
