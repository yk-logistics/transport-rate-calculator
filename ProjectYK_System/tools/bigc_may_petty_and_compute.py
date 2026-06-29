"""BigC พ.ค.2026 final — โอ 29มิ.ย.: income คิดใหม่จากเดลี่ + ยอดหักสดย่อยเดิม.

ขั้นตอน:
  1. สร้าง PettyCashTxn รายคนจากยอด petty ที่โอคิดมือ (locked copy) → cycle 2026-05,
     deduct_from_driver, pending, category=driver_advance, source=bigc_may_petty_manual.
     (engine อ่าน petty จาก PettyCashTxn — นี่คือที่อยู่ที่ถูกต้อง + future-proof)
  2. recompute payrun #4: income (เงินเดือน+เที่ยว+เรทน้ำมัน override) จากเดลี่จริง,
     หัก = SS + petty (จากข้อ 1).

ต้องรัน bigc_may_payroll_finalize.py ก่อน (ตัด 3 คน + fuel-rate override) แล้วค่อยรันนี้.
idempotent: ลบ PettyCashTxn source=bigc_may_petty_manual เดิมก่อนสร้างใหม่.
rollback: ลบ source=bigc_may_petty_manual + restore payrun จาก backup.
"""
import io
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select  # noqa: E402
from models import Employee, PayRun, PayRunItem, PettyCashTxn  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402
from services.payroll import compute_pay_run  # noqa: E402

SOURCE = "bigc_may_petty_manual"
TAG = "2026-05"
# ยอด petty รายคน จาก locked copy (โอคิดมือ) — ไม่ใช่การเดา
PETTY = {103: 9000.0, 104: 7000.0, 105: 1000.0, 106: 9500.0,
         107: 4925.0, 108: 8000.0, 111: 8500.0, 112: 12000.0}


def main() -> None:
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    eng = make_engine()
    with Session(eng) as s:
        pr = s.exec(select(PayRun).where(
            PayRun.site_code == "BIGC", PayRun.pay_cycle_tag == TAG)).first()

        # 1) wipe prior manual petty (idempotent) then create
        prior = s.exec(select(PettyCashTxn).where(PettyCashTxn.source == SOURCE)).all()
        print(f"=== 1) PettyCashTxn (manual petty) — ลบเก่า {len(prior)}, สร้าง {len(PETTY)} ===")
        if not dry:
            for p in prior:
                s.delete(p)
            s.flush()
        now = datetime.utcnow()
        for eid, amt in PETTY.items():
            e = s.get(Employee, eid)
            print(f"  emp{eid} {str(e.full_name)[:20]:<20} เงินเบิกสดย่อย = {amt:>9,.2f}")
            if not dry:
                s.add(PettyCashTxn(
                    txn_date=pr.period_end, site_code="BIGC", direction="out",
                    amount=amt, requester_raw=e.full_name, driver_id=eid,
                    memo="เงินเบิก (ลอกยอดโอคิดมือ พ.ค.)", category="driver_advance",
                    has_receipt=False, deduct_from_driver=True, deduct_amount=amt,
                    deduction_status="pending", pay_cycle_tag=TAG, source=SOURCE,
                    status="active", parsed_confidence=1.0, created_at=now, updated_at=now,
                ))
        if not dry:
            s.commit()

        # 2) recompute
        print("\n=== 2) recompute payrun #4 (income จากเดลี่ + petty) ===")
        if dry:
            print("  (dry-run: ข้าม recompute)")
            return
        old_net = sum((it.net_pay or 0) for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all())
        s.refresh(pr)
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        new_net = sum((it.net_pay or 0) for it in items)
        print(f"  items={len(items)}")
        hdr = f"{'emp':<5}{'name':<22}{'base':>8}{'trip':>8}{'fuel':>8}{'gross':>10}{'ss':>7}{'petty':>8}{'net':>10}"
        print("\n" + hdr)
        for it in sorted(items, key=lambda x: x.employee_id):
            e = s.get(Employee, it.employee_id)
            print(f"{it.employee_id:<5}{str(e.full_name)[:20]:<22}"
                  f"{it.base_salary_earned:>8,.0f}{it.trip_fee_total:>8,.0f}"
                  f"{it.fuel_rate_income:>8,.0f}{it.gross_total:>10,.2f}"
                  f"{it.social_security:>7,.0f}{it.petty_cash_deduction:>8,.0f}"
                  f"{it.net_pay:>10,.2f}")
        print(f"\n  net (before this recompute): {old_net:,.2f}")
        print(f"  net (income-from-daily + petty): {new_net:,.2f}")
        print(f"  locked manual ground truth was: 110,613.81")
        print(f"  Δ vs locked: {new_net-110613.81:,.2f}")


if __name__ == "__main__":
    main()
