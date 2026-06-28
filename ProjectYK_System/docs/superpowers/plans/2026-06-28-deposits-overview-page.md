# เงินประกันตนรวม (Deposits Overview) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** หน้า `/deposits` ที่แสดงยอดเงินประกันตน (security deposit) ของทุกคนในตารางเดียว แก้ยอดได้พร้อม audit log และดูประวัติการหักรายคนได้

**Architecture:** เพิ่ม routes ใน `main.py` (monolith) อ่านจาก `Employee` + `PayRunItem` ที่มีอยู่, เขียนเฉพาะ `employee.deposit_balance/target` ผ่านปุ่มแก้ + INSERT `DepositAudit` (model ใหม่ INSERT-only แบบเดียวกับ `DailyJobAudit`). เทมเพลต Jinja2 + HTMX 1 ไฟล์. ไม่แตะ payroll engine.

**Tech Stack:** FastAPI + SQLModel + Jinja2 + HTMX (ตามสแต็กเดิม), pytest + Starlette TestClient

## Global Constraints

- `fastapi<0.115`, `starlette<0.40` — ห้ามอัปเกรด (Jinja2 globals พัง)
- ฟอร์แมตวันใน template ใช้ filter `| dmy` / `| dmy_hm` เสมอ — ห้ามฟอร์แมตเอง
- เขียนเฉพาะ `deposit_balance` / `deposit_target` + INSERT `DepositAudit` เท่านั้น — ห้ามแตะ logic payroll, ยอด net ของทุก payrun ต้องเท่าเดิม
- `SITE_CODES = ("AYU", "BIGC", "LCB")` (models.py:1241) — ใช้ค่านี้ ไม่ hardcode ซ้ำ
- `changed_by` ดึงจาก `current_user(request)` แบบ `(_u.username if _u else "") or "?"` (เหมือน main.py:1674-1675)
- รัน test จาก `ProjectYK_System/app/` ด้วย `.venv/Scripts/python.exe -m pytest`

---

### Task 1: Model `DepositAudit` + bump schema

**Files:**
- Modify: `ProjectYK_System/app/models.py` (เพิ่ม class หลัง `DailyJobAudit` ~บรรทัด 1411)
- Modify: `ProjectYK_System/app/main.py:91` (`SCHEMA_VERSION` 27 → 28)
- Test: `ProjectYK_System/app/tests/test_deposits.py`

**Interfaces:**
- Produces: `models.DepositAudit(employee_id:int, changed_at:datetime, changed_by:str, field_name:str, old_value:str, new_value:str, reason:str)` — INSERT-only audit row. Table สร้างอัตโนมัติโดย `SQLModel.metadata.create_all` ใน `init_db()`.

- [ ] **Step 1: Write the failing test**

สร้างไฟล์ `ProjectYK_System/app/tests/test_deposits.py` (header เหมือน test อื่น — ตั้ง env ก่อน import):

```python
"""หน้า /deposits — ยอดเงินประกันตนรวม: ดู + แก้ (มี audit) + ประวัติรายคน."""
import os, tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import Employee, PayRun, PayRunItem, AppUser, DepositAudit


def test_deposit_audit_model_exists():
    # ฟิลด์ครบตามสเปก
    a = DepositAudit(employee_id=1, changed_by="yk1",
                     field_name="deposit_balance", old_value="0", new_value="1000",
                     reason="test")
    assert a.employee_id == 1
    assert a.field_name == "deposit_balance"
    assert a.new_value == "1000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py::test_deposit_audit_model_exists -v`
Expected: FAIL — `ImportError: cannot import name 'DepositAudit'`

- [ ] **Step 3: เพิ่ม model**

ใน `models.py` หลัง class `DailyJobAudit` (หลังบรรทัด ~1411, ก่อน `TRIP_TYPE_CODES_BY_SITE`):

```python
class DepositAudit(SQLModel, table=True):
    """ประวัติการแก้ยอดเงินประกันตนในหน้า /deposits — INSERT-only, ไม่แก้ของเดิม."""
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    changed_by: str = ""
    field_name: str = ""        # deposit_balance | deposit_target
    old_value: str = ""
    new_value: str = ""
    reason: str = ""
```

- [ ] **Step 4: Bump schema version**

`main.py:91` เปลี่ยน:
```python
SCHEMA_VERSION = 28  # v28: DepositAudit (deposit edit log) for /deposits page
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py::test_deposit_audit_model_exists -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/models.py ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_deposits.py
git commit -m "feat(deposits): DepositAudit model + schema v28"
```

---

### Task 2: Route `GET /deposits` + summary + ตารางหลัก

**Files:**
- Modify: `ProjectYK_System/app/main.py` (เพิ่ม route หลัง `employees_list` ~บรรทัด 838)
- Create: `ProjectYK_System/app/templates/deposits_list.html`
- Modify: `ProjectYK_System/app/templates/base.html:122` (เพิ่มลิงก์เมนู)
- Test: `ProjectYK_System/app/tests/test_deposits.py`

**Interfaces:**
- Consumes: `models.DepositAudit` (Task 1), `Employee.deposit_balance/target/home_site_code/full_name`
- Produces: route `GET /deposits?site=` → render `deposits_list.html` ด้วย ctx keys: `rows` (list ของ dict `{emp, remaining, pct}`), `site`, `summary` (`{count, total_balance, total_remaining}`), `site_codes`

- [ ] **Step 1: Write the failing tests**

เพิ่มใน `tests/test_deposits.py`:

```python
@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # มีเงินประกัน: 2 LCB + 1 BIGC
        s.add(Employee(id=10, code="D10", full_name="เอ", home_site_code="LCB",
                       status="active", deposit_balance=3000, deposit_target=10000))
        s.add(Employee(id=11, code="D11", full_name="บี", home_site_code="LCB",
                       status="active", deposit_balance=10000, deposit_target=10000))
        s.add(Employee(id=12, code="D12", full_name="ซี", home_site_code="BIGC",
                       status="active", deposit_balance=5000, deposit_target=10000))
        # ไม่มีเงินประกัน (target==0) → ต้องไม่โผล่
        s.add(Employee(id=13, code="D13", full_name="ดี", home_site_code="AYU",
                       status="active", deposit_balance=0, deposit_target=0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_deposits_page_lists_only_those_with_target(client):
    r = client.get("/deposits", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "เอ" in b and "บี" in b and "ซี" in b
    assert "ดี" not in b            # target==0 ไม่แสดง


def test_deposits_summary_totals(client):
    r = client.get("/deposits", follow_redirects=True)
    b = r.text
    # 3 คนมีเงินประกัน, รวมสะสม 18,000, ยังขาดรวม = (7000+0+5000)=12,000
    assert "18,000" in b
    assert "12,000" in b


def test_deposits_filter_by_site(client):
    r = client.get("/deposits?site=LCB", follow_redirects=True)
    b = r.text
    assert "เอ" in b and "บี" in b
    assert "ซี" not in b            # BIGC ถูกกรองออก
```

- [ ] **Step 2: Run to verify fail**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -k "deposits_page or summary or filter_by_site" -v`
Expected: FAIL — 404 (route ยังไม่มี) / TemplateNotFound

- [ ] **Step 3: เพิ่ม route**

ใน `main.py` หลัง `employees_list` (หลังบรรทัด ~838):

```python
@app.get("/deposits", response_class=HTMLResponse)
def deposits_list(request: Request, site: str = ""):
    with Session(engine) as s:
        stmt = select(Employee).where(Employee.deposit_target > 0)
        if site:
            stmt = stmt.where(Employee.home_site_code == site)
        stmt = stmt.order_by(Employee.home_site_code, Employee.full_name)
        emps = s.exec(stmt).all()
    rows = []
    total_balance = 0.0
    total_remaining = 0.0
    for e in emps:
        bal = e.deposit_balance or 0.0
        tgt = e.deposit_target or 0.0
        remaining = max(0.0, tgt - bal)
        pct = min(100, round(bal / tgt * 100)) if tgt > 0 else 0
        rows.append({"emp": e, "remaining": remaining, "pct": pct})
        total_balance += bal
        total_remaining += remaining
    summary = {"count": len(rows), "total_balance": total_balance,
               "total_remaining": total_remaining}
    ctx = base_context(request)
    ctx.update({"rows": rows, "site": site, "summary": summary,
                "site_codes": models.SITE_CODES})
    return templates.TemplateResponse("deposits_list.html", ctx)
```

- [ ] **Step 4: สร้าง template**

`templates/deposits_list.html`:

```html
{% extends "base.html" %}
{% block content %}
<div class="max-w-5xl mx-auto p-4">
  <h1 class="text-xl font-bold mb-3">เงินประกันตน (รวม)</h1>

  <div class="grid grid-cols-3 gap-3 mb-4">
    <div class="bg-white rounded-lg border p-4">
      <div class="text-xs text-slate-500">จำนวนคนมีเงินประกัน</div>
      <div class="text-2xl font-bold">{{ summary.count }}</div>
    </div>
    <div class="bg-white rounded-lg border p-4">
      <div class="text-xs text-slate-500">ยอดสะสมรวม</div>
      <div class="text-2xl font-bold">{{ '{:,.0f}'.format(summary.total_balance) }}</div>
    </div>
    <div class="bg-white rounded-lg border p-4">
      <div class="text-xs text-slate-500">ยังขาดอีก (ครบเพดานทุกคน)</div>
      <div class="text-2xl font-bold">{{ '{:,.0f}'.format(summary.total_remaining) }}</div>
    </div>
  </div>

  <div class="mb-3 flex gap-1 text-sm">
    <a href="/deposits" class="px-3 py-1 rounded border {{ 'bg-slate-800 text-white' if not site else 'bg-white' }}">ทั้งหมด</a>
    {% for sc in site_codes %}
    <a href="/deposits?site={{ sc }}" class="px-3 py-1 rounded border {{ 'bg-slate-800 text-white' if site==sc else 'bg-white' }}">{{ sc }}</a>
    {% endfor %}
  </div>

  <div class="bg-white rounded-lg border overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-slate-100 text-left">
        <tr>
          <th class="px-3 py-2">ชื่อ</th>
          <th class="px-3 py-2">ไซต์</th>
          <th class="px-3 py-2 text-right">สะสมแล้ว</th>
          <th class="px-3 py-2 text-right">เพดาน</th>
          <th class="px-3 py-2 text-right">เหลืออีก</th>
          <th class="px-3 py-2">สถานะ</th>
          <th class="px-3 py-2"></th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
        {% include "deposits_row.html" %}
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: เพิ่มลิงก์เมนู**

`base.html` หลังบรรทัด 122 (ในเมนู "เงิน", หลังลิงก์ CFO):

```html
            <a href="/deposits" class="block px-4 py-2 hover:bg-slate-100">🔒 เงินประกันตน</a>
```

- [ ] **Step 6: สร้าง row partial (placeholder ปุ่มแก้ — เติม edit ใน Task 3)**

`templates/deposits_row.html`:

```html
<tr id="dep-row-{{ r.emp.id }}">
  <td class="px-3 py-2">
    <a href="/deposits/{{ r.emp.id }}/history" class="text-blue-600 hover:underline"
       hx-get="/deposits/{{ r.emp.id }}/history" hx-target="#dep-history" hx-swap="innerHTML">
      {{ r.emp.full_name }}</a>
  </td>
  <td class="px-3 py-2">{{ r.emp.home_site_code }}</td>
  <td class="px-3 py-2 text-right">{{ '{:,.0f}'.format(r.emp.deposit_balance or 0) }}</td>
  <td class="px-3 py-2 text-right">{{ '{:,.0f}'.format(r.emp.deposit_target or 0) }}</td>
  <td class="px-3 py-2 text-right">
    {% if r.remaining <= 0 %}<span class="text-green-600">✓ ครบ</span>
    {% else %}{{ '{:,.0f}'.format(r.remaining) }}{% endif %}
  </td>
  <td class="px-3 py-2">
    <div class="w-24 bg-slate-200 rounded h-2 inline-block align-middle">
      <div class="bg-blue-500 h-2 rounded" style="width: {{ r.pct }}%"></div>
    </div>
    <span class="text-xs text-slate-500 ml-1">{{ r.pct }}%</span>
  </td>
  <td class="px-3 py-2 text-right">
    <button class="text-slate-500 hover:text-blue-600"
            hx-get="/deposits/{{ r.emp.id }}/edit" hx-target="#dep-row-{{ r.emp.id }}"
            hx-swap="outerHTML">✏️</button>
  </td>
</tr>
```

เพิ่ม container ประวัติใต้ตารางใน `deposits_list.html` (ก่อน `{% endblock %}`):
```html
  <div id="dep-history" class="mt-4"></div>
```

- [ ] **Step 7: Run to verify pass**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -k "deposits_page or summary or filter_by_site" -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/deposits_list.html ProjectYK_System/app/templates/deposits_row.html ProjectYK_System/app/templates/base.html ProjectYK_System/app/tests/test_deposits.py
git commit -m "feat(deposits): GET /deposits ตารางรวม + summary + กรองไซต์ + เมนู"
```

---

### Task 3: แก้ยอด (`GET/POST /deposits/{id}/edit`) + audit

**Files:**
- Modify: `ProjectYK_System/app/main.py` (เพิ่ม 2 routes หลัง `deposits_list`)
- Create: `ProjectYK_System/app/templates/deposits_edit_row.html`
- Test: `ProjectYK_System/app/tests/test_deposits.py`

**Interfaces:**
- Consumes: route `GET /deposits` + `deposits_row.html` (Task 2), `models.DepositAudit` (Task 1)
- Produces: `GET /deposits/{emp_id}/edit` → คืน `deposits_edit_row.html` (แถวโหมดแก้ไข); `POST /deposits/{emp_id}/edit` (form: `deposit_balance`, `deposit_target`, `reason`) → อัปเดต + INSERT audit เฉพาะ field ที่เปลี่ยน, คืน `deposits_row.html` (แถวปกติ refresh แล้ว)

- [ ] **Step 1: Write the failing tests**

เพิ่มใน `tests/test_deposits.py`:

```python
def test_edit_updates_balance_and_writes_audit(client):
    r = client.post("/deposits/10/edit",
                    data={"deposit_balance": "4000", "deposit_target": "10000",
                          "reason": "หักเพิ่ม มิ.ย."})
    assert r.status_code == 200
    with Session(engine) as s:
        e = s.get(Employee, 10)
        assert e.deposit_balance == 4000
        audits = s.exec(select(DepositAudit).where(DepositAudit.employee_id == 10)).all()
        assert len(audits) == 1
        assert audits[0].field_name == "deposit_balance"
        assert audits[0].old_value == "3000.0"
        assert audits[0].new_value == "4000.0"
        assert audits[0].changed_by == "yk1"
        assert audits[0].reason == "หักเพิ่ม มิ.ย."


def test_edit_no_change_writes_no_audit(client):
    # ส่งค่าเดิม (เอ: balance 3000, target 10000) → ไม่มี audit
    r = client.post("/deposits/10/edit",
                    data={"deposit_balance": "3000", "deposit_target": "10000", "reason": ""})
    assert r.status_code == 200
    with Session(engine) as s:
        audits = s.exec(select(DepositAudit).where(DepositAudit.employee_id == 10)).all()
        assert len(audits) == 0


def test_edit_negative_rejected(client):
    r = client.post("/deposits/10/edit",
                    data={"deposit_balance": "-500", "deposit_target": "10000", "reason": ""})
    assert r.status_code == 400
    with Session(engine) as s:
        e = s.get(Employee, 10)
        assert e.deposit_balance == 3000      # ไม่เปลี่ยน
        audits = s.exec(select(DepositAudit).where(DepositAudit.employee_id == 10)).all()
        assert len(audits) == 0
```

- [ ] **Step 2: Run to verify fail**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -k "edit_" -v`
Expected: FAIL — 404 / 405 (route ยังไม่มี)

- [ ] **Step 3: เพิ่ม routes**

ใน `main.py` หลัง `deposits_list`:

```python
def _deposit_row_ctx(request: Request, e: "Employee") -> dict:
    bal = e.deposit_balance or 0.0
    tgt = e.deposit_target or 0.0
    remaining = max(0.0, tgt - bal)
    pct = min(100, round(bal / tgt * 100)) if tgt > 0 else 0
    ctx = base_context(request)
    ctx.update({"r": {"emp": e, "remaining": remaining, "pct": pct}})
    return ctx


@app.get("/deposits/{emp_id}/edit", response_class=HTMLResponse)
def deposits_edit_form(emp_id: int, request: Request):
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if not e:
            raise HTTPException(404)
    ctx = _deposit_row_ctx(request, e)
    return templates.TemplateResponse("deposits_edit_row.html", ctx)


@app.post("/deposits/{emp_id}/edit", response_class=HTMLResponse)
def deposits_edit_submit(
    emp_id: int, request: Request,
    deposit_balance: str = Form("0"),
    deposit_target: str = Form("0"),
    reason: str = Form(""),
):
    new_bal = _parse_float(deposit_balance)
    new_tgt = _parse_float(deposit_target)
    if new_bal < 0 or new_tgt < 0:
        return HTMLResponse("ยอดต้องไม่ติดลบ", status_code=400)
    _u = current_user(request)
    changed_by = (_u.username if _u else "") or "?"
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if not e:
            raise HTTPException(404)
        for field_name, new_val in (("deposit_balance", new_bal),
                                    ("deposit_target", new_tgt)):
            old_val = getattr(e, field_name) or 0.0
            if old_val != new_val:
                s.add(models.DepositAudit(
                    employee_id=emp_id, changed_by=changed_by, field_name=field_name,
                    old_value=str(old_val), new_value=str(new_val), reason=reason.strip()))
                setattr(e, field_name, new_val)
        s.add(e)
        s.commit()
        s.refresh(e)
        ctx = _deposit_row_ctx(request, e)
    return templates.TemplateResponse("deposits_row.html", ctx)
```

- [ ] **Step 4: สร้าง edit-row template**

`templates/deposits_edit_row.html`:

```html
<tr id="dep-row-{{ r.emp.id }}" class="bg-yellow-50">
  <td class="px-3 py-2">{{ r.emp.full_name }}</td>
  <td class="px-3 py-2">{{ r.emp.home_site_code }}</td>
  <td class="px-3 py-2" colspan="4">
    <form hx-post="/deposits/{{ r.emp.id }}/edit" hx-target="#dep-row-{{ r.emp.id }}"
          hx-swap="outerHTML" class="flex flex-wrap gap-2 items-center">
      <label class="text-xs">สะสมแล้ว
        <input type="number" step="0.01" name="deposit_balance"
               value="{{ '%g'|format(r.emp.deposit_balance or 0) }}"
               class="border rounded px-2 py-1 w-28" /></label>
      <label class="text-xs">เพดาน
        <input type="number" step="0.01" name="deposit_target"
               value="{{ '%g'|format(r.emp.deposit_target or 0) }}"
               class="border rounded px-2 py-1 w-28" /></label>
      <input type="text" name="reason" placeholder="เหตุผล (ไม่บังคับ)"
             class="border rounded px-2 py-1 flex-grow min-w-[120px]" />
      <button type="submit" class="bg-blue-600 text-white rounded px-3 py-1 text-sm">บันทึก</button>
      <button type="button" class="text-slate-500 text-sm"
              hx-get="/deposits/{{ r.emp.id }}/edit" hx-target="#dep-row-{{ r.emp.id }}"
              hx-swap="outerHTML"
              onclick="this.closest('tr').querySelector('form').reset()">ยกเลิก</button>
    </form>
  </td>
  <td></td>
</tr>
```

หมายเหตุ: ปุ่ม "ยกเลิก" reload แถวแก้ไขใหม่ (ค่ากลับเป็นจาก DB) — เพียงพอสำหรับ UX นี้; ไม่ทำ revert-to-readonly แยกเพื่อความง่าย (YAGNI).

- [ ] **Step 5: Run to verify pass**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -k "edit_" -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/deposits_edit_row.html ProjectYK_System/app/tests/test_deposits.py
git commit -m "feat(deposits): แก้ยอด inline + audit log (ค่าไม่เปลี่ยน=ไม่ log, ติดลบ=reject)"
```

---

### Task 4: ประวัติรายคน (`GET /deposits/{id}/history`) + เตือนข้อจำกัด

**Files:**
- Modify: `ProjectYK_System/app/main.py` (เพิ่ม route)
- Create: `ProjectYK_System/app/templates/deposits_history.html`
- Test: `ProjectYK_System/app/tests/test_deposits.py`

**Interfaces:**
- Consumes: route `GET /deposits` (Task 2), `PayRunItem.deposit_install`, `PayRun.site_code/pay_cycle_tag`, `models.DepositAudit` (Task 1)
- Produces: `GET /deposits/{emp_id}/history` → คืน `deposits_history.html` ด้วย ctx: `emp`, `hist` (list `{site, tag, amount}`), `hist_total`, `carried` (balance − hist_total), `edit_log` (list DepositAudit เรียงใหม่→เก่า)

- [ ] **Step 1: Write the failing tests**

เพิ่มใน `tests/test_deposits.py` — fixture แยกที่มี payrun + payrunitem:

```python
@pytest.fixture()
def client_hist():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # บี: balance 10000 แต่ระบบหักจริงแค่ 2 รอบ × 1000 = 2000 → carried 8000 (ลอกยอด)
        s.add(Employee(id=11, code="D11", full_name="บี", home_site_code="LCB",
                       status="active", deposit_balance=10000, deposit_target=10000))
        s.add(PayRun(id=1, site_code="LCB", pay_cycle_tag="2026-05",
                     period_start=date(2026,4,16), period_end=date(2026,5,15), status="final"))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026,5,16), period_end=date(2026,6,15), status="draft"))
        s.add(PayRunItem(pay_run_id=1, employee_id=11, deposit_install=1000))
        s.add(PayRunItem(pay_run_id=2, employee_id=11, deposit_install=1000))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_history_shows_deductions_and_carried_diff(client_hist):
    r = client_hist.get("/deposits/11/history", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "2026-05" in b and "2026-06" in b      # 2 รอบที่หักจริง
    # carried = 10000 - 2000 = 8000 → โชว์ส่วนต่าง "ยอดยกมา"
    assert "8,000" in b
    assert "ยอดยกมา" in b or "ไม่ได้หักผ่านระบบ" in b
```

- [ ] **Step 2: Run to verify fail**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -k history -v`
Expected: FAIL — 404 / TemplateNotFound

- [ ] **Step 3: เพิ่ม route**

ใน `main.py` หลัง `deposits_edit_submit`:

```python
@app.get("/deposits/{emp_id}/history", response_class=HTMLResponse)
def deposits_history(emp_id: int, request: Request):
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if not e:
            raise HTTPException(404)
        items = s.exec(
            select(PayRunItem, PayRun)
            .join(PayRun, PayRun.id == PayRunItem.pay_run_id)
            .where(PayRunItem.employee_id == emp_id, PayRunItem.deposit_install > 0)
            .order_by(PayRun.period_start)
        ).all()
        hist = [{"site": pr.site_code, "tag": pr.pay_cycle_tag,
                 "amount": pi.deposit_install} for pi, pr in items]
        hist_total = sum(h["amount"] for h in hist)
        carried = (e.deposit_balance or 0.0) - hist_total
        edit_log = s.exec(
            select(models.DepositAudit)
            .where(models.DepositAudit.employee_id == emp_id)
            .order_by(models.DepositAudit.changed_at.desc())
        ).all()
    ctx = base_context(request)
    ctx.update({"emp": e, "hist": hist, "hist_total": hist_total,
                "carried": carried, "edit_log": edit_log})
    return templates.TemplateResponse("deposits_history.html", ctx)
```

- [ ] **Step 4: สร้าง template**

`templates/deposits_history.html`:

```html
<div class="bg-white rounded-lg border p-4">
  <div class="flex justify-between items-center mb-2">
    <h2 class="font-bold">ประวัติเงินประกันตน — {{ emp.full_name }}</h2>
    <button class="text-slate-400 hover:text-slate-700" onclick="document.getElementById('dep-history').innerHTML=''">✕</button>
  </div>

  <table class="w-full text-sm mb-3">
    <thead class="bg-slate-100 text-left">
      <tr><th class="px-2 py-1">ไซต์</th><th class="px-2 py-1">รอบ</th><th class="px-2 py-1 text-right">หัก</th></tr>
    </thead>
    <tbody>
      {% for h in hist %}
      <tr><td class="px-2 py-1">{{ h.site }}</td><td class="px-2 py-1">{{ h.tag }}</td>
          <td class="px-2 py-1 text-right">{{ '{:,.0f}'.format(h.amount) }}</td></tr>
      {% else %}
      <tr><td colspan="3" class="px-2 py-2 text-slate-500">ไม่มีรายการหักผ่านระบบ</td></tr>
      {% endfor %}
    </tbody>
    <tfoot class="border-t font-semibold">
      <tr><td colspan="2" class="px-2 py-1">รวมหักผ่านระบบ</td>
          <td class="px-2 py-1 text-right">{{ '{:,.0f}'.format(hist_total) }}</td></tr>
    </tfoot>
  </table>

  {% if carried > 0.5 %}
  <div class="bg-amber-50 border border-amber-200 rounded p-2 text-sm text-amber-800">
    ⚠️ ยอดยกมา/ตั้งค่า (ไม่ได้หักผ่านระบบ): <b>{{ '{:,.0f}'.format(carried) }}</b> บาท
    — รอบที่ลอกยอดมาจะไม่มีรายการหักแยก
  </div>
  {% else %}
  <div class="text-sm text-green-700">ประวัติการหักครบตามยอดสะสม</div>
  {% endif %}

  {% if edit_log %}
  <h3 class="font-semibold mt-3 mb-1 text-sm">ประวัติการแก้ยอด</h3>
  <table class="w-full text-xs">
    <tbody>
      {% for a in edit_log %}
      <tr class="border-b">
        <td class="px-2 py-1">{{ a.changed_at | dmy_hm }}</td>
        <td class="px-2 py-1">{{ a.changed_by }}</td>
        <td class="px-2 py-1">{{ a.field_name }}: {{ a.old_value }} → {{ a.new_value }}</td>
        <td class="px-2 py-1 text-slate-500">{{ a.reason }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}
</div>
```

- [ ] **Step 5: Run to verify pass**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -k history -v`
Expected: PASS

- [ ] **Step 6: Run ALL deposit tests + full suite (regression)**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_deposits.py -v`
Expected: PASS (all)

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest -q`
Expected: ทุก test เดิมยังผ่าน (ไม่มี regression)

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/deposits_history.html ProjectYK_System/app/tests/test_deposits.py
git commit -m "feat(deposits): ประวัติการหักรายคน + เตือนยอดยกมา + ประวัติการแก้"
```

---

## Self-Review

**Spec coverage:**
- ✅ Section 1 (summary + ตารางหลัก + กรองไซต์) → Task 2
- ✅ Section 2 แก้ยอด + audit → Task 3; ประวัติรายคน + เตือน → Task 4
- ✅ Section 3 DepositAudit model + schema 28 → Task 1; routes/template/menu → Tasks 2-4
- ✅ Testing (7 เคสในสเปก) → ครอบ: lists-only-target(2), summary(2), filter(2), edit+audit(3), no-change(3), negative(3), history-carried(4)
- ✅ Money safety: ไม่แตะ payroll engine; regression run เต็ม suite ใน Task 4 Step 6

**Placeholder scan:** ไม่มี TBD/TODO; ทุก step มีโค้ดจริง

**Type consistency:** `_deposit_row_ctx` คืน key `r` ใช้ทั้งใน `deposits_row.html`/`deposits_edit_row.html`; `DepositAudit` field names ตรงกันทุก task; `_parse_float` มีอยู่แล้วใน main.py (ใช้ที่ employee form), `current_user` import แล้ว (main.py:585)

## Deploy (หลัง 4 tasks ผ่าน — งาน UI, deploy ในรอบเดียว)

1. Merge `feat/deposits-overview-page` → `main`
2. Restart local app, smoke test `/deposits` ขึ้นจริง
3. Deploy ขึ้น server ผ่าน Tailscale (backup app.db → stop → scp DB ไม่ต้อง (ไม่มี data change), scp code → bump schema auto-migrate → restart). **DepositAudit เป็นตารางใหม่ create_all จะสร้างเอง — ไม่ต้อง migrate ข้อมูล.**
4. Verify public `/deposits` 200 + จำนวนคนตรง snapshot
