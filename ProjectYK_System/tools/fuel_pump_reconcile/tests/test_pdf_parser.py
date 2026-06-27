"""Tests for the PDF line parser. Uses raw text lines (parse_lines) so no real
PDF is needed; parse_pdf just feeds pypdf-extracted lines into parse_lines."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pdf_parser import parse_lines  # noqa: E402

# Real lines from the pump report (วายเค มิถุนายน).
LINES = [
    "ลำดับที่ วันที่ ทะเบียนรถ สถานีบริการ ประเภทน้ำมัน จำนวนลิตร ราคา/ลิตร จำนวนเงิน ยอดชำระ",
    "1 01.06.2026 71-9629 เพิ่มทรัพย์ Diesel B7 10.00 40.72 407.20 -22,400.74",
    "2 01.06.2026 71-9629 เพิ่มทรัพย์ Diesel B20 30.00 35.22 1,056.60 -23,457.34",
    "7 01.06.2026 บร-9785 ทวีโชค Diesel B7 12.28 40.72 500.00 -31,964.54",
    # a payment/top-up line that must be skipped (no plate/liter columns):
    "25 03.06.2026 วายเคแสกน/รุ่งโรจน์ 69,500.00 5,388.36",
]


def test_parses_fuel_lines():
    bills = parse_lines(LINES)
    assert len(bills) == 3  # payment line skipped


def test_parsed_fields():
    bills = parse_lines(LINES)
    b = bills[0]
    assert b.date == date(2026, 6, 1)
    assert b.plate == "71-9629"
    assert b.ftype == "Diesel B7"
    assert b.liter == 10.0
    assert b.amount == 407.20


def test_comma_thousands_amount():
    b = parse_lines(LINES)[1]
    assert b.amount == 1056.60
    assert b.liter == 30.0


def test_skips_payment_line():
    bills = parse_lines(LINES)
    assert all("วายเค" not in b.plate for b in bills)
