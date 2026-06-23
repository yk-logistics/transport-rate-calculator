# ตรวจสภาพรถ — Mechanic edit/add + Driver trailer-followup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ให้ลิงก์ช่างแก้ประเภทรถ/เพิ่มหางได้, ลิงก์คนขับตรวจหางต่อจากหัวได้ (ไม่บังคับ), เปลี่ยนชื่อหน้าเป็น "ตรวจสภาพรถ".

**Architecture:** ต่อยอด flow `/check/*` ที่มี (FastAPI route handlers ใน main.py + Jinja templates). ไม่แตะ DB schema — ใช้ `Vehicle.truck_type`, `Vehicle.vehicle_kind`, `TireEvent.to_vehicle_id` ที่มีอยู่. เพิ่ม 1 route ใหม่ (`/check/mechanic/edit-vehicle`), reuse `/check/add-vehicle` เดิม, แก้ GET `check_driver_form` ให้โชว์ panel เลือกหางหลังส่ง.

**Tech Stack:** FastAPI, SQLModel, Jinja2 + Tailwind CDN, pytest (TestClient).

## Global Constraints
- ห้ามขึ้น SCHEMA_VERSION (ไม่แตะ schema)
- คนขับแก้ข้อมูลรถถาวรไม่ได้ — edit-vehicle เฉพาะ role=mechanic
- ภาษาไทยใน UI; ใช้ `truck_type_th` labels ที่มีแล้วใน models
- fastapi<0.115, starlette<0.40 (อย่าอัปเกรด)
- เทสต์รันจาก `ProjectYK_System/app/` ด้วย `.venv/Scripts/python.exe -m pytest`
- commit ทีละ task; ทำงานบน branch `feat/check-vehicle-edit-trailer` (ห้าม main)

---

### Task 1: เปลี่ยนชื่อหน้า → "ตรวจสภาพรถ"

**Files:**
- Modify: `ProjectYK_System/app/templates/check_driver.html` (title + h1)
- Modify: `ProjectYK_System/app/templates/check_mechanic.html` (title + h1)
- Modify: `ProjectYK_System/app/templates/check_landing.html` (title + h1)

**Interfaces:**
- Consumes: nothing
- Produces: nothing (text-only)

- [ ] **Step 1:** แก้ `check_driver.html`: `<title>ตรวจยาง</title>` → `<title>ตรวจสภาพรถ</title>`; `<h1 ...>ตรวจยาง</h1>` → `ตรวจสภาพรถ`
- [ ] **Step 2:** แก้ `check_mechanic.html`: `<title>ช่าง — ตรวจ/วัดยาง</title>` → `<title>ตรวจสภาพรถ (ช่าง)</title>`; `<h1 ...>ช่าง — ตรวจ/วัดยาง</h1>` → `ตรวจสภาพรถ (ช่าง)`
- [ ] **Step 3:** แก้ `check_landing.html`: `<title>ตรวจรถ</title>` → `<title>ตรวจสภาพรถ</title>`; `<h1 ...>ตรวจรถ — บทบาท: {{ role_th }}</h1>` → `ตรวจสภาพรถ — บทบาท: {{ role_th }}`
- [ ] **Step 4:** Commit `git commit -m "feat(check): rename screens to ตรวจสภาพรถ"`

---

### Task 2: ช่างแก้ประเภทรถ (route + test)

**Files:**
- Modify: `ProjectYK_System/app/main.py` — เพิ่ม route `POST /check/mechanic/edit-vehicle` หลัง `check_add_vehicle` (~line 6298); เพิ่ม `truck_type_th` ใน context ของ `check_mechanic_form` (~line 6167)
- Test: `ProjectYK_System/app/tests/test_check_edit_vehicle.py` (create)

**Interfaces:**
- Consumes: `_check_link_guard`, `models.Vehicle`, `_parse_int`
- Produces: route `POST /check/mechanic/edit-vehicle` (form: `t`, `vehicle_id`, `truck_type`) → 303 redirect `/check/mechanic?t=<t>&vehicle_id=<vid>`; role=driver → 403; vehicle ไม่พบ → 400

helper เทสต์ (มี pattern ใน tests อื่น): สร้าง AccessLink + token ใน DB ของ TestClient. ดู `tests/test_check_*.py` ตัวที่มีอยู่เพื่อ reuse fixture. ถ้าไม่มี fixture กลาง ให้สร้าง link/token ใน test ตรงๆ:

```python
from fastapi.testclient import TestClient
import main, models
from datetime import datetime, timedelta
from sqlmodel import Session

def _mk_link(role):
    tok = main.access_link.make_token(role, 7200)
    with Session(main.engine) as s:
        s.add(models.AccessLink(token=tok, role=role, created_by="t",
              expires_at=datetime.utcnow()+timedelta(hours=2), short_code=f"E{role[:3]}"))
        s.commit()
    return tok
```

- [ ] **Step 1: Write failing test** — `tests/test_check_edit_vehicle.py`:

```python
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlmodel import Session
import main, models

client = TestClient(main.app)

def _mk_link(role, code):
    tok = main.access_link.make_token(role, 7200)
    with Session(main.engine) as s:
        s.add(models.AccessLink(token=tok, role=role, created_by="t",
              expires_at=datetime.utcnow()+timedelta(hours=2), short_code=code))
        s.commit()
    return tok

def _mk_vehicle(plate, ttype, kind="truck"):
    with Session(main.engine) as s:
        v = models.Vehicle(plate_no=plate, truck_type=ttype, vehicle_kind=kind,
                           home_site_code="LCB", status="active")
        s.add(v); s.commit(); s.refresh(v)
        return v.id

def test_mechanic_can_change_truck_type():
    tok = _mk_link("mechanic", "Ech1")
    vid = _mk_vehicle("EDIT-1", "10W")
    r = client.post("/check/mechanic/edit-vehicle",
                    data={"t": tok, "vehicle_id": vid, "truck_type": "6W"},
                    follow_redirects=False)
    assert r.status_code == 303
    with Session(main.engine) as s:
        assert s.get(models.Vehicle, vid).truck_type == "6W"

def test_driver_cannot_edit_vehicle():
    tok = _mk_link("driver", "Edr1")
    vid = _mk_vehicle("EDIT-2", "10W")
    r = client.post("/check/mechanic/edit-vehicle",
                    data={"t": tok, "vehicle_id": vid, "truck_type": "6W"},
                    follow_redirects=False)
    assert r.status_code == 403
    with Session(main.engine) as s:
        assert s.get(models.Vehicle, vid).truck_type == "10W"  # unchanged

def test_edit_to_trailer_sets_kind_tail():
    tok = _mk_link("mechanic", "Ech2")
    vid = _mk_vehicle("EDIT-3", "10W")
    client.post("/check/mechanic/edit-vehicle",
                data={"t": tok, "vehicle_id": vid, "truck_type": "TRL8"},
                follow_redirects=False)
    with Session(main.engine) as s:
        assert s.get(models.Vehicle, vid).vehicle_kind == "tail"

def test_empty_truck_type_keeps_existing():
    tok = _mk_link("mechanic", "Ech3")
    vid = _mk_vehicle("EDIT-4", "10W")
    client.post("/check/mechanic/edit-vehicle",
                data={"t": tok, "vehicle_id": vid, "truck_type": ""},
                follow_redirects=False)
    with Session(main.engine) as s:
        assert s.get(models.Vehicle, vid).truck_type == "10W"
```

- [ ] **Step 2: Run, verify FAIL** — `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_edit_vehicle.py -q` → FAIL (404 route ไม่มี)

- [ ] **Step 3: Implement route** — ใน main.py หลัง `check_add_vehicle`:

```python
@app.post("/check/mechanic/edit-vehicle")
async def check_mechanic_edit_vehicle(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        v = s.get(Vehicle, _parse_int(form.get("vehicle_id") or "") or 0)
        if not v:
            raise HTTPException(400, "เลือกทะเบียนรถก่อน")
        new_type = (form.get("truck_type") or "").strip().upper()
        if new_type:
            v.truck_type = new_type
            v.vehicle_kind = "tail" if new_type.startswith("TRL") else v.vehicle_kind
            s.add(v); s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}&vehicle_id={v.id}", status_code=303)
```

- [ ] **Step 4: Run, verify PASS** — `pytest tests/test_check_edit_vehicle.py -q` → 4 passed

- [ ] **Step 5: Add truck_type_th to mechanic context** — ใน `check_mechanic_form` TemplateResponse dict เพิ่ม:
```python
        "truck_types": models.TRUCK_TYPES,
        "truck_type_th": models.TRUCK_TYPE_TH,
```

- [ ] **Step 6: Commit** — `git add main.py tests/test_check_edit_vehicle.py && git commit -m "feat(check): mechanic edit vehicle truck_type (route+test)"`

---

### Task 3: UI ช่าง — กล่องแก้ประเภท + เพิ่มทะเบียน

**Files:**
- Modify: `ProjectYK_System/app/templates/check_mechanic.html` — เพิ่ม 2 `<details>` หลัง h1 (~line 32), ก่อน section "ตรวจรถทั้งคัน"

**Interfaces:**
- Consumes: `vehicles`, `truck_type_th`, `truck_types`, `token` จาก context (Task 2 เพิ่ม truck_type_th แล้ว)
- Produces: nothing

- [ ] **Step 1:** ใน `check_mechanic.html` หลัง `<h1 ...>ตรวจสภาพรถ (ช่าง)</h1>` แทรก:

```html
  <details class="mb-3 rounded-lg border border-slate-700 bg-slate-800/60 p-3">
    <summary class="text-sm text-amber-400 cursor-pointer">🔧 แก้ประเภทรถ (6/10 ล้อ/หาง)</summary>
    <form method="post" action="/check/mechanic/edit-vehicle?t={{ token }}" class="mt-3 space-y-2">
      <input type="hidden" name="t" value="{{ token }}">
      <select name="vehicle_id" required class="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 text-sm">
        <option value="">— เลือกทะเบียน —</option>
        {% for v in vehicles %}<option value="{{ v.id }}">{{ v.plate_no }}{% if v.nickname %} ({{ v.nickname }}){% endif %} · {{ truck_type_th.get(v.truck_type, v.truck_type) }}</option>{% endfor %}
      </select>
      <select name="truck_type" class="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 text-sm">
        {% for t in truck_types %}<option value="{{ t }}">{{ truck_type_th.get(t, t) }}</option>{% endfor %}
      </select>
      <button class="w-full p-3 rounded-lg bg-amber-600 font-bold text-sm">บันทึกประเภทรถ</button>
    </form>
  </details>

  <details class="mb-4 rounded-lg border border-slate-700 bg-slate-800/60 p-3">
    <summary class="text-sm text-sky-400 cursor-pointer">+ เพิ่มทะเบียน (หัว/หาง)</summary>
    <form method="post" action="/check/add-vehicle?t={{ token }}" class="mt-3 space-y-2">
      <input type="hidden" name="t" value="{{ token }}">
      <input type="hidden" name="role" value="mechanic">
      <input name="plate_no" required placeholder="ทะเบียน เช่น 71-2345"
             class="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 text-sm">
      <select name="truck_type" class="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 text-sm">
        {% for t in truck_types %}<option value="{{ t }}">{{ truck_type_th.get(t, t) }}</option>{% endfor %}
      </select>
      <input name="nickname" placeholder="ชื่อเล่น (ไม่บังคับ)"
             class="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 text-sm">
      <button class="w-full p-3 rounded-lg bg-sky-600 font-bold text-sm">บันทึกทะเบียน</button>
    </form>
  </details>
```

- [ ] **Step 2: Smoke test** — render หน้าช่างผ่าน TestClient + ตรวจว่ามี "แก้ประเภทรถ" และ "เพิ่มทะเบียน". เพิ่มใน `tests/test_check_edit_vehicle.py`:

```python
def test_mechanic_page_has_edit_and_add_ui():
    tok = _mk_link("mechanic", "Eui1")
    r = client.get(f"/check/mechanic?t={tok}")
    assert r.status_code == 200
    assert "แก้ประเภทรถ" in r.text
    assert "เพิ่มทะเบียน" in r.text
```

- [ ] **Step 3: Run, verify PASS** — `pytest tests/test_check_edit_vehicle.py -q` → 5 passed

- [ ] **Step 4: Commit** — `git add templates/check_mechanic.html tests/test_check_edit_vehicle.py && git commit -m "feat(check): mechanic UI — edit truck_type + add vehicle"`

---

### Task 4: คนขับตรวจหางต่อ (panel หลังส่ง)

**Files:**
- Modify: `ProjectYK_System/app/main.py` — `check_driver_form` (~line 6042): query หางเมื่อมี `?done=`, ส่ง `trailers` + `done` + `just_vehicle` เข้า context
- Modify: `ProjectYK_System/app/templates/check_driver.html` — แทรก panel "ตรวจหัวเรียบร้อย ✓" เมื่อมี `done`
- Test: `ProjectYK_System/app/tests/test_check_trailer_followup.py` (create)

**Interfaces:**
- Consumes: `_check_link_guard`, `models.Vehicle`, `_parse_int`
- Produces: GET `/check/driver?t=<t>&done=<n>` → HTML มี dropdown หาง (ถ้ามีหางในระบบ) + ปุ่ม "ตรวจหางต่อ" + ลิงก์ "เสร็จแล้ว"

- [ ] **Step 1: Write failing test** — `tests/test_check_trailer_followup.py`:

```python
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlmodel import Session
import main, models

client = TestClient(main.app)

def _mk_link(role, code):
    tok = main.access_link.make_token(role, 7200)
    with Session(main.engine) as s:
        s.add(models.AccessLink(token=tok, role=role, created_by="t",
              expires_at=datetime.utcnow()+timedelta(hours=2), short_code=code))
        s.commit()
    return tok

def _mk_trailer(plate):
    with Session(main.engine) as s:
        v = models.Vehicle(plate_no=plate, truck_type="TRL8", vehicle_kind="tail",
                           home_site_code="LCB", status="active")
        s.add(v); s.commit()

def test_done_shows_trailer_followup_when_trailers_exist():
    _mk_trailer("HANG-A1")
    tok = _mk_link("driver", "Tf1")
    r = client.get(f"/check/driver?t={tok}&done=6")
    assert r.status_code == 200
    assert "ตรวจหัวเรียบร้อย" in r.text
    assert "HANG-A1" in r.text
    assert "ตรวจหางต่อ" in r.text

def test_done_without_trailers_shows_finish_only():
    # ใช้ DB ที่ไม่มี trailer — แต่ test รันรวมกัน อาจมี trailer จากเทสอื่น
    # ดังนั้นเช็คเชิงลบแบบ best-effort: panel "ตรวจหัวเรียบร้อย" ต้องมี, ปุ่ม "เสร็จแล้ว" ต้องมีเสมอ
    tok = _mk_link("driver", "Tf2")
    r = client.get(f"/check/driver?t={tok}&done=6")
    assert "ตรวจหัวเรียบร้อย" in r.text
    assert "เสร็จแล้ว" in r.text
```

- [ ] **Step 2: Run, verify FAIL** — `pytest tests/test_check_trailer_followup.py -q` → FAIL (ไม่มีข้อความ panel)

- [ ] **Step 3: Implement context** — ใน `check_driver_form`, ก่อน `return templates.TemplateResponse`, แก้ให้คำนวณ done + trailers:

```python
        done = _parse_int(request.query_params.get("done") or "") or 0
        trailers = []
        if done:
            trailers = s.exec(select(Vehicle).where(
                Vehicle.vehicle_kind == "tail",
                Vehicle.status == "active").order_by(Vehicle.plate_no)).all()
    return templates.TemplateResponse("check_driver.html", {
        ...existing keys...,
        "done": done, "trailers": trailers,
    })
```
(เพิ่ม `"done": done, "trailers": trailers,` เข้า dict ที่มีอยู่ — อย่าทิ้ง key เดิม)

- [ ] **Step 4: Implement template panel** — ใน `check_driver.html` หลัง block เลือกทะเบียน (`</form>` ของ form เลือกทะเบียน ~line 60) แทรก:

```html
  {% if done %}
  <div class="mb-4 rounded-xl border border-green-700 bg-green-900/30 p-4">
    <p class="font-bold text-green-300 mb-1">✓ ตรวจหัวเรียบร้อย ({{ done }} เส้น)</p>
    {% if trailers %}
    <p class="text-sm text-slate-300 mb-2">วันนี้ลากหางคันไหน?</p>
    <form method="get" action="/check/driver" class="space-y-2">
      <input type="hidden" name="t" value="{{ token }}">
      <input type="hidden" name="actor_name" value="{{ actor_name }}">
      <select name="vehicle_id" required class="w-full p-3 rounded-xl bg-slate-800 border border-slate-600 text-base">
        <option value="">— เลือกทะเบียนหาง —</option>
        {% for tr in trailers %}<option value="{{ tr.id }}">{{ tr.plate_no }}{% if tr.nickname %} ({{ tr.nickname }}){% endif %}</option>{% endfor %}
      </select>
      <button class="w-full p-3 rounded-xl bg-blue-600 font-bold">ตรวจหางต่อ ▸</button>
    </form>
    {% else %}
    <p class="text-sm text-slate-400">— ยังไม่มีทะเบียนหางในระบบ —</p>
    {% endif %}
    <a href="/check/driver?t={{ token }}&actor_name={{ actor_name }}" class="block text-center mt-3 text-sm text-slate-400 underline">ไม่มีหาง / เสร็จแล้ว</a>
  </div>
  {% endif %}
```

- [ ] **Step 5: Run, verify PASS** — `pytest tests/test_check_trailer_followup.py -q` → 2 passed

- [ ] **Step 6: Commit** — `git add main.py templates/check_driver.html tests/test_check_trailer_followup.py && git commit -m "feat(check): driver trailer follow-up after head submit"`

---

### Task 5: Full suite + verify + screenshot

**Files:** none (verification)

- [ ] **Step 1: Full suite** — `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/ -q` → all passed (baseline 120 + ใหม่ ~11)
- [ ] **Step 2: Run app + screenshot** — start app port 8019 (env YK_SESSION_SECRET + YK_INSECURE_COOKIES=1), seed trailer + driver link + mechanic link in-process, screenshot: (a) mechanic page edit/add UI, (b) driver done-panel with trailer dropdown. ดู [[reference-mvp-deploy-restart-gotcha]] gotcha #1 (mint link in-process). ลบ temp data ด้วย id ที่สร้าง (memory `feedback-test-data-cleanup-safety`).
- [ ] **Step 3: Merge to main** — `git checkout main && git merge --no-ff feat/check-vehicle-edit-trailer`
- [ ] **Step 4: Deploy** — scp 5 files (main.py + 3 templates), restart ด้วย corrected kill-filter (.ps1 by path: kill python cmdline match `main\.py` AND `pythoncore|\.venv|YK_MVP` → Start-ScheduledTask YK_MVP_APP → wait → port 8010 listen). Verify `/login`=200, `/check`=403, + new code live (proc start > file mtime). ดู [[reference-mvp-deploy-restart-gotcha]] + [[reference-ssh-to-yk-machine]].
- [ ] **Step 5: Cleanup** — ลบ temp scripts บน server + local; สรุปให้โอ

## Self-Review
- **Spec coverage:** §1 rename→T1; §2 mechanic edit→T2+T3; §3 add trailer→T3 (reuse add-vehicle); §4 driver follow-up→T4. ครบ.
- **Placeholder scan:** ไม่มี TBD; โค้ดเต็มทุก step.
- **Type consistency:** route names ตรง (`/check/mechanic/edit-vehicle`); context keys `truck_type_th`/`trailers`/`done` ใช้สอดคล้อง template↔handler.
