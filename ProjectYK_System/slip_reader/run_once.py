from __future__ import annotations
import sys
import io

from . import config, slip_source, mvp_push, mvp_config
from .engine import get_engine
from .plan_context import parse_plan
from .entry_builder import build_entry

# Server default; override on dev with SLIP_ARCHIVE_DB env var.
import os
DB = os.environ.get("SLIP_ARCHIVE_DB", r"C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db")
GROUP = "หัวลาก LCB"


def main(since=None) -> int:
    # Money gate: ask the MVP if we're enabled BEFORE building the engine or making
    # any Anthropic call. OFF (and no "check now") → exit early, zero API spend.
    cfg = mvp_config.fetch_config()
    if not cfg.get("enabled") and not cfg.get("run_now"):
        msg = "DISABLED" if "error" not in cfg else f"CONFIG_UNREACHABLE {cfg['error']}"
        print(msg)
        return 0
    # MVP-set since-date wins over the CLI/rolling-window arg (blank = keep `since`).
    cfg_since = (cfg.get("since") or "").strip()
    if cfg_since:
        since = f"{cfg_since} 00:00:00"

    engine = get_engine(config.SLIP_ENGINE)
    slips = slip_source.company_slips(DB, GROUP, since=since)
    # Optional single-day filter (SLIP_ONLY_DAY=16.06.26) — for targeted/test runs.
    only_day = os.environ.get("SLIP_ONLY_DAY", "")
    if only_day:
        slips = [s for s in slips if s["day_ddmmyy"] == only_day]
    plan_cache: dict[str, dict] = {}
    pushed = 0
    for s in slips:
        day = s["day_ddmmyy"]
        if day not in plan_cache:
            texts = slip_source.day_plans(DB, GROUP, day)
            texts.sort(key=lambda x: x[0])
            plan_cache[day] = parse_plan(texts[-1][1]) if texts else {}
        try:
            with open(s["media_abspath"], "rb") as f:
                readout = engine.read(f.read())
        except Exception as e:
            print("READ_FAIL", s["message_id"], e)
            continue
        payload = build_entry(readout, day=day, plan=plan_cache[day],
                              slip_line_message_id=s["message_id"],
                              slip_media_path=s["media_abspath"])
        if not payload:
            print("SKIP non-slip/no-amount", s["message_id"])
            continue
        res = mvp_push.push(payload)
        print(res["status"], res.get("id"), payload["requester_raw"], payload["amount"])
        if res["status"] == "created":
            pushed += 1
    print("PUSHED", pushed, "of", len(slips))
    # Report status back + ack any "check now" so it fires once, not every poll.
    mvp_config.report(f"pushed {pushed} of {len(slips)}", ack_run_now=bool(cfg.get("run_now")))
    return pushed


if __name__ == "__main__":
    # Force UTF-8 stdout so Thai names print on the Windows (cp1252) server console.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main(since=sys.argv[1] if len(sys.argv) > 1 else None)
