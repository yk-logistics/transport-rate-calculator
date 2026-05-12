# Last Session Handoff — 2026-05-09

## Resume here tomorrow

**Task:** AYU run 7 — clear 33 unresolved drivers, unblock AYU finalize

**File to open first:**
`reports/preflight_unresolved_queue/unresolved_preflight_AYU_2026-03_run7.json`

**Steps:**
1. Review the 33 unresolved drivers in the JSON
2. Resolve each using safe auto-resolve rules (single-prefix unique) or flag for manual review
3. Rerun preflight for AYU 2026-03
4. Confirm cycle-date drift reduced + unlinked count drops
5. If drift = 0 → AYU finalize is unblocked

**Do not touch BigC or LCB in this session.**

---

## Priority queue after AYU run 7

1. `pay_cycle_policy` data cleanup + `/petty-cash?review=1` → zero
2. BigC cross-site collision check (6 drivers)
3. BigC audit residual (สมพร, สมประสงค์, พรศักดิ์)
4. Employee SSO field + LCB non-split UI

---

## Start command for Claude Code

Paste at top of new chat:
```
Token mode: ULTRA-LEAN. Task: AYU run 7 — clear 33 unresolved from reports/preflight_unresolved_queue/unresolved_preflight_AYU_2026-03_run7.json and rerun AYU preflight. Read AGENT_BOOTSTRAP.md + MODULE_REGISTRY.md only, then go straight to the queue file.
```
