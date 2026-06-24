# LCB Mixed Mode (lcb_mixed) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `lcb_mixed` pay mode that computes a single LCB driver's pay per-day — เหมา days one way, เที่ยว days another — into one PayRunItem, with a slip that shows the two parts separately.

**Architecture:** A new per-day classifier `_classify_lcb_days` splits a driver's DailyJob rows in the cycle into mao-days / trip-days / ambiguous using the ratio rule. A new `lcb_mixed` branch in `calc_one_employee` aggregates each side into the existing PayrollCalc fields (fuel_share_income + fuel_cost_self for the เหมา side; trip_fee_total + other_income + prorated base/care for the เที่ยว side). Deductions (SS/tax/petty/etc.) run unchanged. One PayRunItem per employee; the slip template branches on `pay_mode == "lcb_mixed"` to render เหมา/เที่ยว subsections.

**Tech Stack:** FastAPI + SQLModel, SQLite (dev), pytest 8.4 (in `app/.venv`), Jinja2 templates. Run python via `ProjectYK_System/app/.venv/Scripts/python.exe` with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` (Thai output crashes cp1252 otherwise).

## Global Constraints

- Money engine work runs on branch `feat/lcb-mixed-mode`, never on `main`.
- MUST NOT change the computed numbers of any existing pay_mode (regression: the other 16 LCB drivers in payrun #2 keep identical net to the penny).
- pin: `fastapi<0.115`, `starlette<0.40` — do not upgrade.
- Ratio rule (โอ-approved): per DailyJob day, `ratio = trip_fee_driver / revenue_customer`. `revenue>0 and abs(ratio-0.60)<=0.05` → mao day; `revenue>0 and ratio < 0.55` → trip day; `revenue<=0` → ambiguous (skipped, no money). Any other ratio (0.55–0.95 band excluding the 60% window) → ambiguous (flagged, treated as trip day = conservative, no fuel deducted).
- base+care prorate by TRIP days only for lcb_mixed (mao days carry no base).
- All money-affecting runs: backup `app.db` first, provide read-only preview before writing.
- Thai text stays in values; English keys. Concise summaries to โอ.

---

### Task 1: Per-day classifier `_classify_lcb_days`

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` (add function near the other `_sum_*` helpers, after `_sum_fuel_cost` ~line 276)
- Test: `ProjectYK_System/tests/test_lcb_mixed.py` (create)

**Interfaces:**
- Consumes: `DailyJob` model (fields `work_date`, `revenue_customer`, `trip_fee_driver`, `driver_id`, `site_code`), `Session`, `select` — all already imported in payroll.py.
- Produces: `_classify_lcb_days(session, emp_id, start, end, site_code="") -> dict` returning
  `{"mao_days": list[DailyJob], "trip_days": list[DailyJob], "ambiguous": list[DailyJob]}`.

- [ ] **Step 1: Write the failing test**

Create `ProjectYK_System/tests/test_lcb_mixed.py`:

```python
import sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlmodel import SQLModel, Session, create_engine
from models import Employee, DailyJob
from services.payroll import _classify_lcb_days


def _mk_session():
    engine = create_engine("sqlite://")  # in-memory
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add_day(s, emp_id, d, rev, trip):
    s.add(DailyJob(driver_id=emp_id, site_code="LCB", work_date=d,
                   revenue_customer=rev, trip_fee_driver=trip))


def test_classify_splits_mao_trip_ambiguous():
    s = _mk_session()
    # mao day: ratio = 3000/5000 = 0.60
    _add_day(s, 1, date(2026, 6, 2), 5000, 3000)
    # trip day: ratio = 350/5000 = 0.07
    _add_day(s, 1, date(2026, 6, 3), 5000, 350)
    # ambiguous: revenue 0
    _add_day(s, 1, date(2026, 6, 4), 0, 0)
    # ambiguous ratio: 0.30 (neither window)
    _add_day(s, 1, date(2026, 6, 5), 5000, 1500)
    s.commit()

    out = _classify_lcb_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert {d.work_date for d in out["mao_days"]} == {date(2026, 6, 2)}
    assert {d.work_date for d in out["trip_days"]} == {date(2026, 6, 3)}
    assert {d.work_date for d in out["ambiguous"]} == {date(2026, 6, 4), date(2026, 6, 5)}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py::test_classify_splits_mao_trip_ambiguous -v`
Expected: FAIL with `ImportError: cannot import name '_classify_lcb_days'`

- [ ] **Step 3: Write minimal implementation**

Add to `payroll.py` after `_sum_fuel_cost`:

```python
LCB_MAO_RATIO = 0.60
LCB_MAO_RATIO_TOL = 0.05
LCB_TRIP_RATIO_MAX = 0.55


def _classify_lcb_days(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> dict:
    """Split a driver's DailyJob rows in [start,end] into เหมา / เที่ยว / ambiguous.

    Rule (โอ-approved 2026-06-24): ratio = trip_fee_driver / revenue_customer.
      revenue>0 & |ratio-0.60|<=0.05 -> mao day (60% share formula)
      revenue>0 & ratio<0.55         -> trip day
      otherwise (revenue<=0, or ratio in the murky middle) -> ambiguous
    Ambiguous days are NOT auto-assigned to เหมา (never auto-deduct fuel).
    """
    stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= start,
        DailyJob.work_date <= end,
    )
    if site_code:
        stmt = stmt.where(DailyJob.site_code == site_code)
    rows = session.exec(stmt).all()
    mao, trip, amb = [], [], []
    for r in rows:
        rev = r.revenue_customer or 0.0
        fee = r.trip_fee_driver or 0.0
        if rev <= 0:
            amb.append(r)
            continue
        ratio = fee / rev
        if abs(ratio - LCB_MAO_RATIO) <= LCB_MAO_RATIO_TOL:
            mao.append(r)
        elif ratio < LCB_TRIP_RATIO_MAX:
            trip.append(r)
        else:
            amb.append(r)
    return {"mao_days": mao, "trip_days": trip, "ambiguous": amb}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/payroll.py ProjectYK_System/tests/test_lcb_mixed.py
git commit -m "feat(payroll): _classify_lcb_days per-day เหมา/เที่ยว classifier"
```

---

### Task 2: Fuel cost for a specific set of days

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` (add after `_classify_lcb_days`)
- Test: `ProjectYK_System/tests/test_lcb_mixed.py` (append)

**Interfaces:**
- Consumes: `FuelTxn` (fields `driver_id`, `txn_date`, `amount`, `site_code`), `Session`, `select`.
- Produces: `_sum_fuel_cost_for_dates(session, emp_id, dates, site_code="") -> float` where `dates` is an iterable of `date`. Sums FuelTxn.amount whose `txn_date` is in `dates`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lcb_mixed.py`:

```python
from models import FuelTxn
from services.payroll import _sum_fuel_cost_for_dates


def test_sum_fuel_cost_for_dates_only_listed_days():
    s = _mk_session()
    s.add(FuelTxn(driver_id=1, site_code="LCB", txn_date=date(2026, 6, 2), amount=1000))
    s.add(FuelTxn(driver_id=1, site_code="LCB", txn_date=date(2026, 6, 3), amount=500))
    s.commit()
    # only ask for the 2nd -> 1000, not 1500
    total = _sum_fuel_cost_for_dates(s, 1, {date(2026, 6, 2)}, "LCB")
    assert total == 1000.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py::test_sum_fuel_cost_for_dates_only_listed_days -v`
Expected: FAIL with `ImportError: cannot import name '_sum_fuel_cost_for_dates'`

- [ ] **Step 3: Write minimal implementation**

```python
def _sum_fuel_cost_for_dates(
    session: Session, emp_id: int, dates, site_code: str = ""
) -> float:
    """Sum FuelTxn.amount for this driver on only the given set of dates."""
    date_set = set(dates)
    if not date_set:
        return 0.0
    stmt = select(FuelTxn).where(
        FuelTxn.driver_id == emp_id,
        FuelTxn.txn_date >= min(date_set),
        FuelTxn.txn_date <= max(date_set),
    )
    if site_code:
        stmt = stmt.where(FuelTxn.site_code == site_code)
    rows = session.exec(stmt).all()
    return round(sum((r.amount or 0.0) for r in rows if r.txn_date in date_set), 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/payroll.py ProjectYK_System/tests/test_lcb_mixed.py
git commit -m "feat(payroll): _sum_fuel_cost_for_dates (fuel by day subset)"
```

---

### Task 3: `lcb_mixed` earnings branch in `calc_one_employee`

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` — add `elif mode == "lcb_mixed":` branch inside `calc_one_employee`, immediately after the `elif mode == "lcb_mao":` block (ends ~line 829).
- Test: `ProjectYK_System/tests/test_lcb_mixed.py` (append)

**Interfaces:**
- Consumes: `_classify_lcb_days`, `_sum_fuel_cost_for_dates` (Tasks 1-2); existing `PayrollCalc` fields `base_salary_earned`, `care_allowance_earned`, `trip_fee_total`, `fuel_share_income`, `fuel_cost_self`, `other_income`, `note`; `employee.gross_share_rate` (default 0.60); local vars in scope at that point: `base`, `care`, `days_in_month`, `site`, `start`, `end`, `calc`.
- Produces: after this branch runs, `calc.fuel_share_income` = เหมา income, `calc.fuel_cost_self` = เหมา fuel, `calc.trip_fee_total` = เที่ยว fee, `calc.base_salary_earned`/`care_allowance_earned` = prorated by trip-day count, `calc.other_income` includes พิเศษ 100×(trip days). The shared deductions block below it is unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lcb_mixed.py`:

```python
from models import PayRun
from services.payroll import calc_one_employee


def test_lcb_mixed_splits_income_and_prorates_base():
    s = _mk_session()
    emp = Employee(full_name="ทดสอบ ลูกผสม", home_site_code="LCB",
                   pay_mode="lcb_mixed", base_salary=9240, care_allowance=3000,
                   gross_share_rate=0.60, start_date=date(2026, 5, 16))
    s.add(emp)
    s.commit()
    s.refresh(emp)
    # 1 mao day: rev 5000 ratio .60 ; fuel 1000 that day
    s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 2),
                   revenue_customer=5000, trip_fee_driver=3000))
    s.add(FuelTxn(driver_id=emp.id, site_code="LCB", txn_date=date(2026, 6, 2), amount=1000))
    # 1 trip day: rev 5000 fee 350
    s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 3),
                   revenue_customer=5000, trip_fee_driver=350))
    s.commit()

    calc = calc_one_employee(s, emp, date(2026, 5, 16), date(2026, 6, 15), "2026-06")

    # เหมา side: 5000 * 0.60 = 3000 income ; fuel 1000 self-cost
    assert calc.fuel_share_income == 3000.0
    assert calc.fuel_cost_self == 1000.0
    # เที่ยว side: trip fee 350
    assert calc.trip_fee_total == 350.0
    # พิเศษ 100 * 1 trip day = 100
    assert calc.other_income == 100.0
    # base prorated by trip days only: 1 trip day / 31-day cycle
    period_days = 31  # 16 May..15 Jun inclusive
    assert abs(calc.base_salary_earned - 9240 * (1 / period_days)) < 0.5
    assert abs(calc.care_allowance_earned - 3000 * (1 / period_days)) < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py::test_lcb_mixed_splits_income_and_prorates_base -v`
Expected: FAIL — `calc.note` will be `pay_mode ไม่รู้จัก: 'lcb_mixed'` and assertions on income fail (fields are 0).

- [ ] **Step 3: Write minimal implementation**

Insert this branch right after the `elif mode == "lcb_mao":` block closes (after its `calc.note = ...` line, before `elif mode == "ayu_trip":`):

```python
    elif mode == "lcb_mixed":
        if base == 0:
            base = 9240.0
        if care == 0:
            care = 3000.0
        split = _classify_lcb_days(session, employee.id, start, end, site_code=site)
        mao_days = split["mao_days"]
        trip_days = split["trip_days"]
        # เหมา side: 60% of revenue on mao days, minus fuel on those days
        mao_rev = sum((d.revenue_customer or 0.0) for d in mao_days)
        share_rate = employee.gross_share_rate or 0.60
        calc.fuel_share_income = round(mao_rev * share_rate, 2)
        mao_dates = {d.work_date for d in mao_days}
        calc.fuel_cost_self = _sum_fuel_cost_for_dates(
            session, employee.id, mao_dates, site_code=site
        )
        # เที่ยว side: trip fees + พิเศษ 100/เที่ยว on trip days only
        calc.trip_fee_total = round(
            sum((d.trip_fee_driver or 0.0) for d in trip_days), 2
        )
        n_trip = len(trip_days)
        calc.other_income += round(n_trip * 100.0, 2)
        # base+care prorate by TRIP days only (mao days have no base)
        calc.base_salary_earned = round(base * (n_trip / days_in_month), 2)
        calc.care_allowance_earned = round(care * (n_trip / days_in_month), 2)
        amb_note = (
            f" | ⚠ วันกำกวม {len(split['ambiguous'])} (เช็ค)"
            if split["ambiguous"] else ""
        )
        calc.note = (
            f"ลูกผสม: เหมา {len(mao_days)}วัน {mao_rev:,.0f}×{share_rate*100:.0f}%"
            f"−น้ำมัน {calc.fuel_cost_self:,.0f} | เที่ยว {n_trip}วัน "
            f"{calc.trip_fee_total:,.0f}+พิเศษ {n_trip*100} | ฐาน×{n_trip}/{int(days_in_month)}วัน"
            f"{amb_note}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/payroll.py ProjectYK_System/tests/test_lcb_mixed.py
git commit -m "feat(payroll): lcb_mixed earnings branch (per-day เหมา/เที่ยว)"
```

---

### Task 4: Regression guard — other modes unchanged

**Files:**
- Test: `ProjectYK_System/tests/test_lcb_mixed_regression.py` (create)

**Interfaces:**
- Consumes: `compute_pay_run` from `services.payroll`, the live `app.db` (read-only snapshot of payrun #2 nets captured before any code change).

This task proves the new branch did not perturb existing pay_modes. It compares each non-mixed driver's net in payrun #2 against a frozen baseline.

- [ ] **Step 1: Capture baseline (one-time, before trusting the test)**

Run this to snapshot current nets to a JSON the test reads:

```bash
cd ProjectYK_System && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 app/.venv/Scripts/python.exe -X utf8 -c "
import json, sqlite3
c=sqlite3.connect('app/app.db').cursor()
rows=c.execute('SELECT employee_id, pay_mode, net_pay FROM payrunitem WHERE pay_run_id=2').fetchall()
base={str(e):{'mode':m,'net':round(n,2)} for e,m,n in rows}
json.dump(base, open('tests/_payrun2_baseline.json','w'))
print('saved', len(base), 'drivers')
"
```
Expected: `saved 18 drivers`

- [ ] **Step 2: Write the test**

Create `ProjectYK_System/tests/test_lcb_mixed_regression.py`:

```python
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from sqlmodel import Session, select
import main
from models import PayRun
from services.payroll import calc_one_employee
from models import Employee

BASE = json.load(open(os.path.join(os.path.dirname(__file__), "_payrun2_baseline.json")))


def test_existing_modes_net_unchanged():
    """Recompute each non-mixed driver in payrun #2; net must equal baseline."""
    with Session(main.engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        for emp_id, info in BASE.items():
            if info["mode"] == "lcb_mixed":
                continue  # mixed drivers are allowed to change
            emp = s.get(Employee, int(emp_id))
            calc = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                     pr.pay_cycle_tag, pay_run_id=2)
            assert round(calc.net_pay, 2) == info["net"], (
                f"emp {emp_id} ({info['mode']}) net drifted: "
                f"{calc.net_pay:.2f} != {info['net']:.2f}"
            )
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd ProjectYK_System && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 app/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_lcb_mixed_regression.py -v`
Expected: PASS — no driver drifted (mixed branch is only reachable by `lcb_mixed`, which no one has yet).

- [ ] **Step 4: Commit**

```bash
git add ProjectYK_System/tests/test_lcb_mixed_regression.py ProjectYK_System/tests/_payrun2_baseline.json
git commit -m "test(payroll): regression guard — existing modes net unchanged"
```

---

### Task 5: Read-only preview for พชร / สุรเดช

**Files:**
- Create: `ProjectYK_System/tools/preview_lcb_mixed.py`

**Interfaces:**
- Consumes: `calc_one_employee`, `_classify_lcb_days`, `Employee`, `PayRun`. Writes NOTHING. Temporarily sets `emp.pay_mode = "lcb_mixed"` in-memory only and rolls back.

- [ ] **Step 1: Write the preview tool**

Create `ProjectYK_System/tools/preview_lcb_mixed.py`:

```python
"""Preview lcb_mixed for พชร(86)/สุรเดช(91) — READ-ONLY, writes nothing.

Shows per-day classification + เหมา/เที่ยว split + net, so โอ can compare to
hand calc before we flip pay_mode for real.
"""
from __future__ import annotations
import io, sys
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR
sys.path.insert(0, str(APP_DIR))

from sqlmodel import Session, create_engine, select
from models import Employee, PayRun
from services.payroll import calc_one_employee, _classify_lcb_days

engine = create_engine(f"sqlite:///{APP_DIR/'app.db'}",
                       connect_args={"check_same_thread": False})

TARGETS = [(86, "พชร"), (91, "สุรเดช")]


def main():
    with Session(engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        for eid, nm in TARGETS:
            emp = s.get(Employee, eid)
            split = _classify_lcb_days(s, eid, pr.period_start, pr.period_end, "LCB")
            orig = emp.pay_mode
            emp.pay_mode = "lcb_mixed"
            calc = calc_one_employee(s, emp, pr.period_start, pr.period_end,
                                     pr.pay_cycle_tag, pay_run_id=2)
            emp.pay_mode = orig
            print(f"=== {nm} (emp{eid}) ===")
            print(f"  เหมา {len(split['mao_days'])}วัน / เที่ยว {len(split['trip_days'])}วัน "
                  f"/ กำกวม {len(split['ambiguous'])}วัน")
            print(f"  เหมา income {calc.fuel_share_income:,.2f}  − น้ำมัน {calc.fuel_cost_self:,.2f}")
            print(f"  เที่ยว fee {calc.trip_fee_total:,.2f}  + พิเศษ {calc.other_income:,.0f}")
            print(f"  ฐาน {calc.base_salary_earned:,.2f} + ดูแล {calc.care_allowance_earned:,.2f}")
            print(f"  gross {calc.gross_total:,.2f}  หักรวม {calc.deduction_total:,.2f}  NET {calc.net_pay:,.2f}")
            if split["ambiguous"]:
                print("  ⚠ วันกำกวม:", ", ".join(str(d.work_date) for d in split["ambiguous"]))
            print()
        s.rollback()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the preview**

Run: `cd ProjectYK_System && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 app/.venv/Scripts/python.exe -X utf8 tools/preview_lcb_mixed.py`
Expected: prints per-day split + net for both drivers, no DB write. **STOP and show โอ these numbers; let him compare to his hand calc before Task 6.**

- [ ] **Step 3: Commit**

```bash
git add ProjectYK_System/tools/preview_lcb_mixed.py
git commit -m "tools(payroll): read-only lcb_mixed preview for พชร/สุรเดช"
```

---

### Task 6: Slip template — render เหมา/เที่ยว split

**Files:**
- Modify: `ProjectYK_System/app/templates/` slip template (locate the one served by `GET /payroll/{run_id}/employee/{emp_id}/slip` — `main.py:3626`). Find with: `grep -rl "trip_fee_total\|fuel_share_income" ProjectYK_System/app/templates/`.
- Test: manual visual via running app.

**Interfaces:**
- Consumes: the PayRunItem passed to the slip template (has `pay_mode`, `fuel_share_income`, `fuel_cost_self`, `trip_fee_total`, `base_salary_earned`, `care_allowance_earned`, `other_income`, `note`).
- Produces: when `item.pay_mode == "lcb_mixed"`, the income section shows two labelled sub-blocks (▸ เหมา … / ▸ เที่ยว …) as in the approved mockup. Other modes render unchanged.

- [ ] **Step 1: Locate the slip template block**

Run: `grep -rn "fuel_share_income\|trip_fee_total" ProjectYK_System/app/templates/`
Identify the income rows in the slip template. Note the file path and the surrounding Jinja structure (table rows vs divs).

- [ ] **Step 2: Add the mixed-mode conditional**

In the slip template income section, wrap a new branch (match existing markup style — example assumes table rows):

```jinja
{% if item.pay_mode == "lcb_mixed" %}
  <tr><td>▸ เหมา (60% ค่าขนส่ง)</td><td class="text-right">{{ item.fuel_share_income | round(2) }}</td></tr>
  <tr><td>▸ เที่ยว (ค่าเที่ยว)</td><td class="text-right">{{ item.trip_fee_total | round(2) }}</td></tr>
  <tr><td>พิเศษ/เที่ยว</td><td class="text-right">{{ item.other_income | round(2) }}</td></tr>
  <tr><td>ฐาน+ดูแล (ตามวันเที่ยว)</td><td class="text-right">{{ (item.base_salary_earned + item.care_allowance_earned) | round(2) }}</td></tr>
{% else %}
  {# ...existing income rows unchanged... #}
{% endif %}
```

Keep the deduction section (น้ำมัน as `fuel_cost_self`, เบิก, SS) exactly as-is — it already renders for mao-style modes.

- [ ] **Step 3: Verify visually**

Start app: `cd ProjectYK_System/app && PYTHONUTF8=1 .venv/Scripts/python.exe main.py` (background), then open `http://localhost:8010/payroll/2/employee/86/slip` after Task 7 flips พชร to mixed. Confirm the เหมา/เที่ยว rows show and totals match the preview. (If run before Task 7, พชร still renders as trip — revisit after flip.)

- [ ] **Step 4: Commit**

```bash
git add ProjectYK_System/app/templates/
git commit -m "feat(ui): slip renders lcb_mixed เหมา/เที่ยว split"
```

---

### Task 7: Flip พชร/สุรเดช to lcb_mixed and recompute (gated on โอ approval)

**Files:**
- Create: `ProjectYK_System/tools/apply_lcb_mixed.py`

**Interfaces:**
- Consumes: `compute_pay_run`, `Employee`, `PayRun`. WRITES to app.db (backs up first). Gated: only run after โอ approves the Task 5 preview numbers.

- [ ] **Step 1: Write the apply tool**

Create `ProjectYK_System/tools/apply_lcb_mixed.py`:

```python
"""Flip พชร(86)/สุรเดช(91) to lcb_mixed and recompute payrun #2.

Backs up app.db first. Run ONLY after โอ approves preview_lcb_mixed numbers.
"""
from __future__ import annotations
import io, sys, shutil, datetime
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR
sys.path.insert(0, str(APP_DIR))

import main
from sqlmodel import Session, select
from models import Employee, PayRun
from services.payroll import compute_pay_run

TARGETS = [86, 91]


def main_run():
    db = APP_DIR / "app.db"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(db, APP_DIR / f"app.db.bak_before_lcb_mixed_{stamp}")
    print("backup done")
    with Session(main.engine) as s:
        pr = s.exec(select(PayRun).where(PayRun.id == 2)).one()
        assert pr.status == "draft", f"payrun not draft: {pr.status}"
        for eid in TARGETS:
            emp = s.get(Employee, eid)
            print(f"emp{eid} {emp.full_name}: {emp.pay_mode} -> lcb_mixed")
            emp.pay_mode = "lcb_mixed"
            s.add(emp)
        s.commit()
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        print(f"recomputed {len(items)} items; net total {sum(i.net_pay for i in items):,.2f}")


if __name__ == "__main__":
    main_run()
```

- [ ] **Step 2: STOP — get โอ approval on Task 5 preview before running**

Do not run Step 3 until โอ confirms the preview numbers are correct.

- [ ] **Step 3: Run apply, then regression**

Run: `cd ProjectYK_System && PYTHONUTF8=1 PYTHONIOENCODING=utf-8 app/.venv/Scripts/python.exe -X utf8 tools/apply_lcb_mixed.py`
Then re-run the regression test (Task 4) to confirm the OTHER drivers still match baseline:
`PYTHONUTF8=1 PYTHONIOENCODING=utf-8 app/.venv/Scripts/python.exe -X utf8 -m pytest tests/test_lcb_mixed_regression.py -v`
Expected: apply prints new net total; regression PASS (only พชร/สุรเดช changed, both excluded from the baseline-equality check by their new mode).

- [ ] **Step 4: Commit**

```bash
git add ProjectYK_System/tools/apply_lcb_mixed.py
git commit -m "tools(payroll): apply lcb_mixed to พชร/สุรเดช + recompute payrun #2"
```

---

## Notes for the implementer

- `models.py` field names must be confirmed before Task 1: verify `DailyJob.revenue_customer`, `DailyJob.trip_fee_driver`, `FuelTxn.amount`, `FuelTxn.txn_date`, `Employee.gross_share_rate` exist (they're used by existing mao code, so they do). If `Employee` requires non-null fields the test constructor omits, add them in the test (in-memory only).
- The in-memory test DB (`create_engine("sqlite://")`) creates all tables from SQLModel metadata — importing `models` is enough.
- Ambiguous days are deliberately NOT counted as either เหมา or เที่ยว for money; they only raise a note. โอ decides them case-by-case.
