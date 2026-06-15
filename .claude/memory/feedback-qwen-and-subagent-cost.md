---
name: feedback-qwen-and-subagent-cost
description: "โอ's delegation priorities — minimize MAIN context window first; delegate bulky reads aggressively (free Qwen preferred, native subagents OK), keep synthesis in main"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 768861b2-a0c9-47cb-ae87-3a101a0dbce6
---

โอ's top priority for delegation is keeping the **main context window as small as possible** — this matters to โอ more than saving tokens. So delegate bulky work aggressively instead of reading everything in the main thread.

**Tool choice (best → fallback):**
- **Free Qwen (via 9arm — [[reference-qwen-subagent]]):** first choice for bulky **read-only** work (grep across many files, digest long logs/output, file recon). Runs in a separate process and returns only a summary → keeps main context lean AND costs no money. Proactively offer it.
- **Native subagents (Explore / Plan / custom like bill-checker):** use when the task needs real intelligence or parallel/independent exploration. They isolate context too (main only sees the summary), so they DO serve the context goal — the trade-off is paid tokens + cold start. โอ accepts that cost for a lean context, so use them freely for the right shape of task; just announce when you do.

**Still keep in the MAIN thread (don't subagent):**
- Trivial/tiny lookups — cold-start overhead outweighs the benefit; do them inline.
- Tightly interactive / iterative work — subagents are one-shot and stateless.
- Synthesis, final decisions, writing code, and money/payroll logic — Opus does these directly (CLAUDE.md money rule).

**Why:** โอ explicitly wants minimal context-window usage and is happy to use subagents often to get it.
**How to apply:** default to delegating exploration/search/reading (Qwen first; native subagent if it needs brains); keep the main thread for deciding and writing.
