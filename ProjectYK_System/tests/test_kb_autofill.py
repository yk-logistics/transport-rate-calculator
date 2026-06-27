import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlmodel import Session, SQLModel, create_engine
from models import KbRule
from services.kb import kb_default_for_status, kb_warning_for_row


def _sess():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    s.add(KbRule(status_code="NHL", default_kb=110.0, required=False))
    s.add(KbRule(status_code="CY", default_kb=0.0, required=True))
    s.commit()
    return s


def test_default_for_known_status():
    s = _sess()
    assert kb_default_for_status(s, "NHL") == 110.0


def test_default_for_unknown_status():
    s = _sess()
    assert kb_default_for_status(s, "รถจอด") == 0.0


def test_cy_zero_kb_triggers_warning():
    s = _sess()
    assert kb_warning_for_row(s, "CY", 0.0) is True
    assert kb_warning_for_row(s, "CY", 250.0) is False


def test_nhl_zero_kb_no_warning():
    s = _sess()
    assert kb_warning_for_row(s, "NHL", 0.0) is False
