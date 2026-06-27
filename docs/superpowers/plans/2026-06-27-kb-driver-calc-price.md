# KB + Driver-Calc-Price Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แยกราคาที่วางบิลลูกค้า (`revenue_customer`) ออกจากราคาที่ใช้คิดเงินคนขับ (`driver_calc_price`) โดยรองรับ KB (ใต้โต๊ะ) ต่อแถวและราคากลาง override ต่อแถว

**Architecture:** เพิ่ม 2 column (`kb_amount`, `price_override`) บน `DailyJob` + ตาราง `KbRule` (default KB ต่อ `status_code`). ราคาคนขับคำนวณสดจาก helper เดียว `driver_calc_price(row)`. payroll หันมาใช้ helper นี้แทน `revenue_customer` ทุกที่ที่คิดเงินคนขับ; ฝั่งวางบิล/finance คงเดิม. UI เพิ่มคอลัมน์ใน `/daily` grid (admin); ไม่แตะ driver PWA.

**Tech Stack:** FastAPI + SQLModel + SQLite, Jinja2 + Tabulator (daily grid), pytest

## Global Constraints

- ห้ามทำงานบน `main` — ต้องอยู่บน branch `feat/kb-driver-calc-price` (project rule)
- เพิ่ม schema ต้อง bump `main.py:SCHEMA_VERSION` (ปัจจุบัน 24 → 25) พร้อม `_ensure_column` ใน `_apply_additive_migrations()` ทุกครั้ง
- `fastapi<0.115`, `starlette<0.40` — ห้ามอัปเกรด
- งานเงิน (payroll) ห้าม recompute run ที่ finalize แล้วโดยไม่ขอ — recompute ย้อนหลังต้องมี preflight ให้โอเซ็นก่อน
- เงิน round 2 ตำแหน่งเสมอ (ตามสไตล์ payroll.py เดิม)
- KB config: `KB_OUR_CUT=0.10`, `KB_WHT=0.03`
- KB rule seed: NHL→110(req=False), MOL→100(req=False), CY→0(req=True)

**Test import convention (IMPORTANT — overrides the snippets below):** existing tests
in `ProjectYK_System/tests/` do NOT use `app.` package prefix. Every test file starts with:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
```
then imports bare: `from models import DailyJob, KbRule`,
`from services.payroll import driver_calc_price`, `from services.kb import ...`,
`import main` (NOT `from app.models import`, NOT `from app import main`).
Tools likewise `sys.path.insert(... "app")` then `from models import ...`.
Where a snippet below shows `from app.X import Y`, read it as `from X import Y` with the
preamble above. Match `tests/test_lcb_mixed.py` for the exact boilerplate.

**pytest invocation (IMPORTANT):** use the venv python, NOT bare `python`. Every
`pytest` command below should be run as:
```
cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest <args>
```
(bare `python` lacks pytest/deps on this machine.)

**Known pre-existing red tests (NOT caused by this work — verified red on `main`):**
1. `tests/test_lcb_mixed.py::test_lcb_mixed_splits_income_and_prorates_base` — asserts old
   flat "พิเศษ 100/เที่ยว" (`other_income == 100.0`), superseded by sheet-based
   `_sum_lcb_driver_extra_fees` ([LCB driver extra fees]).
2. `tests/test_lcb_mixed_regression.py::test_existing_modes_net_unchanged` — also red on
   `main` before this branch (same [LCB driver extra fees] era drift).
Both stay red through this plan; that is the baseline, not a regression. All KB tests +
the other mixed tests must be green. (Optional cleanup of these two stale assertions only
with โอ's OK — out of scope.)

---

### Task 1: เพิ่ม column kb_amount + price_override บน DailyJob (+ migration)

**Files:**
- Modify: `ProjectYK_System/app/models.py:148-149` (DailyJob money fields)
- Modify: `ProjectYK_System/app/main.py:90` (SCHEMA_VERSION 24→25)
- Modify: `ProjectYK_System/app/main.py:392-393` (add `_ensure_column` calls in `_apply_additive_migrations`)
- Test: `ProjectYK_System/tests/test_kb_schema.py`

**Interfaces:**
- Produces: `DailyJob.kb_amount: float = 0.0`, `DailyJob.price_override: Optional[float] = None`

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_kb_schema.py
from app.models import DailyJob

def test_dailyjob_has_kb_fields():
    j = DailyJob(work_date="2026-06-27", site_code="LCB")
    assert j.kb_amount == 0.0
    assert j.price_override is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_schema.py -v`
Expected: FAIL — `AttributeError`/`TypeError` (kb_amount/price_override not a field)

- [ ] **Step 3: Add fields to DailyJob model**

In `models.py`, after line 149 (`trip_fee_driver: float = 0.0`):

```python
    # KB (ใต้โต๊ะ/commission) ต่อแถว — seed จาก KbRule ตาม status_code, แก้มือได้
    kb_amount: float = 0.0
    # ราคากลาง/over-market override — None = ใช้ revenue_customer เป็นฐาน
    price_override: Optional[float] = Field(default=None)
```

- [ ] **Step 4: Bump SCHEMA_VERSION + add migrations**

In `main.py:90` change to:
```python
SCHEMA_VERSION = 25  # v25: DailyJob.kb_amount + price_override; KbRule table
```

In `main.py` `_apply_additive_migrations()`, before the closing of the function (after line 392 comment block), add:
```python
    # v24 → v25: DailyJob KB + ราคากลาง override (KbRule table via create_all)
    _ensure_column("dailyjob", "kb_amount", "REAL", default="0")
    _ensure_column("dailyjob", "price_override", "REAL")  # nullable, no default
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/tests/test_kb_schema.py
git commit -m "feat(daily): add DailyJob.kb_amount + price_override (schema v25)"
```

---

### Task 2: ตาราง KbRule + seed NHL/MOL/CY

**Files:**
- Modify: `ProjectYK_System/app/models.py` (add `KbRule` class near `Customer`, ~line 106)
- Modify: `ProjectYK_System/app/main.py:418-434` (`seed_initial_data` — add KB rule seed)
- Test: `ProjectYK_System/tests/test_kb_rule.py`

**Interfaces:**
- Produces: `KbRule(status_code: str, default_kb: float, required: bool, note: str)`; seeded rows NHL/MOL/CY

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_kb_rule.py
from sqlmodel import Session, SQLModel, create_engine, select
from app.models import KbRule
from app import main

def _mem_session():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    return Session(eng)

def test_kbrule_model_fields():
    r = KbRule(status_code="NHL", default_kb=110.0, required=False)
    assert r.status_code == "NHL"
    assert r.default_kb == 110.0
    assert r.required is False

def test_seed_creates_nhl_mol_cy():
    s = _mem_session()
    main.seed_kb_rules(s)
    codes = {r.status_code: r for r in s.exec(select(KbRule)).all()}
    assert codes["NHL"].default_kb == 110.0 and codes["NHL"].required is False
    assert codes["MOL"].default_kb == 100.0 and codes["MOL"].required is False
    assert codes["CY"].default_kb == 0.0 and codes["CY"].required is True
    # idempotent — second call adds nothing
    main.seed_kb_rules(s)
    assert len(s.exec(select(KbRule)).all()) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_rule.py -v`
Expected: FAIL — `ImportError: cannot import name 'KbRule'`

- [ ] **Step 3: Add KbRule model**

In `models.py`, after the `Customer` class (line 106):

```python
class KbRule(SQLModel, table=True):
    """Default KB (ใต้โต๊ะ) ต่อ status_code (= ชื่อลูกค้าในไฟล์ LCB).

    required=True → แถวที่ status นี้แต่ kb_amount==0 จะถูกเตือน (กันลืม), ไม่บล็อก.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    status_code: str = Field(index=True, unique=True)
    default_kb: float = 0.0
    required: bool = False
    note: str = ""
```

- [ ] **Step 4: Add seed_kb_rules + call from seed_initial_data**

In `main.py`, add a new function (near `seed_initial_data`):

```python
def seed_kb_rules(s: Session) -> None:
    """Seed default KB rules. Idempotent — only adds missing status_codes."""
    from models import KbRule
    defaults = [
        KbRule(status_code="NHL", default_kb=110.0, required=False),
        KbRule(status_code="MOL", default_kb=100.0, required=False),
        KbRule(status_code="CY",  default_kb=0.0,   required=True),
    ]
    for rule in defaults:
        existing = s.exec(select(KbRule).where(KbRule.status_code == rule.status_code)).first()
        if not existing:
            s.add(rule)
    s.commit()
```

Then in `seed_initial_data` (after the yk1 admin seed, line 449), add:
```python
    seed_kb_rules(s)
```

Ensure `KbRule` is imported where models are imported in `main.py` (same import line as `DailyJob`, `Customer`, etc.).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_rule.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/tests/test_kb_rule.py
git commit -m "feat(daily): add KbRule table + seed NHL/MOL/CY defaults"
```

---

### Task 3: helper driver_calc_price() — สูตรกลาง

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` (add helper near top, before `_classify_lcb_days` ~line 260)
- Test: `ProjectYK_System/tests/test_driver_calc_price.py`

**Interfaces:**
- Produces: `driver_calc_price(row) -> float` — `row` is any object with `.price_override`, `.revenue_customer`, `.kb_amount`

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_driver_calc_price.py
from app.services.payroll import driver_calc_price
from app.models import DailyJob

def _row(rev=0.0, kb=0.0, override=None):
    return DailyJob(work_date="2026-06-27", site_code="LCB",
                    revenue_customer=rev, kb_amount=kb, price_override=override)

def test_plain_revenue_no_kb():
    assert driver_calc_price(_row(rev=5000)) == 5000.0

def test_kb_subtracted_from_revenue():
    # NHL: bill 5200, kb 110 -> driver 5090
    assert driver_calc_price(_row(rev=5200, kb=110)) == 5090.0

def test_override_replaces_revenue():
    # over-market: bill 6000 but ราคากลาง 5500 -> driver 5500
    assert driver_calc_price(_row(rev=6000, override=5500)) == 5500.0

def test_override_minus_kb_stacks():
    # override 5500 with kb 110 -> 5390
    assert driver_calc_price(_row(rev=6000, override=5500, kb=110)) == 5390.0

def test_zero_revenue_zero_result():
    assert driver_calc_price(_row(rev=0)) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_driver_calc_price.py -v`
Expected: FAIL — `ImportError: cannot import name 'driver_calc_price'`

- [ ] **Step 3: Add helper to payroll.py**

In `payroll.py`, before `LCB_MAO_RATIO = 0.60` (line 260):

```python
def driver_calc_price(row) -> float:
    """ราคาที่ใช้คิดเงินคนขับ (≠ ราคาวางบิลลูกค้า).

    base = price_override ถ้าตั้งไว้ มิฉะนั้น = revenue_customer; แล้วหัก KB.
    override แทนฐาน, KB หักจากฐานเสมอ (ซ้อนกันได้).
    """
    override = getattr(row, "price_override", None)
    base = override if override is not None else (row.revenue_customer or 0.0)
    return round(base - (getattr(row, "kb_amount", 0.0) or 0.0), 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ProjectYK_System && python -m pytest tests/test_driver_calc_price.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/payroll.py ProjectYK_System/tests/test_driver_calc_price.py
git commit -m "feat(payroll): add driver_calc_price helper (override - KB)"
```

---

### Task 4: payroll ใช้ driver_calc_price แทน revenue_customer (ฝั่งคนขับ)

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py:289-290` (`_classify_lcb_days` ratio)
- Modify: `ProjectYK_System/app/services/payroll.py:1004` (mixed-mode mao_rev sum)
- Test: `ProjectYK_System/tests/test_kb_payroll_integration.py`

**Interfaces:**
- Consumes: `driver_calc_price(row)` from Task 3, `_classify_lcb_days` from payroll.py
- Note: `_sum_gross_revenue` (line 232-243) stays on `revenue_customer` — it feeds เหมาน้ำมัน gross-share, but per spec the เหมา share base must also use driver_calc_price. Verify: line 290 `fee/rev` is the classification ratio; line 1004 `mao_rev` is the 60%-share base. Both switch to driver_calc_price. `_sum_gross_revenue` is used by the pure `mao` (เหมาน้ำมัน) mode at line ~720/872 — those rows have no KB/override today, but switching keeps them correct if they ever do.

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_kb_payroll_integration.py
from sqlmodel import Session, SQLModel, create_engine
from datetime import date
from app.models import DailyJob, Employee
from app.services import payroll

def _setup():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    emp = Employee(full_name="ทดสอบ", site_code="LCB")
    s.add(emp); s.commit(); s.refresh(emp)
    return s, emp

def test_classify_uses_driver_calc_price_not_billed():
    # bill 9000 with override 5000, fee 3000 -> ratio = 3000/5000 = 0.60 = mao day
    # (if it wrongly used revenue_customer 9000, ratio=0.33 -> ambiguous, NOT mao)
    s, emp = _setup()
    s.add(DailyJob(work_date=date(2026,6,1), site_code="LCB", driver_id=emp.id,
                   revenue_customer=9000, price_override=5000, trip_fee_driver=3000,
                   status_code="DHL Overflow"))
    s.commit()
    split = payroll._classify_lcb_days(s, emp.id, date(2026,6,1), date(2026,6,30), "LCB")
    assert len(split["mao_days"]) == 1
    assert len(split["ambiguous"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_payroll_integration.py -v`
Expected: FAIL — day lands in `ambiguous` (ratio computed from 9000, not 5000)

- [ ] **Step 3: Switch classification ratio to driver_calc_price**

In `payroll.py` `_classify_lcb_days`, replace lines 289-294:
```python
        rev = r.revenue_customer or 0.0
        fee = r.trip_fee_driver or 0.0
        if rev <= 0:
            no_work.append(r)  # rest/off day — no money either way, not "ambiguous"
            continue
        ratio = fee / rev
```
with:
```python
        rev = driver_calc_price(r)
        fee = r.trip_fee_driver or 0.0
        if rev <= 0:
            no_work.append(r)  # rest/off day — no money either way, not "ambiguous"
            continue
        ratio = fee / rev
```

- [ ] **Step 4: Switch mixed-mode mao share base to driver_calc_price**

In `payroll.py` line 1004, replace:
```python
        mao_rev = sum((d.revenue_customer or 0.0) for d in mao_days)
```
with:
```python
        mao_rev = sum(driver_calc_price(d) for d in mao_days)
```

- [ ] **Step 5: Switch _sum_gross_revenue to driver_calc_price**

In `payroll.py` line 243, replace:
```python
    return round(sum((r.revenue_customer or 0.0) for r in rows), 2)
```
with:
```python
    return round(sum(driver_calc_price(r) for r in rows), 2)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_payroll_integration.py tests/test_lcb_mixed.py tests/test_pending_price.py -v`
Expected: PASS — new test passes AND existing mixed-mode tests still pass (no regression; existing rows have kb=0/override=None so driver_calc_price == revenue_customer)

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/services/payroll.py ProjectYK_System/tests/test_kb_payroll_integration.py
git commit -m "feat(payroll): compute driver pay from driver_calc_price (KB/override aware)"
```

---

### Task 5: KB auto-fill จาก rule (service)

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` OR new `ProjectYK_System/app/services/kb.py` — add `kb_default_for_status` + `kb_warning_for_row`
- Test: `ProjectYK_System/tests/test_kb_autofill.py`

**Interfaces:**
- Produces:
  - `kb_default_for_status(session, status_code) -> float` — rule default or 0.0
  - `kb_warning_for_row(session, status_code, kb_amount) -> bool` — True if rule.required and kb_amount==0

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_kb_autofill.py
from sqlmodel import Session, SQLModel, create_engine
from app.models import KbRule
from app.services.kb import kb_default_for_status, kb_warning_for_row

def _sess():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    s.add(KbRule(status_code="NHL", default_kb=110.0, required=False))
    s.add(KbRule(status_code="CY", default_kb=0.0, required=True))
    s.commit()
    return s

def test_default_for_known_status():
    s = _sess()
    assert kb_default_for_status(s, "NHL") == 110.0

def test_default_for_unknown_status():
    s = _sess()
    assert kb_default_for_status(s, "รถจอด") == 0.0

def test_cy_zero_kb_triggers_warning():
    s = _sess()
    assert kb_warning_for_row(s, "CY", 0.0) is True
    assert kb_warning_for_row(s, "CY", 250.0) is False

def test_nhl_zero_kb_no_warning():
    s = _sess()
    assert kb_warning_for_row(s, "NHL", 0.0) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_autofill.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.kb`

- [ ] **Step 3: Create kb.py service**

```python
# ProjectYK_System/app/services/kb.py
"""KB (ใต้โต๊ะ) rule helpers — default ต่อ status_code + คำเตือนกันลืม."""
from sqlmodel import Session, select
from models import KbRule

KB_OUR_CUT = 0.10
KB_WHT = 0.03


def kb_default_for_status(session: Session, status_code: str) -> float:
    rule = session.exec(select(KbRule).where(KbRule.status_code == status_code)).first()
    return rule.default_kb if rule else 0.0


def kb_warning_for_row(session: Session, status_code: str, kb_amount: float) -> bool:
    """True เมื่อ rule บังคับ KB (CY) แต่แถวนี้ kb_amount == 0 → เตือนกันลืม."""
    rule = session.exec(select(KbRule).where(KbRule.status_code == status_code)).first()
    return bool(rule and rule.required and (kb_amount or 0.0) == 0.0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_autofill.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/kb.py ProjectYK_System/tests/test_kb_autofill.py
git commit -m "feat(daily): KB rule defaults + required-KB warning helper"
```

---

### Task 6: grid-save รองรับ kb_amount + price_override (+ auto-fill on save)

**Files:**
- Modify: `ProjectYK_System/app/main.py:1583` (add to `editable` set)
- Modify: `ProjectYK_System/app/main.py:1611-1621` (float coercion — kb_amount like other floats; price_override nullable)
- Test: `ProjectYK_System/tests/test_kb_grid_save.py`

**Interfaces:**
- Consumes: `daily_grid_save` endpoint at `/api/daily/grid-save`

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_kb_grid_save.py
# Verifies the float-coercion logic for the two new fields directly.
from app.main import _parse_float

def test_kb_amount_parses_like_float():
    assert _parse_float("110") == 110.0

def test_price_override_blank_is_none():
    # price_override must become None (not 0.0) when blank — checked in endpoint logic
    val = ""
    parsed = None if str(val).strip() == "" else _parse_float(str(val))
    assert parsed is None

def test_price_override_value_parses():
    val = "5500"
    parsed = None if str(val).strip() == "" else _parse_float(str(val))
    assert parsed == 5500.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_grid_save.py -v`
Expected: FAIL only if `_parse_float` import path wrong; if it passes immediately, the coercion helper already works — proceed to wire the endpoint (Steps 3-4) which the manual verify covers. (This task's real deliverable is endpoint wiring; the unit test guards the nullable rule.)

- [ ] **Step 3: Add fields to editable set**

In `main.py` `daily_grid_save`, add to the `editable` set (after `"trip_fee_driver",` line 1574):
```python
        "kb_amount",
        "price_override",
```

- [ ] **Step 4: Add coercion (kb_amount float, price_override nullable float)**

In `main.py`, add `"kb_amount"` to the float tuple at line 1611-1619 (alongside `revenue_customer`). Then BEFORE that float block (so it's handled first), add a special case for the nullable override:
```python
                if key == "price_override":
                    text = (str(val) if val is not None else "").strip()
                    setattr(row, key, None if text == "" else _parse_float(text))
                    continue
```

- [ ] **Step 5: Run test + manual verify**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_grid_save.py -v`
Expected: PASS

Manual: start app, edit a row in `/daily`, set kb_amount=110 and price_override=5500, save, reload — values persist; clear price_override → becomes blank (None) not 0.

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/tests/test_kb_grid_save.py
git commit -m "feat(daily): grid-save accepts kb_amount + price_override (override nullable)"
```

---

### Task 7: grid UI — คอลัมน์ KB + ราคาคนขับ + คำเตือน CY

**Files:**
- Modify: `ProjectYK_System/app/templates/daily_grid.html:273` (ALL_FIELDS — add kb_amount, price_override)
- Modify: `ProjectYK_System/app/templates/daily_grid.html:283` (money preset)
- Modify: `ProjectYK_System/app/templates/daily_grid.html:289,556,557` (NUM_FIELDS sets, RIGHT_ALIGN)
- Modify: `ProjectYK_System/app/templates/daily_grid.html` (add computed "ราคาคนขับ" column + CY warning formatter)
- Test: manual (UI / Tabulator — no JS test harness in repo)

**Interfaces:**
- Consumes: grid-data API returning the new fields (already returned — endpoint serializes the model). Verify `/api/daily/grid-data` includes `kb_amount`/`price_override` (it serializes DailyJob columns; confirm in step 1).

- [ ] **Step 1: Verify grid-data returns new fields**

Run app, open `/api/daily/grid-data?...`, confirm JSON rows include `kb_amount` and `price_override`. If the serializer is an explicit field list, add the two fields there (check `main.py:1445` `daily_grid_data`). If it dumps the model, nothing to do.

- [ ] **Step 2: Add columns to ALL_FIELDS**

In `daily_grid.html` line 273, after `["trip_fee_driver","ค่าเที่ยว (AD)",true],`:
```javascript
    ["kb_amount","KB (ใต้โต๊ะ)",true], ["price_override","ราคากลาง",true],
    ["driver_calc_price","ราคาคนขับ",false],
```

- [ ] **Step 3: Register numeric/align/missing sets**

Add `"kb_amount"`, `"price_override"`, `"driver_calc_price"` to:
- `NUM_FIELDS` (line 289)
- `NUM_FIELDS_ARR` (line 556)
- `RIGHT_ALIGN` (line 557)

Add `kb_amount` and `price_override` to the `money` preset (line 283) before `"remark"`, plus `driver_calc_price`.

- [ ] **Step 4: Compute driver_calc_price client-side + CY warning**

`driver_calc_price` is read-only (not stored). Add a Tabulator column formatter that computes per row:
```javascript
// driver_calc_price = (price_override ?? revenue_customer) - kb_amount
function calcDriverPrice(row) {
  const ov = row.price_override;
  const base = (ov !== null && ov !== undefined && ov !== "") ? Number(ov) : Number(row.revenue_customer || 0);
  return base - Number(row.kb_amount || 0);
}
```
For the `kb_amount` column formatter, add a visual warning when `status_code === "CY"` and `(kb_amount||0) === 0`: render the cell with a red/orange background or a ⚠ marker and tooltip "แถว CY ไม่มี KB — ไม่มีจริงใช่ไหม?". (Match existing MISSING_FIELDS highlight style at line 555 for consistency.)

- [ ] **Step 5: Manual verify**

Start app → `/daily`, money preset. Confirm:
- KB, ราคากลาง editable; ราคาคนขับ shows base−KB live as you edit
- NHL row default-fills KB=110 (from Task 8 backfill) ; editing recomputes ราคาคนขับ
- CY row with KB=0 shows the ⚠ warning highlight

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/templates/daily_grid.html ProjectYK_System/app/main.py
git commit -m "feat(daily): grid shows KB / ราคากลาง / ราคาคนขับ + CY-missing-KB warning"
```

---

### Task 8: Backfill KB ย้อนหลังจาก rule (tool, read-confirm)

**Files:**
- Create: `ProjectYK_System/tools/backfill_kb_from_rule.py`
- Test: `ProjectYK_System/tests/test_backfill_kb.py`

**Interfaces:**
- Produces: a script that sets `kb_amount = rule.default_kb` for rows where `kb_amount==0` and a non-required rule matches `status_code` (NHL/MOL). CY left at 0 (will warn). `--dry-run` default; `--apply` to write. Backs up app.db first.

- [ ] **Step 1: Write the failing test**

```python
# ProjectYK_System/tests/test_backfill_kb.py
from sqlmodel import Session, SQLModel, create_engine, select
from datetime import date
from app.models import DailyJob, KbRule
from tools.backfill_kb_from_rule import plan_backfill

def _sess():
    eng = create_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    s = Session(eng)
    s.add(KbRule(status_code="NHL", default_kb=110.0, required=False))
    s.add(KbRule(status_code="CY", default_kb=0.0, required=True))
    s.add(DailyJob(work_date=date(2026,6,1), site_code="LCB", status_code="NHL", kb_amount=0))
    s.add(DailyJob(work_date=date(2026,6,2), site_code="LCB", status_code="NHL", kb_amount=110))  # already set
    s.add(DailyJob(work_date=date(2026,6,3), site_code="LCB", status_code="CY", kb_amount=0))     # required, skip
    s.commit()
    return s

def test_plan_only_fills_nonrequired_zero_rows():
    s = _sess()
    plan = plan_backfill(s)
    # only the NHL kb=0 row -> 1 change to 110
    assert len(plan) == 1
    assert plan[0]["new_kb"] == 110.0
    assert plan[0]["status_code"] == "NHL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System && python -m pytest tests/test_backfill_kb.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write backfill tool**

```python
# ProjectYK_System/tools/backfill_kb_from_rule.py
"""Backfill DailyJob.kb_amount จาก KbRule (เฉพาะ rule ที่ required=False, แถว kb==0).
CY (required=True) ไม่แตะ — ให้คนกรอกเอง (จะ warn ในกริด). dry-run by default."""
import sys, shutil, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from sqlmodel import Session, select, create_engine
from models import DailyJob, KbRule

def plan_backfill(session: Session) -> list[dict]:
    rules = {r.status_code: r for r in session.exec(select(KbRule)).all() if not r.required and r.default_kb > 0}
    out = []
    for r in session.exec(select(DailyJob)).all():
        rule = rules.get(r.status_code or "")
        if rule and (r.kb_amount or 0.0) == 0.0:
            out.append({"id": r.id, "status_code": r.status_code,
                        "old_kb": r.kb_amount or 0.0, "new_kb": rule.default_kb})
    return out

def main(apply: bool):
    db = Path(__file__).resolve().parents[1] / "app" / "app.db"
    eng = create_engine(f"sqlite:///{db}")
    with Session(eng) as s:
        plan = plan_backfill(s)
        print(f"rows to backfill: {len(plan)}")
        for p in plan[:20]:
            print(p)
        if apply:
            bak = db.with_suffix(f".db.bak_before_kb_backfill_{datetime.datetime.now():%Y%m%d_%H%M%S}")
            shutil.copy2(db, bak)
            print(f"backup -> {bak}")
            for p in plan:
                row = s.get(DailyJob, p["id"]); row.kb_amount = p["new_kb"]; s.add(row)
            s.commit()
            print(f"applied {len(plan)} rows")

if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ProjectYK_System && python -m pytest tests/test_backfill_kb.py -v`
Expected: PASS

- [ ] **Step 5: Dry-run against real db (report only, NO --apply)**

Run: `cd ProjectYK_System && python tools/backfill_kb_from_rule.py`
Expected: prints count + sample of NHL/MOL rows that WOULD get KB. Do NOT apply — โอ reviews count first.

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/tools/backfill_kb_from_rule.py ProjectYK_System/tests/test_backfill_kb.py
git commit -m "feat(tools): backfill_kb_from_rule (dry-run default, NHL/MOL only)"
```

---

### Task 9: Preflight — net เปลี่ยนต่อคน ก่อน recompute payroll

**Files:**
- Create: `ProjectYK_System/tools/preflight_kb_driver_price.py`
- Test: manual (read-only report against real db)

**Interfaces:**
- Consumes: `driver_calc_price` from payroll.py; reads DailyJob rows
- Produces: read-only report — per LCB cycle/driver, list rows where `driver_calc_price != revenue_customer`, sum the gross-base delta per driver, and flag CY rows with kb_amount==0.

- [ ] **Step 1: Write the report tool**

```python
# ProjectYK_System/tools/preflight_kb_driver_price.py
"""READ-ONLY: โชว์ผลกระทบของ driver_calc_price ก่อน recompute payroll.
ต่อคนขับ (LCB): ผลรวม revenue_customer vs driver_calc_price + แถว CY ที่ลืม KB."""
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
                d = delta[r.driver_id]; d[0]+=billed; d[1]+=dcp; d[2]+=1
            if (r.status_code in req) and (r.kb_amount or 0.0) == 0.0:
                cy_missing.append((r.id, r.work_date, r.status_code))
        print("=== driver gross-base delta (billed -> driver_calc) ===")
        for did, (b, c, n) in sorted(delta.items(), key=lambda x: x[1][1]-x[1][0]):
            print(f"{names.get(did, did)!r:24} rows={n:3}  billed={b:>12,.0f}  driver={c:>12,.0f}  delta={c-b:>+12,.0f}")
        print(f"\n=== required-KB rows missing KB (e.g. CY): {len(cy_missing)} ===")
        for row in cy_missing[:40]:
            print(row)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run against real db (read-only)**

Run: `cd ProjectYK_System && python tools/preflight_kb_driver_price.py`
Expected: per-driver delta table + list of CY rows missing KB. Hand this to โอ for sign-off BEFORE any recompute.

- [ ] **Step 3: Commit**

```bash
git add ProjectYK_System/tools/preflight_kb_driver_price.py
git commit -m "feat(tools): preflight KB/driver-calc-price impact (read-only)"
```

---

### Task 10: ตรวจ driver PWA ไม่โชว์ KB (guard)

**Files:**
- Inspect: driver PWA templates (driver-facing) — confirm none render `kb_amount`/`price_override`
- Test: grep-based assertion

- [ ] **Step 1: Grep driver-facing templates for KB leakage**

Run: `grep -rn "kb_amount\|price_override" ProjectYK_System/app/templates/driver*.html ProjectYK_System/app/templates/pwa*.html 2>/dev/null`
Expected: NO matches. Driver PWA never renders KB.

- [ ] **Step 2: Confirm driver pay surfaces use driver_calc_price, not raw fields**

Inspect the driver submission / slip templates and the payroll slip. Driver sees only `trip_fee_driver` / computed pay (which already flows through `driver_calc_price` in payroll). Confirm no template shows the KB column to drivers. If any does, remove it.

- [ ] **Step 3: Add a regression guard test**

```python
# ProjectYK_System/tests/test_kb_not_in_driver_pwa.py
from pathlib import Path
import glob

def test_no_kb_in_driver_templates():
    tpl = Path(__file__).resolve().parents[1] / "app" / "templates"
    for f in glob.glob(str(tpl / "driver*.html")) + glob.glob(str(tpl / "pwa*.html")):
        txt = Path(f).read_text(encoding="utf-8")
        assert "kb_amount" not in txt, f"KB leaked into driver template {f}"
```

- [ ] **Step 4: Run test**

Run: `cd ProjectYK_System && python -m pytest tests/test_kb_not_in_driver_pwa.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/tests/test_kb_not_in_driver_pwa.py
git commit -m "test(daily): guard KB never renders in driver PWA"
```

---

## Self-Review

**Spec coverage:**
- KB field + override field → Task 1 ✓
- KB rule table (NHL/MOL/CY) → Task 2 ✓
- driver_calc_price formula (override−KB, override replaces base) → Task 3 ✓
- payroll uses driver_calc_price (ratio + mao share + gross) → Task 4 ✓
- KB auto-fill from rule + CY required warning → Task 5 (logic) + Task 7 (UI warning) ✓
- grid edit surface (admin) → Task 6 (save) + Task 7 (columns) ✓
- 10%/WHT computed live (config constants) → Task 5 (`KB_OUR_CUT`/`KB_WHT` defined; report uses them) — NOTE: report display deferred but constants + formula in place per spec "รอบนี้คำนวณสด"
- backward recompute with preflight → Task 8 (backfill) + Task 9 (preflight) ✓
- admin-visible / driver-hidden → Task 7 (admin grid) + Task 10 (driver guard) ✓
- status_code as customer key → Tasks 2,5,8 all key on status_code ✓
- YAGNI exclusions respected (no Customer master, no separate WHT fields, no size-based KB, no per-admin RBAC) ✓

**Placeholder scan:** No TBD/TODO. Task 6 step 2 notes the unit test may pass immediately (real deliverable is endpoint wiring covered by manual verify) — explicit, not a placeholder. Task 7/9/10 use manual verify where no JS/integration harness exists — explicit.

**Type consistency:** `driver_calc_price(row)` signature identical across Tasks 3,4,9. `KbRule(status_code, default_kb, required, note)` identical across Tasks 2,5,8. `kb_amount: float`, `price_override: Optional[float]` identical across Tasks 1,6,7. ✓

**Note on KB report UI:** The spec's KB P&L summary (เราเก็บ 10%/WHT 3%/จ่ายคนจ่ายงาน) has constants + formula landed in Task 5, but a dedicated finance-page display is NOT a separate task — it's a thin read-only render deferred until โอ confirms placement (finance vs preflight). Flag to โอ at execution handoff; add as Task 11 if wanted.
