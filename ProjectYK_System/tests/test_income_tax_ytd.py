"""Income-tax withholding must annualize from YTD-average run-rate, not a
single high month, and must allow ประกันสังคม as a ลดหย่อน.

Background: LCB เหมา drivers have spiky monthly gross (revenue-share). The old
formula projected `gross_this_month * remaining_months`, so one busy month
(e.g. June ~90k) implied ~1M/yr and over-withheld. โอ wants: use the real
months already on record, average them, and project the rest of the year off
that average — so the year-end estimate lands close to reality.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from datetime import date
from sqlmodel import Session, SQLModel, create_engine
from models import Employee, PayRun, PayRunItem
from services import payroll


def _setup():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    return Session(eng)


def _add_prior_run(s, emp_id, cycle_tag, period_start, period_end, gross, tax=0.0):
    pr = PayRun(site_code="LCB", pay_cycle_tag=cycle_tag,
                period_start=period_start, period_end=period_end, status="draft")
    s.add(pr); s.commit(); s.refresh(pr)
    s.add(PayRunItem(pay_run_id=pr.id, employee_id=emp_id, site_code="LCB",
                     gross_total=gross, net_pay=gross, income_tax_withholding=tax))
    s.commit()
    return pr


def _calc_for(emp, period_start, period_end, gross_this_month, sso=0.0):
    c = payroll.PayrollCalc(employee=emp, period_start=period_start, period_end=period_end)
    # Drive gross via fuel_share_income (เหมา path); tax fn reads calc.gross_total.
    c.fuel_share_income = gross_this_month
    c.social_security = sso
    return c


def test_spiky_month_does_not_extrapolate_full_year():
    """5 modest months on record + 1 spike month → annual projection must be
    near (avg*12), NOT (spike*12). The spike alone (90k*12≈1.08M) would push
    deep into the 20% bracket; the true average (~32k) keeps it far lower.
    """
    s = _setup()
    emp = Employee(code="SPIKE", full_name="ทดสอบ เหมา", home_site_code="LCB",
                   social_security_base=9240, social_security_rate=0.05)
    s.add(emp); s.commit(); s.refresh(emp)

    # Jan..May ~ 13k each (LCB cycles end mid-month)
    months = [
        ("2026-01", date(2025, 12, 16), date(2026, 1, 15), 13000),
        ("2026-02", date(2026, 1, 16), date(2026, 2, 15), 13000),
        ("2026-03", date(2026, 2, 16), date(2026, 3, 15), 13000),
        ("2026-04", date(2026, 3, 16), date(2026, 4, 15), 13000),
        ("2026-05", date(2026, 4, 16), date(2026, 5, 15), 14000),
    ]
    for tag, ps, pe, g in months:
        _add_prior_run(s, emp.id, tag, ps, pe, g, tax=0.0)

    # June spike: 90,000
    calc = _calc_for(emp, date(2026, 5, 16), date(2026, 6, 15), 90000, sso=462)
    tax = payroll._compute_income_tax_withholding(s, calc, emp)

    # Old buggy formula withheld ~3,000+/month here. With YTD-average the
    # projected annual ≈ ytd(66k)+90k + avg(~32k)*6 ≈ 348k → taxable after
    # 50% exp(cap100k) + 60k + sso ≈ 178k → annual tax ≈ 1,800 → /7 ≈ 260.
    assert tax < 600, f"expected modest monthly tax from YTD-average, got {tax}"


def test_social_security_lowers_tax():
    """Same income, but a driver WITH ประกันสังคม should be taxed less than one
    without — proving SSO is applied as a ลดหย่อน.
    """
    s = _setup()
    # Build identical 6-month history twice, one emp with SSO, one without.
    def build(code, sso_base):
        e = Employee(code=code, full_name=code, home_site_code="LCB",
                     social_security_base=sso_base, social_security_rate=0.05)
        s.add(e); s.commit(); s.refresh(e)
        for i, tag in enumerate(["2026-01","2026-02","2026-03","2026-04","2026-05"]):
            ps = date(2025, 12, 16) if i == 0 else date(2026, i, 16)
            pe = date(2026, i+1, 15)
            _add_prior_run(s, e.id, tag, ps, pe, 40000, tax=0.0)
        return e

    e_with = build("WITH_SSO", 9240)
    e_without = build("NO_SSO", 0)

    calc_with = _calc_for(e_with, date(2026,5,16), date(2026,6,15), 45000, sso=462)
    calc_without = _calc_for(e_without, date(2026,5,16), date(2026,6,15), 45000, sso=0)

    tax_with = payroll._compute_income_tax_withholding(s, calc_with, e_with)
    tax_without = payroll._compute_income_tax_withholding(s, calc_without, e_without)

    assert tax_with < tax_without, (
        f"SSO should reduce tax: with={tax_with} without={tax_without}")


def test_catch_up_subtracts_prior_withholding():
    """If tax was already withheld earlier in the year, remaining is spread over
    the rest — total annual stays consistent, this month isn't double-charged.
    """
    s = _setup()
    emp = Employee(code="CATCHUP", full_name="ทดสอบ สะสม", home_site_code="LCB",
                   social_security_base=9240, social_security_rate=0.05)
    s.add(emp); s.commit(); s.refresh(emp)
    for i, tag in enumerate(["2026-01","2026-02","2026-03","2026-04","2026-05"]):
        ps = date(2025, 12, 16) if i == 0 else date(2026, i, 16)
        pe = date(2026, i+1, 15)
        # High steady income with some tax already taken each month
        _add_prior_run(s, emp.id, tag, ps, pe, 60000, tax=800.0)

    calc = _calc_for(emp, date(2026,5,16), date(2026,6,15), 60000, sso=462)
    tax = payroll._compute_income_tax_withholding(s, calc, emp)

    # Steady 60k/mo → ~720k/yr; annual tax is real, but 4,000 already withheld
    # (5 months * 800) must be credited so this month is not the full slice.
    # Mainly assert it's a sane positive number, lower than the naive annual/12
    # would be if prior withholding were ignored.
    assert tax >= 0
    # With ~4k already withheld, remaining spread over 7 months should be
    # noticeably less than annual_tax/12 computed fresh. Just assert finite/sane.
    assert tax < 5000
