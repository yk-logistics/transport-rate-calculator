"""
Finance / CFO Dashboard services.

Provides:
- amortization schedule for a Loan
- monthly P&L aggregation (revenue, cost breakdown)
- cost per vehicle / per km / per trip
- cash flow projection (next N days)
- break-even + cash runway

No side effects. All functions take a Session and return plain dicts/lists.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func as sa_func
from sqlmodel import Session, select

from models import (
    DailyJob,
    DailyJobFee,
    Employee,
    FuelTxn,
    Loan,
    LoanPayment,
    MaintRecord,
    PayRun,
    PayRunItem,
    PettyCashTxn,
    Vehicle,
)


# --------------------------------------------------------------------------
# DATE HELPERS
# --------------------------------------------------------------------------

def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def add_months(d: date, n: int) -> date:
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def parse_month(ym: str) -> tuple[int, int]:
    """'2026-04' → (2026, 4). Accept '2026-4' too."""
    parts = ym.split("-")
    return int(parts[0]), int(parts[1])


# --------------------------------------------------------------------------
# LOAN / DEBT
# --------------------------------------------------------------------------

@dataclass
class AmortRow:
    idx: int
    due_date: date
    beginning_balance: float
    payment: float
    interest: float
    principal: float
    ending_balance: float


def compute_monthly_payment(principal: float, annual_rate_pct: float, term_months: int) -> float:
    """Standard amortization formula."""
    if term_months <= 0 or principal <= 0:
        return 0.0
    r = (annual_rate_pct / 100.0) / 12.0
    if r == 0:
        return principal / term_months
    return principal * r * (1 + r) ** term_months / ((1 + r) ** term_months - 1)


def amortization_schedule(loan: Loan, max_rows: int = 360) -> list[AmortRow]:
    """Generate month-by-month schedule. Uses monthly_payment if set, else computes it.
    For revolving (term_months=0) → interest-only monthly on current_balance."""
    rows: list[AmortRow] = []
    principal = loan.principal or 0.0
    rate = loan.annual_rate_pct or 0.0
    term = loan.term_months or 0
    r = (rate / 100.0) / 12.0
    start = loan.first_payment_date or loan.start_date or date.today()

    if loan.loan_kind == "revolving" or term == 0:
        # interest-only, up to 36 projections; uses current_balance
        bal = loan.current_balance or principal
        payment = loan.monthly_payment or (bal * r)
        for i in range(min(36, max_rows)):
            due = add_months(start, i)
            interest = bal * r
            princ_paid = max(0.0, payment - interest)
            end_bal = max(0.0, bal - princ_paid)
            rows.append(AmortRow(i + 1, due, bal, payment, interest, princ_paid, end_bal))
            bal = end_bal
            if bal <= 0.01:
                break
        return rows

    # Standard term loan
    payment = loan.monthly_payment if loan.monthly_payment > 0 else compute_monthly_payment(principal, rate, term)
    bal = principal
    for i in range(min(term, max_rows)):
        due = add_months(start, i)
        interest = bal * r
        princ_paid = payment - interest
        end_bal = max(0.0, bal - princ_paid)
        rows.append(AmortRow(i + 1, due, bal, payment, interest, princ_paid, end_bal))
        bal = end_bal
        if bal <= 0.01:
            break
    return rows


def loan_summary(session: Session) -> dict:
    """Aggregate all active loans: total principal, total balance, monthly burden, yearly interest."""
    loans = session.exec(select(Loan).where(Loan.status == "active")).all()

    total_principal = 0.0
    total_balance = 0.0
    monthly_burden = 0.0
    next_year_interest = 0.0
    by_kind: dict[str, dict] = {}

    for loan in loans:
        total_principal += loan.principal or 0.0
        total_balance += loan.current_balance or 0.0
        mp = loan.monthly_payment or compute_monthly_payment(
            loan.principal or 0.0, loan.annual_rate_pct or 0.0, loan.term_months or 0
        )
        if loan.loan_kind == "revolving" and loan.current_balance:
            mp = loan.monthly_payment or (loan.current_balance * (loan.annual_rate_pct / 100.0) / 12.0)
        monthly_burden += mp

        # Estimate next 12 months interest
        schedule = amortization_schedule(loan, max_rows=12)
        next_year_interest += sum(r.interest for r in schedule)

        g = by_kind.setdefault(loan.loan_kind, {"count": 0, "balance": 0.0, "monthly": 0.0})
        g["count"] += 1
        g["balance"] += loan.current_balance or 0.0
        g["monthly"] += mp

    return {
        "count": len(loans),
        "total_principal": total_principal,
        "total_balance": total_balance,
        "monthly_burden": monthly_burden,
        "next_year_interest": next_year_interest,
        "by_kind": by_kind,
    }


# --------------------------------------------------------------------------
# P&L MONTHLY
# --------------------------------------------------------------------------

def monthly_pnl(session: Session, year: int, month: int, site: str = "",
                include_other_petty: bool = False) -> dict:
    """Compute P&L for one month. Simple cash-basis view.

    Revenue = sum DailyJob.revenue_customer + sum DailyJobFee.amount
    Costs:
      - Fuel (sum FuelTxn amount in period, for AYU/BIGC/LCB depending on pay_mode)
      - Petty cash (sum expenses that are real cash-out, not deduction-from-driver)
      - Payroll (from PayRun that matches the period)
      - Maintenance (sum MaintRecord.total_cost in period)
      - WHT (sum wht_53 as receivables withheld, not a P&L expense — tracked separately)
    """
    start, end = month_bounds(year, month)

    # --- Revenue ---
    stmt = select(DailyJob).where(DailyJob.work_date >= start, DailyJob.work_date <= end)
    if site:
        stmt = stmt.where(DailyJob.site_code == site)
    jobs = session.exec(stmt).all()
    job_ids = [j.id for j in jobs]

    revenue_transport = sum((j.revenue_customer or 0.0) for j in jobs)
    total_wht = sum((j.wht_53 or 0.0) for j in jobs)
    trip_count = len(jobs)

    # Fees on jobs (lift, yard, etc.)
    revenue_fees = 0.0
    if job_ids:
        fees = session.exec(select(DailyJobFee).where(DailyJobFee.daily_job_id.in_(job_ids))).all()
        revenue_fees = sum((f.amount or 0.0) for f in fees)

    revenue_total = revenue_transport + revenue_fees

    # --- Costs ---
    # Fuel
    fuel_stmt = select(FuelTxn).where(FuelTxn.txn_date >= start, FuelTxn.txn_date <= end)
    if site:
        fuel_stmt = fuel_stmt.where(FuelTxn.site_code == site)
    fuels = session.exec(fuel_stmt).all()
    cost_fuel = sum((f.amount or 0.0) for f in fuels)
    cost_fuel_liters = sum((f.liter or 0.0) for f in fuels)

    # Petty cash — only REAL company expenses:
    # Exclude categories that double-count with Fuel/Payroll/Maint or are just advances:
    #   - driver_advance, salary_partial  (recovered from payroll)
    #   - fuel         (double-counted in FuelTxn)
    #   - repair, tire (double-counted in MaintRecord)
    #   - deposit_refund, owner_transfer (fund transfers)
    #   - customer_refund (offsets revenue)
    # Strict include: toll, parking, loading, fine, accident
    # Optional:       other (legacy data mostly here — admin can toggle)
    EXPENSE_CATEGORIES = {"toll", "parking", "loading", "fine", "accident"}
    if include_other_petty:
        EXPENSE_CATEGORIES = EXPENSE_CATEGORIES | {"other"}

    petty_stmt = select(PettyCashTxn).where(
        PettyCashTxn.txn_date >= start,
        PettyCashTxn.txn_date <= end,
        PettyCashTxn.direction == "out",
    )
    if site:
        petty_stmt = petty_stmt.where(PettyCashTxn.site_code == site)
    petties_all = session.exec(petty_stmt).all()

    # Breakdown by category (for display — shows what's included/excluded)
    petty_by_cat: dict[str, dict] = {}
    for p in petties_all:
        cat = p.category or "other"
        g = petty_by_cat.setdefault(cat, {"count": 0, "amount": 0.0, "deduct": 0.0, "included": cat in EXPENSE_CATEGORIES})
        g["count"] += 1
        g["amount"] += (p.amount or 0.0)
        if p.deduct_from_driver:
            g["deduct"] += (p.deduct_amount or 0.0)

    petties = [p for p in petties_all if (p.category or "other") in EXPENSE_CATEGORIES]
    cost_petty_gross = sum((p.amount or 0.0) for p in petties)
    petty_recovered = sum(
        (p.deduct_amount or 0.0)
        for p in petties
        if p.deduct_from_driver and (p.deduction_status or "") != "waived"
    )
    cost_petty_net = cost_petty_gross - petty_recovered

    # Payroll — use PayRunItem gross_to_pay where pay_cycle_tag matches month
    cycle_tag = f"{year:04d}-{month:02d}"
    pri_stmt = select(PayRunItem).join(PayRun, PayRunItem.pay_run_id == PayRun.id).where(
        PayRun.pay_cycle_tag == cycle_tag
    )
    if site:
        pri_stmt = pri_stmt.where(PayRun.site_code == site)
    pri_rows = session.exec(pri_stmt).all()
    cost_payroll = sum((r.gross_total or 0.0) for r in pri_rows)

    # Maintenance
    maint_stmt = select(MaintRecord).where(
        MaintRecord.work_date >= start, MaintRecord.work_date <= end
    )
    maints = session.exec(maint_stmt).all()
    cost_maint = sum((m.total_cost or 0.0) for m in maints)

    # Interest on loans (from amortization for this month)
    loans = session.exec(select(Loan).where(Loan.status == "active")).all()
    cost_interest = 0.0
    for loan in loans:
        schedule = amortization_schedule(loan, max_rows=360)
        for r in schedule:
            if start <= r.due_date <= end:
                cost_interest += r.interest

    cost_total = cost_fuel + cost_petty_net + cost_payroll + cost_maint + cost_interest

    return {
        "period": cycle_tag,
        "period_start": start,
        "period_end": end,
        "site": site or "ALL",
        "trip_count": trip_count,
        # Revenue
        "revenue_transport": revenue_transport,
        "revenue_fees": revenue_fees,
        "revenue_total": revenue_total,
        "wht": total_wht,
        # Costs
        "cost_fuel": cost_fuel,
        "cost_fuel_liters": cost_fuel_liters,
        "cost_petty_gross": cost_petty_gross,
        "petty_recovered": petty_recovered,
        "cost_petty_net": cost_petty_net,
        "petty_by_cat": petty_by_cat,
        "include_other_petty": include_other_petty,
        "cost_payroll": cost_payroll,
        "cost_maint": cost_maint,
        "cost_interest": cost_interest,
        "cost_total": cost_total,
        # Profit
        "gross_profit": revenue_total - cost_fuel - cost_payroll,
        "net_profit": revenue_total - cost_total,
        "net_margin_pct": (revenue_total - cost_total) / revenue_total * 100 if revenue_total else 0,
    }


def yearly_rollup(session: Session, year: int, site: str = "") -> list[dict]:
    """Monthly P&L for each month of a year."""
    return [monthly_pnl(session, year, m, site) for m in range(1, 13)]


# --------------------------------------------------------------------------
# COST PER VEHICLE
# --------------------------------------------------------------------------

def cost_per_vehicle(session: Session, year: int, month: int, site: str = "") -> list[dict]:
    """For each active vehicle in the period, compute revenue + cost breakdown."""
    start, end = month_bounds(year, month)

    # Jobs per vehicle (revenue side)
    stmt = select(DailyJob).where(
        DailyJob.work_date >= start, DailyJob.work_date <= end
    )
    if site:
        stmt = stmt.where(DailyJob.site_code == site)
    jobs = session.exec(stmt).all()

    # Fee map
    fees = session.exec(select(DailyJobFee)).all()
    fee_by_job: dict[int, float] = {}
    for f in fees:
        fee_by_job[f.daily_job_id] = fee_by_job.get(f.daily_job_id, 0.0) + (f.amount or 0.0)

    # Fuel per vehicle
    fuels = session.exec(
        select(FuelTxn).where(FuelTxn.txn_date >= start, FuelTxn.txn_date <= end)
    ).all()
    fuel_by_v: dict[int, tuple[float, float]] = {}  # vehicle_id → (amount, liters)
    for f in fuels:
        if f.vehicle_id:
            amt, lit = fuel_by_v.get(f.vehicle_id, (0.0, 0.0))
            fuel_by_v[f.vehicle_id] = (amt + (f.amount or 0.0), lit + (f.liter or 0.0))

    # Maintenance per vehicle
    maints = session.exec(
        select(MaintRecord).where(
            MaintRecord.work_date >= start, MaintRecord.work_date <= end
        )
    ).all()
    maint_by_v: dict[int, float] = {}
    for m in maints:
        if m.vehicle_id:
            maint_by_v[m.vehicle_id] = maint_by_v.get(m.vehicle_id, 0.0) + (m.total_cost or 0.0)

    # Aggregate per vehicle
    agg: dict[int, dict] = {}
    for j in jobs:
        vid = j.head_vehicle_id
        if not vid:
            continue
        g = agg.setdefault(vid, {
            "vehicle_id": vid, "trips": 0,
            "revenue": 0.0, "fees": 0.0,
        })
        g["trips"] += 1
        g["revenue"] += (j.revenue_customer or 0.0)
        g["fees"] += fee_by_job.get(j.id, 0.0)

    # Bring in all vehicles even if no revenue (they still incurred maint/fuel)
    for vid in set(fuel_by_v) | set(maint_by_v):
        if vid not in agg:
            agg[vid] = {"vehicle_id": vid, "trips": 0, "revenue": 0.0, "fees": 0.0}

    vehicles = session.exec(select(Vehicle)).all()
    v_map = {v.id: v for v in vehicles}

    rows = []
    for vid, g in agg.items():
        v = v_map.get(vid)
        fuel_amt, fuel_l = fuel_by_v.get(vid, (0.0, 0.0))
        maint_amt = maint_by_v.get(vid, 0.0)
        rev = g["revenue"] + g["fees"]
        cost = fuel_amt + maint_amt
        rows.append({
            "vehicle_id": vid,
            "plate": v.plate_no if v else f"?#{vid}",
            "nickname": (v.nickname or "") if v else "",
            "truck_type": (v.truck_type or "") if v else "",
            "trips": g["trips"],
            "revenue": rev,
            "cost_fuel": fuel_amt,
            "fuel_liters": fuel_l,
            "cost_maint": maint_amt,
            "cost_total": cost,
            "gross_margin": rev - cost,
            "margin_pct": (rev - cost) / rev * 100 if rev else 0,
        })
    rows.sort(key=lambda r: -r["revenue"])
    return rows


# --------------------------------------------------------------------------
# CASH FLOW PROJECTION
# --------------------------------------------------------------------------

def cash_flow_projection(session: Session, start: date, days: int = 90) -> list[dict]:
    """Forward-looking cash flow by day. Simplified.

    Inflows:
    - From DailyJob.revenue_customer in recent history, assume avg 30-day AR delay
      (most customers pay next-month, so revenue booked in May hits cash in June)

    Outflows:
    - Known recurring: Loan payments (from amortization schedule)
    - Upcoming payroll (estimate from last month's PayRun × 1.0)
    - Upcoming fuel/petty (estimate from last 30 days average × days)
    """
    end = start + timedelta(days=days)
    rows: list[dict] = []

    # 1. Loan payments
    loans = session.exec(select(Loan).where(Loan.status == "active")).all()
    for loan in loans:
        schedule = amortization_schedule(loan, max_rows=360)
        for r in schedule:
            if start <= r.due_date <= end:
                rows.append({
                    "date": r.due_date,
                    "direction": "out",
                    "category": "loan",
                    "label": f"{loan.lender} ({loan.code})",
                    "amount": r.payment,
                })

    # 2. Last-period historical monthly averages (for next-30-day projection)
    look_start = start - timedelta(days=90)
    # Average monthly revenue (last 90 days / 3)
    hist_jobs = session.exec(
        select(DailyJob).where(
            DailyJob.work_date >= look_start, DailyJob.work_date < start
        )
    ).all()
    avg_monthly_rev = sum(j.revenue_customer or 0.0 for j in hist_jobs) / 3.0 if hist_jobs else 0.0

    # 3. Projected inflows: assume revenue invoiced in month M is collected in M+1 end
    # Simplified: at end of each upcoming month, we get last month's revenue (minus WHT)
    avg_wht_pct = 0.01  # 1% typical
    cur = start
    while cur <= end:
        last_day = (add_months(cur.replace(day=1), 1) - timedelta(days=1))
        if last_day > end:
            break
        if last_day >= start:
            rows.append({
                "date": last_day,
                "direction": "in",
                "category": "ar_collection",
                "label": "เก็บเงินลูกค้ารายเดือน (ประมาณจากเฉลี่ย 90 วัน)",
                "amount": avg_monthly_rev * (1 - avg_wht_pct),
            })
        cur = last_day + timedelta(days=1)

    # 4. Average monthly payroll from last PayRun(s)
    recent_runs = session.exec(
        select(PayRun).order_by(PayRun.id.desc()).limit(3)
    ).all()
    payroll_monthly = 0.0
    if recent_runs:
        for pr in recent_runs:
            items = session.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
            payroll_monthly += sum((i.gross_total or 0.0) for i in items)
        payroll_monthly /= len(recent_runs)

    # Apply payroll on pay_day (default: 1st of month, or pay cycle end). Simple: 1st of each month.
    cur = start.replace(day=1)
    while cur <= end:
        if cur >= start:
            rows.append({
                "date": cur,
                "direction": "out",
                "category": "payroll",
                "label": "เงินเดือน (ประมาณจากรอบล่าสุด)",
                "amount": payroll_monthly,
            })
        cur = add_months(cur, 1)

    # 5. Daily average petty + fuel
    petty_30 = session.exec(
        select(PettyCashTxn).where(
            PettyCashTxn.txn_date >= start - timedelta(days=30),
            PettyCashTxn.txn_date < start,
            PettyCashTxn.direction == "out",
        )
    ).all()
    daily_petty = sum(
        (p.amount or 0.0) - ((p.deduct_amount or 0.0) if p.deduct_from_driver else 0.0)
        for p in petty_30
    ) / 30.0

    fuel_30 = session.exec(
        select(FuelTxn).where(FuelTxn.txn_date >= start - timedelta(days=30), FuelTxn.txn_date < start)
    ).all()
    daily_fuel = sum((f.amount or 0.0) for f in fuel_30) / 30.0

    rows.append({
        "date": start, "direction": "note", "category": "assumption",
        "label": f"สมมติฐาน: petty {daily_petty:,.0f}฿/วัน · fuel {daily_fuel:,.0f}฿/วัน · AR รับใน M+1",
        "amount": 0.0,
    })

    rows.sort(key=lambda x: (x["date"], x["direction"]))
    return rows


# --------------------------------------------------------------------------
# BREAK-EVEN + RUNWAY
# --------------------------------------------------------------------------

def break_even_and_runway(session: Session, as_of: Optional[date] = None) -> dict:
    """High-level financial health snapshot.

    - fixed_monthly: payroll + loan + baseline maintenance + overhead
    - variable_per_trip: avg fuel cost per trip + misc
    - avg revenue per trip
    - break-even = fixed_monthly / (avg_rev - avg_var_per_trip)
    """
    as_of = as_of or date.today()
    look_start = as_of - timedelta(days=90)

    jobs = session.exec(
        select(DailyJob).where(
            DailyJob.work_date >= look_start,
            DailyJob.work_date <= as_of,
            DailyJob.revenue_customer > 0,
        )
    ).all()
    trip_count = len(jobs)
    rev_total = sum(j.revenue_customer or 0.0 for j in jobs)
    avg_rev_per_trip = rev_total / trip_count if trip_count else 0.0

    fuels = session.exec(
        select(FuelTxn).where(FuelTxn.txn_date >= look_start, FuelTxn.txn_date <= as_of)
    ).all()
    fuel_total = sum(f.amount or 0.0 for f in fuels)
    avg_fuel_per_trip = fuel_total / trip_count if trip_count else 0.0

    # Monthly averages (90 days = 3 months)
    monthly_rev = rev_total / 3.0
    monthly_fuel = fuel_total / 3.0

    # Payroll
    runs = session.exec(select(PayRun).order_by(PayRun.id.desc()).limit(3)).all()
    payroll_monthly = 0.0
    if runs:
        for pr in runs:
            items = session.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
            payroll_monthly += sum((i.gross_total or 0.0) for i in items)
        payroll_monthly /= len(runs)

    # Loans
    ls = loan_summary(session)
    loan_monthly = ls["monthly_burden"]

    # Maintenance (90-day avg)
    maints = session.exec(
        select(MaintRecord).where(
            MaintRecord.work_date >= look_start, MaintRecord.work_date <= as_of
        )
    ).all()
    maint_monthly = sum(m.total_cost or 0.0 for m in maints) / 3.0

    fixed_monthly = payroll_monthly + loan_monthly + maint_monthly
    contribution_per_trip = avg_rev_per_trip - avg_fuel_per_trip
    break_even_trips = fixed_monthly / contribution_per_trip if contribution_per_trip > 0 else 0
    current_monthly_trips = trip_count / 3.0

    net_monthly = monthly_rev - monthly_fuel - fixed_monthly

    return {
        "as_of": as_of,
        "trip_count_90d": trip_count,
        "avg_rev_per_trip": avg_rev_per_trip,
        "avg_fuel_per_trip": avg_fuel_per_trip,
        "contribution_per_trip": contribution_per_trip,
        "contribution_margin_pct": (contribution_per_trip / avg_rev_per_trip * 100) if avg_rev_per_trip else 0,
        "monthly_rev_avg": monthly_rev,
        "monthly_fuel_avg": monthly_fuel,
        "fixed_monthly": fixed_monthly,
        "payroll_monthly": payroll_monthly,
        "loan_monthly": loan_monthly,
        "maint_monthly": maint_monthly,
        "break_even_trips_per_month": break_even_trips,
        "current_monthly_trips": current_monthly_trips,
        "headroom_trips": current_monthly_trips - break_even_trips,
        "net_monthly": net_monthly,
        "status": "healthy" if net_monthly > 0 else "losing",
    }
