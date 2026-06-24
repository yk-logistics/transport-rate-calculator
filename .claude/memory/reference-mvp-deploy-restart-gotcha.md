---
name: reference-mvp-deploy-restart-gotcha
description: "deploy_mvp_to_server.sh copies code fine but its restart often leaves OLD code serving — the live app runs under GLOBAL python, not the venv the script's kill-filter expects"
metadata: 
  node_type: memory
  type: reference
  originSessionId: e92ef343-8b79-4772-85b7-96c18c6a8ce7
---

`deploy_mvp_to_server.sh` does two jobs: (1) scp code to `C:/Users/yklog/YK_MVP/app` — this works; (2) restart `YK_MVP_APP` task. **Step 2 is unreliable.**

The MVP app on the server (.197, user `yklog`) actually runs under **global Python** `C:\Users\yklog\AppData\Local\Python\pythoncore-3.12-64\python.exe main.py` (launched by `start_mvp.bat`), NOT the `.venv` the script assumes. The script's kill filter `CommandLine -match 'YK_MVP'` matches neither the global-python process nor the venv one (whose cmdline is just `.\.venv\Scripts\python.exe main.py`), so the OLD process keeps holding port 8010 and the deployed code never goes live (symptom: new routes 404/redirect even though `main.py` on disk is new + mtime fresh).

**Fix that worked (2026-06-22):** write a `.ps1` to the server and run by path (here-strings over SSH get mangled by quoting). Kill any python whose cmdline matches `main\.py` AND (`pythoncore` OR `\.venv` OR `YK_MVP`), `Start-Sleep 3`, `Start-ScheduledTask YK_MVP_APP`, wait 15s, confirm `Get-NetTCPConnection -LocalPort 8010 -State Listen`. Verify live with `curl https://app.yklogistics.uk/login` (200) + a known new route.

**Watch out:** killing the port-8010 owner takes the LIVE company app down for ~15s → 502 at the tunnel until the task relaunches. Confirm UP before walking away.

**Out-of-process token minting won't verify:** signing an AccessLink token via an SSH-run python uses a different `YK_SESSION_SECRET` than the running app (the app gets its secret from `start_mvp.bat`'s env). So `/check?t=<minted>` returns "ลิงก์ไม่ถูกต้อง" even though the feature is fine. To truly test a magic link, generate it from inside the running app (`/admin/check-links`). See [[reference-mvp-server-deploy]], [[project-lcb-slip-reader]].
