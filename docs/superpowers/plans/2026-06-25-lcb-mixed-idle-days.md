# LCB lcb_mixed นับวันรถจอด + เตือนวันรอลงราคา — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แก้ pay_mode `lcb_mixed` ให้นับวันรถจอด(idle)เข้าตัวหารฐาน, ขยายการจับ status "รถจอด" ให้ครอบอุบัติเหตุ/ซ่อม/DHL-Overflow, และเตือนวันที่มี status ลูกค้าแต่ยังไม่ลงราคาในหน้าเงินเดือน.

**Architecture:** แก้ใน `services/payroll.py` 2 จุด (ตัวหาร mixed + token จับ idle) แบบ TDD บน in-memory SQLite. เพิ่ม read-only helper หาวันรอลงราคา + guardrail banner ในหน้า `/payroll/{run_id}` ตาม pattern `unlinked`/`cycle_drift` ที่มีอยู่.

**Tech Stack:** Python, SQLModel, FastAPI, Jinja2, pytest. รันเทสต์: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/ -q`

## Global Constraints

- งานเงิน → ทุกการเขียนทับ DB จริงต้อง backup `app.db` ก่อน. งานนี้แก้โค้ด+เทสต์เท่านั้น; การ recompute payrun#2 จริงทำใน Task 5 หลัง backup.
- ตัวหารฐาน LCB = จำนวนวันจริงใน cycle (16/5–15/6 = 31 วัน), อย่า hardcode 30.
- ห้ามเดาราคาวันรอลงราคา — แค่เตือน, read-only.
- pattern เทสต์: in-memory `create_engine("sqlite://")`, `SQLModel.metadata.create_all`. ดู `tests/test_lcb_mixed.py` เดิม.
- ห้าม finalize payrun ในงานนี้.

---

### Task 1: ขยาย `_count_work_days` จับ idle เพิ่ม (อุบัติเหตุ/ซ่อม/DHL Overflow)

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` (function `_count_work_days`, ~บรรทัด 711-717 `is_company_no_work`)
- Test: `ProjectYK_System/tests/test_count_work_days_idle.py` (สร้างใหม่)

**Interfaces:**
- Consumes: `_count_work_days(session, emp_id, start, end, site_code) -> dict` คืน keys `worked/leave/absent/company_no_work` (มีอยู่แล้ว)
- Produces: หลังแก้ วันที่ revenue=0 และ status_code มีคำ `อุบัติเหตุ`/`ซ่อม` (token) หรือ `dhl overflow` (วลีในสตริง) ถูกนับเป็น `company_no_work` ไม่ใช่ตกหาย

- [ ] **Step 1: เขียนเทสต์ที่ fail**

สร้าง `ProjectYK_System/tests/test_count_work_days_idle.py`:

```python
import sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sqlmodel import SQLModel, Session, create_engine
from models import DailyJob
from services.payroll import _count_work_days


def _mk_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add(s, emp_id, d, status, rev=0, fee=0):
    s.add(DailyJob(driver_id=emp_id, site_code="LCB", work_date=d,
                   status_code=status, revenue_customer=rev, trip_fee_driver=fee))


def test_accident_repair_dhloverflow_count_as_idle():
    s = _mk_session()
    _add(s, 1, date(2026, 6, 2), "รถอุบัติเหตุ")
    _add(s, 1, date(2026, 6, 3), "รถซ่อม")
    _add(s, 1, date(2026, 6, 4), "DHL Overflow")
    _add(s, 1, date(2026, 6, 5), "รถจอด")        # เดิมก็จับได้
    s.commit()
    out = _count_work_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert out["company_no_work"] == 4.0
    assert out["leave"] == 0.0
    assert out["absent"] == 0.0


def test_leave_still_not_idle():
    s = _mk_session()
    _add(s, 1, date(2026, 6, 2), "ลา / ไม่พร้อม")
    s.commit()
    out = _count_work_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert out["leave"] == 1.0
    assert out["company_no_work"] == 0.0
```

- [ ] **Step 2: รันเทสต์ ยืนยันว่า fail**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_count_work_days_idle.py -v`
Expected: `test_accident_repair_dhloverflow_count_as_idle` FAIL (company_no_work == 1.0 not 4.0 — จับได้แค่ "รถจอด")

- [ ] **Step 3: แก้ `is_company_no_work`**

ใน `payroll.py` function `_count_work_days`, block `is_company_no_work` (ปัจจุบัน):

```python
        is_company_no_work = (
            ("company_no_work" in leave_statuses)
            or ("idle" in status_codes)
            or ("ไม่มีงาน" in tokens)
            or ("รถจอด" in tokens)
            or ("รองาน" in tokens)
        )
```

เปลี่ยนเป็น (เพิ่ม 3 เงื่อนไข; `status_blob` รวม status_code ทุกแถวของวันนั้นเป็นสตริงเดียวสำหรับ match วลี "dhl overflow"):

```python
        status_blob = " ".join((r.status_code or "") for r in drows).lower()
        is_company_no_work = (
            ("company_no_work" in leave_statuses)
            or ("idle" in status_codes)
            or ("ไม่มีงาน" in tokens)
            or ("รถจอด" in tokens)
            or ("รองาน" in tokens)
            or ("อุบัติเหตุ" in tokens)
            or ("ซ่อม" in tokens)
            or ("dhl overflow" in status_blob)
        )
```

- [ ] **Step 4: รันเทสต์ ยืนยัน pass**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_count_work_days_idle.py -v`
Expected: PASS ทั้ง 2 เทสต์

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/tests/test_count_work_days_idle.py ProjectYK_System/app/services/payroll.py
git commit -m "fix(payroll): นับวันอุบัติเหตุ/ซ่อม/DHL-Overflow เป็น company_no_work"
```

---

### Task 2: ตัวหารฐาน/ค่าดูแล lcb_mixed รวมวันรถจอด

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` (branch `lcb_mixed`, ~บรรทัด 916-917 + note)
- Test: `ProjectYK_System/tests/test_lcb_mixed.py` (เพิ่มเทสต์ใหม่ในไฟล์เดิม)

**Interfaces:**
- Consumes: `calc.days_company_no_work` (set ที่บรรทัด 807 จาก `_count_work_days`), `n_trip = len(trip_days)`, `days_in_month`
- Produces: `calc.base_salary_earned` / `calc.care_allowance_earned` = `base × ((n_trip + n_idle) / days_in_month)` โดย `n_idle = calc.days_company_no_work`

- [ ] **Step 1: เขียนเทสต์ที่ fail**

เพิ่มท้าย `ProjectYK_System/tests/test_lcb_mixed.py`:

```python
def test_lcb_mixed_idle_day_counts_toward_base():
    s = _mk_session()
    emp = Employee(code="TEST-MIX2", full_name="ทดสอบ รถจอด", home_site_code="LCB",
                   pay_mode="lcb_mixed", base_salary=9240, care_allowance=3000,
                   gross_share_rate=0.60, start_date=date(2026, 5, 16))
    s.add(emp); s.commit(); s.refresh(emp)
    # 1 trip day
    s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 3),
                   revenue_customer=5000, trip_fee_driver=350))
    # 1 idle day (รถจอด, rev=0)
    s.add(DailyJob(driver_id=emp.id, site_code="LCB", work_date=date(2026, 6, 4),
                   status_code="รถจอด", revenue_customer=0, trip_fee_driver=0))
    s.commit()

    calc = calc_one_employee(s, emp, date(2026, 5, 16), date(2026, 6, 15), "2026-06")
    period_days = 31
    # base prorated by (trip + idle) = 2 days, not 1
    assert abs(calc.base_salary_earned - 9240 * (2 / period_days)) < 0.5
    assert abs(calc.care_allowance_earned - 3000 * (2 / period_days)) < 0.5
```

- [ ] **Step 2: รันเทสต์ ยืนยันว่า fail**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py::test_lcb_mixed_idle_day_counts_toward_base -v`
Expected: FAIL (base ยังหารด้วย 1/31 ไม่ใช่ 2/31)

- [ ] **Step 3: แก้ตัวหารใน branch lcb_mixed**

ใน `payroll.py` branch `lcb_mixed` (ปัจจุบัน):

```python
        # base+care prorate by TRIP days only (mao days have no base)
        calc.base_salary_earned = round(base * (n_trip / days_in_month), 2)
        calc.care_allowance_earned = round(care * (n_trip / days_in_month), 2)
```

เปลี่ยนเป็น:

```python
        # base+care prorate by TRIP days + IDLE (รถจอด) days.
        # mao days have no base; idle days (รถจอด/อุบัติเหตุ/ซ่อม) DO earn base
        # per โอ policy 2026-06-25 — คนขับมาแต่บริษัทไม่มีงาน ต้องได้ฐาน.
        n_idle = calc.days_company_no_work
        base_days = n_trip + n_idle
        calc.base_salary_earned = round(base * (base_days / days_in_month), 2)
        calc.care_allowance_earned = round(care * (base_days / days_in_month), 2)
```

แก้ `calc.note` ในบล็อกเดียวกัน จาก `ฐาน×{n_trip}/{int(days_in_month)}วัน` เป็น:

```python
            f"{calc.trip_fee_total:,.0f}+พิเศษ {n_trip*100} | ฐาน×{int(base_days)}/{int(days_in_month)}วัน"
```

(บรรทัด note ปัจจุบันใช้ `n_trip` ในส่วน "ฐาน×" — เปลี่ยนเป็น `int(base_days)`. ส่วน "เที่ยว {n_trip}วัน" คงเดิม.)

- [ ] **Step 4: รันเทสต์ ยืนยัน pass (ทั้งไฟล์ — กันของเดิมพัง)**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_lcb_mixed.py -v`
Expected: PASS ทุกเทสต์ (รวม `test_lcb_mixed_splits_income_and_prorates_base` เดิม — เทสต์นั้นไม่มี idle day จึง base_days = n_trip ค่าไม่เปลี่ยน)

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/tests/test_lcb_mixed.py ProjectYK_System/app/services/payroll.py
git commit -m "fix(payroll): lcb_mixed นับวันรถจอดเข้าตัวหารฐาน/ค่าดูแล"
```

---

### Task 3: Regression — net คนอื่น 16 คนต้องไม่เปลี่ยน

**Files:**
- Modify: `ProjectYK_System/tests/test_lcb_mixed_regression.py` (มีอยู่แล้ว — อัปเดต golden ถ้าจำเป็น) หรือสร้างสคริปต์เทียบ
- Test: รันเทียบ net จริงกับ golden snapshot ใน spec

**Interfaces:**
- Consumes: `calc_one_employee` กับ payrun#2 จาก `app.db`
- Produces: ยืนยัน net ของ 16 คน non-mixed ตรง golden; พชร(86)/สุรเดช(91) เปลี่ยนตามคาด

- [ ] **Step 1: เขียนสคริปต์เทียบ net ก่อน-หลัง (ไม่เขียน DB)**

สร้าง `ProjectYK_System/tools/verify_idle_fix_impact.py`:

```python
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
```

- [ ] **Step 2: รันสคริปต์**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe tools/verify_idle_fix_impact.py`
Expected: ทุกแถว golden ไม่มี `CHANGED`, mixed 86/91 net สูงกว่าเดิม, ปิดท้าย `RESULT: OK`

- [ ] **Step 3: ถ้ามี non-mixed เปลี่ยน → หยุด, รายงานโอ**

ห้ามแก้ golden ให้ตรง. ถ้าใครเปลี่ยน แปลว่า `days_worked` ถูกใช้ทางอ้อมที่อื่น — สืบหาแล้วรายงาน. ถ้า OK ไปต่อ.

- [ ] **Step 4: Commit**

```bash
git add ProjectYK_System/tools/verify_idle_fix_impact.py
git commit -m "test(payroll): สคริปต์ยืนยัน idle-fix กระทบแค่ mixed 86/91"
```

---

### Task 4: Guardrail — เตือนวันรอลงราคาในหน้าเงินเดือน

**Files:**
- Modify: `ProjectYK_System/app/services/payroll.py` (เพิ่ม helper `find_pending_price_days`)
- Modify: `ProjectYK_System/app/main.py` (`payroll_detail` ~3330-3408: เรียก helper + ใส่ ctx)
- Modify: `ProjectYK_System/app/templates/payroll_detail.html` (เพิ่ม banner ตาม pattern `cycle_drift`)
- Test: `ProjectYK_System/tests/test_pending_price.py` (สร้างใหม่)

**Interfaces:**
- Consumes: `Session`, payrun roster (emp_ids), `pr.period_start/end`, site
- Produces: `find_pending_price_days(session, emp_id, start, end, site_code) -> list[dict]` แต่ละ dict = `{"date": str, "status": str}`. วันที่นับ = `revenue_customer<=0 AND trip_fee_driver<=0 AND status_code != "" AND` ไม่เข้า idle/leave/absent keyword.

- [ ] **Step 1: เขียนเทสต์ helper ที่ fail**

สร้าง `ProjectYK_System/tests/test_pending_price.py`:

```python
import sys, os
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from sqlmodel import SQLModel, Session, create_engine
from models import DailyJob
from services.payroll import find_pending_price_days


def _mk_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add(s, d, status, rev=0, fee=0):
    s.add(DailyJob(driver_id=1, site_code="LCB", work_date=d,
                   status_code=status, revenue_customer=rev, trip_fee_driver=fee))


def test_pending_price_flags_customer_code_zero_revenue():
    s = _mk_session()
    _add(s, date(2026, 6, 2), "KAO")            # ลูกค้า, rev=0 -> รอลงราคา
    _add(s, date(2026, 6, 3), "รถจอด")           # idle -> ไม่ใช่
    _add(s, date(2026, 6, 4), "ลา / ไม่พร้อม")   # leave -> ไม่ใช่
    _add(s, date(2026, 6, 5), "KLND", rev=5000, fee=350)  # มีรายได้ -> ไม่ใช่
    s.commit()
    out = find_pending_price_days(s, 1, date(2026, 6, 1), date(2026, 6, 15), "LCB")
    assert [r["date"] for r in out] == ["2026-06-02"]
    assert out[0]["status"] == "KAO"
```

- [ ] **Step 2: รันเทสต์ ยืนยันว่า fail**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_pending_price.py -v`
Expected: FAIL — `ImportError: cannot import name 'find_pending_price_days'`

- [ ] **Step 3: เขียน helper**

เพิ่มใน `payroll.py` (วางก่อน `def calc_one_employee`):

```python
def find_pending_price_days(
    session: Session, emp_id: int, start: date, end: date, site_code: str = ""
) -> list[dict]:
    """วันที่มี status_code (ปกติเป็นรหัสลูกค้า) แต่ revenue=0 และ trip_fee=0
    = พี่ตาลยังไม่ลงราคา. ไม่นับวัน idle (รถจอด/อุบัติเหตุ/ซ่อม/DHL Overflow)
    หรือ leave/absent. READ-ONLY — แค่เตือนให้ไปเติมราคา ไม่เดาเงิน."""
    IDLE_LEAVE_KW = ("รถจอด", "รองาน", "ไม่มีงาน", "อุบัติเหตุ", "ซ่อม",
                     "dhl overflow", "ลา", "ขาด", "ป่วย", "หยุด", "idle")
    stmt = select(DailyJob).where(
        DailyJob.driver_id == emp_id,
        DailyJob.work_date >= start,
        DailyJob.work_date <= end,
    )
    if site_code:
        stmt = stmt.where(DailyJob.site_code == site_code)
    out = []
    for r in session.exec(stmt).all():
        if (r.revenue_customer or 0) > 0 or (r.trip_fee_driver or 0) > 0:
            continue
        sc = (r.status_code or "").strip()
        if not sc:
            continue
        low = sc.lower()
        if any(kw in low for kw in IDLE_LEAVE_KW):
            continue
        out.append({"date": str(r.work_date), "status": sc})
    out.sort(key=lambda x: x["date"])
    return out
```

- [ ] **Step 4: รันเทสต์ ยืนยัน pass**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -m pytest tests/test_pending_price.py -v`
Expected: PASS

- [ ] **Step 5: ต่อ helper เข้า payroll_detail + ctx**

ใน `main.py` function `payroll_detail`, หลังบรรทัด `policy_review = _collect_policy_review_for_payrun(s, pr, limit=8)` เพิ่ม:

```python
        from services.payroll import find_pending_price_days
        pending_price = []
        for it in items:
            emp_pp = s.get(Employee, it.employee_id)
            days = find_pending_price_days(
                s, it.employee_id, pr.period_start, pr.period_end,
                site_code=(emp_pp.home_site_code if emp_pp else pr.site_code),
            )
            for d in days:
                pending_price.append({
                    "name": (emp_pp.nickname or emp_pp.full_name) if emp_pp else str(it.employee_id),
                    "date": d["date"], "status": d["status"],
                })
        pending_price.sort(key=lambda x: (x["date"], x["name"]))
```

ใน `ctx.update({...})` เพิ่ม key:

```python
        "pending_price": pending_price,
```

- [ ] **Step 6: เพิ่ม banner ใน template**

ใน `payroll_detail.html` หลังบล็อก `{% if cycle_drift and cycle_drift.count > 0 %}...{% endif %}` เพิ่ม:

```html
{% if pending_price and pending_price|length > 0 %}
<div class="mb-3 rounded-lg border border-orange-300 bg-orange-50 p-3 flex items-start gap-3">
  <div class="text-orange-600 text-xl leading-none">⚠</div>
  <div class="text-sm flex-1">
    <div class="font-semibold text-orange-900">มีวันรอลงราคา {{ pending_price|length }} วัน — คนขับมีงานลูกค้าแต่ยังไม่ได้กรอกค่าขนส่ง/ค่าเที่ยว</div>
    <div class="text-orange-800 mt-1 grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-0.5">
      {% for r in pending_price %}
      <div>{{ r.name }} — {{ r.date }} <span class="text-orange-500">({{ r.status }})</span></div>
      {% endfor %}
    </div>
    <div class="text-orange-700 mt-1 text-xs">ไปเติมราคาในหน้า Daily ก่อน finalize เพื่อไม่ให้เงินคนขับตกหล่น</div>
  </div>
</div>
{% endif %}
```

- [ ] **Step 7: เทสต์ route ไม่พัง (smoke import)**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'app'); import main; print('import OK')"`
Expected: `import OK` (ไม่มี SyntaxError/ImportError)

- [ ] **Step 8: Commit**

```bash
git add ProjectYK_System/tests/test_pending_price.py ProjectYK_System/app/services/payroll.py ProjectYK_System/app/main.py ProjectYK_System/app/templates/payroll_detail.html
git commit -m "feat(payroll): เตือนวันรอลงราคาในหน้าเงินเดือน (read-only guardrail)"
```

---

### Task 5: Recompute payrun#2 (draft) + regen หน้าเทียบมือ

**Files:**
- ใช้: `app.db` (เขียนจริง — backup ก่อน), route `POST /payroll/2/recompute` หรือ engine โดยตรง
- Modify: `reports/lcb_mixed_compare_2026-06.html` (regen ด้วยเลขใหม่ผ่าน `tools/export_lcb_mixed_compare.py`)

**Interfaces:**
- Consumes: payroll engine ที่แก้แล้ว
- Produces: payrun#2 items net ใหม่ (draft, ยังไม่ finalize), หน้าเทียบมือเลขใหม่

- [ ] **Step 1: Backup app.db**

```bash
cd "ProjectYK_System/app" && cp app.db "app.db.bak_before_idle_fix_recompute_$(date +%Y%m%d_%H%M%S)"
```
Expected: ไฟล์ backup ใหม่ปรากฏ

- [ ] **Step 2: รัน verify impact อีกรอบ (กันพลาดหลัง backup)**

Run: `cd ProjectYK_System && app/.venv/Scripts/python.exe tools/verify_idle_fix_impact.py`
Expected: `RESULT: OK — only mixed changed`

- [ ] **Step 3: Recompute payrun#2**

ใช้ route (แอปต้องรัน) หรือ engine โดยตรง. แบบ engine (เขียน items ใหม่):
รัน `POST /payroll/2/recompute` ผ่าน UI ปุ่ม "⚠ คำนวณใหม่" บนหน้า `/payroll/2` (ปลอดภัยสุด — ใช้ path เดียวกับ production).
Expected: หน้า payrun#2 แสดง net พชร/สุรเดชสูงขึ้น, มี banner วันรอลงราคา

- [ ] **Step 4: regen หน้าเทียบมือ**

```bash
cd ProjectYK_System && app/.venv/Scripts/python.exe tools/export_lcb_mixed_compare.py
```
จากนั้น re-embed JSON เข้า `reports/lcb_mixed_compare_2026-06.html` (ใช้สคริปต์ embed เดิมที่ replace `const DATA`).
Expected: หน้าเทียบมือแสดง base_days = trip+idle, net ใหม่

- [ ] **Step 5: เทียบเลขกับโอ ก่อน finalize (หยุดรอ)**

แสดงตาราง net เก่า/ใหม่ของ 18 คน + รายการวันรอลงราคา. **ไม่ finalize** — โอเป็นคนตัดสิน.

- [ ] **Step 6: Commit (โค้ด+รายงาน ไม่รวม app.db)**

```bash
git add reports/lcb_mixed_compare_2026-06.html
git commit -m "chore: regen หน้าเทียบมือ LCB mixed ด้วยเลขหลัง idle-fix"
```

---

## Self-Review

**Spec coverage:**
- จุด 1 (ตัวหารฐาน mixed) → Task 2 ✓
- จุด 2 (ขยาย is_company_no_work) → Task 1 ✓
- จุด 3 (warning วันรอลงราคาในหน้าเงินเดือน) → Task 4 ✓
- regression net 16 คน → Task 3 ✓
- backup + recompute + เทียบเลข ก่อน finalize → Task 5 ✓
- golden snapshot ใช้ใน Task 3 ✓

**Placeholder scan:** ไม่มี TBD/TODO; โค้ดเต็มทุก step ✓

**Type consistency:** `find_pending_price_days(...) -> list[dict]` คืน `{"date","status"}` ใช้ตรงกันใน Task 4 helper/test/ctx ✓. `calc.days_company_no_work` ชื่อตรงกับ models/payroll ✓. `n_idle`/`base_days` นิยามใน Task 2 ✓.

**หมายเหตุความเสี่ยง:** Task 1 อาจทำให้ `days_worked` ของ 4 คนเปลี่ยน (วัน worked→idle) — Task 3 จับได้ถ้า net เพี้ยน. ถ้า net เท่าเดิม (คาดไว้) ผ่าน.
