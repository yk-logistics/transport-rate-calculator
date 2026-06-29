"""BigC พ.ค.2026 (payrun #4) — ทำเงินเดือนจากเดลี่จริง ตามที่โอยืนยัน 29มิ.ย.:

  1. ตัดคนที่คืนเงินประกันแล้ว 3 คน (บุญชอบ109/พรศักดิ์110/กฤษฎา113) ออกจากการคิด
     เงินเดือน — set status=inactive + end_date=2026-04-30 (ก่อนรอบ พ.ค.) เพื่อให้
     engine overlap-guard ข้าม. **ไม่ hard delete** เพราะมีประวัติ payrun เดือนก่อน.
  2. เรทน้ำมัน BigC: ลอก "เงินที่ได้" ต่อคน จากไฟล์ เรทน้ำมันเดือนพฤษภาคม69.xlsx
     ชีท รวมเรท → set PayRunAdjust.fuel_rate_override_thb (bypass auto-calc ที่เพี้ยน).
     คน active ที่ไม่อยู่ในชีท → override = 0 (กัน auto-calc บวม).
  3. recompute payrun #4 จากเดลี่จริง → net ใหม่.

Safe: --dry-run, backup ทำแล้วนอก script. rollback: เปิด 3 คนกลับ active + ลบ
PayRunAdjust ที่ note='bigc_may_fuelrate' + recompute.
"""
import io
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import openpyxl  # noqa: E402
from sqlmodel import Session, select  # noqa: E402
from models import Employee, PayRun, PayRunItem, PayRunAdjust  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402
from services.payroll import compute_pay_run  # noqa: E402

RESIGNED_IDS = [109, 110, 113]  # โอ: คืนเงินประกันหมดแล้ว ตัดออก
RESIGNED_END = date(2026, 4, 30)  # ก่อนรอบ พ.ค. → ไม่โผล่ใน payrun #4
FUEL_XLSX = Path(r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026"
                 r"\6.Jun\BigC\เรทน้ำมันเดือนพฤษภาคม69.xlsx")
ADJ_NOTE = "bigc_may_fuelrate (ลอกจากชีท รวมเรท)"


def first_name(full: str) -> str:
    parts = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").split()
    return parts[0] if parts else ""


def load_fuelrate() -> dict:
    """first_name -> เงินที่ได้ (float) จากชีท รวมเรท."""
    wb = openpyxl.load_workbook(FUEL_XLSX, data_only=True, read_only=True)
    rows = [list(r) for r in wb["รวมเรท"].iter_rows(values_only=True)]
    wb.close()
    out = {}
    for r in rows[1:]:
        if len(r) > 6 and r[2] and isinstance(r[6], (int, float)):
            out[first_name(str(r[2]))] = round(float(r[6]), 2)
    return out


def upsert_adjust(s: Session, run_id: int, emp_id: int, thb: float) -> None:
    adj = s.exec(
        select(PayRunAdjust).where(
            PayRunAdjust.pay_run_id == run_id,
            PayRunAdjust.employee_id == emp_id,
        )
    ).first()
    if adj is None:
        adj = PayRunAdjust(pay_run_id=run_id, employee_id=emp_id)
    adj.fuel_rate_override_thb = thb
    adj.note = ADJ_NOTE
    s.add(adj)


def main() -> None:
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    fuelrate = load_fuelrate()
    eng = make_engine()
    with Session(eng) as s:
        pr = s.exec(select(PayRun).where(
            PayRun.site_code == "BIGC", PayRun.pay_cycle_tag == "2026-05")).first()
        old_net = sum((it.net_pay or 0) for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all())
        print(f"payrun #{pr.id} BIGC 2026-05 status={pr.status}  OLD net={old_net:,.2f}\n")

        # 1) deactivate resigned
        print("=== 1) ตัดคนคืนเงินประกันแล้ว 3 คน ===")
        for eid in RESIGNED_IDS:
            e = s.get(Employee, eid)
            print(f"  emp{eid} {e.full_name!r}: status {e.status}->inactive, end_date->{RESIGNED_END}")
            if not dry:
                e.status = "inactive"
                e.end_date = RESIGNED_END
                s.add(e)

        # 2) fuel-rate overrides
        print("\n=== 2) เรทน้ำมัน override จากชีท ===")
        emps = s.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all()
        for e in emps:
            if e.id in RESIGNED_IDS:
                continue
            if e.end_date and e.end_date < pr.period_start:
                continue
            if e.start_date and e.start_date > pr.period_end:
                continue
            thb = fuelrate.get(first_name(e.full_name), 0.0)
            src = "ชีท" if first_name(e.full_name) in fuelrate else "ไม่อยู่ในชีท→0"
            print(f"  emp{e.id:<4}{str(e.full_name)[:22]:<24} เรทน้ำมัน={thb:>10,.2f}  ({src})")
            if not dry:
                upsert_adjust(s, pr.id, e.id, thb)

        if not dry:
            s.commit()

        # 3) recompute
        print("\n=== 3) recompute payrun #4 จากเดลี่จริง ===")
        if dry:
            print("  (dry-run: ข้าม recompute)")
            return
        s.refresh(pr)
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        new_net = sum((it.net_pay or 0) for it in items)
        print(f"  items={len(items)}")
        print(f"\n{'emp':<6}{'name':<24}{'base':>9}{'trip':>9}{'fuelrate':>10}{'gross':>11}{'ded':>9}{'net':>11}")
        for it in sorted(items, key=lambda x: x.employee_id):
            e = s.get(Employee, it.employee_id)
            print(f"{it.employee_id:<6}{str(e.full_name)[:22]:<24}"
                  f"{it.base_salary_earned:>9,.0f}{it.trip_fee_total:>9,.0f}"
                  f"{it.fuel_rate_income:>10,.0f}{it.gross_total:>11,.2f}"
                  f"{it.deduction_total:>9,.0f}{it.net_pay:>11,.2f}")
        print(f"\n  OLD net (locked copy): {old_net:,.2f}")
        print(f"  NEW net (from daily):  {new_net:,.2f}")
        print(f"  Δ:                     {new_net-old_net:,.2f}")


if __name__ == "__main__":
    main()
