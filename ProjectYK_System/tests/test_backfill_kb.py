import sys, os, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import date
from sqlmodel import Session, SQLModel, create_engine
from models import DailyJob, KbRule

# tools/ has no __init__.py — load the script module by file path
_spec = importlib.util.spec_from_file_location(
    "backfill_kb_from_rule",
    os.path.join(os.path.dirname(__file__), "..", "tools", "backfill_kb_from_rule.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
plan_backfill = _mod.plan_backfill


def _sess():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    s.add(KbRule(status_code="NHL", default_kb=110.0, required=False))
    s.add(KbRule(status_code="CY", default_kb=0.0, required=True))
    s.add(DailyJob(work_date=date(2026, 6, 1), site_code="LCB", status_code="NHL", kb_amount=0))
    s.add(DailyJob(work_date=date(2026, 6, 2), site_code="LCB", status_code="NHL", kb_amount=110))  # already set
    s.add(DailyJob(work_date=date(2026, 6, 3), site_code="LCB", status_code="CY", kb_amount=0))     # required, skip
    s.commit()
    return s


def test_plan_only_fills_nonrequired_zero_rows():
    s = _sess()
    plan = plan_backfill(s)
    # only the NHL kb=0 row -> 1 change to 110
    assert len(plan) == 1
    assert plan[0]["new_kb"] == 110.0
    assert plan[0]["status_code"] == "NHL"
