---
name: reference-mvp-server-deploy
description: "How the Project YK MVP runs on the YK server at app.yklogistics.uk (copy-folder deploy, unattended boot tasks, RBAC login)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 704dfda8-34fa-45ec-8373-e1f382092740
---

The Project YK MVP is deployed to the YK server (Tailscale `100.97.150.114`, user `yklog`) and served at **https://app.yklogistics.uk** for the office-team trial (started 2026-06-15).

- **Code + venv:** `C:\Users\yklog\YK_MVP\app\` — Python **3.12** venv (3.14 was too new for pinned deps). **No git on server** → copy-folder deploy via `ProjectYK_System/tools/deploy_mvp_to_server.sh` from Dev.
- **DB:** `YK_MVP\app\app.db` lives ONLY on server, created fresh on first boot (seeds admin **yk1** / temp pw `changeme1`). Never copied from Dev. Daily backup task `YK_MVP_DB_BACKUP` → `YK_MVP\backups\app-YYYYMMDD.db` (keep 14).
- **Runs unattended** (before login, survives reboot) via 3 SYSTEM `-AtStartup` scheduled tasks: `YK_MVP_APP` (app on 127.0.0.1:8010), `YK_CLOUDFLARED_TUNNEL` (the yk-line tunnel), plus pre-existing `YK_LINE_HEALTHPOLL`. Tailscale set `--unattended` → SSH works without PIN after reboot.
- **Tunnel:** one shared `yk-line` cloudflared tunnel. ingress `app.yklogistics.uk→8010` (MVP) + `line.yklogistics.uk→8020` (LINE archiver). Config `C:\Users\yklog\.cloudflared\config.yml` (backup `.bak_before_mvp`). `.com` email domain untouched.
- **Auth = RBAC login** (not preview_auth). Roles admin/office/accountant/viewer; office/viewer can't see payroll/finance. Matrix in `app/permissions.py` — โอ edits to adjust. Session secret in server-only `YK_MVP\start_mvp.bat` (not in git).

**Security (red-team + app hardening 2026-06-15):** XAMPP disabled (Apache/mysql), SSH key-only + port22 scoped to Tailscale/LAN, SMB scoped, Firewall+Defender+UAC on, RDP off, AnyDesk kept (outbound relay). App: bcrypt passwords (admin can't view → reset only), brute-force guard (`login_guard.py`: user lockout + per-IP via CF-Connecting-IP), secure session cookie (Secure/HttpOnly/SameSite=Lax/8h), security headers (HSTS/X-Frame DENY/nosniff/Referrer). Residual: keylogger on user PC (unfixable server-side), cookie-based sessions (no remote kill). `YK_INSECURE_COOKIES=1` only for local http tests. โอ-facing explainer: `docs/SECURITY_FOR_OAT.md`.

**Deploy gotcha:** `Restart-ScheduledTask` does NOT kill the old python (it keeps holding 8010 with stale code) — must Stop-Process the YK_MVP python first. `deploy_mvp_to_server.sh` does this now. Confirmed 28มิ.ย.: the MVP runs under GLOBAL python `C:\Users\yklog\AppData\Local\Python\pythoncore-3.12-64\python.exe main.py` (NOT the venv) — find it by 8010 listener PID (`Get-NetTCPConnection -LocalPort 8010`), not by python.exe name (LINE archiver also runs main.py). Clean restart that works for code-only (no-DB) deploy: `Stop-ScheduledTask YK_MVP_APP` (this alone freed 8010) → re-resolve+Stop-Process the 8010 PID if any → `Start-ScheduledTask YK_MVP_APP`. Don't kill by `\.venv` filter — too broad, hits LINE archiver.

**Login pw is NOT changeme1 anymore:** seed admin yk1 temp pw `changeme1` was changed during the trial — programmatic login with changeme1 returns **401**. Don't script-verify via login; verify deploy by (a) `Select-String dep_install` on the server file + (b) `/deposits`→303 & `/login`→200 & public `app.yklogistics.uk/login`→200 (app listening = imports incl. new Jinja filters succeeded).

Runbook: `ProjectYK_System/docs/MVP_SERVER_DEPLOY.md`. Design/plan: `docs/superpowers/specs/2026-06-15-user-accounts-rbac-design.md` + `docs/superpowers/plans/2026-06-15-user-accounts-rbac.md`. Built on branch `feat/mvp-server-deploy`. See [[reference-ssh-to-yk-machine]], [[reference-line-archiver]], [[reference-yklogistics-dns]].
