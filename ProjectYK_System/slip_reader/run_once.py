from __future__ import annotations
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from . import config, slip_source, mvp_push
from .engine import get_engine
from .plan_context import parse_plan
from .entry_builder import build_entry

DB = r"C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db"
GROUP = "หัวลาก LCB"


def main(since=None) -> int:
    engine = get_engine(config.SLIP_ENGINE)
    slips = slip_source.company_slips(DB, GROUP, since=since)
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
    return pushed


if __name__ == "__main__":
    main(since=sys.argv[1] if len(sys.argv) > 1 else None)
