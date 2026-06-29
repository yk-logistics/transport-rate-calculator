"""net_guard.py — all-site payroll net snapshot + diff guard (read-only).

The single most-repeated hand-check in this project is "recompute run X, then confirm
that ONLY run X moved and every other site/run net stayed put" (memory: regression
9-คน-เท่าเดิม, net-ไซต์อื่น-ไม่ขยับ, COPY-LOCK). `_bigc_guard_snapshot.py` only watched
BIGC. This generalizes it to ALL sites/runs so I can verify the whole board in one shot.

It NEVER writes to app.db. It snapshots net per payrun to a JSON, and on `after` diffs
against the snapshot and exits non-zero if anything moved unexpectedly.

Usage (from repo root):
  python ProjectYK_System/tools/net_guard.py before                  # snapshot every run's net
  # ... do the recompute / import / fix ...
  python ProjectYK_System/tools/net_guard.py after --allow 2,18      # run 2 and 18 are ALLOWED to move
  python ProjectYK_System/tools/net_guard.py show                    # just print the current board

Any run that changed and is NOT in --allow → printed as ❌ and exit 1.
A run in --allow that did NOT change is fine (you intended to touch it; no-op is allowed).
"""
from __future__ import annotations

import io
import json
import sqlite3
import sys
from argparse import ArgumentParser
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, REPO_ROOT  # noqa: E402

DB = str(APP_DIR / "app.db")
SNAP = REPO_ROOT / "ProjectYK_System" / "reports" / "_net_guard.json"


def snapshot() -> dict[str, dict]:
    """net + item count per payrun, keyed by run id (as str for JSON)."""
    con = sqlite3.connect(DB)
    cur = con.cursor()
    out: dict[str, dict] = {}
    rows = cur.execute(
        """SELECT pr.id, pr.site_code, pr.pay_cycle_tag, pr.status,
                  ROUND(COALESCE(SUM(pi.net_pay), 0), 2), COUNT(pi.id)
           FROM payrun pr
           LEFT JOIN payrunitem pi ON pi.pay_run_id = pr.id
           GROUP BY pr.id
           ORDER BY pr.site_code, pr.pay_cycle_tag"""
    ).fetchall()
    con.close()
    for rid, site, tag, status, net, n in rows:
        out[str(rid)] = {"site": site, "tag": tag, "status": status,
                         "net": net, "items": n}
    return out


def _print_board(snap: dict[str, dict]) -> None:
    for rid, r in sorted(snap.items(), key=lambda kv: int(kv[0])):
        print(f"  run {rid:>3} {r['site']:<5} {r['tag']:<8} {r['status']:<9} "
              f"net={r['net']:>14,.2f}  ({r['items']} items)")


def main() -> int:
    ap = ArgumentParser()
    ap.add_argument("mode", choices=["before", "after", "show"])
    ap.add_argument("--allow", default="",
                    help="comma-separated run ids ALLOWED to change (after mode)")
    args = ap.parse_args()

    cur = snapshot()

    if args.mode == "show":
        print("Current payroll net board:")
        _print_board(cur)
        return 0

    if args.mode == "before":
        SNAP.parent.mkdir(parents=True, exist_ok=True)
        SNAP.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"BEFORE snapshot saved ({len(cur)} runs) -> {SNAP.name}")
        _print_board(cur)
        return 0

    # mode == after
    if not SNAP.exists():
        print("FAIL  no BEFORE snapshot — run `net_guard.py before` first")
        return 1
    before = json.loads(SNAP.read_text(encoding="utf-8"))
    allow = {x.strip() for x in args.allow.split(",") if x.strip()}

    bad: list[str] = []
    all_ids = sorted(set(before) | set(cur), key=int)
    for rid in all_ids:
        b = before.get(rid, {}).get("net")
        a = cur.get(rid, {}).get("net")
        if b == a:
            continue
        site = (cur.get(rid) or before.get(rid))["site"]
        delta = (a or 0) - (b or 0)
        if rid in allow:
            print(f"OK    run {rid} {site} moved (allowed): {b} -> {a}  (Δ {delta:+,.2f})")
        else:
            bad.append(rid)
            print(f"❌    run {rid} {site} CHANGED but not in --allow: {b} -> {a}  (Δ {delta:+,.2f})")

    if bad:
        print(f"\nRESULT FAIL — {len(bad)} unexpected net change(s): {','.join(bad)}")
        return 1
    print("\nRESULT OK — only allowed runs moved; every other net is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
