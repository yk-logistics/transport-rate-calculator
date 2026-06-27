"""Test that report rendering writes files containing the key figures."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from matcher import reconcile  # noqa: E402
from models import FuelBill, SysFuel  # noqa: E402
from report import render  # noqa: E402


def test_render_writes_files_with_totals(tmp_path):
    bills = [FuelBill(date(2026, 6, 10), "71-8681", "ทวีโชค", "Diesel B7", 50, 41.3, 2066.0)]
    sysf = [SysFuel(date(2026, 6, 11), "71-8681", 50, 2066.0, 101, "วราวุฒิ", "lcb_mao"),
            SysFuel(date(2026, 6, 12), "71-8681", 20, 999.0, 101, "วราวุฒิ", "lcb_mao")]
    r = reconcile(bills, sysf, date(2026, 5, 16), date(2026, 6, 15))
    html_path, md_path = render(r, "2026-06", str(tmp_path))
    assert Path(html_path).exists() and Path(md_path).exists()
    md = Path(md_path).read_text(encoding="utf-8")
    # the unmatched 999 system row should appear, and the เหมา driver section
    assert "999" in md
    assert "วราวุฒิ" in md
