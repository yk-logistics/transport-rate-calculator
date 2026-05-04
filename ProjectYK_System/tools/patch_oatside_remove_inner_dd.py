# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"
s = p.read_text(encoding="utf-8")
old = (
    '    """+50% of one trip rate when a rolling 24h window from Origin_In contains exactly 1 matched trip."""\n'
    "    from collections import defaultdict as _dd\n"
    "    by_pl: dict[str, list[Trip]] = _dd(list)\n"
)
new = (
    '    """+50% of one trip rate when a rolling 24h window from Origin_In contains exactly 1 matched trip."""\n'
    "    by_pl: dict[str, list[Trip]] = defaultdict(list)\n"
)
if old not in s:
    raise SystemExit("inner defaultdict block not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("ok")
