# User Accounts + RBAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-user login accounts with role-based access (admin/office/accountant/viewer), an admin UI to manage users, and self-service password change — so the office team can each have their own login before the MVP trial on `app.yklogistics.uk`.

**Architecture:** New `AppUser` SQLModel table (separate from `Employee`). Passwords hashed with bcrypt. Sessions are signed cookies via Starlette `SessionMiddleware`. A single RBAC middleware enforces a code-defined permission matrix (`permissions.py`) by URL-prefix + HTTP method. Auth helpers live in `auth.py`. Existing `preview_auth.py` stays as a fallback.

**Tech Stack:** FastAPI + SQLModel + SQLite, Starlette SessionMiddleware, bcrypt, itsdangerous, pytest + TestClient. All work in `ProjectYK_System/app/`.

---

## File Structure

- `ProjectYK_System/app/auth.py` (new) — bcrypt hash/verify, `current_user` dependency, session get/set/clear helpers.
- `ProjectYK_System/app/permissions.py` (new) — role list, prefix→menu map, permission matrix, `check(role, path, method) -> "edit"|"view"|"deny"`.
- `ProjectYK_System/app/models.py` (modify) — add `AppUser`.
- `ProjectYK_System/app/main.py` (modify) — bump SCHEMA_VERSION, lifespan migration + seed `yk1`, add SessionMiddleware + RBAC middleware, login/logout/admin/account routes.
- `ProjectYK_System/app/templates/login.html`, `admin_users.html`, `account_password.html` (new); menu partial hides unauthorized links.
- `ProjectYK_System/app/requirements.txt` (modify) — add `bcrypt`, `itsdangerous`.
- `ProjectYK_System/app/conftest.py` (new) — pytest fixtures (temp DB + TestClient).
- `ProjectYK_System/app/tests/` (new) — test modules.

**Convention notes for the engineer:**
- No Alembic. Schema changes bump `SCHEMA_VERSION` in `main.py` and add an `ALTER/CREATE` block in `lifespan()`.
- Config via `os.environ.get("YK_...")`. Session secret = `YK_SESSION_SECRET`.
- Run python as `.venv/Scripts/python.exe` from `ProjectYK_System/app/`. Run pytest as `.venv/Scripts/python.exe -m pytest`.

---

## Task 1: Add deps + test harness

**Files:**
- Modify: `ProjectYK_System/app/requirements.txt`
- Create: `ProjectYK_System/app/conftest.py`
- Create: `ProjectYK_System/app/tests/__init__.py`
- Create: `ProjectYK_System/app/tests/test_harness.py`

- [ ] **Step 1: Add deps to requirements.txt**

Append these two lines:

```
bcrypt>=4.1,<5
itsdangerous>=2.1,<3
```

- [ ] **Step 2: Install**

Run: `.venv/Scripts/python.exe -m pip install "bcrypt>=4.1,<5" "itsdangerous>=2.1,<3"`
Expected: installs successfully; `bcrypt` and `itsdangerous` importable.

- [ ] **Step 3: Write conftest.py (temp DB + client fixtures)**

```python
import os
import tempfile
import pytest

# Force a throwaway SQLite DB BEFORE importing the app/db modules.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "test-secret-key-not-for-prod"

from starlette.testclient import TestClient  # noqa: E402
import main as appmod  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(appmod.app) as c:
        yield c
```

- [ ] **Step 4: Write a smoke test**

`tests/test_harness.py`:

```python
def test_app_boots(client):
    r = client.get("/login")
    assert r.status_code in (200, 404)  # route added later; harness just confirms boot
```

`tests/__init__.py`: empty file.

- [ ] **Step 5: Run it**

Run: `.venv/Scripts/python.exe -m pytest tests/test_harness.py -v`
Expected: PASS (app boots against temp DB).

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/requirements.txt ProjectYK_System/app/conftest.py ProjectYK_System/app/tests/
git commit -m "test(rbac): add bcrypt/itsdangerous deps + pytest harness"
```

---

## Task 2: Password hashing (auth.py)

**Files:**
- Create: `ProjectYK_System/app/auth.py`
- Create: `ProjectYK_System/app/tests/test_auth_hash.py`

- [ ] **Step 1: Write failing test**

`tests/test_auth_hash.py`:

```python
from auth import hash_password, verify_password

def test_hash_then_verify_true():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h) is True

def test_verify_wrong_password_false():
    h = hash_password("s3cret")
    assert verify_password("nope", h) is False
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_hash.py -v`
Expected: FAIL (`No module named 'auth'`).

- [ ] **Step 3: Implement hash/verify in auth.py**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_auth_hash.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/auth.py ProjectYK_System/app/tests/test_auth_hash.py
git commit -m "feat(rbac): bcrypt password hash/verify helpers"
```

---

## Task 3: Permission matrix (permissions.py)

**Files:**
- Create: `ProjectYK_System/app/permissions.py`
- Create: `ProjectYK_System/app/tests/test_permissions.py`

- [ ] **Step 1: Write failing test**

`tests/test_permissions.py`:

```python
from permissions import check, ROLES

def test_roles_are_the_four_expected():
    assert ROLES == ["admin", "office", "accountant", "viewer"]

def test_admin_can_edit_everything():
    assert check("admin", "/payroll", "POST") == "edit"
    assert check("admin", "/admin/users", "GET") == "edit"

def test_office_cannot_see_payroll_or_finance():
    assert check("office", "/payroll", "GET") == "deny"
    assert check("office", "/finance", "GET") == "deny"

def test_office_can_edit_daily_but_only_view_master():
    assert check("office", "/daily/new", "POST") == "edit"
    assert check("office", "/employees", "GET") == "view"
    assert check("office", "/employees/5/edit", "POST") == "deny"  # view-only -> edit denied

def test_accountant_sees_payroll_edit_finance_view():
    assert check("accountant", "/payroll", "POST") == "edit"
    assert check("accountant", "/finance", "GET") == "view"
    assert check("accountant", "/finance", "POST") == "deny"

def test_viewer_view_only_and_no_money_menus():
    assert check("viewer", "/daily", "GET") == "view"
    assert check("viewer", "/daily/new", "POST") == "deny"
    assert check("viewer", "/payroll", "GET") == "deny"

def test_only_admin_reaches_admin_users():
    assert check("office", "/admin/users", "GET") == "deny"
    assert check("accountant", "/admin/users", "GET") == "deny"

def test_unmapped_prefix_defaults_admin_only():
    assert check("office", "/something-new", "GET") == "deny"
    assert check("admin", "/something-new", "GET") == "edit"
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_permissions.py -v`
Expected: FAIL (`No module named 'permissions'`).

- [ ] **Step 3: Implement permissions.py**

```python
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
# Order matters: longest/most-specific prefixes first within MENU_PREFIXES lookup.
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
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_permissions.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/permissions.py ProjectYK_System/app/tests/test_permissions.py
git commit -m "feat(rbac): role permission matrix (prefix + method)"
```

---

## Task 4: AppUser model + migration + seed yk1

**Files:**
- Modify: `ProjectYK_System/app/models.py`
- Modify: `ProjectYK_System/app/main.py` (SCHEMA_VERSION + lifespan)
- Create: `ProjectYK_System/app/tests/test_appuser_seed.py`

- [ ] **Step 1: Write failing test**

`tests/test_appuser_seed.py`:

```python
from sqlmodel import Session, select
from db_config import engine
from models import AppUser

def test_yk1_admin_seeded_on_boot(client):
    # client fixture booted the app -> lifespan ran -> yk1 created
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
    assert u is not None
    assert u.role == "admin"
    assert u.must_change_pw is True
    assert u.password_hash and u.password_hash != ""
```

Note: confirm the engine import path — `db_config.py` exposes `engine`. If the symbol differs, use the project's actual session helper (check `db_config.py`).

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_appuser_seed.py -v`
Expected: FAIL (`cannot import name 'AppUser'`).

- [ ] **Step 3: Add AppUser to models.py**

Add near the other table classes:

```python
class AppUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    display_name: str = ""
    role: str = Field(default="viewer", index=True)   # admin|office|accountant|viewer
    status: str = Field(default="active", index=True)  # active|disabled
    must_change_pw: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

Verify `datetime` and `Optional` are already imported at the top of `models.py` (they are used by other models). If not, add `from datetime import datetime`.

- [ ] **Step 4: Bump SCHEMA_VERSION + seed in lifespan (main.py)**

Find `SCHEMA_VERSION = 18` and change to `SCHEMA_VERSION = 19`.

In `lifespan()`, after tables are created (where other migrations run), add a seed block. `SQLModel.metadata.create_all` already creates the new table; this block only seeds yk1:

```python
# v19: seed first admin account (yk1) for the RBAC trial.
from models import AppUser
from auth import hash_password
with Session(engine) as s:
    exists = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
    if not exists:
        temp_pw = os.environ.get("YK_ADMIN_TEMP_PW", "changeme1")
        s.add(AppUser(
            username="yk1",
            password_hash=hash_password(temp_pw),
            display_name="โอ (admin)",
            role="admin",
            status="active",
            must_change_pw=True,
        ))
        s.commit()
        print("[seed] created admin user yk1 (must change password on first login)")
```

Confirm `Session`, `select`, `engine`, and `os` are imported in `main.py` (they are used elsewhere). If `engine` is accessed via a helper, match the existing pattern used by other lifespan migrations.

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_appuser_seed.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_appuser_seed.py
git commit -m "feat(rbac): AppUser table + seed yk1 admin (SCHEMA_VERSION 19)"
```

---

## Task 5: Session helpers + login/logout routes

**Files:**
- Modify: `ProjectYK_System/app/auth.py`
- Modify: `ProjectYK_System/app/main.py` (add SessionMiddleware + routes)
- Create: `ProjectYK_System/app/templates/login.html`
- Create: `ProjectYK_System/app/tests/test_login.py`

- [ ] **Step 1: Write failing test**

`tests/test_login.py`:

```python
def test_login_page_renders(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "username" in r.text.lower()

def test_login_success_sets_session_and_redirects(client):
    r = client.post("/login", data={"username": "yk1", "password": "changeme1"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    # must_change_pw -> redirect target is the password page
    assert "/account/password" in r.headers.get("location", "")

def test_login_wrong_password_rejected(client):
    r = client.post("/login", data={"username": "yk1", "password": "WRONG"},
                    follow_redirects=False)
    assert r.status_code in (200, 401)
    assert "/daily" not in r.headers.get("location", "")

def test_logout_clears_session(client):
    client.post("/login", data={"username": "yk1", "password": "changeme1"})
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_login.py -v`
Expected: FAIL (no `/login` route).

- [ ] **Step 3: Add session helpers to auth.py**

Append:

```python
from sqlmodel import Session, select
from db_config import engine
from models import AppUser


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
```

Match the `engine` import to `db_config.py`'s actual export.

- [ ] **Step 4: Wire SessionMiddleware + login/logout in main.py**

Add the middleware (note: add AFTER `PreviewAuthMiddleware` line so session is outermost; Starlette applies last-added first):

```python
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("YK_SESSION_SECRET", "dev-insecure-secret-change-me"),
    same_site="lax",
    https_only=False,
)
```

Add routes (place with other routes):

```python
from fastapi import Form
from auth import (verify_password, login_session, logout_session,
                  get_user_by_username, current_user)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    u = get_user_by_username(username.strip())
    if u is None or u.status != "active" or not verify_password(password, u.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"},
            status_code=401,
        )
    login_session(request, u)
    dest = "/account/password" if u.must_change_pw else "/daily"
    return RedirectResponse(dest, status_code=303)

@app.get("/logout")
async def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=303)
```

Confirm `Request`, `RedirectResponse`, `HTMLResponse`, `templates` are already imported/defined in `main.py` (they are — used by existing routes).

- [ ] **Step 5: Create login.html**

`templates/login.html` (match existing templates' Tailwind-CDN style; minimal):

```html
<!doctype html>
<html lang="th">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>เข้าสู่ระบบ — Project YK</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
  <form method="post" action="/login" class="bg-white p-8 rounded-xl shadow w-80 space-y-4">
    <h1 class="text-xl font-bold text-center">Project YK</h1>
    {% if error %}<p class="text-red-600 text-sm text-center">{{ error }}</p>{% endif %}
    <input name="username" placeholder="ชื่อผู้ใช้" autofocus
           class="w-full border rounded px-3 py-2" required>
    <input name="password" type="password" placeholder="รหัสผ่าน"
           class="w-full border rounded px-3 py-2" required>
    <button class="w-full bg-blue-600 text-white rounded py-2">เข้าสู่ระบบ</button>
  </form>
</body></html>
```

- [ ] **Step 6: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_login.py -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/auth.py ProjectYK_System/app/main.py ProjectYK_System/app/templates/login.html ProjectYK_System/app/tests/test_login.py
git commit -m "feat(rbac): session middleware + login/logout routes"
```

---

## Task 6: RBAC + auth-required middleware

**Files:**
- Modify: `ProjectYK_System/app/main.py`
- Create: `ProjectYK_System/app/tests/test_rbac_middleware.py`

- [ ] **Step 1: Write failing test**

`tests/test_rbac_middleware.py`:

```python
import pytest
from sqlmodel import Session
from db_config import engine
from models import AppUser
from auth import hash_password

def _make_user(username, role):
    with Session(engine) as s:
        if not s.get(AppUser, username):  # id lookup won't match; just add
            pass
        s.add(AppUser(username=username, password_hash=hash_password("pw123456"),
                      display_name=username, role=role, status="active",
                      must_change_pw=False))
        s.commit()

@pytest.fixture()
def office_client(client):
    _make_user("office1", "office")
    client.post("/login", data={"username": "office1", "password": "pw123456"})
    return client

def test_unauthenticated_redirects_to_login(client):
    r = client.get("/daily", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")

def test_office_denied_payroll(office_client):
    r = office_client.get("/payroll", follow_redirects=False)
    assert r.status_code == 403

def test_office_denied_finance(office_client):
    r = office_client.get("/finance", follow_redirects=False)
    assert r.status_code == 403

def test_office_allowed_daily(office_client):
    r = office_client.get("/daily", follow_redirects=False)
    assert r.status_code == 200

def test_office_cannot_post_to_master(office_client):
    # /employees is view-only for office; a write must be blocked
    r = office_client.post("/employees/new", data={}, follow_redirects=False)
    assert r.status_code == 403
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_rbac_middleware.py -v`
Expected: FAIL (no RBAC yet — `/daily` returns 200 even unauthenticated, payroll not 403).

- [ ] **Step 3: Add RBAC middleware to main.py**

Add a `@app.middleware("http")` function. Place it so it runs for all routes. Public paths bypass it.

```python
from permissions import check as perm_check

PUBLIC_PREFIXES = ("/login", "/logout", "/static/", "/uploads/", "/health")

@app.middleware("http")
async def rbac_middleware(request: Request, call_next):
    path = request.url.path
    if path == "/" or any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)
    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    # Force password change before anything else.
    if user.must_change_pw and not path.startswith("/account/password"):
        return RedirectResponse("/account/password", status_code=303)
    # /account/* is allowed for any logged-in user (own settings).
    if path.startswith("/account/"):
        return await call_next(request)
    decision = perm_check(user.role, path, request.method)
    if decision == "deny":
        return Response("ไม่มีสิทธิ์เข้าถึงส่วนนี้", status_code=403,
                        media_type="text/plain; charset=utf-8")
    return await call_next(request)
```

Confirm `Response` is imported in `main.py` (add `from starlette.responses import Response` if absent).

Note on ordering: this `@app.middleware("http")` and `SessionMiddleware` — Starlette runs the SessionMiddleware first (it must, to populate `request.session`). `@app.middleware` decorators are added to the same stack; since SessionMiddleware was added via `add_middleware`, ensure the decorator-based rbac runs INSIDE it. In practice FastAPI's `@app.middleware("http")` wraps as the innermost user middleware and session is available. Verify with the unauthenticated test: if `request.session` raises, move SessionMiddleware to be added last.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_rbac_middleware.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Run full suite (no regressions)**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_rbac_middleware.py
git commit -m "feat(rbac): enforce auth + permission matrix via middleware"
```

---

## Task 7: Self-service password change

**Files:**
- Modify: `ProjectYK_System/app/main.py`
- Create: `ProjectYK_System/app/templates/account_password.html`
- Create: `ProjectYK_System/app/tests/test_password_change.py`

- [ ] **Step 1: Write failing test**

`tests/test_password_change.py`:

```python
def test_change_password_clears_must_change_and_works(client):
    client.post("/login", data={"username": "yk1", "password": "changeme1"})
    r = client.post("/account/password",
                    data={"old_password": "changeme1",
                          "new_password": "newpass123",
                          "confirm": "newpass123"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    # old password no longer works
    client.get("/logout")
    bad = client.post("/login", data={"username": "yk1", "password": "changeme1"},
                      follow_redirects=False)
    assert bad.status_code == 401
    # new password works and no longer forces change
    ok = client.post("/login", data={"username": "yk1", "password": "newpass123"},
                     follow_redirects=False)
    assert "/account/password" not in ok.headers.get("location", "")

def test_change_password_mismatch_rejected(client):
    client.post("/login", data={"username": "yk1", "password": "changeme1"})
    r = client.post("/account/password",
                    data={"old_password": "changeme1",
                          "new_password": "aaaaaa11",
                          "confirm": "bbbbbb22"},
                    follow_redirects=False)
    assert r.status_code in (200, 400)
```

(This test assumes a fresh DB so yk1 temp pw is `changeme1`. conftest uses a temp DB per session.)

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_password_change.py -v`
Expected: FAIL (no `/account/password` route).

- [ ] **Step 3: Implement routes in main.py**

```python
from auth import hash_password

@app.get("/account/password", response_class=HTMLResponse)
async def password_page(request: Request):
    u = current_user(request)
    return templates.TemplateResponse("account_password.html",
                                      {"request": request, "error": None, "user": u})

@app.post("/account/password")
async def password_submit(request: Request,
                          old_password: str = Form(...),
                          new_password: str = Form(...),
                          confirm: str = Form(...)):
    u = current_user(request)
    def fail(msg):
        return templates.TemplateResponse(
            "account_password.html",
            {"request": request, "error": msg, "user": u}, status_code=400)
    if not verify_password(old_password, u.password_hash):
        return fail("รหัสผ่านเดิมไม่ถูกต้อง")
    if new_password != confirm:
        return fail("รหัสผ่านใหม่ไม่ตรงกัน")
    if len(new_password) < 8:
        return fail("รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัวอักษร")
    with Session(engine) as s:
        db_u = s.get(AppUser, u.id)
        db_u.password_hash = hash_password(new_password)
        db_u.must_change_pw = False
        s.add(db_u)
        s.commit()
    return RedirectResponse("/daily", status_code=303)
```

Confirm `AppUser`, `Session`, `engine`, `select` are imported in `main.py`.

- [ ] **Step 4: Create account_password.html**

```html
<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>เปลี่ยนรหัสผ่าน</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
  <form method="post" action="/account/password"
        class="bg-white p-8 rounded-xl shadow w-80 space-y-4">
    <h1 class="text-lg font-bold text-center">เปลี่ยนรหัสผ่าน</h1>
    {% if error %}<p class="text-red-600 text-sm text-center">{{ error }}</p>{% endif %}
    <input name="old_password" type="password" placeholder="รหัสผ่านเดิม"
           class="w-full border rounded px-3 py-2" required>
    <input name="new_password" type="password" placeholder="รหัสผ่านใหม่ (≥8 ตัว)"
           class="w-full border rounded px-3 py-2" required>
    <input name="confirm" type="password" placeholder="ยืนยันรหัสใหม่"
           class="w-full border rounded px-3 py-2" required>
    <button class="w-full bg-blue-600 text-white rounded py-2">บันทึก</button>
  </form>
</body></html>
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_password_change.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/account_password.html ProjectYK_System/app/tests/test_password_change.py
git commit -m "feat(rbac): self-service password change + clears must_change_pw"
```

---

## Task 8: Admin user management UI

**Files:**
- Modify: `ProjectYK_System/app/main.py`
- Create: `ProjectYK_System/app/templates/admin_users.html`
- Create: `ProjectYK_System/app/tests/test_admin_users.py`

- [ ] **Step 1: Write failing test**

`tests/test_admin_users.py`:

```python
import pytest
from sqlmodel import Session
from db_config import engine
from models import AppUser
from auth import hash_password

def _login_admin(client):
    # yk1 is admin but must_change_pw -> change it first to get past the gate
    client.post("/login", data={"username": "yk1", "password": "changeme1"})
    client.post("/account/password",
                data={"old_password": "changeme1", "new_password": "adminpass1",
                      "confirm": "adminpass1"})
    return client

def test_admin_can_list_users(client):
    _login_admin(client)
    r = client.get("/admin/users")
    assert r.status_code == 200
    assert "yk1" in r.text

def test_admin_can_create_user(client):
    _login_admin(client)
    r = client.post("/admin/users/new",
                    data={"username": "yk2", "display_name": "Tester 2",
                          "role": "office", "temp_password": "temp1234"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        from sqlmodel import select
        u = s.exec(select(AppUser).where(AppUser.username == "yk2")).first()
    assert u is not None and u.role == "office" and u.must_change_pw is True

def test_non_admin_cannot_reach_admin_users(client):
    with Session(engine) as s:
        s.add(AppUser(username="off2", password_hash=hash_password("pw123456"),
                      display_name="off2", role="office", status="active",
                      must_change_pw=False))
        s.commit()
    client.post("/login", data={"username": "off2", "password": "pw123456"})
    r = client.get("/admin/users", follow_redirects=False)
    assert r.status_code == 403

def test_admin_can_disable_user(client):
    _login_admin(client)
    client.post("/admin/users/new",
                data={"username": "yk3", "display_name": "T3",
                      "role": "viewer", "temp_password": "temp1234"})
    with Session(engine) as s:
        from sqlmodel import select
        uid = s.exec(select(AppUser).where(AppUser.username == "yk3")).first().id
    r = client.post(f"/admin/users/{uid}/disable", follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        assert s.get(AppUser, uid).status == "disabled"
```

- [ ] **Step 2: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_admin_users.py -v`
Expected: FAIL (no admin routes).

- [ ] **Step 3: Implement admin routes in main.py**

```python
from permissions import ROLES

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_list(request: Request):
    with Session(engine) as s:
        users = s.exec(select(AppUser).order_by(AppUser.username)).all()
    return templates.TemplateResponse("admin_users.html",
                                      {"request": request, "users": users, "roles": ROLES})

@app.post("/admin/users/new")
async def admin_users_create(request: Request,
                             username: str = Form(...),
                             display_name: str = Form(""),
                             role: str = Form(...),
                             temp_password: str = Form(...)):
    if role not in ROLES:
        role = "viewer"
    with Session(engine) as s:
        exists = s.exec(select(AppUser).where(AppUser.username == username.strip())).first()
        if not exists:
            s.add(AppUser(username=username.strip(),
                          password_hash=hash_password(temp_password),
                          display_name=display_name.strip(), role=role,
                          status="active", must_change_pw=True))
            s.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/disable")
async def admin_users_disable(request: Request, user_id: int):
    with Session(engine) as s:
        u = s.get(AppUser, user_id)
        if u and u.username != "yk1":   # never disable the seed admin
            u.status = "disabled"
            s.add(u); s.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/enable")
async def admin_users_enable(request: Request, user_id: int):
    with Session(engine) as s:
        u = s.get(AppUser, user_id)
        if u:
            u.status = "active"; s.add(u); s.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/users/{user_id}/reset")
async def admin_users_reset(request: Request, user_id: int, temp_password: str = Form(...)):
    with Session(engine) as s:
        u = s.get(AppUser, user_id)
        if u:
            u.password_hash = hash_password(temp_password)
            u.must_change_pw = True
            s.add(u); s.commit()
    return RedirectResponse("/admin/users", status_code=303)
```

- [ ] **Step 4: Create admin_users.html**

```html
<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>จัดการผู้ใช้</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-100 p-6">
  <div class="max-w-3xl mx-auto space-y-6">
    <h1 class="text-xl font-bold">จัดการผู้ใช้</h1>
    <table class="w-full bg-white rounded shadow text-sm">
      <thead class="bg-gray-200"><tr>
        <th class="p-2 text-left">username</th><th class="p-2 text-left">ชื่อ</th>
        <th class="p-2 text-left">role</th><th class="p-2 text-left">สถานะ</th>
        <th class="p-2"></th></tr></thead>
      <tbody>
      {% for u in users %}
        <tr class="border-t">
          <td class="p-2">{{ u.username }}</td><td class="p-2">{{ u.display_name }}</td>
          <td class="p-2">{{ u.role }}</td><td class="p-2">{{ u.status }}</td>
          <td class="p-2 text-right">
            {% if u.username != 'yk1' %}
            {% if u.status == 'active' %}
              <form method="post" action="/admin/users/{{ u.id }}/disable" class="inline">
                <button class="text-red-600">ปิด</button></form>
            {% else %}
              <form method="post" action="/admin/users/{{ u.id }}/enable" class="inline">
                <button class="text-green-600">เปิด</button></form>
            {% endif %}
            {% endif %}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>

    <form method="post" action="/admin/users/new"
          class="bg-white p-4 rounded shadow grid grid-cols-2 gap-3">
      <h2 class="col-span-2 font-semibold">เพิ่มผู้ใช้</h2>
      <input name="username" placeholder="username (เช่น yk2)" class="border rounded px-2 py-1" required>
      <input name="display_name" placeholder="ชื่อแสดง" class="border rounded px-2 py-1">
      <select name="role" class="border rounded px-2 py-1">
        {% for r in roles %}<option value="{{ r }}">{{ r }}</option>{% endfor %}
      </select>
      <input name="temp_password" placeholder="รหัสชั่วคราว" class="border rounded px-2 py-1" required>
      <button class="col-span-2 bg-blue-600 text-white rounded py-2">เพิ่ม</button>
    </form>
  </div>
</body></html>
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_admin_users.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Run full suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/admin_users.html ProjectYK_System/app/tests/test_admin_users.py
git commit -m "feat(rbac): admin user management UI (create/disable/enable/reset)"
```

---

## Task 9: Hide unauthorized menu links + manual smoke

**Files:**
- Modify: the shared nav/menu template (locate via `grep -rl "/payroll" ProjectYK_System/app/templates/`)
- Create: `ProjectYK_System/app/tests/test_menu_visibility.py`

- [ ] **Step 1: Locate the nav partial**

Run: `grep -rln 'href="/payroll"' ProjectYK_System/app/templates/`
Note the file (likely a base/layout template). This is the nav to edit.

- [ ] **Step 2: Write failing test**

`tests/test_menu_visibility.py`:

```python
import pytest
from sqlmodel import Session
from db_config import engine
from models import AppUser
from auth import hash_password

@pytest.fixture()
def office_client(client):
    with Session(engine) as s:
        s.add(AppUser(username="offm", password_hash=hash_password("pw123456"),
                      display_name="offm", role="office", status="active",
                      must_change_pw=False))
        s.commit()
    client.post("/login", data={"username": "offm", "password": "pw123456"})
    return client

def test_office_nav_hides_payroll_and_finance(office_client):
    r = office_client.get("/daily")
    assert r.status_code == 200
    assert 'href="/payroll"' not in r.text
    assert 'href="/finance"' not in r.text
```

- [ ] **Step 3: Run to verify fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_menu_visibility.py -v`
Expected: FAIL (links still present for office).

- [ ] **Step 4: Make current user + permission helper available to templates**

In `main.py`, add a small context helper used when rendering nav. Simplest: a Jinja global that the template calls. Add after `templates` is defined:

```python
from permissions import check as perm_check

def _can_see(request, prefix):
    u = current_user(request)
    if u is None:
        return False
    return perm_check(u.role, prefix, "GET") != "deny"

templates.env.globals["can_see"] = _can_see
```

- [ ] **Step 5: Guard nav links in the located template**

For each money/admin menu link in the nav partial, wrap it. Example for payroll/finance/admin:

```html
{% if can_see(request, "/payroll") %}
  <a href="/payroll" class="...">เงินเดือน</a>
{% endif %}
{% if can_see(request, "/finance") %}
  <a href="/finance" class="...">การเงิน</a>
{% endif %}
{% if can_see(request, "/admin/users") %}
  <a href="/admin/users" class="...">จัดการผู้ใช้</a>
{% endif %}
```

Confirm the template receives `request` in its context (FastAPI `TemplateResponse` always passes `request`). Apply the same `{% if can_see(...) %}` wrap to every nav link so each role sees only its menus.

- [ ] **Step 6: Run to verify pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_menu_visibility.py -v`
Expected: PASS.

- [ ] **Step 7: Full suite + manual smoke**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: all PASS.

Manual smoke (real server): set `YK_SESSION_SECRET=devsecret`, start app, browse `http://127.0.0.1:8010` → redirected to `/login` → login `yk1`/`changeme1` → forced to change password → set new → land on `/daily` → add `yk2` (office) via `/admin/users` → log out → log in as `yk2` → confirm no payroll/finance menu and `/payroll` returns 403.

- [ ] **Step 8: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/ ProjectYK_System/app/tests/test_menu_visibility.py
git commit -m "feat(rbac): hide unauthorized nav links per role"
```

---

## Self-Review Notes

- **Spec coverage:** Data model (T4), login/session (T5), RBAC enforcement (T6), admin UI (T8), self-service password (T7), nav hiding (T9), first-run seed yk1 (T4), fallback preview_auth (untouched — kept by not removing it). All spec sections map to a task.
- **Open verification points flagged for the engineer (not placeholders — real checks):** exact `engine` export name in `db_config.py`; SessionMiddleware vs `@app.middleware` ordering (test `test_unauthenticated_redirects_to_login` catches it); the nav partial filename (located by grep in T9).
- **Type consistency:** `check()` signature `(role, path, method) -> str` used identically in T3/T6/T9. `AppUser` fields consistent across T4–T8. `hash_password`/`verify_password` consistent T2/T5/T7/T8.
- **YAGNI:** no DB session table, no dynamic roles, no per-field perms — matches spec non-goals.
