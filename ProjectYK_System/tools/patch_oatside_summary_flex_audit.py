# -*- coding: utf-8 -*-
"""Flex summary: push Excel link right; move (คลิกเพื่อขยาย) to start of Audit label."""
from __future__ import annotations

from pathlib import Path

P = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")


def main() -> None:
    s = P.read_text(encoding="utf-8")

    old_css = (
        '"".section-sum-row{display:flex;justify-content:space-between;align-items:center;gap:12px}""'
        'summary.section-sum-row .sum-main{flex:1;text-align:left}""'
        'summary.section-sum-row .sum-dl{flex-shrink:0}""'
    )
    new_css = (
        '""summary.section-sum-row{display:flex!important;width:100%;box-sizing:border-box;'
        'justify-content:space-between;align-items:center;gap:12px;list-style:none}""'
        'summary.section-sum-row .sum-main{flex:1 1 auto;min-width:0;text-align:left}""'
        'summary.section-sum-row .sum-dl{margin-left:auto;flex:0 0 auto}""'
    )
    if old_css not in s:
        raise SystemExit("css block not found (already patched?)")
    s = s.replace(old_css, new_css, 1)

    old_audit = (
        "<span class='sum-main'>Audit Log — เหตุผลการคิดเงิน รายวัน × ทะเบียน (คลิกเพื่อขยาย)</span>"
    )
    new_audit = (
        "<span class='sum-main'>(คลิกเพื่อขยาย) Audit Log — เหตุผลการคิดเงิน รายวัน × ทะเบียน</span>"
    )
    if old_audit not in s:
        raise SystemExit("audit span not found")
    s = s.replace(old_audit, new_audit, 1)

    P.write_text(s, encoding="utf-8")
    print("patched", P)


if __name__ == "__main__":
    main()
