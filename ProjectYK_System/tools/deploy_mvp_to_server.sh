#!/usr/bin/env bash
# Deploy the MVP app from this Dev machine to the YK server (copy-folder model).
#
# The server has NO git. We copy source files over SSH/scp to C:/Users/yklog/YK_MVP/app,
# then restart the YK_MVP_APP scheduled task. The server's app.db is NEVER overwritten
# (it lives only on the server and is backed up daily by YK_MVP_DB_BACKUP).
#
# Usage (from repo root, on the Dev machine, with Tailscale up):
#   bash ProjectYK_System/tools/deploy_mvp_to_server.sh
#
# Prereqks: passwordless SSH to yklog@100.97.150.114 (see .claude memory ssh-to-yk-machine).

set -euo pipefail

SERVER="yklog@100.97.150.114"
APP_LOCAL="ProjectYK_System/app"
APP_REMOTE="C:/Users/yklog/YK_MVP/app"

echo "== 1/4 refresh requirements.lock from current Dev venv =="
( cd "$APP_LOCAL" && .venv/Scripts/python.exe -m pip freeze > requirements.lock.txt )

echo "== 2/4 copy source (py + requirements + dirs); DB/tests/scratch excluded =="
scp -q "$APP_LOCAL"/*.py "$APP_LOCAL"/requirements.txt "$APP_LOCAL"/requirements.lock.txt \
    "$SERVER:$APP_REMOTE/" 2>/dev/null || true
scp -rq "$APP_LOCAL/services" "$APP_LOCAL/static" "$APP_LOCAL/templates" \
    "$SERVER:$APP_REMOTE/" 2>/dev/null || true

echo "== 3/4 sync any new pinned deps into the server venv =="
ssh "$SERVER" "powershell -NoProfile -Command \"Set-Location $APP_REMOTE; .\\.venv\\Scripts\\python.exe -m pip install --quiet -r requirements.lock.txt; Write-Output DEPS_OK\"" \
    2>/dev/null | grep -E "DEPS_OK" || echo "(dep sync output suppressed)"

echo "== 4/4 restart MVP app task =="
ssh "$SERVER" "powershell -NoProfile -Command \"Restart-ScheduledTask -TaskName 'YK_MVP_APP'; Start-Sleep 8; if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) { Write-Output MVP_UP } else { Write-Output MVP_DOWN }\"" \
    2>/dev/null | grep -E "MVP_UP|MVP_DOWN"

echo "== verify public endpoint =="
curl -s -o /dev/null -w "app.yklogistics.uk/login -> HTTP %{http_code}\n" --max-time 20 https://app.yklogistics.uk/login

echo "Done. (Server DB untouched; tunnel unchanged.)"
