"""
Payroll calculation engine.

Pay cycles differ per site:
  BIGC  : 1 → last day of month            (paid on 1st next month)    tag = "YYYY-MM"
  LCB   : 16 → 15 of next month            (paid on 1st after)         tag = month in which cycle ENDS
  AYU   : 26 → 25 of next month            (paid at end of next month) tag = month in which cycle ENDS

Pay modes:
  bigc_monthly        : base 9000 + trip_fee + (future: fuel-rate rebate 16฿/L)
  lcb_monthly         : base 9240 + care 3000 + trip_fee + (100฿ × trip_count พิเศษ)
                        base/care หักแบบเฉลี่ยรายวันต่อวันลา-ขาด (หารด้วยวันจริงใน cycle)
  lcb_mao             : 60% of gross revenue − 100% fuel cost
  ayu_trip            : trip_fee only (+ optional monthly guarantee top-up)
  ayu_trip_self_fuel  : trip_fee − fuel_cost (คนขับออกน้ำมันเอง เช่น นิวัติ, เรวัตร, ธัชชนพล, เสรี)
  ayu_mao             : 55-60% of gross revenue − fuel − tolls
  none                : not a payroll-earning employee (office/owner/mechanic)

Deductions (all sites, driver pay modes):
  social_security : social_security_base × social_security_rate (default 9000×5% = 450)
                    scaled down pro-rata when cycle < full month
  deposit_install : 1000/mo until deposit_balance >= deposit_target (default 10000)
  accident_install: sum of AccidentInstallment installment_amount due in cycle
  petty_cash_ded  : sum of PettyCashTxn where deduction_status='pending' and
                    pay_cycle_tag == this cycle tag
"""
from __future__ import annotations

import calendar
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlmodel import Session, select
from sqlalchemy import func as sa_func

from models import (
    AccidentInstallment,
    DailyJob,
    Employee,
    FuelTxn,
    PayRun,
    PayRunAdjust,
    PayRunItem,
    PettyCashTxn,
)

KNOWN_PAY_CYCLE_POLICIES = {
    "site_default",
    "cut_26_25",
    "cut_16_15",
    "calendar",
    "calendar_m1",
}


# ---------------------------------------------------------------------
# Cycle boundary math
# ---------------------------------------------------------------------

def compute_period(site_code: str, tag: str) -> tuple[date, date]:
    """Return (period_start, period_end_inclusive) for a given site + cycle tag.

    tag format: "YYYY-MM" — the month the cycle ENDS in (this matches the payroll
    tag stored on PettyCashTxn etc).
    """
    year, month = (int(x) for x in tag.split("-"))
    last_day = calendar.monthrange(year, month)[1]

    site = (site_code or "").upper()
    if site == "BIGC":
        return date(year, month, 1), date(year, month, last_day)

    if site == "LCB":
        end = date(year, month, 15)
        prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
        start = date(prev_year, prev_month, 16)
        return start, end

    if site == "AYU":
        end = date(year, month, 25)
        prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
        start = date(prev_year, prev_month, 26)
        return start, end

    # fallback: assume calendar month
    return date(year, month, 1), date(year, month, last_day)


def compute_pay_cycle_tag(site_code: str, txn_date: date) -> str:
    """Given a transaction date, return the cycle tag it belongs to."""
    site = (site_code or "").upper()
    y, m, d = txn_date.year, txn_date.month, txn_date.day

    def bump(year: int, month: int) -> tuple[int, int]:
        return (year + 1, 1) if month == 12 else (year, month + 1)

    if site == "BIGC":
        return f"{y:04d}-{m:02d}"
    if site == "LCB":
        if d >= 16:
            ny, nm = bump(y, m)
            return f"{ny:04d}-{nm:02d}"
        return f"{y:04d}-{m:02d}"
    if site == "AYU":
        if d >= 26:
            ny, nm = bump(y, m)
            return f"{ny:04d}-{nm:02d}"
        return f"{y:04d}-{m:02d}"
    return f"{y:04d}-{m:02d}"


def normalize_pay_cycle_policy(policy: str) -> str:
    p = (policy or "").strip().lower()
    return p if p in KNOWN_PAY_CYCLE_POLICIES else "site_default"


def compute_pay_cycle_tag_by_policy(policy: str, txn_date: date, site_code: str = "") -> str:
    """Resolve payroll cycle tag by driver policy first, then site fallback."""
    p = normalize_pay_cycle_policy(policy)
    y, m, d = txn_date.year, txn_date.month, txn_date.day

    if p == "calendar":
        return f"{y:04d}-{m:02d}"
    if p == "calendar_m1":
        py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
        return f"{py:04d}-{pm:02d}"
    if p == "cut_16_15":
        if d >= 16:
            ny, nm = ((y + 1, 1) if m == 12 else (y, m + 1))
            return f"{ny:04d}-{nm:02d}"
        return f"{y:04d}-{m:02d}"
    if p == "cut_26_25":
        if d >= 26:
            ny, nm = ((y + 1, 1) if m == 12 else (y, m + 1))
            return f"{ny:04d}-{nm:02d}"
        return f"{y:04d}-{m:02d}"
    return compute_pay_cycle_tag(site_code, txn_date)


# ---------------------------------------------------------------------
# Per-employee calculation
# ---------------------------------------------------------------------

@dataclass
class PayrollCalc:
    """In-memory result before persisting as PayRunItem."""
    employee: Employee
    period_start: date
    period_end: date

    days_worked: float = 0.0
    days_leave: float = 0.0
    days_absent: float = 0.0
    days_company_no_work: float = 0.0

    base_salary_earned: float = 0.0
    care_allowance_earned: float = 0.0
    trip_fee_total: float = 0.0
    fuel_rate_income: float = 0.0
    fuel_share_income: float = 0.0
    guarantee_topup: float = 0.0
    other_income: float = 0.0

    # BIGC audit fields
    fuel_budget_liter: float = 0.0
    fuel_consumed_liter: float = 0.0
    fuel_residual_liter: float = 0.0

    social_security: float = 0.0
    income_tax_withholding: float = 0.0
    deposit_install: float = 0.0
    accident_install: float = 0.0
    petty_cash_deduction: float = 0.0
    fuel_cost_self: float = 0.0
    other_deduction: float = 0.0
    note: str = ""

    @property
    def gross_total(self) -> float:
        return round(
            self.base_salary_earned
            + self.care_allowance_earned
            + self.trip_fee_total
            + self.fuel_rate_income
            + self.fuel_share_income
            + self.guarantee_topup
            + self.other_income,
            2,
        )

    @property
    def deduction_total(self) -> float:
        return round(
            self.social_security
            + self.income_tax_withholding
            + self.deposit_install
            + self.accident_install
            + self.petty_cash_deduction
            + self.fuel_cost_self
            + self.other_deduction,
            2,
        )

    @property
    def net_pay(self) -> float:
        return round(self.gross_total - self.deduction_total, 2)


def _count_days(start: date, end: date) -> int:
    return (end - start).days + 1


def _sum_trip_fees(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> float:
    stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= start,
        DailyJob.work_date <= end,
    )
    if site_code:
        stmt = stmt.where(DailyJob.site_code == site_code)
    rows = session.exec(stmt).all()
    return round(sum((r.trip_fee_driver or 0.0) for r in rows), 2)


def _count_trips(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> int:
    """Count DailyJob rows that represent an actual trip (has trip_fee_driver > 0
    or revenue_customer > 0). Used for LCB "พิเศษ 100฿ per trip" bonus."""
    stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= start,
        DailyJob.work_date <= end,
    )
    if site_code:
        stmt = stmt.where(DailyJob.site_code == site_code)
    rows = session.exec(stmt).all()
    count = 0
    for r in rows:
        if (r.trip_fee_driver or 0.0) > 0 or (r.revenue_customer or 0.0) > 0:
            count += 1
    return count


def _sum_gross_revenue(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> float:
    stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= start,
        DailyJob.work_date <= end,
    )
    if site_code:
        stmt = stmt.where(DailyJob.site_code == site_code)
    rows = session.exec(stmt).all()
    return round(sum((r.revenue_customer or 0.0) for r in rows), 2)


def _sum_fuel_cost(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> float:
    stmt = select(FuelTxn).where(
        FuelTxn.driver_id == emp_id,
        FuelTxn.txn_date >= start,
        FuelTxn.txn_date <= end,
    )
    if site_code:
        stmt = stmt.where(FuelTxn.site_code == site_code)
    rows = session.exec(stmt).all()
    return round(sum((r.amount or 0.0) for r in rows), 2)


# BIGC fuel-rate rebate rate: driver is paid ฿16 per liter of the fuel allowance
# they did NOT consume. Half of the original ~฿32/L price, sharing the saving 50/50.
BIGC_FUEL_RATE_REBATE = 16.0
# When residual (budget − consumed) is negative, Excel charges full pump-style
# THB/L to the driver (ลูกค้า/แอดมินใช้ ~32.15 ในไฟล์ มี.ค. 69 — ปรับค่าคงที่ได้)
BIGC_FUEL_OVERSPEND_THB_PER_L = 32.15


def _parse_custom_terms(raw: str) -> dict:
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _annual_progressive_tax(annual_taxable_income: float) -> float:
    """Thai progressive PIT brackets (บุคคลธรรมดา) for annual taxable income."""
    taxable = max(float(annual_taxable_income or 0.0), 0.0)
    if taxable <= 0:
        return 0.0
    brackets = [
        (150000.0, 0.00),
        (300000.0, 0.05),
        (500000.0, 0.10),
        (750000.0, 0.15),
        (1000000.0, 0.20),
        (2000000.0, 0.25),
        (5000000.0, 0.30),
        (float("inf"), 0.35),
    ]
    tax = 0.0
    prev = 0.0
    for upper, rate in brackets:
        if taxable <= prev:
            break
        slab = min(taxable, upper) - prev
        if slab > 0:
            tax += slab * rate
        prev = upper
    return round(tax, 2)


def _compute_income_tax_withholding(
    session: Session,
    calc: PayrollCalc,
    employee: Employee,
) -> float:
    """Estimate monthly withholding from annualized income (progressive PIT).

    Defaults:
    - deductible expense = 50% capped at 100,000 / year
    - personal allowance = 60,000 / year

    Optional per-employee overrides via Employee.custom_terms JSON:
    - tax_exempt: true/false
    - tax_mode: "catch_up" | "safe" (default catch_up)
    - tax_monthly_cap_rate: number (default 0.15)
    - tax_deduct_expense_pct: number (default 0.5)
    - tax_deduct_expense_cap: number (default 100000)
    - tax_personal_allowance: number (default 60000)
    - tax_extra_allowance_annual: number (default 0)
    """
    if calc.gross_total <= 0:
        return 0.0
    terms = _parse_custom_terms(employee.custom_terms or "")
    if terms.get("tax_exempt") is True:
        return 0.0

    # Default mode = catch-up (ผู้ใช้อนุมัติเป็นค่าเริ่มต้น)
    tax_mode = str(terms.get("tax_mode", "catch_up") or "catch_up").strip().lower()

    # Build projected annual income from YTD actual + projected remaining months.
    # Payroll runs are monthly-tagged; period_end.month is the cycle's end month.
    month_idx = max(min(calc.period_end.month, 12), 1)
    ytd_rows = session.exec(
        select(PayRunItem, PayRun)
        .join(PayRun, PayRun.id == PayRunItem.pay_run_id)
        .where(
            PayRunItem.employee_id == employee.id,
            PayRun.period_end >= date(calc.period_end.year, 1, 1),
            PayRun.period_end < calc.period_end,
        )
    ).all()
    ytd_gross_before = sum((it.gross_total or 0.0) for it, _pr in ytd_rows)
    ytd_tax_withheld_before = sum((it.income_tax_withholding or 0.0) for it, _pr in ytd_rows)

    ytd_gross_including_current = ytd_gross_before + max(calc.gross_total, 0.0)
    months_remaining_including_current = 12 - month_idx + 1
    months_remaining_after_current = max(12 - month_idx, 0)
    projected_annual_income = ytd_gross_including_current + (max(calc.gross_total, 0.0) * months_remaining_after_current)
    exp_pct = float(terms.get("tax_deduct_expense_pct", 0.5) or 0.5)
    exp_cap = float(terms.get("tax_deduct_expense_cap", 100000.0) or 100000.0)
    expense = min(projected_annual_income * exp_pct, exp_cap)
    personal_allowance = float(terms.get("tax_personal_allowance", 60000.0) or 60000.0)
    extra_allowance = float(terms.get("tax_extra_allowance_annual", 0.0) or 0.0)

    annual_taxable = max(projected_annual_income - expense - personal_allowance - extra_allowance, 0.0)
    annual_tax = _annual_progressive_tax(annual_taxable)
    if annual_tax <= 0:
        return 0.0

    cap_rate = float(terms.get("tax_monthly_cap_rate", 0.15) or 0.15)
    cap_rate = min(max(cap_rate, 0.0), 1.0)
    net_before_tax = max(calc.gross_total - (calc.deduction_total - calc.income_tax_withholding), 0.0)
    monthly_cap = round(net_before_tax * cap_rate, 2)

    if tax_mode == "safe":
        # Safe mode: start deducting once projected annual tax > 0, no backlog chase.
        raw_monthly = round(annual_tax / 12.0, 2)
        return round(min(raw_monthly, monthly_cap), 2)

    # Catch-up mode (default): spread remaining tax over remaining months
    # after subtracting what was already withheld in prior runs this year.
    remaining_tax = max(annual_tax - ytd_tax_withheld_before, 0.0)
    if months_remaining_including_current <= 0:
        raw_monthly = round(remaining_tax, 2)
    else:
        raw_monthly = round(remaining_tax / months_remaining_including_current, 2)
    return round(min(raw_monthly, monthly_cap), 2)


def _get_pay_run_adjust(
    session: Session, pay_run_id: Optional[int], employee_id: int
) -> Optional[PayRunAdjust]:
    if pay_run_id is None:
        return None
    return session.exec(
        select(PayRunAdjust).where(
            PayRunAdjust.pay_run_id == pay_run_id,
            PayRunAdjust.employee_id == employee_id,
        )
    ).first()


def _compute_bigc_fuel_rebate(
    session: Session,
    emp_id: int,
    start: date,
    end: date,
    site_code: str = "",
    adjust: Optional[PayRunAdjust] = None,
) -> tuple[float, float, float, float]:
    """Compute BIGC "ค่าเรทน้ำมัน" — ฿16 × (budget − consumed + admin_adjust).

    Can be **negative** when driver overspent (payroll deduction).

    Returns: (rebate_thb, budgeted_liters, consumed_liters, residual_liters)
    """
    fuel_stmt = select(FuelTxn).where(
        FuelTxn.driver_id == emp_id,
        FuelTxn.txn_date >= start,
        FuelTxn.txn_date <= end,
    )
    if site_code:
        fuel_stmt = fuel_stmt.where(FuelTxn.site_code == site_code)
    fuel_rows = session.exec(fuel_stmt).all()
    consumed = sum((r.liter or 0.0) for r in fuel_rows)

    daily_stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= start,
        DailyJob.work_date <= end,
    )
    if site_code:
        daily_stmt = daily_stmt.where(DailyJob.site_code == site_code)
    daily_rows = session.exec(daily_stmt).all()
    budgeted = sum((r.fuel_liter or 0.0) for r in daily_rows)

    adjust_l = (adjust.fuel_adjust_liter if adjust else 0.0) or 0.0
    residual = budgeted - consumed + adjust_l

    # Manual rebate override — bypasses auto-compute entirely
    if adjust and adjust.fuel_rate_override_thb is not None:
        return (
            round(adjust.fuel_rate_override_thb, 2),
            round(budgeted, 2),
            round(consumed, 2),
            round(residual, 2),
        )

    if budgeted <= 0 and adjust_l == 0:
        return (0.0, 0.0, round(consumed, 2), 0.0)

    if residual < 0:
        rebate = round(residual * BIGC_FUEL_OVERSPEND_THB_PER_L, 2)
    else:
        rebate = round(residual * BIGC_FUEL_RATE_REBATE, 2)
    return (rebate, round(budgeted, 2), round(consumed, 2), round(residual, 2))


def _sum_ayu_toll_deduction(session: Session, emp_id: int, tag: str, site_code: str = "") -> float:
    """AYU mao drivers pay tolls themselves. When petty cash pays for tolls on
    their behalf (direction=out + category=toll), it becomes a payroll deduction."""
    stmt = select(PettyCashTxn).where(
        PettyCashTxn.driver_id == emp_id,
        PettyCashTxn.pay_cycle_tag == tag,
        PettyCashTxn.direction == "out",
        PettyCashTxn.category == "toll",
    )
    if site_code:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                PettyCashTxn.site_code == site_code,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            )
        )
    rows = session.exec(stmt).all()
    return round(sum((r.amount or 0.0) for r in rows), 2)


def _resolve_effective_window(
    session: Session, emp_id: int, start: date, end: date
) -> tuple[date, date]:
    """Compute the effective employment window for an employee within [start, end].

    Applies the same rules as calc_one_employee:
    - Trim by Employee.start_date / end_date if set
    - Fallback: when start_date is missing, use first DailyJob in period (if AFTER period_start)
    - Resignation trim: when end_date is set, trim eff_end to last DailyJob in window
      (the resignation-filing day often isn't a real work day)
    Returns (eff_start, eff_end). If eff_end < eff_start the window is empty.
    """
    eff_start = start
    eff_end = end
    emp_obj = session.get(Employee, emp_id)
    if emp_obj is not None:
        if emp_obj.start_date and emp_obj.start_date > eff_start:
            eff_start = emp_obj.start_date
        if emp_obj.end_date and emp_obj.end_date < eff_end:
            eff_end = emp_obj.end_date
        if not emp_obj.start_date:
            first_work = session.exec(
                select(DailyJob.work_date)
                .where(
                    DailyJob.driver_id == emp_id,
                    DailyJob.work_date >= start,
                    DailyJob.work_date <= end,
                )
                .order_by(DailyJob.work_date.asc())
                .limit(1)
            ).first()
            if first_work and first_work > eff_start:
                eff_start = first_work
        if emp_obj.end_date and eff_end >= eff_start:
            last_work = session.exec(
                select(DailyJob.work_date)
                .where(
                    DailyJob.driver_id == emp_id,
                    DailyJob.work_date >= eff_start,
                    DailyJob.work_date <= eff_end,
                )
                .order_by(DailyJob.work_date.desc())
                .limit(1)
            ).first()
            if last_work and last_work < eff_end:
                eff_end = last_work
    return eff_start, eff_end


def _count_work_days(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> dict[str, float]:
    """Return dict with keys: worked, leave, absent, company_no_work.

    Business rule (BIGC manual-style):
    - worked = วันที่มีข้อมูลเดลี่ของคนขับคนนั้น - leave - absent
    - NO_WORK (รองาน/รถจอด) ไม่นำไปหัก worked
    - ถ้าไม่มีแถวเดลี่เลยในช่วงนั้น -> worked=0 (รองรับเคสยังไม่เริ่มงาน/ลาออก)
    - วันใน employment window ที่ไม่มี DailyJob เลย = "implicit absent" (ขาดงานเงียบ)
      → ถูกบวกเข้า absent ตาม policy "ไม่มีงาน=หัก"
    """
    # Honor employee's effective employment window (start/end + fallbacks)
    eff_start, eff_end = _resolve_effective_window(session, emp_id, start, end)

    stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= eff_start,
        DailyJob.work_date <= eff_end,
    )
    if site_code:
        stmt = stmt.where(DailyJob.site_code == site_code)
    rows = session.exec(stmt).all()
    # One employee may have multiple DailyJob rows per day (multiple trips).
    # Count distinct work_date as "worked" unless all rows that day are leave/absent.
    by_date: dict[date, list[DailyJob]] = {}
    for r in rows:
        by_date.setdefault(r.work_date, []).append(r)

    # Implicit absent = days within employment window that have no DailyJob row at all.
    # Per user policy: "ชื่อใครถ้าไม่มีณ วันที่นั้นๆ หักออกเลย"
    # IMPORTANT: only apply when the employee HAS at least one DailyJob in the
    # window — otherwise it would also penalize office_monthly staff who don't
    # log DailyJob rows. (For office staff, base is prorated by explicit
    # leave/absent only.)
    if eff_end >= eff_start:
        emp_window_days = (eff_end - eff_start).days + 1
    else:
        emp_window_days = 0
    if by_date:
        implicit_absent_days = max(emp_window_days - len(by_date), 0)
    else:
        implicit_absent_days = 0

    if not by_date:
        return {
            "worked": 0.0,
            "leave": 0.0,
            "absent": 0.0,
            "company_no_work": 0.0,
        }

    leave = absent = company_no_work = 0
    for d, drows in by_date.items():
        # GUARD: ถ้าวันไหน มี trip ที่มี revenue หรือ trip_fee จริง → ทำงานจริง
        # ห้าม classify เป็น leave/absent (ป้องกัน false-positive จาก destination
        # ที่มีคำว่า "ลา" เช่น "ลาดพร้าว", "ตลาดบุญเจริญ").
        has_revenue = any(
            (r.revenue_customer or 0) > 0 or (r.trip_fee_driver or 0) > 0
            for r in drows
        )
        if has_revenue:
            continue

        # Classify this day by the "worst" status across the rows.
        # รองรับทั้งรหัสอังกฤษและคำไทยจากไฟล์เดลี่ (เช่น "ลา", "ขาด", "ป่วย").
        # NOTE: ตัด destination ออกจาก scan ทั่วไป (destination เป็นชื่อสถานที่)
        # ยกเว้นคำว่า "เข้าบ้าน" ที่ admin ใช้เป็น status (ไม่ใช่ชื่อสถานที่)
        leave_statuses = {(r.leave_status or "").strip().lower() for r in drows}
        status_codes = {(r.status_code or "").strip().lower() for r in drows}
        # Token-based match: split by spaces/punctuation เพื่อกัน "ลา" match ภายใน "ลาดพร้าว"
        import re as _re_local
        tokens: set[str] = set()
        has_home_visit = False
        for r in drows:
            blob = " ".join([
                (r.leave_status or ""),
                (r.status_code or ""),
                (r.remark or ""),
            ]).strip().lower()
            for tok in _re_local.split(r"[\s/,;()\[\]\-_.]+", blob):
                tok = tok.strip()
                if tok:
                    tokens.add(tok)
            # "เข้าบ้าน" might be in destination (admin uses it as a status marker)
            dest_blob = (r.destination or "").strip().lower()
            if "เข้าบ้าน" in dest_blob or "เข้าบ้าน" in blob:
                has_home_visit = True

        is_absent = (
            ("absent" in leave_statuses)
            or ("ขาด" in tokens)
        )
        is_leave = (
            ("leave" in status_codes)
            or ("sick" in leave_statuses)
            or ("personal" in leave_statuses)
            or ("ลา" in tokens)
            or ("ป่วย" in tokens)
            or ("ลากิจ" in tokens)
            or ("ลาป่วย" in tokens)
            or ("ลาออก" in tokens)
            or ("หยุด" in tokens)
            # Domain rule: คนขับแจ้ง "เข้าบ้าน" = ขอลากลับบ้าน (นับเป็นลา)
            or has_home_visit
        )
        is_company_no_work = (
            ("company_no_work" in leave_statuses)
            or ("idle" in status_codes)
            or ("ไม่มีงาน" in tokens)
            or ("รถจอด" in tokens)
            or ("รองาน" in tokens)
        )

        if is_absent:
            absent += 1
        elif is_leave:
            leave += 1
        elif is_company_no_work:
            company_no_work += 1
    # worked = all dates with any row - leave - absent (ignore NO_WORK deduction)
    worked = max(len(by_date) - leave - absent, 0)
    # Total absent = explicit (admin tagged) + implicit (no row at all)
    total_absent = absent + implicit_absent_days
    return {
        "worked": float(worked),
        "leave": float(leave),
        "absent": float(total_absent),
        "company_no_work": float(company_no_work),
    }


def _sum_petty_cash_deduction(
    session: Session, emp_id: int, tag: str, site_code: str = "", exclude_toll: bool = False
) -> float:
    """Sum petty-cash rows flagged deduct_from_driver, in this driver's cycle tag.

    exclude_toll=True for ayu_mao drivers (tolls handled separately as they're a
    category-specific deduction rule even without the deduct_from_driver flag)."""
    stmt = select(PettyCashTxn).where(
        PettyCashTxn.driver_id == emp_id,
        PettyCashTxn.pay_cycle_tag == tag,
        PettyCashTxn.deduct_from_driver == True,   # noqa: E712
        PettyCashTxn.deduction_status == "pending",
    )
    if site_code:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                PettyCashTxn.site_code == site_code,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            )
        )
    if exclude_toll:
        stmt = stmt.where(PettyCashTxn.category != "toll")
    rows = session.exec(stmt).all()
    total = 0.0
    for r in rows:
        total += (r.deduct_amount if r.deduct_amount is not None else (r.amount or 0.0))
    return round(total, 2)


def _sum_accident_install(
    session: Session, emp_id: int, tag: str
) -> float:
    """AccidentInstallment is tagged with due_cycle (YYYY-MM). employee lookup via case."""
    from models import AccidentCase
    rows = session.exec(
        select(AccidentInstallment, AccidentCase)
        .join(AccidentCase, AccidentCase.id == AccidentInstallment.case_id)
        .where(
            AccidentCase.driver_id == emp_id,
            AccidentInstallment.due_cycle == tag,
            AccidentInstallment.status.in_(["planned", "pending"]),
        )
    ).all()
    return round(sum((inst.amount or 0.0) for inst, _case in rows), 2)


def calc_one_employee(
    session: Session,
    employee: Employee,
    start: date,
    end: date,
    tag: str,
    pay_run_id: Optional[int] = None,
) -> PayrollCalc:
    calc = PayrollCalc(employee=employee, period_start=start, period_end=end)
    mode = employee.pay_mode or ""
    site = employee.home_site_code
    base = employee.base_salary or 0.0
    care = employee.care_allowance or 0.0
    days = _count_work_days(session, employee.id, start, end, site_code=site)
    calc.days_worked = days["worked"]
    calc.days_leave = days["leave"]
    calc.days_absent = days["absent"]
    calc.days_company_no_work = days["company_no_work"]

    period_days = _count_days(start, end)
    # Daily divisor uses the actual number of calendar days in the pay cycle
    # for every site (BIGC: 28-31, LCB: 28-31 across 16→15, AYU: 28-31 across
    # 26→25). Matches user policy "หารตามจำนวนวันของเดือนนั้นๆ".
    days_in_month = float(period_days) if period_days > 0 else 30.0

    # Employment window inside this pay period — single source of truth via helper
    # (also used by _count_work_days for implicit-absent detection)
    eff_emp_start, eff_emp_end = _resolve_effective_window(session, employee.id, start, end)
    if eff_emp_end >= eff_emp_start:
        employed_days_in_period = _count_days(eff_emp_start, eff_emp_end)
    else:
        employed_days_in_period = 0
    not_employed_days = max(period_days - employed_days_in_period, 0)

    adjust = _get_pay_run_adjust(session, pay_run_id, employee.id)

    # Apply manual day overrides if admin set them on PayRunAdjust
    if adjust is not None:
        if adjust.days_worked_override is not None:
            calc.days_worked = float(adjust.days_worked_override)
        if adjust.days_leave_override is not None:
            calc.days_leave = float(adjust.days_leave_override)
        if adjust.days_absent_override is not None:
            calc.days_absent = float(adjust.days_absent_override)

    # ---- Earnings ----
    if mode in ("bigc_monthly", "bigc_standard"):
        if base == 0:
            base = 9000.0
        # Start full, deduct per missed day (leave/absent + not-employed).
        missed = calc.days_leave + calc.days_absent + not_employed_days
        calc.base_salary_earned = round(base - (base / days_in_month) * missed, 2)
        calc.trip_fee_total = _sum_trip_fees(session, employee.id, start, end, site_code=site)
        rebate, budgeted, consumed, residual = _compute_bigc_fuel_rebate(
            session, employee.id, start, end, site_code=site, adjust=adjust
        )
        calc.fuel_rate_income = rebate
        calc.fuel_budget_liter = budgeted
        calc.fuel_consumed_liter = consumed
        calc.fuel_residual_liter = residual
        adj_l = (adjust.fuel_adjust_liter if adjust else 0.0) or 0.0
        if budgeted > 0:
            adj_str = f" (+adjust {adj_l:+.1f})" if adj_l else ""
            calc.note = (
                f"เรทน้ำมัน: งบ {budgeted:,.1f}L − ใช้จริง {consumed:,.1f}L"
                f"{adj_str} = residual {residual:,.1f}L × 16฿ = {rebate:,.0f}"
            )
        else:
            calc.note = (
                "ค่าเรทน้ำมัน = 0 (ยังไม่ได้ import ไฟล์เรทน้ำมัน BIGC)"
            )

    elif mode in ("lcb_monthly", "lcb_trip"):
        if base == 0:
            base = 9240.0
        if care == 0:
            care = 3000.0
        missed = calc.days_leave + calc.days_absent + not_employed_days
        calc.base_salary_earned = round(base - (base / days_in_month) * missed, 2)
        calc.care_allowance_earned = round(care - (care / days_in_month) * missed, 2)
        calc.trip_fee_total = _sum_trip_fees(session, employee.id, start, end, site_code=site)
        # LCB "พิเศษ" = 100฿ ต่อเที่ยว (เริ่มสมัยโควิท) — เก็บใน other_income
        trip_count = _count_trips(session, employee.id, start, end, site_code=site)
        calc.other_income += round(trip_count * 100.0, 2)
        calc.note = (
            f"LCB: base {base:,.0f} + care {care:,.0f} ÷ {int(days_in_month)}วัน"
            f" (ลา/ขาด {int(missed)}วัน) + trip {calc.trip_fee_total:,.0f}"
            f" + พิเศษ {trip_count}เที่ยว×100 = {trip_count*100:,}"
        )

    elif mode == "lcb_mao":
        revenue = _sum_gross_revenue(session, employee.id, start, end, site_code=site)
        share_rate = employee.gross_share_rate or 0.60
        calc.fuel_share_income = round(revenue * share_rate, 2)
        calc.fuel_cost_self = _sum_fuel_cost(session, employee.id, start, end, site_code=site)
        calc.note = f"Gross revenue {revenue:,.2f} × {share_rate*100:.0f}% − น้ำมันจริง"

    elif mode == "ayu_trip":
        calc.trip_fee_total = _sum_trip_fees(session, employee.id, start, end, site_code=site)
        if employee.has_guarantee and employee.guarantee_monthly_amount > 0:
            # Guarantee applies only to "company_no_work" days, not absent/leave
            eligible_days = calc.days_worked + calc.days_company_no_work
            if eligible_days > 0:
                prorated_guarantee = (
                    employee.guarantee_monthly_amount / days_in_month
                ) * eligible_days
                if calc.trip_fee_total < prorated_guarantee:
                    calc.guarantee_topup = round(prorated_guarantee - calc.trip_fee_total, 2)
                    calc.note = f"การันตี {prorated_guarantee:,.2f} > ค่าเที่ยวจริง {calc.trip_fee_total:,.2f}"

    elif mode == "ayu_trip_self_fuel":
        # AYU drivers who pay their own fuel: gross = trip_fee, but fuel_cost_self
        # becomes a deduction line (like lcb_mao). Used for นิวัติ, เรวัตร, ธัชชนพล, เสรี.
        calc.trip_fee_total = _sum_trip_fees(session, employee.id, start, end, site_code=site)
        calc.fuel_cost_self = _sum_fuel_cost(session, employee.id, start, end, site_code=site)
        calc.note = (
            f"AYU self-fuel: trip {calc.trip_fee_total:,.0f} − น้ำมัน {calc.fuel_cost_self:,.0f}"
        )

    elif mode == "ayu_mao":
        revenue = _sum_gross_revenue(session, employee.id, start, end, site_code=site)
        share_rate = employee.gross_share_rate or 0.60
        calc.fuel_share_income = round(revenue * share_rate, 2)
        calc.fuel_cost_self = _sum_fuel_cost(session, employee.id, start, end, site_code=site)
        # AYU mao drivers ALSO pay their own tolls/Mflow — petty cash rows with
        # category=toll for this driver become a deduction.
        calc.other_deduction += _sum_ayu_toll_deduction(session, employee.id, tag, site_code=site)
        calc.note = f"60% × {revenue:,.0f} − น้ำมัน − ทางด่วน/Mflow"

    elif mode == "office_monthly":
        # Office staff: base salary + fixed monthly bonus (stored in
        # guarantee_monthly_amount for convenience). Pay is prorated only if
        # they were explicitly absent/on-leave (no DailyJob rows expected for
        # office roles).
        missed = calc.days_leave + calc.days_absent + not_employed_days
        calc.base_salary_earned = round(base - (base / days_in_month) * missed, 2)
        bonus = employee.guarantee_monthly_amount or 0.0
        calc.other_income += round(bonus - (bonus / days_in_month) * missed, 2)
        calc.note = f"Office: base {base:,.0f} + bonus {bonus:,.0f}"

    elif mode == "none":
        calc.note = "ไม่ใช่คนขับ — ข้าม payroll"
        return calc   # no deductions either

    else:
        calc.note = f"pay_mode ไม่รู้จัก: {mode!r}"

    # ---- Deductions ----
    # ---- Social Security ----
    # Resolve effective rate / min / max in priority order:
    #   1) PayRunAdjust per-employee override
    #   2) PayRun-level override (applies to whole run, e.g. รัฐลด rate ทั้ง period)
    #   3) Employee defaults
    #   4) Hard defaults: rate 5%, min 1650, max 15000 (Thai law)
    pay_run_obj = session.get(PayRun, pay_run_id) if pay_run_id else None
    ss_rate = (
        (adjust.ss_rate_override if adjust and adjust.ss_rate_override is not None else None)
        or (pay_run_obj.ss_rate if pay_run_obj and pay_run_obj.ss_rate is not None else None)
        or (employee.social_security_rate if employee.social_security_rate else None)
        or 0.05
    )
    ss_base_min = (
        (adjust.ss_base_min_override if adjust and adjust.ss_base_min_override is not None else None)
        or (pay_run_obj.ss_base_min if pay_run_obj and pay_run_obj.ss_base_min is not None else None)
        or 1650.0
    )
    ss_base_max = (
        (adjust.ss_base_max_override if adjust and adjust.ss_base_max_override is not None else None)
        or (pay_run_obj.ss_base_max if pay_run_obj and pay_run_obj.ss_base_max is not None else None)
        or 15000.0
    )

    # Imputed SS base: คนเหมา (mao / trip-only) ถูกอนุมานเป็นเงินเดือน 9,000
    # ตามข้อตกลง user — ใช้คำนวณ SS เท่านั้น ไม่ใช่จ่ายเพิ่ม
    raw_ss_base = employee.social_security_base or 0.0
    if raw_ss_base <= 0:
        if mode in (
            "lcb_mao", "ayu_mao", "ayu_trip", "ayu_trip_self_fuel",
            "bigc_monthly", "bigc_standard", "lcb_monthly", "office_monthly",
        ):
            raw_ss_base = 9000.0
        else:
            raw_ss_base = 0.0

    # Order of operations matters:
    #   1) Prorate the contract base by employment-window & leave/absent
    #   2) THEN clamp to legal min/max (1,650 / 15,000)
    # This produces the correct floor: anyone who worked at least one day in
    # the cycle pays at least 5% × 1,650 ≈ 83 ฿ (Thai SS minimum).
    missed_days = calc.days_leave + calc.days_absent + not_employed_days
    work_factor = max((days_in_month - missed_days) / days_in_month, 0.0) if days_in_month > 0 else 0.0
    prorated_base = raw_ss_base * work_factor
    if prorated_base > 0:
        capped_base = max(ss_base_min, min(prorated_base, ss_base_max))
    else:
        # No employment days at all → no SS contribution (e.g. fully resigned)
        capped_base = 0.0
    # Thai SSO รายงานเป็นจำนวนเต็มบาทและปัดขึ้นเสมอ:
    #   82.50 → 83 ฿ (ขั้นต่ำ), 435.48 → 436 ฿
    raw_ss = capped_base * ss_rate
    calc.social_security = float(math.ceil(raw_ss)) if raw_ss > 0 else 0.0

    # Deposit: 1000/mo until target reached
    if (employee.deposit_balance or 0.0) < (employee.deposit_target or 10000.0):
        remaining = (employee.deposit_target or 10000.0) - (employee.deposit_balance or 0.0)
        calc.deposit_install = round(min(1000.0, remaining), 2)

    calc.accident_install = _sum_accident_install(session, employee.id, tag)
    # For ayu_mao, tolls are already in other_deduction; don't double-count.
    calc.petty_cash_deduction = _sum_petty_cash_deduction(
        session, employee.id, tag, site_code=site, exclude_toll=(mode == "ayu_mao")
    )
    # Income-tax withholding (progressive annualized estimate).
    income_tax = _compute_income_tax_withholding(session, calc, employee)
    calc.income_tax_withholding = income_tax
    if income_tax > 0:
        calc.note = (calc.note + f" | ภาษีหัก ณ ที่จ่าย {income_tax:,.2f}/เดือน").strip(" |")

    return calc


# ---------------------------------------------------------------------
# PayRun orchestration
# ---------------------------------------------------------------------

def get_or_create_pay_run(
    session: Session, site_code: str, tag: str, notes: str = ""
) -> PayRun:
    existing = session.exec(
        select(PayRun).where(PayRun.site_code == site_code, PayRun.pay_cycle_tag == tag)
    ).first()
    if existing is not None:
        return existing
    start, end = compute_period(site_code, tag)
    pr = PayRun(
        site_code=site_code,
        pay_cycle_tag=tag,
        period_start=start,
        period_end=end,
        status="draft",
        notes=notes,
    )
    session.add(pr)
    session.commit()
    session.refresh(pr)
    return pr


def compute_pay_run(
    session: Session, pay_run: PayRun, recompute: bool = True
) -> list[PayRunItem]:
    """Compute PayRunItems for every Employee belonging to this site (role=driver)."""
    if pay_run.status == "finalized" and not recompute:
        return session.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pay_run.id)
        ).all()

    # Delete old items if recompute
    if recompute:
        old_items = session.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pay_run.id)
        ).all()
        for o in old_items:
            session.delete(o)
        session.flush()

    start, end = pay_run.period_start, pay_run.period_end
    tag = pay_run.pay_cycle_tag

    # Employees at this site. We later filter by employment overlap with pay period
    # so resigned drivers can still appear in historical cycles they worked in.
    emps = session.exec(
        select(Employee).where(
            Employee.home_site_code == pay_run.site_code,
        )
    ).all()

    items: list[PayRunItem] = []
    for emp in emps:
        # employment overlap guard:
        # - start_date after period_end => not started yet
        # - end_date before period_start => already left before this cycle
        if emp.start_date and emp.start_date > end:
            continue
        if emp.end_date and emp.end_date < start:
            continue
        role = (emp.role or "driver")
        if role not in ("driver", "office"):
            continue
        if (emp.pay_mode or "") == "none":
            continue
        mode = emp.pay_mode or ""
        # Activity filter applies to drivers only. Office staff never have
        # DailyJob rows so they're always included.
        if role != "office" and mode != "office_monthly":
            dj_count = session.exec(
                select(sa_func.count()).select_from(DailyJob).where(
                    DailyJob.driver_id == emp.id,
                    DailyJob.work_date >= start,
                    DailyJob.work_date <= end,
                )
            ).one()
            if mode in ("lcb_mao", "ayu_mao"):
                ft_count = session.exec(
                    select(sa_func.count()).select_from(FuelTxn).where(
                        FuelTxn.driver_id == emp.id,
                        FuelTxn.txn_date >= start,
                        FuelTxn.txn_date <= end,
                    )
                ).one()
                if (dj_count or 0) == 0 and (ft_count or 0) == 0:
                    continue
            elif (dj_count or 0) == 0:
                continue
        calc = calc_one_employee(session, emp, start, end, tag, pay_run_id=pay_run.id)
        item = PayRunItem(
            pay_run_id=pay_run.id,
            employee_id=emp.id,
            site_code=emp.home_site_code,
            pay_mode=emp.pay_mode,
            days_worked=calc.days_worked,
            days_leave=calc.days_leave,
            days_absent=calc.days_absent,
            days_company_no_work=calc.days_company_no_work,
            base_salary_earned=calc.base_salary_earned,
            care_allowance_earned=calc.care_allowance_earned,
            trip_fee_total=calc.trip_fee_total,
            fuel_rate_income=calc.fuel_rate_income,
            fuel_share_income=calc.fuel_share_income,
            guarantee_topup=calc.guarantee_topup,
            other_income=calc.other_income,
            gross_total=calc.gross_total,
            fuel_budget_liter=calc.fuel_budget_liter,
            fuel_consumed_liter=calc.fuel_consumed_liter,
            fuel_residual_liter=calc.fuel_residual_liter,
            social_security=calc.social_security,
            income_tax_withholding=calc.income_tax_withholding,
            deposit_install=calc.deposit_install,
            accident_install=calc.accident_install,
            petty_cash_deduction=calc.petty_cash_deduction,
            fuel_cost_self=calc.fuel_cost_self,
            other_deduction=calc.other_deduction,
            deduction_total=calc.deduction_total,
            net_pay=calc.net_pay,
            note=calc.note,
        )
        session.add(item)
        items.append(item)
    session.commit()
    for it in items:
        session.refresh(it)
    return items
