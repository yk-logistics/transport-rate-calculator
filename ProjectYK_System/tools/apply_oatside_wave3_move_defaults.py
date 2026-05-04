# -*- coding: utf-8 -*-
"""Move _DEFAULT_NO_WORK_RANGES block before _DEFAULT_CONFIG (fix NameError)."""
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


BLOCK_START = "_DEFAULT_NO_WORK_RANGES: list[tuple[date, date, str]] = ["
BLOCK_END = "_DEFAULT_OUTBOUND_HALF_DATES: frozenset[date] = _recovery_dest_dates_from_no_work(_DEFAULT_NO_WORK_RANGES)\n\n\n"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    i0 = s.find(BLOCK_START)
    if i0 < 0:
        raise SystemExit("BLOCK_START not found")
    i1 = s.find(BLOCK_END, i0)
    if i1 < 0:
        raise SystemExit("BLOCK_END not found")
    i1 += len(BLOCK_END)
    block = s[i0:i1]
    s_wo = s[:i0] + s[i1:]

    anchor = "\n_DEFAULT_CONFIG = OatsideConfig("
    a = s_wo.find(anchor)
    if a < 0:
        raise SystemExit("anchor not found")
    new_s = s_wo[:a] + "\n\n" + block + s_wo[a:]

    TARGET.write_text(new_s, encoding="utf-8")
    print("moved default no-work block before _DEFAULT_CONFIG")


if __name__ == "__main__":
    main()
