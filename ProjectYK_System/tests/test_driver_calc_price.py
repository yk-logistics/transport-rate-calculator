import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import date
from models import DailyJob
from services.payroll import driver_calc_price


def _row(rev=0.0, kb=0.0, override=None):
    return DailyJob(work_date=date(2026, 6, 27), site_code="LCB",
                    revenue_customer=rev, kb_amount=kb, price_override=override)


def test_plain_revenue_no_kb():
    assert driver_calc_price(_row(rev=5000)) == 5000.0


def test_kb_subtracted_from_revenue():
    # NHL: bill 5200, kb 110 -> driver 5090
    assert driver_calc_price(_row(rev=5200, kb=110)) == 5090.0


def test_override_replaces_revenue():
    # over-market: bill 6000 but ราคากลาง 5500 -> driver 5500
    assert driver_calc_price(_row(rev=6000, override=5500)) == 5500.0


def test_override_minus_kb_stacks():
    # override 5500 with kb 110 -> 5390
    assert driver_calc_price(_row(rev=6000, override=5500, kb=110)) == 5390.0


def test_zero_revenue_zero_result():
    assert driver_calc_price(_row(rev=0)) == 0.0
