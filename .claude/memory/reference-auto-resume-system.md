---
name: reference-auto-resume-system
description: "How โอ's overnight Claude auto-resume works (files, arming, cap, logs) across ~/.claude and project _Claude Tools"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1a713099-ae54-435a-9519-67382befa59c
---

โอ's "resume after token limit while I sleep" automation. Spans two locations:

**Wiring:** project `.claude/settings.local.json` has a **SessionStart** hook → `~/.claude/save_session.ps1` (writes current `session_id` to `~/.claude/last_session.txt`, **no BOM** — a BOM here breaks `claude --resume`). Previously this was a **Stop** hook (`on_stop.ps1`, now orphaned) that fired every turn → caused the cmd popup flashing on every reply. Moving to SessionStart killed the popup.

**Watcher:** `~/.claude/auto_resume.ps1` (v3) — only runs when armed. Each cycle: `claude --resume <id> -p <prompt> --dangerously-skip-permissions`; detects limit via exit code ≠ 0 or text match. On limit it **parses the reset time** ("Resets at HH:MM" / "try again in N min" via `Get-ResetSeconds`) and sleeps until exactly then (+60s), falling back to 30-min poll if unparseable. Stops on `[AUTO_DONE]`, manual disarm, or **time cap**. Also calls `SetThreadExecutionState` (keep-awake) so the machine won't sleep mid-window; cleared on exit.

**Why NOT Claude Code's built-in schedulers** (checked, all unfit for this): RemoteTrigger = cloud, can't touch local files; CronCreate = needs the rate-limited REPL open & idle (the stuck session is the one we're waiting on); scheduled-tasks = fresh memoryless agent that would just shell out to `claude --resume` anyway. The local PS watcher is the right tool.

**Arm/Disarm:** `_Claude Tools/ArmClaudeResume.ps1` (creates `autoresume_armed.txt` + spawns watcher) / `disarm_claude_resume.ps1` (deletes armed file).

**Operational knobs:**
- Time cap default **12h** — override by putting a number in `~/.claude/autoresume_max_hours.txt`.
- Log of every step: `~/.claude/auto_resume.log` (ARMED/RESUME/LIMITED/CONTINUED/DONE/STOP).
- All `.ps1` here must be **UTF-8 with BOM** or PS 5.1 mangles Thai in strings.

Not a substitute for Claude Code's built-in scheduled tasks (cron) — a future "v2" could schedule a single resume at the exact reset time instead of 30-min polling. See [[claude-code-multiple-installs]].
