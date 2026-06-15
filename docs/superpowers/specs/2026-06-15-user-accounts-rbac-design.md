# User Accounts + Role-Based Access Control (RBAC) — Design

**Date:** 2026-06-15
**Author:** Claude (brainstormed with โอ)
**Status:** Awaiting review
**Context:** Required before exposing the MVP to the office team on `app.yklogistics.uk`. The team must each have their own login, and not everyone should see payroll/finance data.

---

## Problem

The app currently has only `preview_auth.py` — a **single shared username/password** for the whole system (HTTP Basic). Everyone who logs in sees everything. Before letting the office team use the system (even for a feedback trial), we need:

- Per-person accounts (each user has their own username + password).
- Role-based access: control which menus a user sees and whether they can view vs. edit.
- An admin UI so โอ can add people and set their role/permissions without editing files.
- Users can change their own password; admin can reset a forgotten one.

Money data (payroll, finance) is sensitive — office staff must not see other people's salaries.

---

## Non-goals (YAGNI)

- No dynamic role creation. The 4 roles are fixed in code; admin only assigns a user to a role.
- No per-field permissions (e.g., hiding a single salary column). Control is at menu + action level only.
- No external auth (OAuth/SSO). Local username/password only.
- No DB-backed session table. Sessions are signed cookies.

These can be added later if the team asks after the trial.

---

## Design

### 1. Data model

New table `AppUser` — separate from `Employee` (which is a payroll subject, not a system login).

```
AppUser
  id             int, PK
  username       str, unique, indexed   # login handle
  password_hash  str                    # bcrypt; never store plaintext
  display_name   str                    # shown in UI
  role           str, indexed           # admin | office | accountant | viewer
  status         str = "active"         # active | disabled
  must_change_pw bool = False           # force password change on next login
  created_at     datetime
```

Role → permission mapping lives in **code** (`permissions.py`), not the DB. Four fixed roles, a small menu list — a hard-coded dict is easier to read and edit than a dynamic permissions table. โอ adjusts the matrix later by editing this one file.

Schema change: bump `SCHEMA_VERSION` in `main.py` and add the `AppUser` create/alter block in `lifespan()` (project convention — no Alembic).

### 2. Login & session

- Not logged in → every page redirects to `/login`.
- `/login` (GET form, POST check) → verify password against `password_hash` (bcrypt) → set session cookie.
- `/logout` → clear session.
- Session = **signed cookie** via Starlette `SessionMiddleware` (already in stack — no new dependency). Stores `user_id` + `role` only. No DB session table.
- Secret key for signing comes from env var (`YK_SESSION_SECRET`) on Server — not hard-coded, not committed.

Guards:
- `must_change_pw=True` → all pages redirect to `/account/password` until changed (prevents admin-set temp passwords lingering).
- `status=disabled` → login refused immediately (disable a person without deleting their account).

Existing `preview_auth.py` is **kept as a fallback**, controlled by its existing env var, default off once the new login works. Surgical: not deleted up front.

### 3. Permission enforcement (2 layers)

**Layer A — menu (see / don't see):** by URL prefix.
**Layer B — action (view vs edit):** GET = view; POST/PUT/DELETE = edit.

Default matrix (โอ edits later in `permissions.py`):

| Menu (prefix)                   | Admin | Office  | Accountant | Viewer  |
|---------------------------------|-------|---------|------------|---------|
| Daily `/daily`                  | edit  | edit    | view       | view    |
| Billing (under daily/customer)  | edit  | edit    | view       | view    |
| Petty `/petty-cash`             | edit  | edit    | view       | view    |
| Payroll `/payroll`              | edit  | hidden  | edit       | hidden  |
| Finance `/finance`              | edit  | hidden  | view       | hidden  |
| Maintenance `/maint`            | edit  | edit    | view       | view    |
| Master `/employees` `/vehicles` | edit  | view    | view       | view    |
| Admin `/admin/users`            | edit  | hidden  | hidden     | hidden  |

Rationale: payroll + finance are the most sensitive → office/viewer can't see them; accountant can (they do the money); admin sees all.

Implementation (surgical, not per-route edits):
- One middleware checks prefix + method against the matrix → 403 if not allowed.
- Templates hide links/buttons the user lacks permission for (no dead buttons).
- Routes that don't fit a clean prefix (e.g. billing nested under `/daily` or customer) are mapped explicitly in `permissions.py` based on the real routes in `main.py` — not guessed. Unmapped routes default to admin-only and are flagged for โอ.

### 4. Admin UI

`/admin/users` (admin only):
- Table of all users — username, display name, role, status.
- Add user — username + name + role + temp password (`must_change_pw=True` auto-set).
- Edit user — change role, disable/enable, reset password.
- Delete = soft delete (set `disabled`); never hard-delete, keep history.

`/account/password` (any logged-in user): change own password (old + new).

### 5. First-run seed

On first deploy, create one admin user `yk1` with a temp password and `must_change_pw=True`. โอ logs in, changes the password, then adds the team via the admin UI. During the trial, usernames are sequential: `yk1`, `yk2`, `yk3`, … (real names can come later).

---

## Affected files

- `models.py` — add `AppUser`.
- `main.py` — bump `SCHEMA_VERSION`, lifespan migration, wire session + RBAC middleware, login/logout/admin/account routes.
- `permissions.py` (new) — role→permission matrix + prefix map.
- `auth.py` (new) — bcrypt hash/verify, session helpers, current-user dependency.
- `templates/` — `login.html`, `admin_users.html`, `account_password.html`; menu partial hides unauthorized links.
- `preview_auth.py` — unchanged, kept as fallback.

## Verification

- Unit: bcrypt hash/verify; matrix lookup returns expected allow/deny per role+prefix+method.
- Integration (TestClient): each role logs in → allowed pages 200, forbidden pages 403/redirect; office cannot reach `/payroll` or `/finance`; non-admin cannot reach `/admin/users`; `must_change_pw` forces redirect; disabled user can't log in.
- Manual: โอ first-run flow (temp pw → change → add a teammate → that teammate sees only their menus).

## Rollback

RBAC is additive (new table + middleware). To disable: set the new auth off and re-enable `preview_auth` env var. `AppUser` table is harmless if unused.
