# MVP Server Deployment — Runbook

How the Project YK MVP runs on the YK server (`yk` / Tailscale `100.97.150.114`),
served at **https://app.yklogistics.uk** for the office-team trial.

## Layout on server

- App code + venv: `C:\Users\yklog\YK_MVP\app\` (Python 3.12 venv; **no git** on server — copy-folder deploy)
- Launcher: `C:\Users\yklog\YK_MVP\start_mvp.bat` (sets `YK_SESSION_SECRET`, `YK_PORT=8010`, bind `127.0.0.1`, `YK_ADMIN_TEMP_PW`)
- App DB: `C:\Users\yklog\YK_MVP\app\app.db` (created on first boot; **lives only on server**, never copied from Dev)
- Tunnel config: `C:\Users\yklog\.cloudflared\config.yml` (shared `yk-line` tunnel; backup at `config.yml.bak_before_mvp`)

## Runs unattended (before login, survives reboot)

Three SYSTEM scheduled tasks, all `-AtStartup`, run whether a user is logged on or not:

| Task | What |
|------|------|
| `YK_MVP_APP` | runs `start_mvp.bat` → app on `127.0.0.1:8010` |
| `YK_CLOUDFLARED_TUNNEL` | runs the `yk-line` tunnel (serves both `app.` and `line.` hostnames) |
| `YK_LINE_HEALTHPOLL` | (pre-existing) LINE archiver health poll |

Tailscale is set `--unattended` + service Automatic → SSH works after a reboot **without** entering the PIN.

## Tunnel ingress (one shared tunnel)

```
app.yklogistics.uk  -> http://127.0.0.1:8010   (MVP)
line.yklogistics.uk -> http://127.0.0.1:8020   (LINE archiver — untouched)
```

`.com` (email) is a different domain and is never touched.

## First login

- Seed admin: **yk1** / temp password `changeme1` → forced to change on first login.
- Then yk1 adds the team via `/admin/users` (yk2, yk3, …). Roles: admin / office / accountant / viewer.

## Redeploy after code changes (from Dev)

**Use `deploy_mvp.sh` (self-verifying).** It copies source, syncs deps, does the cutover,
and then *proves the deploy worked* before reporting success — so a green run is real, not eyeballed.

```bash
# code-only deploy, with a marker that proves the change went live:
bash ProjectYK_System/tools/deploy_mvp.sh --markers "fuel_grade"

# also push app.db (server DB backed up first + byte-size verified before restart):
bash ProjectYK_System/tools/deploy_mvp.sh --with-db --markers "fuel_grade"
```

What the verify step checks (all must pass or it exits 1):

1. **DB byte-size** matches Dev before restart (only with `--with-db`) — refuses to restart onto a partial scp.
2. **Port 8010 freed by PID + `YK_MVP` cmdline** — *not* a bare `\.venv` filter (that also kills the LINE archiver on 8020).
3. **New process started AFTER the copy** — catches the classic "old code still serving" trap (global-python proc survives a naive restart).
4. **Port 8020 (LINE archiver) still up** — confirms the cutover didn't take it down.
5. **ASCII `--markers` present on server files** — guards against revert / stale code. Use ASCII only (Thai `Select-String` over SSH gives false negatives). Pick a marker unique to what you just shipped.
6. **Public `app.yklogistics.uk/login` → 200**.

Always pass a `--markers` string unique to the change you're shipping — that single arg is what turns "I copied files" into "I confirmed the new code is live."

The old `deploy_mvp_to_server.sh` is kept for reference but its restart is unreliable
(its kill-filter misses the global-python process → old code keeps serving). Prefer `deploy_mvp.sh`.

## Watchdog (added 2026-07-04)

`YK_MVP_HEALTHPOLL` scheduled task (SYSTEM, every 5 min) runs
`C:\Users\yklog\YK_MVP\mvp_health_poll.py` (source: `tools/server_watchdog/`):

- Probes `127.0.0.1:8010/health` + `https://app.yklogistics.uk/health` (must send a
  User-Agent — Cloudflare/Discord 403 the default `Python-urllib` UA).
- On fresh DOWN: tries `schtasks /Run /TN YK_MVP_APP` **once per down-episode**, then
  alerts Discord channel `#yk-mvp-alerts` (auto-created; token from the archiver `.env`,
  read-only). Alerts on state CHANGE only — no spam. State: `mvp_health_state.json`.
- App errors now also persist to `app/logs/app.log` (rotating 2MB×5) and surface on
  `/admin/server-health` → "🐞 ข้อผิดพลาดล่าสุด" (previously stdout was lost — SYSTEM task).

## Daily DB backup

`YK_MVP_DB_BACKUP` scheduled task copies `app.db` to `YK_MVP\backups\app-YYYYMMDD.db` daily, keeping the last 14.

## Security posture

- **HTTPS only** via Cloudflare; app binds `127.0.0.1:8010` (reachable only through the tunnel, never directly).
- **Passwords:** bcrypt-hashed. Nobody (incl. admin) can read them. Forgotten password → admin "รีเซ็ตรหัส" sets a temp pw + `must_change_pw`.
- **Brute-force:** `login_guard.py` — username locks after 5 bad passwords (15 min); IP blocked after 20 login hits/60s (10 min); real client IP from `CF-Connecting-IP`. Returns 429 when throttled.
- **RBAC** enforced server-side on every request (can't be bypassed from the browser).
- **Windows Firewall:** ON (all 3 profiles). SSH(22) inbound allowed; Tailscale rules present; cloudflared is outbound (unaffected). **Windows Defender real-time: ON. UAC: ON.** Do not disable these.
- Importing a Dev `app.db` re-seeds `yk1`/`changeme1` (the old DB predates the AppUser table) — โอ must re-set the yk1 password after any DB import.

### Server hardening (red-team pass, 2026-06-15)

Attack-surface reduction after reviewing the box as an outside attacker:

- **XAMPP disabled** — `Apache2.4` + `mysql` services stopped + StartupType=Disabled. Closed ports 80/443/3306 (XAMPP defaults are a classic break-in path; โอ doesn't use it).
- **SSH key-only** — `sshd_config`: `PasswordAuthentication no`, `PermitRootLogin no` (backup `sshd_config.bak_before_harden`). Port 22 firewall scoped to `192.168.0.0/16` + `100.64.0.0/10` (Tailscale) — not reachable from the public internet. We log in via Tailscale key.
- **SMB 445/139** scoped to LAN/Tailscale only.
- **AnyDesk kept** (โอ uses it; long unattended password). Works via outbound cloud relay, so no public inbound port needed.
- Already-good baseline left as-is: Windows Defender real-time ON, UAC ON, RDP disabled, Firewall ON (all profiles).
