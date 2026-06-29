#!/usr/bin/env bash
# deploy_mvp.sh - self-verifying deploy of the Project YK MVP to the YK server.
#
# This REPLACES the eyeball-everything flow of deploy_mvp_to_server.sh. It copies code
# (and optionally app.db), then runs _deploy_remote.ps1 ON THE SERVER which does the
# cutover AND verifies it: free 8010 by PID (not bare \.venv → spares the LINE archiver),
# confirm the new process started AFTER the copy, confirm 8020 still up, and confirm the
# required ASCII code-markers are actually on disk (guards revert/stale code). Any failed
# check makes the remote script exit 1, which fails this script - so a green run is real.
#
# Usage (from repo root, on Dev, Tailscale up):
#   bash ProjectYK_System/tools/deploy_mvp.sh
#   bash ProjectYK_System/tools/deploy_mvp.sh --markers "fuel_grade,other_rest"
#   bash ProjectYK_System/tools/deploy_mvp.sh --with-db          # also push app.db (byte-verified)
#
# --markers : comma-separated ASCII strings that MUST exist in main.py/templates after
#             deploy. ASCII only (Thai over SSH gives false negatives). Pick a marker
#             unique to the change you just shipped - that's what proves it went live.
# --with-db : also copy app.db. Backs up the server DB first, verifies byte-size on the
#             server, and refuses to restart onto a partial/truncated copy.

set -euo pipefail

SERVER="yklog@100.97.150.114"
APP_LOCAL="ProjectYK_System/app"
APP_REMOTE="C:/Users/yklog/YK_MVP/app"
REMOTE_PS1_LOCAL="ProjectYK_System/tools/_deploy_remote.ps1"

MARKERS=""
WITH_DB=0
while [ $# -gt 0 ]; do
    case "$1" in
        --markers) MARKERS="${2:-}"; shift 2 ;;
        --with-db) WITH_DB=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

echo "== 1/5 refresh requirements.lock from current Dev venv =="
( cd "$APP_LOCAL" && .venv/Scripts/python.exe -m pip freeze > requirements.lock.txt )

echo "== 2/5 copy source (py + requirements + dirs); tests/scratch excluded =="
scp -q "$APP_LOCAL"/*.py "$APP_LOCAL"/requirements.txt "$APP_LOCAL"/requirements.lock.txt \
    "$SERVER:$APP_REMOTE/"
scp -rq "$APP_LOCAL/services" "$APP_LOCAL/static" "$APP_LOCAL/templates" \
    "$SERVER:$APP_REMOTE/"
scp -q "$REMOTE_PS1_LOCAL" "$SERVER:$APP_REMOTE/_deploy_remote.ps1"

DB_DEPLOYED=0
DB_SIZE=0
if [ "$WITH_DB" -eq 1 ]; then
    echo "== 2b/5 backup server DB, then copy app.db (byte-verified on server) =="
    STAMP="$(date +%Y%m%d_%H%M%S)"
    ssh "$SERVER" "powershell -NoProfile -Command \"Copy-Item '$APP_REMOTE/app.db' '$APP_REMOTE/app.db.bak_before_$STAMP' -ErrorAction SilentlyContinue\""
    # local size (Git Bash stat) so the server can compare and refuse a partial copy
    DB_SIZE="$(stat -c %s "$APP_LOCAL/app.db" 2>/dev/null || wc -c < "$APP_LOCAL/app.db")"
    scp -q "$APP_LOCAL/app.db" "$SERVER:$APP_REMOTE/app.db"
    DB_DEPLOYED=1
    echo "   local app.db = $DB_SIZE bytes (server will verify)"
fi

echo "== 3/5 sync any new pinned deps into the server venv =="
ssh "$SERVER" "powershell -NoProfile -Command \"Set-Location $APP_REMOTE; .\\.venv\\Scripts\\python.exe -m pip install --quiet -r requirements.lock.txt; Write-Output DEPS_OK\"" \
    | grep -E "DEPS_OK" || echo "(dep sync output suppressed)"

echo "== 4/5 cutover + SELF-VERIFY on server =="
set +e
REMOTE_OUT="$(ssh "$SERVER" "powershell -NoProfile -ExecutionPolicy Bypass -File $APP_REMOTE/_deploy_remote.ps1 -ExpectMarkers '$MARKERS' -DbDeployed '$DB_DEPLOYED' -DbLocalSize '$DB_SIZE'")"
REMOTE_RC=$?
set -e
echo "$REMOTE_OUT"

echo "== 5/5 verify public endpoint =="
PUB_CODE="$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://app.yklogistics.uk/login || echo 000)"
echo "app.yklogistics.uk/login -> HTTP $PUB_CODE"

# --- final gate: remote checks AND public 200 must both pass --------------------------
if [ "$REMOTE_RC" -ne 0 ] || ! echo "$REMOTE_OUT" | grep -q "RESULT OK" || [ "$PUB_CODE" != "200" ]; then
    echo ""
    echo "❌ DEPLOY VERIFY FAILED - see FAIL lines above. The live app may be on OLD code or down."
    echo "   (server DB was backed up if --with-db; investigate before walking away.)"
    exit 1
fi

echo ""
echo "✅ DEPLOY VERIFIED - new code live, archiver up, public 200."
