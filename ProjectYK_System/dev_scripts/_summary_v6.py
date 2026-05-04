"""Clean side-by-side summary: PDF vs System per cycle."""
import sys, io
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from sqlmodel import Session, select
from sqlalchemy import func as sf
import main
from models import Employee, PayRun, PayRunItem

# PDF truth (net only, driver section only — no office)
PDF = {
    ("BIGC", "2025-12"): ("BIGC JAN",  116_187),
    ("BIGC", "2026-01"): ("BIGC FEB",  127_004),
    ("BIGC", "2026-02"): ("BIGC MAR",  134_236),
    ("AYU",  "2026-01"): ("AYU JAN",    76_223),   # drivers only (30,391 + 45,832)
    ("AYU",  "2026-02"): ("AYU FEB",   104_503),
    ("AYU",  "2026-03"): ("AYU MAR",   107_563),
    ("LCB",  "2025-12"): ("LCB JAN",   263_511),
    ("LCB",  "2026-02"): ("LCB FEB",   273_811),
    ("LCB",  "2026-03"): ("LCB MAR",   257_901),
}

with Session(main.engine) as s:
    print(f"\n{'Cycle':<12} {'PDF Net':>14} {'Sys Net':>14} {'Diff':>12} {'% diff':>8}")
    print("-" * 66)
    for (site, tag), (label, pdf_net) in PDF.items():
        pr = s.exec(
            select(PayRun).where(PayRun.site_code == site, PayRun.pay_cycle_tag == tag)
        ).first()
        if not pr:
            print(f"{label:<12} {pdf_net:>14,.2f}  [no PayRun found]")
            continue
        sys_net = s.exec(
            select(sf.sum(PayRunItem.net_pay)).where(PayRunItem.pay_run_id == pr.id)
        ).one() or 0
        diff = sys_net - pdf_net
        pct = (diff / pdf_net * 100) if pdf_net else 0
        print(f"{label:<12} {pdf_net:>14,.2f} {sys_net:>14,.2f} {diff:>+12,.2f} {pct:>+7.1f}%")
