"""export_ayu_slips.py — render per-driver payroll slips (web layout, Chrome headless)
to a target folder. Same rendering as the /payroll/{id}/export-zip route → ไทยคมชัด +
งวดประกันตน X/Y ตรงกับ web slip.

usage: python ProjectYK_System/tools/export_ayu_slips.py <run_id> "<out_dir>"
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from sqlmodel import Session, select  # noqa: E402

from db_config import engine  # noqa: E402
from main import templates  # noqa: E402  (registers dep_install/dmy filters)
from models import Employee, PayRun, PayRunItem  # noqa: E402
from services.payroll_slip import build_payroll_slip_context, employee_bank_display_name  # noqa: E402
from services.payroll_zip_pdf import _safe_filename, find_chrome, html_to_pdf_bytes  # noqa: E402


def main() -> int:
    run_id = int(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    chrome = find_chrome()
    if chrome is None:
        print("FAIL no Chrome/Edge")
        return 1

    work_root = Path(__file__).resolve().parents[1] / "app" / "_pdf_tmp" / "ayu_slips"
    work_root.mkdir(parents=True, exist_ok=True)

    tpl = templates.get_template("payroll_slip.html")
    n = 0
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == run_id)).all()
        pairs = []
        for it in items:
            emp = s.get(Employee, it.employee_id)
            if emp:
                pairs.append((it, emp))
        pairs.sort(key=lambda p: -(p[0].net_pay or 0))
        site = pr.site_code or ""
        cycle = pr.pay_cycle_tag or ""
        for idx, (it, emp) in enumerate(pairs, start=1):
            ctx = build_payroll_slip_context(s, pr, emp, it)
            ctx["is_boss"] = False
            html = tpl.render(ctx)
            work = work_root / f"d{idx}"
            work.mkdir(parents=True, exist_ok=True)
            pdf = html_to_pdf_bytes(chrome, html, work)
            disp = employee_bank_display_name(emp, site)
            fname = _safe_filename(f"{disp}_{site}_{cycle}") + ".pdf"
            (out_dir / fname).write_bytes(pdf)
            n += 1
            print(f"  [{idx}] {fname} ({len(pdf)} bytes)")
    print(f"DONE — {n} slips -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
