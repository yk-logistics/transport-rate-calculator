"""READ-ONLY: โชว์ผลกระทบของ driver_calc_price ก่อน recompute payroll.

ต่อคนขับ (LCB): ผลรวม revenue_customer (วางบิล) vs driver_calc_price (คิดเงินคนขับ)
+ รายการแถว required-KB (CY) ที่ยังลืมใส่ KB. ไม่เขียนอะไรลง DB.
รัน: python ProjectYK_System/tools/preflight_kb_driver_price.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from collections import defaultdict
from sqlmodel import Session, select, create_engine
from models import DailyJob, Employee, KbRule
from services.payroll import driver_calc_price


def main():
    db = Path(__file__).resolve().parents[1] / "app" / "app.db"
    eng = create_engine(f"sqlite:///{db}")
    with Session(eng) as s:
        req = {r.status_code for r in s.exec(select(KbRule)).all() if r.required}
        names = {e.id: e.full_name for e in s.exec(select(Employee)).all()}
        delta = defaultdict(lambda: [0.0, 0.0, 0])  # driver -> [billed, driver_calc, n_changed]
        cy_missing = []
        for r in s.exec(select(DailyJob).where(DailyJob.site_code == "LCB")).all():
            dcp = driver_calc_price(r)
            billed = r.revenue_customer or 0.0
            if abs(dcp - billed) > 0.005:
                d = delta[r.driver_id]
                d[0] += billed
                d[1] += dcp
                d[2] += 1
            if (r.status_code in req) and (r.kb_amount or 0.0) == 0.0:
                cy_missing.append((r.id, str(r.work_date), r.status_code))

        print("=== driver gross-base delta (billed -> driver_calc) ===")
        if not delta:
            print("  (ไม่มีแถวที่ driver_calc_price ต่างจาก revenue_customer — KB/override ยังว่างทั้งหมด)")
        for did, (b, c, n) in sorted(delta.items(), key=lambda x: x[1][1] - x[1][0]):
            who = names.get(did, f"driver_id={did}")
            print(f"{who!r:26} rows={n:3}  billed={b:>12,.0f}  driver={c:>12,.0f}  delta={c-b:>+12,.0f}")

        print(f"\n=== required-KB rows missing KB (e.g. CY): {len(cy_missing)} ===")
        for row in cy_missing[:40]:
            print(row)


if __name__ == "__main__":
    main()
