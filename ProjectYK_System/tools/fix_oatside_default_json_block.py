# -*- coding: utf-8 -*-
"""Fix corrupted _DEFAULT_CONFIG_JSON (false -> False, indentation)."""
from __future__ import annotations

import re
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    pat = re.compile(
        r'"use_origin_24h_fifty":\s*false,.*?"charge_min_trip_shortfall":\s*False,',
        re.DOTALL,
    )
    m = pat.search(s)
    if not m:
        raise SystemExit("pattern not found")
    new = '''    "use_origin_24h_fifty": False,
    "_note_use_origin_24h_fifty": "true = 50pct downtime from rolling 24h windows anchored at each trip Origin_In chain; false = legacy Dest_In calendar day (1 trip => +50pct)",
    "customer_idle_windows": [
        {
            "_note": "71-8967 P&G factory parking — customer-irrelevant dwell (CONTEXT_LOG Session #90–91)",
            "plate": "71-8967",
            "start": "2026-04-20 14:00:00",
            "end": "2026-04-29 17:00:00",
            "note": "Parked at customer — clip dest wait from Daily_Time / gap vs 24h",
        },
    ],
    "charge_min_trip_shortfall": False,'''
    s2 = s[: m.start()] + new + s[m.end() :]
    TARGET.write_text(s2, encoding="utf-8")
    print("fixed block", m.end() - m.start(), "->", len(new))


if __name__ == "__main__":
    main()
