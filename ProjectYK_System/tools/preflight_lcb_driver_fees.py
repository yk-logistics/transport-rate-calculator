"""PREFLIGHT (read-only): เงินคนขับ LCB จะเปลี่ยนเท่าไร ถ้า

  - เลิกสูตร "พิเศษ 100/เที่ยว" → ใช้เลข fee 'special'/'พิเศษ' ที่กรอกมือ
  - บวก OT (ot/ค่าล่วงเวลา) + รับตู้แทน (pickup_return/รับตู้แทน) เข้าเงินคนขับ

ไม่แตะ DB เลย — แค่คำนวณ before/after ต่อคน ต่อรอบ LCB ที่ยังไม่ finalized.

รัน:  ProjectYK_System/app/.venv/Scripts/python.exe ProjectYK_System/tools/preflight_lcb_driver_fees.py
"""
from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

from sqlmodel import Session, select  # noqa: E402

from db_config import engine  # noqa: E402
from models import DailyJob, DailyJobFee, Employee, PayRun, PayRunItem  # noqa: E402

OT_TYPES = {"ot", "ค่าล่วงเวลา"}
PICKUP_TYPES = {"pickup_return", "รับตู้แทน"}
SPECIAL_TYPES = {"special", "พิเศษ", "ค่าพิเศษ"}
LCB_MODES = {"lcb_trip", "lcb_mao", "lcb_mixed"}


def _count_trips_old(rows) -> int:
    """สูตรเก่า: นับเที่ยว = แถวที่ trip_fee_driver>0 หรือ revenue_customer>0."""
    return sum(
        1 for r in rows
        if (r.trip_fee_driver or 0) > 0 or (r.revenue_customer or 0) > 0
    )


def main() -> None:
    with Session(engine) as s:
        runs = s.exec(
            select(PayRun).where(PayRun.site_code == "LCB")
        ).all()
        runs = [r for r in runs if (r.status or "").lower() != "finalized"]

        grand_old = grand_new = 0.0
        for pr in runs:
            print("=" * 78)
            print(f"RUN #{pr.id}  {pr.site_code} {pr.pay_cycle_tag}  "
                  f"{pr.period_start}→{pr.period_end}  [{pr.status}]")
            print("-" * 78)
            print(f"{'คนขับ':<24}{'mode':<11}"
                  f"{'พิเศษเก่า':>10}{'พิเศษใหม่':>10}{'OT':>7}{'รับตู้':>8}{'Δnet':>9}")
            items = s.exec(
                select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)
            ).all()
            run_old = run_new = 0.0
            for it in items:
                emp = s.get(Employee, it.employee_id)
                if emp is None or emp.pay_mode not in LCB_MODES:
                    continue
                rows = s.exec(
                    select(DailyJob).where(
                        DailyJob.driver_id == emp.id,
                        DailyJob.site_code == pr.site_code,
                        DailyJob.work_date >= pr.period_start,
                        DailyJob.work_date <= pr.period_end,
                    )
                ).all()
                job_ids = [r.id for r in rows if r.id is not None]
                fees = []
                if job_ids:
                    fees = s.exec(
                        select(DailyJobFee).where(
                            DailyJobFee.daily_job_id.in_(job_ids)
                        )
                    ).all()

                def fsum(types):
                    return round(sum(
                        (f.amount or 0.0) for f in fees
                        if (f.fee_type or "").lower() in types
                    ), 2)

                special_old = _count_trips_old(rows) * 100.0
                special_new = fsum(SPECIAL_TYPES)
                ot = fsum(OT_TYPES)
                pickup = fsum(PICKUP_TYPES)

                old_extra = special_old              # เดิมมีแค่พิเศษ 100/เที่ยว
                new_extra = special_new + ot + pickup
                delta = round(new_extra - old_extra, 2)
                run_old += old_extra
                run_new += new_extra
                if abs(delta) < 0.005 and ot == 0 and pickup == 0 and special_new == special_old:
                    continue  # ไม่เปลี่ยน — ข้ามให้อ่านง่าย
                name = (emp.full_name or emp.code or str(emp.id))[:22]
                print(f"{name:<24}{emp.pay_mode:<11}"
                      f"{special_old:>10,.0f}{special_new:>10,.0f}"
                      f"{ot:>7,.0f}{pickup:>8,.0f}{delta:>+9,.0f}")
            print("-" * 78)
            print(f"{'รวมรอบนี้':<35}{run_old:>10,.0f}{run_new:>10,.0f}"
                  f"{'':>15}{run_new-run_old:>+9,.0f}")
            grand_old += run_old
            grand_new += run_new
        print("=" * 78)
        print(f"รวมทุกรอบ LCB (ยังไม่ปิด):  extra เก่า {grand_old:,.0f} → "
              f"ใหม่ {grand_new:,.0f}  (Δ {grand_new-grand_old:+,.0f})")
        print("=" * 78)
        print("หมายเหตุ: Δnet ต่อคน = ผลต่อ net pay (extra เป็นรายได้บวกตรงๆ).")
        print("ยังไม่แตะ DB — ต้อง recompute จริงเพื่อให้มีผล.")


if __name__ == "__main__":
    main()
