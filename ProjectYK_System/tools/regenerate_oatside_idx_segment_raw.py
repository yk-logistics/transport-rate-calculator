# -*- coding: utf-8 -*-
"""Rewrite ProjectYK_System/tools/_idx_segment_raw.txt from current Oatside/build_oatside_reports.py."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "Oatside" / "build_oatside_reports.py"
OUT = ROOT / "ProjectYK_System" / "tools" / "_idx_segment_raw.txt"


def main() -> None:
    s = BUILDER.read_text(encoding="utf-8")
    start = s.find("<div class='panel'><p class='sub'><b>สีไฮไลต์:")
    if start < 0:
        raise SystemExit("start marker (สีไฮไลต์ panel) not found")
    um = s.find("{um_section_html}", start)
    if um < 0:
        raise SystemExit("{um_section_html} not found after color panel")
    close = s.find("</tbody></table></div>\n<details", um)
    if close < 0:
        raise SystemExit("closing (3) table before Audit <details> not found")
    mid = s[start : close + len("</tbody></table></div>")]
    OUT.write_text(mid, encoding="utf-8")
    print("wrote", OUT, "chars", len(mid))


if __name__ == "__main__":
    main()
