import sys

from _paths import APP_DIR

sys.path.insert(0, str(APP_DIR))
from sqlmodel import Session, select
import main
from models import PettyCashTxn

with Session(main.engine) as s:
    rows = s.exec(
        select(PettyCashTxn).where(PettyCashTxn.source.like("lcb_advance%"))
    ).all()
    for r in rows:
        s.delete(r)
    s.commit()
    print(f"Deleted {len(rows)} rows with source like 'lcb_advance%'")
