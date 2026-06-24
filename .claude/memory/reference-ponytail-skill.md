---
name: reference-ponytail-skill
description: "ponytail plugin (lazy-senior-dev skill) installed, default OFF; how to enable + token cost"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7a7622ef-18ea-446f-9737-fcbc3f3d365c
---

ponytail 4.7.0 (DietrichGebert/ponytail) installed as a Claude Code plugin on โอ's machine — "lazy senior dev" skill that forces minimal code (YAGNI, stdlib first, no unrequested abstractions). 6 skills: ponytail, -audit, -debt, -gain, -help, -review.

**Default mode = OFF** (set in `%APPDATA%\ponytail\config.json` → `{"defaultMode":"off"}`), so it costs nothing until enabled.

How to use:
- `/ponytail lite | full | ultra` to enable for the current heavy-coding session
- `/ponytail off` to silence again
- Change persistent default by editing that config.json (or env `PONYTAIL_DEFAULT_MODE`)

Token cost when on: ~904 tok always-on per session + ~2.2k per ponytail invoke. Worth it only on real code-writing sessions; pure Q&A sessions would pay ~900 for nothing — hence default off.

Install gotcha: hand-editing `~/.claude/plugins/*.json` registry files is NOT enough — Claude Code reads skills from `plugin-catalog-cache.json` which only the supported installer regenerates. Correct non-interactive install: `claude plugin marketplace add DietrichGebert/ponytail` then `claude plugin install ponytail@ponytail`. Overlaps heavily with the Karpathy guidelines already in CLAUDE.md.
