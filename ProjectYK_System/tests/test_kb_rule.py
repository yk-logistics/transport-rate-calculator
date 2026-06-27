import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlmodel import Session, SQLModel, create_engine, select
from models import KbRule
import main


def _mem_session():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    return Session(eng)


def test_kbrule_model_fields():
    r = KbRule(status_code="NHL", default_kb=110.0, required=False)
    assert r.status_code == "NHL"
    assert r.default_kb == 110.0
    assert r.required is False


def test_seed_creates_nhl_mol_cy():
    s = _mem_session()
    main.seed_kb_rules(s)
    codes = {r.status_code: r for r in s.exec(select(KbRule)).all()}
    assert codes["NHL"].default_kb == 110.0 and codes["NHL"].required is False
    assert codes["MOL"].default_kb == 100.0 and codes["MOL"].required is False
    assert codes["CY"].default_kb == 0.0 and codes["CY"].required is True
    # idempotent — second call adds nothing
    main.seed_kb_rules(s)
    assert len(s.exec(select(KbRule)).all()) == 3
