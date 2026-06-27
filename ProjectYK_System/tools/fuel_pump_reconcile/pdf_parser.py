"""Parse pump fuel-report PDFs into FuelBill rows.

Pump line format (verified 2026-06-27):
  seq date(dd.mm.yyyy) plate station Diesel-type liter price amount balance
Payment/top-up lines (วายเครูดบัตร / วายเคแสกน) have no plate/liter and don't
match the regex, so they're naturally skipped. See spec
docs/superpowers/specs/2026-06-27-fuel-pump-reconcile-design.md."""
from __future__ import annotations

import re
from datetime import date

from models import FuelBill

_LINE_RE = re.compile(
    r"^\s*(\d+)\s+(\d{2})\.(\d{2})\.(\d{4})\s+(\S+)\s+(.+?)\s+"
    r"(Diesel\s+\S+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+(-?[\d,]+\.\d+)\s*$"
)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_lines(lines: list[str]) -> list[FuelBill]:
    bills: list[FuelBill] = []
    for ln in lines:
        m = _LINE_RE.match(ln)
        if not m:
            continue
        _, dd, mm, yyyy, plate, station, ftype, liter, price, amount, _bal = m.groups()
        bills.append(FuelBill(
            date=date(int(yyyy), int(mm), int(dd)),
            plate=plate,
            station=station.strip(),
            ftype=ftype,
            liter=_num(liter),
            price=_num(price),
            amount=_num(amount),
        ))
    return bills


def parse_pdf(path: str) -> list[FuelBill]:
    from pypdf import PdfReader
    reader = PdfReader(path)
    lines: list[str] = []
    for page in reader.pages:
        lines.extend(page.extract_text().split("\n"))
    return parse_lines(lines)


def parse_pdfs(paths: list[str]) -> list[FuelBill]:
    out: list[FuelBill] = []
    for p in paths:
        out.extend(parse_pdf(p))
    return out
