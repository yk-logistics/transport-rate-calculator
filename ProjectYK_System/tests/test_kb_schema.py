import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import date
from models import DailyJob


def test_dailyjob_has_kb_fields():
    j = DailyJob(work_date=date(2026, 6, 27), site_code="LCB")
    assert j.kb_amount == 0.0
    assert j.price_override is None
