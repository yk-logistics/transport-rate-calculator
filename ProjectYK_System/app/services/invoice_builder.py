# -*- coding: utf-8 -*-
"""ออกใบวางบิล/ใบแจ้งหนี้จากระบบ (C2) — เติมฟอร์ม xlsx จาก template ไฟล์จริงของลูกค้า.

หลักการ (สเปค C2): **อย่าเขียน layout จากศูนย์** — template ใน app/invoice_templates/
คือสำเนาใบจริงจาก Drive "ใบวางบิล LCB/<ลูกค้า>" ทั้งไฟล์ (สูตร/สไตล์/ปะหน้าครบ)
ตัว builder แค่ลบแถวตู้เดิมแล้วเขียนแถวใหม่จากเดลี่ + ค่าที่ผู้ใช้กรอก.

ความจริงจากการดูดโครงไฟล์จริง (3ก.ค.69 — CYIV2606-023, KTIV2606-017/058):
- ชีท "ค่าขนส่ง" คือความจริง: แถวตู้เริ่ม row 16, ปะหน้าอ้างสูตรทั้งหมด
- ราคาต่อตู้ (J) = DailyJob.revenue_customer ตรงไฟล์จริงเป๊ะ (เทียบ KTIV2606-017 แล้ว)
- ค่าทดรองจ่าย/ค่าใช้จ่ายต่อตู้ **ไม่มีใน DB** → ผู้ใช้กรอกในฟอร์ม (default 0)
- ป้าย CUST./รายการบรรทุก (เช่น FITESACNC / LCB - CNC2) ไม่มีใน DB → กรอก/แก้ได้

builder นี้ **อ่านอย่างเดียว ไม่เขียน DB** — เลขใบที่ออกยังต้องคีย์ในกริดเองเหมือนเดิม
(กันเลขชน/กันเขียนผิดรอบ — รอโอเคาะค่อยให้ระบบเขียน invoice_no กลับ)
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = _APP_DIR / "invoice_templates"


@dataclass
class SeriesCfg:
    key: str                # รหัสชุด (โฟลเดอร์ Drive)
    label: str              # ชื่อโชว์
    prefix: str             # นำหน้าเลขใบ เช่น CYIV
    status_codes: tuple     # ค่า status_code ในเดลี่ของลูกค้ารายนี้
    template: str           # ไฟล์ใน invoice_templates/
    detail_sheet: str = "ค่าขนส่ง"
    row_start: int = 16
    row_end: int = 30       # แถวตู้สุดท้ายก่อนแถวรวม (inclusive)
    inv_cell: str = "G8"
    date_cell: str = "K8"
    # per-row columns บนชีทค่าขนส่ง
    col_route: str = "B"    # รายการบรรทุก
    col_cntr: str = "D"
    col_size: str = "E"
    col_plate: str = "F"
    col_cust: str = "G"
    col_job: str = "H"      # KMMT=JOB(job_ref), CY=BL(bl_booking)
    col_date: str = "I"
    col_price: str = "J"
    job_field: str = "job_ref"      # field ใน DailyJob ที่ลงคอลัมน์ job
    style: str = "advance_sheet"    # advance_sheet (KMMT) | advance_cols (CY)
    # advance_sheet: ชีทค่าทดรองจ่ายแยก mirror แถวด้วยสูตร + J=ยอด
    advance_sheet: str = "ค่าทดรองจ่าย"
    advance_row_end: int = 31
    # advance_cols (CY): ค่าล้าง/ซ่อม K + ค่าใช้จ่าย L + M=SUM(J:L) ในชีทเดียว
    col_wash: str = "K"
    col_advance: str = "L"
    col_amount: str = "M"
    remark_transport: str = "ค่าขนส่ง "


REGISTRY: dict[str, SeriesCfg] = {
    "KMMT": SeriesCfg(
        key="KMMT", label="KMMT / เคอรี่ (KLND)", prefix="KTIV",
        status_codes=("KLND",), template="KMMT.xlsx",
        row_end=30, advance_row_end=31, style="advance_sheet",
        inv_cell="G8", date_cell="K8", job_field="job_ref"),
    "CY": SeriesCfg(
        key="CY", label="CY Logistics", prefix="CYIV",
        status_codes=("CY",), template="CY.xlsx",
        row_end=32, style="advance_cols",
        inv_cell="G8", date_cell="M8", job_field="bl_booking"),
}

# ซีรีส์อื่นที่รู้ mapping แล้วแต่ยังไม่ vendor template (เพิ่มไฟล์+config = ใช้ได้เลย):
# CJ→CJIV, JGL→JGIV, KTL→KLIV, KAO→MTIV, NHL→NHIV, WHALE→WHIV
KNOWN_UNVENDORED = {"CJ": "CJIV", "JGL": "JGIV", "KTL": "KLIV",
                    "KAO": "MTIV", "NHL": "NHIV", "WHALE": "WHIV"}

_SEQ_RE = re.compile(r"^([A-Z]{2,4}IV)(\d{4})-(\d{1,4})")


def parse_invoice_no(raw: str):
    """แยก (prefix, yymm, seq) จากเลขใบ — ทนค่าขยะท้ายช่อง (เคยเจอ 'KTIV2606-035\\t19/6/2026')."""
    m = _SEQ_RE.match((raw or "").strip().upper())
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


def next_invoice_no(session, cfg: SeriesCfg, yymm: str) -> str:
    """เลขถัดไปของชุด = max(seq เดือนนั้นใน DB) + 1 — นับจาก invoice_no ที่ทีมคีย์ในเดลี่.

    หมายเหตุ: DB รู้เฉพาะเลขที่คีย์แล้ว ถ้าทีมออกใบไว้แต่ยังไม่คีย์ เลขอาจชน —
    หน้า UI เตือน + แก้เลขเองได้ก่อนกดสร้าง.
    """
    from sqlmodel import select
    from models import DailyJob

    rows = session.exec(
        select(DailyJob.invoice_no).where(
            DailyJob.invoice_no.like(f"{cfg.prefix}{yymm}-%"))  # type: ignore[attr-defined]
    ).all()
    seqs = [p[2] for p in (parse_invoice_no(r) for r in rows) if p and p[1] == yymm]
    return f"{cfg.prefix}{yymm}-{(max(seqs) + 1 if seqs else 1):03d}"


def _set(ws, coord: str, value) -> None:
    """เขียนเซลล์ ข้ามลูกเซลล์ merge (เขียนได้เฉพาะ anchor — ฟอร์มจริง merge B:C ฯลฯ)."""
    from openpyxl.cell.cell import MergedCell

    if isinstance(ws[coord], MergedCell):
        return
    ws[coord] = value


def _clear_detail_rows(ws, cfg: SeriesCfg, columns: str, r_end: int) -> None:
    for r in range(cfg.row_start, r_end + 1):
        for col in columns:
            _set(ws, f"{col}{r}", None)


def build_invoice(cfg: SeriesCfg, inv_no: str, inv_date: date, rows: list[dict]) -> bytes:
    """เติม template ด้วยแถวตู้ → คืน xlsx bytes.

    rows: [{route, cntr, size, plate, cust, job, date(date), price, wash?, advance?}]
    สูตรรวม/BAHTTEXT/ปะหน้า อยู่ใน template แล้ว — Excel คำนวณใหม่ตอนเปิด.
    """
    import openpyxl

    slots = cfg.row_end - cfg.row_start + 1
    if len(rows) > slots:
        raise ValueError(f"ตู้ {len(rows)} แถว เกินช่องในฟอร์ม {cfg.label} ({slots} แถว)")
    if not rows:
        raise ValueError("ไม่มีแถวตู้")

    tpl = TEMPLATE_DIR / cfg.template
    wb = openpyxl.load_workbook(tpl)
    ws = wb[cfg.detail_sheet]
    _set(ws, cfg.inv_cell, inv_no)
    _set(ws, cfg.date_cell, datetime(inv_date.year, inv_date.month, inv_date.day))

    detail_cols = "A" + cfg.col_route + "C" + cfg.col_cntr + cfg.col_size + \
        cfg.col_plate + cfg.col_cust + cfg.col_job + cfg.col_date + cfg.col_price
    if cfg.style == "advance_cols":
        detail_cols += cfg.col_wash + cfg.col_advance + cfg.col_amount
    else:
        detail_cols += "K"
    _clear_detail_rows(ws, cfg, detail_cols, cfg.row_end)

    for i, row in enumerate(rows):
        r = cfg.row_start + i
        _set(ws, f"A{r}", i + 1)
        _set(ws, f"{cfg.col_route}{r}", row.get("route") or "")
        _set(ws, f"{cfg.col_cntr}{r}", row.get("cntr") or "")
        sz = str(row.get("size") or "").strip()
        _set(ws, f"{cfg.col_size}{r}", int(sz) if sz.isdigit() else sz)
        _set(ws, f"{cfg.col_plate}{r}", row.get("plate") or "")
        _set(ws, f"{cfg.col_cust}{r}", row.get("cust") or "")
        _set(ws, f"{cfg.col_job}{r}", row.get("job") or "")
        d = row.get("date")
        if isinstance(d, date):
            _set(ws, f"{cfg.col_date}{r}", datetime(d.year, d.month, d.day))
        _set(ws, f"{cfg.col_price}{r}", float(row.get("price") or 0))
        if cfg.style == "advance_cols":
            _set(ws, f"{cfg.col_wash}{r}", float(row.get("wash") or 0) or None)
            _set(ws, f"{cfg.col_advance}{r}", float(row.get("advance") or 0) or None)
            _set(ws, f"{cfg.col_amount}{r}", f"=SUM({cfg.col_price}{r}:{cfg.col_advance}{r})")
        else:
            _set(ws, f"K{r}", cfg.remark_transport)

    if cfg.style == "advance_sheet":
        wa = wb[cfg.advance_sheet]
        mirror_cols = "A" + cfg.col_route + "C" + cfg.col_cntr + cfg.col_size + \
            cfg.col_plate + cfg.col_cust + cfg.col_job + cfg.col_date + cfg.col_price + "K"
        _clear_detail_rows(wa, cfg, mirror_cols, cfg.advance_row_end)
        for i, row in enumerate(rows):
            r = cfg.row_start + i
            src = f"{cfg.detail_sheet}!"
            for col in ("A", cfg.col_route, cfg.col_cntr, cfg.col_size,
                        cfg.col_plate, cfg.col_job, cfg.col_date):
                _set(wa, f"{col}{r}", f"={src}{col}{r}")
            _set(wa, f"{cfg.col_cust}{r}", row.get("cust") or "")
            _set(wa, f"{cfg.col_price}{r}", float(row.get("advance") or 0))
            _set(wa, f"K{r}", f'=IF({cfg.col_route}{r}<>"","ค่าใช้จ่าย","")')

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def daily_rows_for_series(session, cfg: SeriesCfg, d1: date, d2: date):
    """แถวเดลี่ของลูกค้าชุดนี้ในช่วงวัน — จัดกลุ่ม billed (ตาม invoice_no) / unbilled."""
    from sqlmodel import select
    from models import DailyJob

    q = select(DailyJob).where(
        DailyJob.work_date >= d1, DailyJob.work_date <= d2,
        DailyJob.status_code.in_(cfg.status_codes),  # type: ignore[attr-defined]
    ).order_by(DailyJob.work_date, DailyJob.id)  # type: ignore[arg-type]
    jobs = session.exec(q).all()
    billed: dict[str, list] = {}
    unbilled: list = []
    for j in jobs:
        p = parse_invoice_no(j.invoice_no)
        if p:
            billed.setdefault(f"{p[0]}{p[1]}-{p[2]:03d}", []).append(j)
        else:
            unbilled.append(j)
    return billed, unbilled


def job_to_row(j, cfg: SeriesCfg) -> dict:
    """แปลง DailyJob → แถวฟอร์ม (prefill — ช่องที่ DB ไม่มีปล่อยว่างให้กรอก)."""
    return {
        "daily_id": j.id,
        "route": "",   # ป้ายรายการบรรทุก เช่น 'LCB - CNC2' — DB ไม่มี ให้กรอก
        "cntr": j.container_no,
        "size": j.container_size,
        "plate": j.plate_no_raw,
        "cust": "",    # ป้ายลูกค้าปลายทาง เช่น FITESACNC — DB ไม่มี ให้กรอก
        "job": getattr(j, cfg.job_field, "") or "",
        "date": j.work_date,
        "price": j.revenue_customer,
        "wash": 0.0,
        "advance": 0.0,
    }
