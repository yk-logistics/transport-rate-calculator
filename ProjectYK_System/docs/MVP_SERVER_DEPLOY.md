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

```bash
bash ProjectYK_System/tools/deploy_mvp_to_server.sh
```

Copies source, syncs deps, restarts `YK_MVP_APP`, verifies the public endpoint. Server DB untouched.

## Daily DB backup

`YK_MVP_DB_BACKUP` scheduled task copies `app.db` to `YK_MVP\backups\app-YYYYMMDD.db` daily, keeping the last 14.
