"""Backfill DailyJob.kb_amount จาก KbRule (เฉพาะ rule ที่ required=False, แถว kb==0).

CY (required=True) ไม่แตะ — ให้คนกรอกเอง (จะ warn ในกริด). dry-run by default.
รัน: python ProjectYK_System/tools/backfill_kb_from_rule.py          (dry-run)
     python ProjectYK_System/tools/backfill_kb_from_rule.py --apply  (เขียนจริง + backup)
"""
import sys
import shutil
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from sqlmodel import Session, select, create_engine
from models import DailyJob, KbRule


def plan_backfill(session: Session) -> list[dict]:
    """รายการแถวที่จะเติม KB: rule required=False & default_kb>0 & แถว kb==0."""
    rules = {
        r.status_code: r
        for r in session.exec(select(KbRule)).all()
        if not r.required and r.default_kb > 0
    }
    out = []
    for r in session.exec(select(DailyJob)).all():
        rule = rules.get(r.status_code or "")
        if rule and (r.kb_amount or 0.0) == 0.0:
            out.append({
                "id": r.id,
                "status_code": r.status_code,
                "old_kb": r.kb_amount or 0.0,
                "new_kb": rule.default_kb,
            })
    return out


def main(apply: bool):
    db = Path(__file__).resolve().parents[1] / "app" / "app.db"
    eng = create_engine(f"sqlite:///{db}")
    with Session(eng) as s:
        plan = plan_backfill(s)
        print(f"rows to backfill: {len(plan)}")
        for p in plan[:20]:
            print(p)
        if apply:
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak = db.with_name(f"{db.name}.bak_before_kb_backfill_{stamp}")
            shutil.copy2(db, bak)
            print(f"backup -> {bak}")
            for p in plan:
                row = s.get(DailyJob, p["id"])
                row.kb_amount = p["new_kb"]
                s.add(row)
            s.commit()
            print(f"applied {len(plan)} rows")
        else:
            print("(dry-run — ใส่ --apply เพื่อเขียนจริง)")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
