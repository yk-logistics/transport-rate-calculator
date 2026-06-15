---
name: scrutinize
description: Outsider-perspective end-to-end review of a plan, PR, or code change. Questions intent first, then traces actual code paths to verify the change does what it claims. Trigger on /scrutinize or when asked to review, audit, sanity-check, or get a second opinion.
---

Stand outside the change and ask whether it should exist at all, then verify it actually does what it claims end-to-end.

## Operating stance

- **Outsider.** Forget who wrote it and why they think it's right. Read the artifact cold.
- **End-to-end, not diff-local.** The diff is the entry point, not the scope. Follow the call graph through real code paths.
- **Actionable, concise, with rationale.** Every finding states _what to change_, _why_, and _what evidence_ led you there. No filler.

## Workflow — run in order, do not skip

### 1. Intent — what is this actually trying to do?
- State the goal in one sentence, in your own words. If you cannot, the artifact is underspecified — say so and stop.
- Ask: **is there a simpler, smaller, or more elegant way?** Consider:
  - Doing nothing (is the problem real / load-bearing?).
  - Using something that already exists in the codebase.
  - A smaller change that solves 90% of the goal with 10% of the risk.
  - Solving it at a different layer (config vs code, framework vs app).
- If a better alternative exists, name it explicitly with rationale. This is the most valuable output — surface it before the line-by-line review.

### 2. Trace — walk the actual code path
- For each behavior the change claims, trace end-to-end: entry point → call sites → branches → state mutated → exit/return/side effect.
- Include unchanged code on either side of the diff. Bugs hide at the seams.
- Note every surprise (unexpected branch, dead code reached, unknown state). Surprises are signal.

### 3. Verify — does it actually do what it claims?
For each claim, answer:
- Does the traced code path actually produce that behavior?
- What inputs/states would break it? (edge cases, concurrent callers, error paths, empty/null inputs, ordering assumptions)
- What does it silently change? (performance, error semantics, contracts for other callers)
- Do the tests actually exercise the traced path, or do they pass while skipping it?

### 4. Report
One section per finding, ordered by severity (blocker → major → nit):
- **Finding** — one sentence, specific. Cite `file:line`.
- **Why it matters** — the consequence, not the principle.
- **Evidence** — the trace step or input that exposes it.
- **Suggested change** — concrete, minimal.

Close with a one-line verdict: `ship` / `fix-then-ship` / `rework` / `reject` — with the single biggest reason.

## Rules
- No rubber-stamps. If you find nothing, say what you traced and checked.
- Cite or it didn't happen. Every claim references a specific path, file, or line.
- Distinguish claim from verification. "The PR says X" ≠ "I traced X and confirmed/refuted it."
- One simpler-alternative pass is mandatory, even on small changes.
- No flattery, no hedging. State the finding.
