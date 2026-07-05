"""Per-driver payroll-slip PDFs via headless Chrome → ZIP (returned to the browser, not saved on server).

Why Chrome (not the fpdf bundle in payroll_export_pdf.py, not client-side html2canvas):
  - fpdf  → Thai OK but a hand-drawn layout, not the HTML slip โอ wants.
  - html2canvas (old ZIP button) → rasterizes the DOM but cannot SHAPE Thai → tone marks/
    vowels detach (วรรณยุกต์ลอย). Confirmed broken in produced PDFs.
  - headless Chrome --print-to-pdf uses the real browser renderer → Thai correct AND the exact
    HTML slip layout, including the JS 1-page zoom-fit. Verified: glyphs render perfectly.

The slip page (payroll_slip.html) already auto-fits to one A4 page via its own JS (CSS `zoom`,
which Chrome's print engine honors). We render ONE driver per Chrome invocation so each file is
exactly that driver's slip.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import time
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from sqlmodel import select

from models import Employee, PayRun, PayRunItem
from services.payroll_slip import (
    build_payroll_slip_context,
    employee_bank_display_name,
    slip_anomaly_rows,
)


def find_chrome() -> Optional[str]:
    """Locate a Chrome/Edge executable (dev box and server are both Windows)."""
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    return None


def html_to_pdf_bytes(chrome: str, html: str, work_dir: Path) -> bytes:
    """Render one HTML string to PDF bytes via headless Chrome.

    Two Windows gotchas, both confirmed while building this:
      1. A unique --user-data-dir is REQUIRED, else Chrome hands off to an already-running
         instance and never renders.
      2. The chrome.exe launcher returns (exit 0) ~0.7s BEFORE the detached render child
         finishes writing the PDF. So we must POLL for the output file after the call returns,
         not check it once — otherwise we false-negative on a render that is actually succeeding.
    """
    src = work_dir / "slip.html"
    out = work_dir / "slip.pdf"
    profile = work_dir / "cprofile"
    src.write_text(html, encoding="utf-8")
    if out.exists():
        out.unlink()

    src_url = "file:///" + str(src).replace("\\", "/")
    args = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={out}",
        "--print-to-pdf-no-header",
        "--virtual-time-budget=10000",
        src_url,
    ]
    proc = subprocess.run(args, capture_output=True, timeout=120)

    # poll: the render child writes the file shortly after the launcher exits
    deadline = time.time() + 60
    last_size = -1
    while time.time() < deadline:
        if out.exists():
            sz = out.stat().st_size
            # wait until the file stops growing (write fully flushed)
            if sz > 0 and sz == last_size:
                return out.read_bytes()
            last_size = sz
        time.sleep(0.25)

    err = (proc.stderr or b"").decode("utf-8", "replace")[-500:]
    raise RuntimeError(f"Chrome did not produce a PDF (exit {proc.returncode}): {err}")


def _safe_filename(name: str, max_len: int = 80) -> str:
    s = (name or "unknown").strip()
    for ch in '<>:"/\\|?*':
        s = s.replace(ch, "_")
    s = " ".join(s.split())
    return s[:max_len]


def export_payroll_slips_zip(
    session,
    pay_run_id: int,
    render_slip_html,
    is_boss: bool = False,
) -> tuple[bytes, str]:
    """Build per-driver slip PDFs and return (zip_bytes, zip_filename).

    render_slip_html(ctx_dict) -> full standalone HTML for one driver's slip (caller passes a
    closure over the Jinja template so this service stays framework-free for testing).
    """
    pr = session.get(PayRun, pay_run_id)
    if pr is None:
        raise ValueError("PayRun not found")

    chrome = find_chrome()
    if chrome is None:
        raise RuntimeError(
            "ไม่พบ Chrome/Edge บนเครื่องนี้ — ติดตั้ง Google Chrome หรือกำหนด CHROME_PATH"
        )

    items = session.exec(
        select(PayRunItem).where(PayRunItem.pay_run_id == pay_run_id)
    ).all()
    pairs: list[tuple[PayRunItem, Employee]] = []
    for it in items:
        emp = session.get(Employee, it.employee_id)
        if emp:
            pairs.append((it, emp))
    # same order as the print page (highest net first)
    pairs.sort(key=lambda p: -(p[0].net_pay or 0))

    site = pr.site_code or ""
    cycle = pr.pay_cycle_tag or ""
    mode = "ผู้บริหาร" if is_boss else "คนขับ"

    # Work dir is created with a plain mkdir (NOT tempfile.TemporaryDirectory/mkdtemp): those
    # set owner-only 0o700 ACLs, and Chrome's headless render child then silently fails to write
    # the PDF (confirmed: identical input renders in ~1.4s from a plain-mkdir dir, hangs 60s from
    # a TemporaryDirectory). We root it next to the app (same writable place as uploads/reports).
    work_root = Path(__file__).resolve().parents[1] / "_pdf_tmp" / uuid.uuid4().hex
    work_root.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO()
    used: set[str] = set()
    anom_rows = slip_anomaly_rows(session, pr)  # scan ธงน้ำมันครั้งเดียวทั้งรอบ ไม่วนต่อคน
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, (it, emp) in enumerate(pairs, start=1):
                ctx = build_payroll_slip_context(session, pr, emp, it,
                                                 anomaly_rows=anom_rows)
                ctx["is_boss"] = is_boss
                html = render_slip_html(ctx)
                work = work_root / f"d{idx}"
                work.mkdir(parents=True, exist_ok=True)
                pdf = html_to_pdf_bytes(chrome, html, work)

                disp = employee_bank_display_name(emp, site)
                base = _safe_filename(f"{disp}_{site}_{cycle}_{mode}")
                fname = base + ".pdf"
                n = 2
                while fname in used:
                    fname = f"{base}_{n}.pdf"
                    n += 1
                used.add(fname)
                zf.writestr(fname, pdf)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    # ประทับวัน-เวลาที่สร้างในชื่อไฟล์ — โอโหลดหลายรอบแล้วชอบเปิดไฟล์เก่า (ชื่อซ้ำ
    # Windows เติม (1)(2) ให้ไฟล์ใหม่) → ชื่อไม่ซ้ำ + ดูออกทันทีว่าอันไหนล่าสุด
    from datetime import datetime

    stamp = datetime.now().strftime("%d-%m-%y_%H.%M")
    zip_name = _safe_filename(f"สลิปแยกคน_{site}_{cycle}_{mode}_สร้าง{stamp}") + ".zip"
    return buf.getvalue(), zip_name
