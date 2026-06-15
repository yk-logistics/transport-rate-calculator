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

Runbook: `ProjectYK_System/docs/MVP_SERVER_DEPLOY.md`. Design/plan: `docs/superpowers/specs/2026-06-15-user-accounts-rbac-design.md` + `docs/superpowers/plans/2026-06-15-user-accounts-rbac.md`. Built on branch `feat/mvp-server-deploy`. See [[reference-ssh-to-yk-machine]], [[reference-line-archiver]], [[reference-yklogistics-dns]].
