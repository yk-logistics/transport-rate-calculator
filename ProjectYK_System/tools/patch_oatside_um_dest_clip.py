# -*- coding: utf-8 -*-
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    old = (
        "    for src, leg, _p in unmatched:\n"
        "        key = (leg.t_in.date(), leg.plate)\n"
        "        h = hours(leg.t_in, leg.t_out)\n"
        "        if h < 0 or h > 72:\n"
        "            continue\n"
        "        if src == \"Origin\":\n"
        "            uo[key] += h\n"
        "        else:\n"
        "            ud[key] += h\n"
    )
    new = (
        "    for src, leg, _p in unmatched:\n"
        "        key = (leg.t_in.date(), leg.plate)\n"
        "        h = hours(leg.t_in, leg.t_out)\n"
        "        if h < 0 or h > 72:\n"
        "            continue\n"
        "        if src == \"Origin\":\n"
        "            uo[key] += h\n"
        "        else:\n"
        "            h2 = h\n"
        "            for w in cfg.customer_idle_windows:\n"
        "                if w.plate == leg.plate:\n"
        "                    h2 -= w.overlap_hours(leg.t_in, leg.t_out)\n"
        "            ud[key] += max(0.0, h2)\n"
    )
    if old not in s:
        raise SystemExit("unmatched loop not found")
    TARGET.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("um dest clip ok")


if __name__ == "__main__":
    main()
