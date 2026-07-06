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

**⚠ kill-filter `\.venv` is TOO BROAD — hits YK_LINE_ARCHIVER (2026-06-28):** a restart .ps1 that kills `python.exe` where cmdline matches `main\.py` AND (`pythoncore`|`\.venv`|`YK_MVP`) ALSO kills the LINE archiver (its cmdline = `...YK_LINE_ARCHIVER\.venv\Scripts\python.exe main.py`). It auto-recovered via `YK_LINE_HEALTHPOLL` task, but don't rely on that. **Safer cutover that worked:** (1) Stop-ScheduledTask YK_MVP_APP; (2) kill the **port-8010 OwningProcess by PID** + python whose cmdline matches **`YK_MVP`** (NOT bare `\.venv`); (3) loop-wait until 8010 free; (4) Start-ScheduledTask; (5) re-read 8010 owner = fresh pid + StartTime AFTER copy; (6) assert port 8020 (archiver) still up. The live MVP runs under GLOBAL pythoncore (owns 8010); `Start-ScheduledTask` may spawn a venv pid that can't bind until you free 8010 first. Thai `Select-String -SimpleMatch` over SSH gives false negatives → verify deployed templates with **ASCII markers** (e.g. `other_rest`, `item.special_income`), not Thai strings.

**เพิ่ม 2026-07-05 (PWA deploy war):** (1) `Win32_Process.CommandLine` ของ process ที่ task scheduler/health-poll เปิด อ่านข้าม SSH session ได้ **null** → kill-filter ตาม cmdline พลาดเงียบๆ ทุกครั้ง; วิธีเดียวที่ชัวร์ = **census python ที่ LISTEN พอร์ต 8010-8060 (เว้น 8020) แล้ว kill ตาม PID**. (2) `mvp_health_poll.py` จะ spawn แอปด้วย **global python** ทันทีที่ 8010 ว่าง → ต้อง Stop-ScheduledTask ก่อน kill แล้ว Start-ScheduledTask ทันทีให้ task จับพอร์ตก่อน health poll. (3) **cloudflared เป็นของ task `YK_CLOUDFLARED_TUNNEL`** — ห้าม kill+relaunch มือ (ได้ตัวกะพริบ ทำ line.+app. 502 ทั้งคู่); ให้ Stop/Start task เท่านั้น. (4) **เซสชันอื่น deploy จาก HEAD จะทับไฟล์ uncommitted ที่ scp ไว้บน server** — งาน surgical deploy ต้อง commit ลง branch ทันทีหลังเขียว ไม่งั้นโดน HEAD-deploy รอบถัดไปลบ (เกิดจริง: PWA /sw.js hunk หายไปกลางคัน).

**Out-of-process token minting won't verify:** signing an AccessLink token via an SSH-run python uses a different `YK_SESSION_SECRET` than the running app (the app gets its secret from `start_mvp.bat`'s env). So `/check?t=<minted>` returns "ลิงก์ไม่ถูกต้อง" even though the feature is fine. To truly test a magic link, generate it from inside the running app (`/admin/check-links`). See [[reference-mvp-server-deploy]], [[project-lcb-slip-reader]].
