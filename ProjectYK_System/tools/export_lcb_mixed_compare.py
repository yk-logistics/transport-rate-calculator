"""Export per-day lcb_mixed breakdown for พชร(86)/สุรเดช(91) -> JSON.

READ-ONLY. Feeds the hand-compare web page. Shows every DailyJob day with the
ratio the engine used and how it classified the day, plus the final net.
"""
from __future__ import annotations
import io, sys, json
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR
sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select
from models import Employee, PayRun
from services.payroll import (
    calc_one_employee, _classify_lcb_days, _sum_fuel_cost_for_dates,
    LCB_MAO_RATIO, LCB_MAO_RATIO_TOL, LCB_TRIP_RATIO_MAX,
)

engine = create_engine(f"sqlite:///{APP_DIR/'app.db'}",
                       connect_args={"check_same_thread": False})

TARGETS = [(86, "พชร"), (91, "สุรเดช")]


_IDLE_KW = ("รถจอด", "รองาน", "ไม่มีงาน", "อุบัติเหตุ", "ซ่อม", "dhl overflow", "idle")
_LEAVE_KW = ("ลา", "ขาด", "ป่วย", "หยุด")


def classify_label(rev, fee, status=""):
    if rev <= 0:
        low = (status or "").strip().lower()
        if not low:
            return "no_work"
        if any(kw in low for kw in _IDLE_KW):
            return "idle"          # รถจอด/อุบัติเหตุ/ซ่อม — ได้ฐาน
        if any(kw in low for kw in _LEAVE_KW):
            return "no_work"       # ลา/ขาด — ไม่ได้ฐาน
        return "pending"           # มี status (รหัสลูกค้า) แต่ยังไม่ลงราคา
    ratio = fee / rev
    if abs(ratio - LCB_MAO_RATIO) <= LCB_MAO_RATIO_TOL:
        return "mao"
    elif ratio < LCB_TRIP_RATIO_MAX:
        return "trip"
    return "ambiguous"


def main():
    out = {
        "rules": {
            "mao_ratio": LCB_MAO_RATIO,
            "mao_tol": LCB_MAO_RATIO_TOL,
            "trip_max": LCB_TRIP_RATIO_MAX,
        },
        "drivers": [],
    }
    with Session(engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        out["period"] = {"start": str(pr.period_start), "end": str(pr.period_end),
                         "tag": pr.pay_cycle_tag}
        for eid, nm in TARGETS:
            emp = s.get(Employee, eid)
            split = _classify_lcb_days(s, eid, pr.period_start, pr.period_end, "LCB")

            # per-day rows (all days, sorted)
            all_rows = (split["mao_days"] + split["trip_days"]
                        + split["ambiguous"] + split["no_work"])
            all_rows.sort(key=lambda r: r.work_date)
            days = []
            for r in all_rows:
                rev = r.revenue_customer or 0.0
                fee = r.trip_fee_driver or 0.0
                days.append({
                    "date": str(r.work_date),
                    "revenue": round(rev, 2),
                    "trip_fee": round(fee, 2),
                    "ratio": round(fee / rev, 4) if rev > 0 else None,
                    "label": classify_label(rev, fee, r.status_code),
                    "status": (r.status_code or ""),
                    "route": getattr(r, "route", "") or getattr(r, "destination", "") or "",
                    "plate": getattr(r, "plate", "") or "",
                })

            # fuel on mao days (the deduction)
            mao_dates = {d.work_date for d in split["mao_days"]}
            fuel_mao = _sum_fuel_cost_for_dates(s, eid, mao_dates, site_code="LCB")

            orig = emp.pay_mode
            emp.pay_mode = "lcb_mixed"
            calc = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                     pr.pay_cycle_tag, pay_run_id=2)
            emp.pay_mode = orig

            out["drivers"].append({
                "emp_id": eid,
                "name": nm,
                "share_rate": emp.gross_share_rate or 0.60,
                "counts": {
                    "mao": len(split["mao_days"]),
                    "trip": len(split["trip_days"]),
                    "ambiguous": len(split["ambiguous"]),
                    "no_work": len(split["no_work"]),
                    # idle = วันรถจอด/อุบัติเหตุ/ซ่อม ที่นับเข้าฐาน (ไม่รวมลา)
                    "idle": int(calc.days_company_no_work),
                    "base_days": int(len(split["trip_days"]) + calc.days_company_no_work),
                },
                "days": days,
                "calc": {
                    "mao_rev": round(sum((d.revenue_customer or 0.0)
                                         for d in split["mao_days"]), 2),
                    "fuel_share_income": calc.fuel_share_income,
                    "fuel_cost_self": calc.fuel_cost_self,
                    "fuel_mao_check": round(fuel_mao, 2),
                    "trip_fee_total": calc.trip_fee_total,
                    "other_income": calc.other_income,
                    "base_salary_earned": calc.base_salary_earned,
                    "care_allowance_earned": calc.care_allowance_earned,
                    "gross_total": calc.gross_total,
                    "deduction_total": calc.deduction_total,
                    "net_pay": calc.net_pay,
                    "note": calc.note,
                    # subtotal per side (เหมา vs เที่ยว)
                    "mao_subtotal": round(calc.fuel_share_income, 2),
                    "trip_subtotal": round(
                        calc.trip_fee_total + calc.other_income
                        + calc.base_salary_earned + calc.care_allowance_earned, 2),
                    # deduction breakdown
                    "ded": {
                        "fuel_cost_self": calc.fuel_cost_self,
                        "petty_cash": calc.petty_cash_deduction,
                        "social_security": calc.social_security,
                        "income_tax": calc.income_tax_withholding,
                        "deposit_install": calc.deposit_install,
                        "accident_install": calc.accident_install,
                        "other": calc.other_deduction,
                    },
                },
            })
        s.rollback()

    dest = Path(__file__).resolve().parent / "_lcb_mixed_compare.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {dest}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
