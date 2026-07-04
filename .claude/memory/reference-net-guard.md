---
name: reference-net-guard
description: "net_guard.py — all-site payroll net snapshot+diff (read-only); before/after a recompute/import, proves ONLY the intended run(s) moved"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d74d681f-065b-452c-9ee6-7d1bcd291f0b
---

`ProjectYK_System/tools/net_guard.py` — read-only guard that snapshots **every** payrun's
net (all sites) and diffs it. Built 29มิ.ย. to generalize `_bigc_guard_snapshot.py` (which
only watched BIGC). Use it around any recompute / import / money fix to prove that ONLY the
run(s) I meant to touch changed — the check I was rebuilding by hand every task
("9 คนเท่าเดิม / net ไซต์อื่นไม่ขยับ").

```bash
python ProjectYK_System/tools/net_guard.py before               # snapshot all runs
# ...do the recompute/import/fix...
python ProjectYK_System/tools/net_guard.py after --allow 2,18    # only runs 2 & 18 may move
python ProjectYK_System/tools/net_guard.py show                  # just print the board
```

`after` exits 1 if any run changed that isn't in `--allow` (prints ❌ + Δ). A run in `--allow`
that didn't move is fine. Snapshot JSON: `ProjectYK_System/reports/_net_guard.json`. NEVER writes app.db.
Verified the fail-path (tampered snapshot → ❌ exit1) and allow-path (→ OK exit0).

Current board baseline (29มิ.ย.): 18 runs, e.g. LCB#1 finalized 378,939.03; LCB#2 draft 266,057.69;
AYU#18 draft 205,892.10. Pairs with the per-feature `preflight_*.py` and [[reference-deploy-mvp-selfverify]].

**Side-finding + cleanup (29มิ.ย.):** full pytest suite (`cd app; .venv/Scripts/python.exe -m pytest -q`,
~3min) was 228 passed / 5 failed — all STALE tests, not money bugs. Fixed 4 (now **233 passed / 1 failed**):
- test_deposits ×2: assertions `3/10→4/10`, `5/10→6/10` — installment X now = งวดที่กำลังหัก (paid+1), per [[project-deposit-installment-number]].
- test_check_link_menu: menu label "ลิงก์ตรวจยาง" → "ลิงก์ตรวจสภาพรถ".
- test_payroll_print_all driver-slip: `"333" not in html` was hitting `#333` in CSS → strip `<style>` first;
  also the driver slip now hides ALL company-side numbers (KB+real-rev+central-price), not just KB
  (per [[project-driver-pay-breakdown-daily-slip]] redesign) — updated assert to expect only ค่าเที่ยว 3,300.

**STILL FAILING — needs โอ decision (not a stale-test fix):** test_boss_slip_shows_kb_and_real_revenue.
The BOSS slip no longer shows ค่าขนส่งจริง (raw revenue 7,456) or central price 5,500 — only KB 333 +
driver fee. The slip redesign dropped the raw-revenue column. Q for โอ: does the boss still want to see
ค่าขนส่งจริง on the slip? If yes → restore the feature; if no → drop that assertion. Left failing on purpose.
