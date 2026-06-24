---
name: project-ai-watch-line-group
description: "Future idea — AI that \"watches\" LINE groups (summarize/alert/triage). Start with cheap API on top of the existing archiver; defer any self-hosted LLM until proven + volume justifies it."
metadata: 
  node_type: memory
  type: project
  originSessionId: de7755ef-cda3-4b02-86f2-6b27483ebf6a
---

โอ wants (future, not now) an AI to "watch" LINE groups — summarize chat, flag who assigned work, send reminders, etc.

**Plan / decision (2026-06-18):** This will work, but **NOT** by investing in a self-hosted LLM up front.

- The hard part (capturing messages/images into a DB) **already exists** — the LINE archiver, port 8020, see [[reference-line-archiver]]. No AI needed for that layer.
- The "watch" layer is mostly summarize/alert/triage = **medium difficulty, does not need the smartest model**. Pulling money/billing numbers out of chat = high-stakes, needs a smart model (Claude) — keep that separate.

**Ladder (do in order, stop when it works):**
1. Start with a **cheap API** (Haiku, or the free Qwen โอ already has) on top of the existing archiver — pay-as-you-go, testable today, near-zero upfront cost.
2. Only if it proves useful AND volume gets so large the API bill hurts → then consider self-host.
3. Self-host is justified only if data must stay off-cloud OR daily volume is huge — and even then on a *separate GPU box*, never the current server (which has no discrete GPU — see [[reference-server-no-gpu-llm]]).

Point: prove value cheaply first; investing in our own LLM now is guessing before we've ever tried it.
