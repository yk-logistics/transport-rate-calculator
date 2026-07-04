---
name: reference-window-warm-routines
description: "5 cloud routines ping \"Hi\" daily to pre-open โอ's 5-hour usage window at target clock times — PROVEN to work"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d22ea057-eedc-44b0-a669-3675d55d1abf
---

โอ wanted his Claude 5-hour usage window to auto-reset at fixed clock times (so 12:00/17:00/21:00 BKT have fresh quota) WITHOUT having to manually type a message. Set up via `/schedule` (cloud Routines, run on Anthropic cloud — no machine/terminal needs to be open; uses his Max subscription quota, NOT separate API billing).

Each routine sends a tiny prompt: "Reply with the single word: Hi. Do nothing else. Do not use any tools. Do not read any files." (minimal token, no repo work).

**ACTIVE SET (revised 2026-06-28):** โอ changed FIRE times to 06:00/11:00/16:00/21:00 BKT — note these are now the actual ping clock times (NOT shifted ~5h earlier like the old set). NO overnight coverage (21:00→06:00 gap is intentional). Same 4 trigger_ids reused, just renamed + new cron.

| Routine name | fire BKT | cron (UTC) | trigger_id |
|---|---|---|---|
| Warm for 06:00 BKT | 06:00 | `0 23 * * *` | trig_01XrfixY93Kkqd2G3fHUkfxc |
| Warm for 11:00 BKT | 11:00 | `0 4 * * *`  | trig_01X6CcziERz6mVtXz3wkaGZs |
| Warm for 16:00 BKT | 16:00 | `0 9 * * *`  | trig_011WNWPvEQsnW1DziaZNMASY |
| Warm for 21:00 BKT | 21:00 | `0 14 * * *` | trig_01JiZjJJuAn5ryCXvJecSMgS |

OLD SET (disabled 2026-06-25, not deleted — API can't delete, only web): trig_017i1MDWtoBYE7tNaUJApPzh, trig_017uScFs6D2EWL3VRjWQQgmU, trig_01V7WK4HNM9BLpsGrsukHJzK, trig_014kSMSAqbeQyD2fd3GQHFvg, trig_01CGk6hG1vnQnHrUxofzmV3V.

**PROVEN 2026-06-25:** routine 07:33 fired at 00:33:26 UTC (last_fired_at) and โอ confirmed his window reset ~00:30 → cloud routine DOES open the same 5-hour window his interactive terminal draws from. The earlier worry (cloud session separate from terminal) is resolved: they share the per-account window.

Caveat: Anthropic once planned (then PAUSED ~15 Jun 2026) to split non-interactive quota into a separate pool. If that goes live, these pings stop feeding the interactive window and this whole setup becomes useless — re-verify if usage behavior changes.

Manage/disable at https://claude.ai/code/routines (cannot delete via API, only via web). Recurring routines created via `/schedule` do NOT auto-expire like session-only CronCreate jobs.
