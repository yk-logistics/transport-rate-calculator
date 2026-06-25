"""เทียบ net payrun#2 ทุกคนกับ golden snapshot ใน spec. READ-ONLY.
รันหลังแก้ payroll.py เพื่อยืนยันมีแต่ mixed(86/91) ที่เปลี่ยน."""
from __future__ import annotations
import io, sys
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from _repo_paths import APP_DIR
sys.path.insert(0, str(APP_DIR))
from sqlmodel import Session, create_engine, select
from models import Employee, PayRun, PayRunItem
from services.payroll import calc_one_employee

# golden = net ก่อนแก้ (จาก spec ภาคผนวก)
GOLDEN = {
    84: -1478.10, 85: 7921.27, 87: 14040.00, 88: 13178.00, 89: 12728.00,
    90: 19757.75, 92: 19518.00, 93: 6129.68, 94: 6128.00, 95: 9850.32,
    96: 8647.17, 97: 7894.80, 98: 14747.88, 99: 19926.12, 100: 62261.15,
    101: 22049.96,
}  # 16 non-mixed; 86/91 ตั้งใจให้เปลี่ยน

engine = create_engine(f"sqlite:///{APP_DIR/'app.db'}",
                       connect_args={"check_same_thread": False})


def main():
    bad = []
    with Session(engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        for did, gold in GOLDEN.items():
            emp = s.get(Employee, did)
            c = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                  pr.pay_cycle_tag, pay_run_id=2)
            now = round(c.net_pay, 2)
            flag = "" if abs(now - gold) < 0.01 else "  <-- CHANGED"
            if flag:
                bad.append((did, gold, now))
            print(f"emp{did:3} golden={gold:>11,.2f} now={now:>11,.2f}{flag}")
        # mixed: just show new value
        for did in (86, 91):
            emp = s.get(Employee, did)
            c = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                  pr.pay_cycle_tag, pay_run_id=2)
            print(f"emp{did:3} (mixed) NEW net = {c.net_pay:>11,.2f}")
        s.rollback()
    print("\nRESULT:", "FAIL — non-mixed changed" if bad else "OK — only mixed changed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
