"""Side-by-side comparison of system net vs PDF net after v7 fixes."""
import sys, io
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from sqlmodel import Session, select
import main
from models import PayRun, PayRunItem

PDF = {
    ("BIGC", "2025-12"): 116_187,
    ("BIGC", "2026-01"): 127_004,
    ("BIGC", "2026-02"): 134_236,
    ("AYU",  "2026-01"): 76_223,
    ("AYU",  "2026-02"): 104_503,
    ("AYU",  "2026-03"): 107_563,
    ("LCB",  "2025-12"): 263_511,
    ("LCB",  "2026-02"): 273_811,
    ("LCB",  "2026-03"): 257_901,
}
V6_SYSTEM = {
    ("BIGC", "2025-12"): 130_355,
    ("BIGC", "2026-01"): 132_577,
    ("BIGC", "2026-02"): 117_390,
    ("AYU",  "2026-01"): 196_782,
    ("AYU",  "2026-02"): 241_846,
    ("AYU",  "2026-03"): 285_994,
    ("LCB",  "2025-12"): 373_988,
    ("LCB",  "2026-02"): 419_786,
    ("LCB",  "2026-03"): 457_123,
}

with Session(main.engine) as s:
    print(f"{'Cycle':<12} {'PDF':>10} {'v6':>10} {'v7':>10} {'Δ v7-PDF':>10} {'%':>6}")
    print("-" * 65)
    for key, pdf_net in PDF.items():
        site, tag = key
        pr = s.exec(
            select(PayRun).where(PayRun.site_code == site, PayRun.pay_cycle_tag == tag)
        ).first()
        if not pr:
            continue
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
        v7 = sum((it.net_pay or 0) for it in items)
        diff = v7 - pdf_net
        pct = (diff / pdf_net * 100) if pdf_net else 0
        v6 = V6_SYSTEM.get(key, 0)
        print(f"{site} {tag:<7} {pdf_net:>10,} {v6:>10,} {v7:>10,.0f} {diff:>+10,.0f} {pct:>+5.1f}%")
