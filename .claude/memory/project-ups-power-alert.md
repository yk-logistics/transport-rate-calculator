---
name: project-ups-power-alert
description: Plan to protect YK server from unexpected power-loss shutdowns (PSU/DB damage) via UPS + USB-signalled auto-shutdown + Discord alert
metadata: 
  node_type: memory
  type: project
  originSessionId: e7d8da15-1cd9-4d53-8d97-28a5d9114b20
---

โอ wants the YK server (LAN .197 / Tailscale 100.97.150.114 — see [[reference-ssh-to-yk-machine]]) protected after it died **unexpectedly Sun 21 Jun 2026 18:39** (power loss, ran ~18h until manually rebooted 22 Jun 12:28). Risk: repeated dirty power-off damages PSU and the SQLite app.db ([[reference-mvp-server-deploy]]).

**Decided approach (แบบ A):** UPS with a **USB communication port** → on power loss the UPS signals over USB → software on the server (not the UPS) decides: alert + graceful self-shutdown.

**Behaviour to implement when UPS arrives:**
1. Power lost → fire Discord alert immediately ("⚠️ ไฟดับ เครื่อง YK กินแบต UPS").
2. Wait **2 minutes** (โอ chose 2 min, not 5 — cheap low-VA UPS, fears battery runs out). If power returns → Discord "✅ ไฟกลับ" and do NOT shut down.
3. Still no power after 2 min **OR battery near-empty before 2 min** (whichever first) → Discord "🔌 กำลัง shutdown" → graceful Windows shutdown.

**Hardware CHOSEN (2026-06-22):** **ZIRCON ZX-1000VA/550W @ 1,690 THB** from Shopee. Has USB-B port + "U.P. Smart monitoring" software, Windows-supported, line-interactive 2–4ms transfer, มอก. certified, 2yr warranty. 1000VA/550W is overkill for the load = long backup (claims 15–30min for 1 PC). Cheaper than APC BV650I (~2,300) with more capacity. (Rejected CyberPower UT650EG ~1,650 — NO USB.) I can't browse Shopee — โอ pasted the spec text + back-panel photo, that's how USB was confirmed.

**Two caveats accepted:**
1. ZIRCON is a Thai brand — bundled software name unclear (likely WinPower/ViewPower-class). Plan: try bundled SW first; if poor, fall back to **NUT** (free) over USB. Can't 100%-confirm SW works until the unit is physically plugged in.
2. Battery mode = **Modified Sine Wave**; listing warns "not for 80+ Active PFC PSU". Server PSU model is UNKNOWN (consumer PSU, not readable via WMI). Machine = MSI board **MS-7E02**, desktop, i5-14400, real load ~100–150W. Risk judged low (fast transfer, goal is graceful shutdown not long runtime). **MUST test a real power-cut once on install** (pull UPS from wall, see if box rides battery cleanly). If it stutters → consider Pure Sine Wave unit.

**Software plan:** try ZIRCON's bundled monitoring SW first; else NUT. Whichever runs a custom command on power events → Discord webhook + 2-min-delay shutdown hook.

## LIVE 2026-06-24 — installed, armed, boot-persistent

UPS arrived & connected. **Plan changed at install time** (the ZIRCON-vs-NUT details below supersede the APC/apcupsd plan above):

- **UPS is a generic Megatec clone** (`VID_0001/PID_0000`, product `MEC0003`). Windows does NOT expose it as a battery — `Win32_Battery` / `BatteryStatus.PowerOnline` return NOTHING. The original `on_power_event.ps1` that polled `PowerOnline` could never have worked. No bundled software came in the box.
- **Solution = NUT for Windows** (Network UPS Tools), the fallback the plan anticipated. Installed at `C:\NUT` (extracted from the v2.8.5 `NUT-for-Windows-x86_64...fixNSS.7z` GitHub release; bsdtar `tar.exe` extracts .7z fine, no 7-Zip needed; winget has no NUT). Driver = `nutdrv_qx`, protocol Megatec 0.09. Reads everything: battery.charge, input.voltage, ups.load (~9%, tiny), **ups.status = OL (online) / OB (on battery) / LB (low batt)**.
- **Architecture (no upsmon — it's the buggy part):** scheduled task **`YK_UPS_Watch`** (runs as SYSTEM, AtStartup, RunLevel Highest) → `C:\YK_PowerAlert\start_watch.ps1` brings up `nutdrv_qx -a zircon` + `upsd` (LISTEN 127.0.0.1 3493), then runs `ups_poll.ps1` in foreground (poll `upsc zircon@127.0.0.1 ups.status` every 15s). On OL→OB transition → calls `on_power_event.ps1` (rewritten to read `ups.status` via `ups_status.ps1` helper, not Win32_Battery; also early-shutdown on LB flag). NUT configs in `C:\NUT\etc\` (ups.conf, upsd.conf, upsd.users, upsmon.conf).
- **Files all UTF-8 WITH BOM** — powershell.exe 5.1 mangles Thai/emoji in no-BOM files (parse errors). This bit us; BOM fixed it. Discord messages now render Thai+emoji correctly (โอ confirmed).
- **Pull-plug test PASSED (DryRun) 16:00** — Discord ⚠️ไฟดับ fired in ~10s, plug back in → ✅ไฟกลับ + abort. Then **re-armed (DryRun=False) 16:07** and verified Running. Real `Stop-Computer -Force` is now live.

**Key ops facts:**
- SSH from this machine → server hangs if a remote command spawns child procs (driver/upsd) that inherit the SSH stdout handle. **Use the scheduled task to start/stop the watcher**, not inline ssh `Start-Process`. SSH also strips PowerShell single-quotes/`$_`/backticks — prefer scp-a-script-then-run-by-`-File` over inline `-Command`.
- Net-down does NOT affect protection: detection+shutdown are USB+local only; only the Discord alert needs net (try/catch'd, failure is harmless). Router is NOT on UPS → on power loss net dies but server still shuts down cleanly; only loses the Discord ping. โอ may later move router/ONU onto UPS (plenty of headroom) to keep alerts during outages.
- To change behavior: edit scripts in `C:\YK_PowerAlert\`, re-run `install_task.ps1` (add `-DryRun` to test safely), then stop/kill/start via `restart_armed.ps1`.

**DONE 2026-06-22 (prepared, NOT armed) — historical, mostly superseded by NUT above:**
- Discord webhook created (reused the LINE-archiver Discord server, new channel) + tested OK. Stored on server at `C:\YK_PowerAlert\discord_webhook.txt`.
- Wrote `C:\YK_PowerAlert\notify.ps1` (events: powerfail/powerback/shutdown/test → Thai Discord msg + timestamp, logs failures to notify_error.log) and `on_power_event.ps1` (on AC loss: notify → wait 2min checking BatteryStatus.PowerOnline every 10s → if restored: powerback+abort; else: shutdown notice + `Stop-Computer -Force`; has `-DryRun` to skip the real shutdown). All 3 Discord messages test-fired successfully from the server.
- Set `Set-ExecutionPolicy RemoteSigned` (LocalMachine) on the server so the .ps1 can run.
- **NOT armed:** nothing yet calls `on_power_event.ps1` — no auto-shutdown is live. Safe.

**Still blocked on:**
- Buy the ZIRCON ZX-1000VA (confirmed good @ 1,690 THB; โอ to purchase on Shopee).
- When UPS arrives: plug USB UPS→server + server power→UPS battery outlets. Then I: install UPS software, set it to call `on_power_event.ps1` on AC-loss (= arm), test with `-DryRun` first (pull UPS from wall, confirm all alerts fire but no real shutdown), then remove `-DryRun`.
- Verify `BatteryStatus.PowerOnline` actually reflects this UPS's AC state once connected (the 2-min wait loop depends on it; if the bundled SW/driver doesn't expose it, switch to reading state from the UPS software/NUT instead).

โอ explicitly declined the ping-from-another-machine fallback (แบบ B): "รู้ตอนดับก็สายไปแล้ว".
