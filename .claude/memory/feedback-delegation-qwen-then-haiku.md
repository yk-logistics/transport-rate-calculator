---
name: feedback-delegation-qwen-then-haiku
description: "โอ's confirmed delegation ladder for read-only recon/summarize work: try free Qwen first, fall back to Haiku subagent; Opus keeps money/decisions/code"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6e5a8d99-9f8d-42be-adb9-9b63a5e0aefd
---

For read-only recon/summarize work (read many files → return a short summary; not money/payroll/billing, not decisions, not code), โอ confirmed (2026-06-17) the delegation ladder:

1. **Qwen free (9arm) first** — cheapest (no money), keeps main context lean. Use `_Claude Tools/qwen-readonly.ps1 "<task>"`. See [[reference-qwen-subagent]] (128k context limit — split into ~4-file chunks for big jobs).
2. **Haiku subagent as fallback** — when Qwen is too slow, too small for the job, or its output looks shaky. Dispatch a native subagent (e.g. Explore) with `model: haiku`. Slightly costs tokens but faster + more reliable than Qwen, still keeps main context lean.
3. **Opus (main) keeps** — synthesis, decisions, writing code, anything touching money/payroll/billing. Never delegate these.

**Why:** โอ's top goal is small main context + token economy; this ladder spends nothing first, escalates to cheap-but-reliable only when needed.
**How to apply:** default delegate read-only bulky reads to Qwen; if it stalls/errors/looks wrong, re-run on Haiku; bring only the summary back to main. Verified live 2026-06-17 — both returned correct tables on the same recon task. Builds on [[feedback-qwen-and-subagent-cost]] and [[project-superpowers-9arm-models]].
