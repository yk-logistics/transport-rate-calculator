"""Generate payroll PDF bundles (สรุปรวม / โอนเงิน / สลิปแต่ละคน) — saves under data/Salary/{SITE}/{เดือนจ่าย}/Driver/.

BIGC: งวดวิ่งมีนาคม (pay_cycle_tag=2026-03) → เก็บที่โฟลเดอร์เดือนจ่ายเมษายน (2026-04).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from fpdf import FPDF

from models import Employee, PayRunItem
from services.payroll_slip import (
    bank_display_line,
    build_payroll_slip_context,
    cycle_tag_th_label,
    employee_bank_display_name,
    export_driver_folder,
    merged_bank_terms,
    salary_folder_month_tag,
)


def _fmt_money_simple(x: float) -> str:
    try:
        v = float(x or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:,.2f}"


def _dep_install_str(emp) -> str:
    """งวดเงินประกันตน 'X/Y' — ตรงกับ web slip (_fmt_dep_install):
    X = งวดที่กำลังหักรอบนี้ = paid+1 (paid = bal//unit); ถ้าครบ/พักหัก = paid.
    หน่วยงวดต่อคน (deposit_install_unit ใน custom_terms; ธัชชนพล/เสรี = 2,000)."""
    import json as _json
    tgt = getattr(emp, "deposit_target", 0) or 0
    if tgt <= 0:
        return ""
    raw = getattr(emp, "custom_terms", "") or ""
    unit = 1000.0
    held = False
    try:
        obj = _json.loads(raw) if raw else {}
        if isinstance(obj, dict):
            unit = float(obj.get("deposit_install_unit") or 1000.0)
            held = bool(obj.get("deposit_hold"))
    except Exception:
        pass
    bal = getattr(emp, "deposit_balance", 0) or 0
    total = int(round(tgt / unit))
    paid = int(round(bal / unit))
    if held or paid >= total:
        current = min(paid, total)
    else:
        current = paid + 1
    return f"{current}/{total}"


def _safe_filename(name: str, max_len: int = 80) -> str:
    s = re.sub(r'[<>:"/\\\\|?*\\x00-\\x1f]', "_", name.strip())
    return s[:max_len] if len(s) > max_len else s


def _find_thai_font() -> tuple[str, Path]:
    """Return (family_alias, path_to_ttf). Prefer Tahoma on Windows."""
    candidates = [
        Path(r"C:\Windows\Fonts\tahoma.ttf"),
        Path(r"C:\Windows\Fonts\Tahoma.ttf"),
        Path(r"C:\Windows\Fonts\THSarabunNew.ttf"),
        Path(r"C:\Windows\Fonts\TH Sarabun New.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ("YKFont", p)
    raise FileNotFoundError(
        "ไม่พบฟอนต์ไทย (Tahoma / TH Sarabun) — ติดตั้งฟอนต์ใน Windows"
    )


class _Pdf(FPDF):
    def __init__(self, orientation: str = "P", auto_break: bool = True, break_margin: float = 12) -> None:
        super().__init__(orientation=orientation, unit="mm", format="A4")
        fam, font_path = _find_thai_font()
        self._font_family = fam
        self.add_font(fam, "", str(font_path))
        self.add_font(fam, "B", str(font_path))
        self.set_auto_page_break(auto=auto_break, margin=break_margin)

    def set_font_default(self, size: float = 10, bold: bool = False) -> None:
        style = "B" if bold else ""
        self.set_font(self._font_family, style, size)


def render_summary_page(pdf: _Pdf, title: str, subtitle: str, rows: list[tuple]) -> None:
    """rows: (idx, name, trip, base, fuel_rt, gross, ss, tax, petty, net)."""
    pdf.add_page(orientation="L")
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 297, 14, "F")
    pdf.set_xy(8, 4)
    pdf.set_font_default(11, bold=True)
    pdf.cell(220, 7, title)
    pdf.set_font_default(8, bold=False)
    pdf.cell(61, 7, subtitle[:52], align="R")
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(8, 18)
    pdf.set_font_default(9)
    pdf.cell(0, 5, f"เรียงตามชื่อ · {len(rows)} คน", ln=True)
    pdf.ln(1)

    col_w = (10, 46, 19, 19, 21, 21, 18, 17, 19, 21)
    headers = ("ลำดับ", "ชื่อ–สกุล", "ค่าเที่ยว", "เงินเดือน", "ค่าเรทน้ำมัน", "รวมรายได้", "ประกันสังคม", "ภาษี", "หักสดย่อย", "สุทธิรับ")
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font_default(7, bold=True)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font_default(7)
    sums = [0.0] * 8
    zebra = False
    for row in rows:
        zebra = not zebra
        if zebra:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        idx, name, trip, base, frt, gross, ss, tax, petty, net = row
        sums[0] += trip
        sums[1] += base
        sums[2] += frt
        sums[3] += gross
        sums[4] += ss
        sums[5] += tax
        sums[6] += petty
        sums[7] += net
        vals = (
            str(idx),
            name[:42],
            _fmt_money_simple(trip),
            _fmt_money_simple(base),
            _fmt_money_simple(frt),
            _fmt_money_simple(gross),
            _fmt_money_simple(ss),
            _fmt_money_simple(tax),
            _fmt_money_simple(petty),
            _fmt_money_simple(net),
        )
        for i, v in enumerate(vals):
            pdf.cell(col_w[i], 6, v, border=1, fill=True)
        pdf.ln()

    pdf.set_fill_color(241, 245, 249)
    pdf.set_font_default(8, bold=True)
    pdf.cell(col_w[0] + col_w[1], 6, "รวม", border=1, fill=True)
    for i, t in enumerate(sums):
        pdf.cell(col_w[2 + i], 6, _fmt_money_simple(t), border=1, fill=True)
    pdf.ln()


def render_bank_page(pdf: _Pdf, site: str, title_cycle: str, bank_rows: list[tuple]) -> None:
    """bank_rows: (idx, full_name, bank_line, account_no, net_pay)."""
    pdf.add_page(orientation="P")
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 210, 11, "F")
    pdf.set_xy(8, 3)
    pdf.set_font_default(11, bold=True)
    pdf.cell(0, 6, f"โอนเงินเดือน · {site}", ln=True)
    pdf.set_text_color(30, 41, 59)
    pdf.set_xy(8, 13)
    pdf.set_font_default(8, bold=False)
    pdf.cell(0, 5, title_cycle[:110], ln=True)
    pdf.set_font_default(8)
    pdf.multi_cell(
        0,
        4,
        "ธนาคารจากข้อมูลพนักงาน (JSON) · BIGC เติมอัตโนมัติจากชุดตัวอย่างเมื่อยังไม่กรอกเลขบัญชี",
    )
    pdf.ln(2)

    w = (11, 68, 34, 38, 28)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font_default(8, bold=True)
    headers = ("ลำดับ", "ชื่อ–สกุล", "ธนาคาร / ช่องทาง", "เลขบัญชี", "จำนวนโอน")
    for i, h in enumerate(headers):
        pdf.cell(w[i], 7, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font_default(8)
    grand = 0.0
    zebra = False
    for idx, name, bank_ln, acct, amt in bank_rows:
        zebra = not zebra
        grand += amt
        if zebra:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(w[0], 7, str(idx), border=1, fill=True)
        pdf.cell(w[1], 7, name[:44], border=1, fill=True)
        pdf.cell(w[2], 7, bank_ln[:22], border=1, fill=True)
        pdf.cell(w[3], 7, acct[:26], border=1, fill=True)
        pdf.cell(w[4], 7, _fmt_money_simple(amt), border=1, fill=True)
        pdf.ln()

    pdf.set_fill_color(241, 245, 249)
    pdf.set_font_default(9, bold=True)
    pdf.cell(w[0] + w[1] + w[2] + w[3], 7, "รวม", border=1, fill=True)
    pdf.cell(w[4], 7, _fmt_money_simple(grand), border=1, fill=True)
    pdf.ln()


def _pdf_bank_title_cycle(pr: Any) -> str:
    """หัวข้อชุดโอนเงิน — BIGC แยกจ่ายกับงวดวิ่ง."""
    site = (pr.site_code or "").upper()
    work = cycle_tag_th_label(pr.pay_cycle_tag or "")
    fold = salary_folder_month_tag(pr)
    pay = cycle_tag_th_label(fold) if fold else ""
    if site == "BIGC" and fold and pr.pay_cycle_tag and fold != pr.pay_cycle_tag:
        return f"จ่ายเดือน {pay} · วิ่งงาน {work}"
    return f"รอบ {work}"


def _slip_period_line(run: Any) -> str:
    """หัวข้อสลิปรายคน."""
    site = (run.site_code or "").upper()
    work_lbl = cycle_tag_th_label(run.pay_cycle_tag or "")
    fold = salary_folder_month_tag(run)
    pay_lbl = cycle_tag_th_label(fold) if fold else ""
    if site == "BIGC" and fold and run.pay_cycle_tag and fold != run.pay_cycle_tag:
        return f"จ่ายเดือน {pay_lbl} · วิ่งงาน {work_lbl}"
    return f"ช่วง {run.period_start} → {run.period_end} · รอบ {work_lbl}"


def render_driver_slip_page(pdf: _Pdf, ctx: dict[str, Any]) -> None:
    """สลิปรายคน 1 หน้า · แนวนอน · ซ้าย=รายเที่ยว / ขวา=สรุปเงิน."""
    emp = ctx["employee"]
    item = ctx["item"]
    run = ctx["run"]
    daily_jobs = ctx["daily_jobs"]

    pdf.add_page(orientation="L")
    pdf.set_auto_page_break(False, margin=0)

    period_line = ctx.get("pdf_period_line") or _slip_period_line(run)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 297, 18, "F")
    pdf.set_xy(8, 5)
    pdf.set_font_default(11, bold=True)
    pdf.cell(175, 7, "Y.K. Logistics — สลิปเงินเดือน")
    pdf.set_font_default(8, bold=False)
    pdf.set_text_color(226, 232, 240)
    pdf.cell(106, 7, period_line[:68], align="R", ln=True)

    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(8, 22)
    pdf.set_font_default(11, bold=True)
    name_w = 195
    disp_nm = employee_bank_display_name(emp, run.site_code or "")
    pdf.cell(name_w, 6, disp_nm + (f" ({emp.nickname})" if emp.nickname else ""))
    pdf.set_font_default(8, bold=False)
    pdf.cell(86, 6, f"{emp.code} · {run.site_code}", align="R", ln=True)
    pdf.set_x(8)
    pdf.set_font_default(8)
    pdf.cell(0, 5, f"ทะเบียน {ctx.get('plates_used') or '—'}", ln=True)

    left_x = 8.0
    left_w = 150.0
    gap = 5.0
    right_x = left_x + left_w + gap
    right_w = 297 - right_x - 8

    mid_top = pdf.get_y() + 2
    net_h = 13.0
    mid_bottom = 210 - 8 - net_h  # bottom page margin + net strip
    mid_h = mid_bottom - mid_top

    n = len(daily_jobs)
    head_h = 5.5
    tab_body = max(12.0, mid_h - head_h)
    denom = float(max(n + 1, 1))
    row_h = max(3.0, min(5.5, tab_body / denom))
    fs = 7.0
    if row_h < 4.2:
        fs = 6.5
    if row_h < 3.7:
        fs = 6.0
    if row_h < 3.2:
        fs = 5.5
    if row_h < 2.85:
        fs = 5.0

    cw = (19, 18, 50, 20, 12, 15, 12)
    hdr = ("วันที่", "ทะเบียน", "ปลายทาง / หมายเหตุ", "ใบงาน", "น้ำมัน", "ค่าเที่ยว", "เรท")

    y0 = mid_top
    pdf.set_xy(left_x, y0)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font_default(max(fs - 0.5, 4.5), bold=True)
    for i, h in enumerate(hdr):
        pdf.cell(cw[i], head_h, h, border=1, fill=True)
    pdf.ln()

    pdf.set_font_default(fs, bold=False)
    z = False
    max_y = mid_top + mid_h - 2
    for r in daily_jobs:
        if pdf.get_y() + row_h > max_y:
            break
        z = not z
        pdf.set_x(left_x)
        if z:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        dest = (r.destination or "").strip()
        if r.remark:
            dest = (dest + " · " + r.remark.strip())[:48]
        else:
            dest = dest[:48]
        pdf.cell(cw[0], row_h, str(r.work_date), border=1, fill=True)
        pdf.cell(cw[1], row_h, (r.plate_no_raw or "")[:12], border=1, fill=True)
        pdf.cell(cw[2], row_h, dest, border=1, fill=True)
        pdf.cell(cw[3], row_h, (r.doc_no or r.job_ref or "")[:14], border=1, fill=True)
        pdf.cell(cw[4], row_h, (f"{r.fuel_liter:.0f}" if r.fuel_liter else ""), border=1, fill=True)
        pdf.cell(cw[5], row_h, (_fmt_money_simple(r.trip_fee_driver) if r.trip_fee_driver else ""), border=1, fill=True)
        pdf.cell(cw[6], row_h, (f"{r.fuel_rate_km_per_l:.2f}" if r.fuel_rate_km_per_l else ""), border=1, fill=True)
        pdf.ln()

    # Right column — สรุป
    # fpdf: cell(..., ln=True) จะรีเซ็ต x ไปขอบซ้ายของหน้า — ต้อง set_x ก่อนทุกบรรทัดจึงจะไม่ทับตารางซ้าย
    rx = right_x + 2
    rw_inner = right_w - 4
    ry = mid_top
    pdf.set_xy(right_x, ry)
    pdf.set_fill_color(241, 245, 249)
    pdf.rect(right_x, ry, right_w, mid_h, "D")

    def _rcell(txt: str, h: float, fs: float, bold: bool = False) -> None:
        pdf.set_x(rx)
        pdf.set_font_default(fs, bold=bold)
        pdf.cell(rw_inner, h, txt, ln=True)

    pdf.set_xy(rx, ry + 2)
    _rcell("การใช้รถ / น้ำมัน", 4, 8, bold=True)
    ms, me = ctx["mile_start"], ctx["mile_end"]
    if ms or me:
        mile_txt = f"ไมล์เริ่ม–จบ: {ms:,.0f} – {me:,.0f}"
    else:
        mile_txt = "ไมล์เริ่ม–จบ: —"
    _rcell(mile_txt, 3.8, 7.5)
    _rcell(
        f"กม.ที่วิ่ง: {ctx['km_run']:,.0f}" if ctx["km_run"] else "กม.ที่วิ่ง: —",
        3.8,
        7.5,
    )
    _rcell(
        f"น้ำมันใช้: {ctx['fuel_used_l']:,.2f} L" if ctx["fuel_used_l"] else "น้ำมันใช้: —",
        3.8,
        7.5,
    )
    _rcell(
        f"เรทเฉลี่ย: {ctx['avg_km_per_l']:.2f} km/L" if ctx["avg_km_per_l"] else "เรทเฉลี่ย: —",
        3.8,
        7.5,
    )
    _rcell(
        f"วันทำงาน {item.days_worked:.0f} · ลา {item.days_leave:.0f} · ขาด {item.days_absent:.0f}",
        3.8,
        7.5,
    )
    pdf.set_x(rx)
    pdf.ln(2)

    inc = [
        ("เงินเดือน", item.base_salary_earned or 0),
        ("ค่าดูแลรถ", item.care_allowance_earned or 0),
        ("ค่าเที่ยว", item.trip_fee_total or 0),
        ("ค่าเรทน้ำมัน", item.fuel_rate_income or 0),
        ("ส่วนแบ่งน้ำมัน", item.fuel_share_income or 0),
        ("ชดเชยการันตี", item.guarantee_topup or 0),
    ]
    inc = [(a, b) for a, b in inc if b]
    _rcell("รายได้", 4, 8, bold=True)
    for lab, amt in inc:
        _rcell(f"· {lab} {_fmt_money_simple(amt)}", 3.8, 7.5)
    _rcell(f"รวมรายได้ {_fmt_money_simple(item.gross_total)}", 4.2, 8, bold=True)
    pdf.set_x(rx)
    pdf.ln(1)

    ded = [
        ("ประกันสังคม", item.social_security or 0),
        ("ภาษีหัก ณ ที่จ่าย", item.income_tax_withholding or 0),
        ("เงินประกัน (ผ่อน)" + (f" งวดที่ {_dep_install_str(emp)}" if (item.deposit_install and _dep_install_str(emp)) else ""), item.deposit_install or 0),
        ("ผ่อนอุบัติเหตุ", item.accident_install or 0),
        ("ค่าน้ำมัน (ออกเอง)", item.fuel_cost_self or 0),
        ("หักอื่นๆ", item.other_deduction or 0),
    ]
    ded = [(a, b) for a, b in ded if b]
    petty_lines = ctx.get("petty_lines") or []
    max_petty = 10
    for pl in petty_lines[:max_petty]:
        ded.append((f"{pl['txn_date']} {pl['label'][:22]}", pl["amount"]))
    extra_petty = len(petty_lines) - max_petty
    _rcell("หัก", 4, 8, bold=True)
    for lab, amt in ded:
        _rcell(f"· {lab} {_fmt_money_simple(amt)}", 3.6, 7.5)
    if extra_petty > 0:
        _rcell(f"· … อีก {extra_petty} รายการสดย่อย (ดูในระบบ)", 3.6, 7.5)
    _rcell(f"รวมหัก {_fmt_money_simple(item.deduction_total)}", 4.2, 8, bold=True)

    # Net bar
    ny = 210 - 8 - net_h + 1
    pdf.set_xy(left_x, ny)
    pdf.set_fill_color(5, 150, 105)
    pdf.set_draw_color(5, 150, 105)
    pdf.rect(left_x, ny, 281, net_h - 1, "DF")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font_default(12, bold=True)
    pdf.cell(180, net_h - 2, "ยอดรับสุทธิ", ln=0)
    pdf.set_font_default(13, bold=True)
    pdf.cell(101, net_h - 2, _fmt_money_simple(item.net_pay) + " บาท", align="R", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)

    pdf.set_auto_page_break(True, margin=12)


def export_payroll_pdf_bundle(session, pay_run_id: int, project_root: Optional[Path] = None) -> dict[str, Any]:
    from sqlmodel import select

    from models import PayRun

    pr = session.get(PayRun, pay_run_id)
    if pr is None:
        raise ValueError("PayRun not found")

    items = session.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pay_run_id)).all()
    pairs: list[tuple[PayRunItem, Employee]] = []
    for it in items:
        emp = session.get(Employee, it.employee_id)
        if emp:
            pairs.append((it, emp))

    pairs.sort(key=lambda p: employee_bank_display_name(p[1], pr.site_code or ""))

    folder_month = salary_folder_month_tag(pr)
    pay_sub = _pdf_bank_title_cycle(pr)
    period_note = f"ช่วง {pr.period_start} → {pr.period_end}"

    out_dir = export_driver_folder(pr.site_code, folder_month, project_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    per_dir = out_dir / "รายคน"
    per_dir.mkdir(parents=True, exist_ok=True)

    site_tag = f"{pr.site_code}_{folder_month}_วิ่ง{pr.pay_cycle_tag}"

    site_sc = pr.site_code or ""
    sum_rows = []
    bank_rows = []
    for idx, (it, emp) in enumerate(pairs, start=1):
        disp_nm = employee_bank_display_name(emp, site_sc)
        sum_rows.append(
            (
                idx,
                disp_nm,
                it.trip_fee_total or 0,
                it.base_salary_earned or 0,
                it.fuel_rate_income or 0,
                it.gross_total or 0,
                it.social_security or 0,
                it.income_tax_withholding or 0,
                it.petty_cash_deduction or 0,
                it.net_pay or 0,
            )
        )
        bt = merged_bank_terms(emp, pr.site_code or "")
        bank_ln, acct = bank_display_line(bt)
        bank_rows.append((idx, disp_nm, bank_ln, acct, it.net_pay or 0))

    sum_title = f"สรุปรวม YK · {pr.site_code}"
    sum_sub = f"{pay_sub} · {period_note}"

    pdf_sum = _Pdf("L")
    render_summary_page(
        pdf_sum,
        sum_title,
        sum_sub,
        sum_rows,
    )
    p_summary = out_dir / f"{site_tag}_สรุปรวม.pdf"
    pdf_sum.output(str(p_summary))

    pdf_bank = _Pdf("P")
    render_bank_page(pdf_bank, pr.site_code, pay_sub + " · " + period_note, bank_rows)
    p_bank = out_dir / f"{site_tag}_โอนเงินบัญชี.pdf"
    pdf_bank.output(str(p_bank))

    pdf_all = _Pdf("P")
    render_summary_page(
        pdf_all,
        sum_title,
        pay_sub,
        sum_rows,
    )
    render_bank_page(pdf_all, pr.site_code, pay_sub + " · " + period_note, bank_rows)

    slip_paths = []
    for it, emp in pairs:
        ctx = build_payroll_slip_context(session, pr, emp, it)
        ctx["pdf_period_line"] = _slip_period_line(pr)
        render_driver_slip_page(pdf_all, ctx)
        pdf_one = _Pdf("L", auto_break=False)
        render_driver_slip_page(pdf_one, ctx)
        slip_fn = (
            _safe_filename(f"{employee_bank_display_name(emp, site_sc)}_{folder_month}_{pr.pay_cycle_tag}") + ".pdf"
        )
        p_one = per_dir / slip_fn
        pdf_one.output(str(p_one))
        slip_paths.append(str(p_one))

    p_bundle = out_dir / f"{site_tag}_ชุดครบ_สรุปโอนสลิป.pdf"
    pdf_all.output(str(p_bundle))

    return {
        "site_code": pr.site_code,
        "pay_cycle_tag": pr.pay_cycle_tag,
        "folder_month_tag": folder_month,
        "out_dir": str(out_dir.resolve()),
        "files": {
            "summary_pdf": str(p_summary.resolve()),
            "bank_pdf": str(p_bank.resolve()),
            "bundle_pdf": str(p_bundle.resolve()),
            "per_driver_folder": str(per_dir.resolve()),
            "per_driver_pdfs": slip_paths,
        },
    }


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[3]
