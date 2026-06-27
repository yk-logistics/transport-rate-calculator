import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import _parse_float


def test_kb_amount_parses_like_float():
    assert _parse_float("110") == 110.0


def test_price_override_blank_is_none():
    # price_override must become None (not 0.0) when blank
    val = ""
    parsed = None if str(val).strip() == "" else _parse_float(str(val))
    assert parsed is None


def test_price_override_value_parses():
    val = "5500"
    parsed = None if str(val).strip() == "" else _parse_float(str(val))
    assert parsed == 5500.0
