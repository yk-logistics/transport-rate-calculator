---
description: Toggle thinking/effort on or off in settings.local.json
---

Read `.claude/settings.local.json`. Check the current value of `alwaysThinkingEnabled`:
- If it is `false` → set it to `true`
- If it is `true` or missing → set it to `false`

Write the updated file back, then report in one line: "Thinking: ON" or "Thinking: OFF" and note that it takes effect next session.
