# Tire Check — Top View + Add-Vehicle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the driver tire-check screen into a top-view truck diagram and let drivers/mechanics add a vehicle (with wheel count) from inside the magic link, building on the merged magic-link tire feature.

**Architecture:** Add a pure layout helper (`axle_layout`) that groups position codes into axles/sides so the template can draw a top view without logic in HTML. Extend `_tire_positions_for_vehicle` to handle the 8-wheel trailer (`TRL8`). Add one public route `POST /check/add-vehicle` that creates a `Vehicle` in the existing master and bounces back into the check flow. Rewrite the driver template grid as a top view; reuse the existing per-tire bottom-sheet and submit handler unchanged.

**Tech Stack:** FastAPI + SQLModel, Jinja2 + HTMX + Tailwind (CDN), vanilla JS (no new libs), pytest + Starlette TestClient.

## Global Constraints

- Version pins (do NOT upgrade): `fastapi<0.115`, `starlette<0.40`.
- No new tables/columns — reuse the existing `Vehicle` master. No `SCHEMA_VERSION` bump.
- `/check/*` stays public (gated in-handler by signed token via `_check_link_guard`); add-vehicle works for any valid token (driver or mechanic).
- Position codes stay English in the DB; Thai labels via `tire_view.th_label` (presentation only).
- Tests live in `ProjectYK_System/app/tests/`. Run from `ProjectYK_System/app/` with the venv python. The `client` fixture builds a fresh schema + seed per test.
- `IS_SQLITE` is False under tests (conftest sets an explicit DATABASE_URL) — migration helpers are skipped under tests; this plan adds no migrations, so that's irrelevant here.
- Match existing route/style: module-level `@app.get/post`, `with Session(engine) as s:`, `_parse_int/_parse_float`, `RedirectResponse(..., status_code=303)`, `_check_link_guard(request, s)`.
- Plate uniqueness: `Vehicle.plate_no` is unique — adding an existing plate must reuse the existing row, never overwrite its `truck_type`.

## Run command (all tasks)

```bash
cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/<file> -v
```

## File Structure

- `ProjectYK_System/app/services/tire_view.py` — add `axle_layout(positions)`; pure, tested in isolation.
- `ProjectYK_System/app/main.py` — extend `_tire_positions_for_vehicle` for `TRL8`; add `POST /check/add-vehicle`; pass `axles` into `/check/driver` context.
- `ProjectYK_System/app/templates/check_driver.html` — replace vertical list with top-view diagram; add "+ add vehicle" form.
- `ProjectYK_System/app/tests/` — new test files per task.

---

### Task 1: `TRL8` recognized by `_tire_positions_for_vehicle`

**Files:**
- Modify: `ProjectYK_System/app/main.py` (`_tire_positions_for_vehicle`, ~line 6242)
- Test: `ProjectYK_System/app/tests/test_trl8_positions.py`

**Interfaces:**
- Consumes: `models.TIRE_POSITIONS_BY_KIND["TRL8"]` (already exists, 8 entries).
- Produces: a `Vehicle` with `truck_type="TRL8"` returns the 8 trailer positions.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_trl8_positions.py
from models import Vehicle
import main as appmod


def test_trl8_returns_eight_trailer_positions():
    v = Vehicle(plate_no="T-1", truck_type="TRL8", vehicle_kind="tail")
    pos = appmod._tire_positions_for_vehicle(v)
    assert len(pos) == 8
    assert pos[0] == "TRL_LO1"
    assert pos[-1] == "TRL_RO2"


def test_six_and_ten_still_work():
    assert len(appmod._tire_positions_for_vehicle(Vehicle(plate_no="a", truck_type="6W"))) == 6
    assert len(appmod._tire_positions_for_vehicle(Vehicle(plate_no="b", truck_type="10W"))) == 10
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_trl8_positions.py -v`
Expected: `test_trl8_returns_eight_trailer_positions` FAILS — current code falls through to the `"10"` branch? No: `TRL8` has no "10"/"6"/"18", so it hits the default `10W` (10 positions) → assert len==8 fails.

- [ ] **Step 3: Add the TRL8 branch (before the others)**

In `_tire_positions_for_vehicle`, add right after the `key = ...` line, before the `"18" in key` check:

```python
    if "TRL8" in key or (("TRL" in key or "TAIL" in key) and "8" in key):
        return models.TIRE_POSITIONS_BY_KIND["TRL8"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_trl8_positions.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_trl8_positions.py
git commit -m "feat(tire-check): recognize TRL8 8-wheel trailer in position resolver"
```

---

### Task 2: `axle_layout` helper for top-view drawing

**Files:**
- Modify: `ProjectYK_System/app/services/tire_view.py`
- Test: `ProjectYK_System/app/tests/test_axle_layout.py`

**Interfaces:**
- Consumes: `is_outer`, `photo_count`, `th_label` (already in tire_view).
- Produces: `axle_layout(positions: tuple) -> list[dict]`. Each dict is one axle:
  `{"tag": str, "left": [cell...], "right": [cell...]}` where a cell is
  `{"pos","label","photos","outer"}`. Front axle = `FL`/`FR` singles
  (left=[FL], right=[FR]). Rear/trailer axles group by side, outer-to-inner
  on each side. `tag` is a Thai axle caption.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_axle_layout.py
import services.tire_view as tv
import models


def test_layout_6w_three_cells_per_side_on_rear():
    axles = tv.axle_layout(models.TIRE_POSITIONS_BY_KIND["6W"])
    assert len(axles) == 2                      # front + 1 rear
    front = axles[0]
    assert [c["pos"] for c in front["left"]] == ["FL"]
    assert [c["pos"] for c in front["right"]] == ["FR"]
    rear = axles[1]
    assert [c["pos"] for c in rear["left"]] == ["RLO", "RLI"]   # outer then inner
    assert [c["pos"] for c in rear["right"]] == ["RRI", "RRO"]  # inner then outer
    # cells carry presentation data
    assert front["left"][0]["label"] == "ซ้ายหน้า"
    assert rear["left"][0]["photos"] == 2 and rear["left"][1]["photos"] == 1


def test_layout_10w_has_front_plus_two_rear():
    axles = tv.axle_layout(models.TIRE_POSITIONS_BY_KIND["10W"])
    assert len(axles) == 3


def test_layout_trl8_two_axles_four_each():
    axles = tv.axle_layout(models.TIRE_POSITIONS_BY_KIND["TRL8"])
    assert len(axles) == 2
    assert sum(len(a["left"]) + len(a["right"]) for a in axles) == 8
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_axle_layout.py -v`
Expected: FAIL — `tire_view has no attribute axle_layout`.

- [ ] **Step 3: Implement `axle_layout`**

Append to `services/tire_view.py`:

```python
def _cell(pos: str) -> dict:
    return {"pos": pos, "label": th_label(pos),
            "photos": photo_count(pos), "outer": is_outer(pos)}


def axle_layout(positions) -> list[dict]:
    """Group position codes into axles for a top-view diagram.

    Returns a list of axles, front-to-back. Each axle:
      {"tag": <thai caption>, "left": [cell...], "right": [cell...]}
    Left side ordered outer->inner; right side ordered inner->outer
    (so the diagram reads outer-edge ... spine ... outer-edge).
    """
    pos = list(positions)
    axles: list[dict] = []

    # Front steer axle (single tyre each side)
    if "FL" in pos or "FR" in pos:
        axles.append({"tag": "เพลาหน้า",
                      "left": [_cell("FL")] if "FL" in pos else [],
                      "right": [_cell("FR")] if "FR" in pos else []})

    # Rear drive axles: RL*/RR* grouped by trailing axle digit ("" , "1", "2", ...)
    rear = [p for p in pos if p.startswith(("RL", "RR"))]
    digits = []
    for p in rear:
        d = "".join(ch for ch in p if ch.isdigit())
        if d not in digits:
            digits.append(d)
    rear_tags = {1: ["เพลาหลัง"], 2: ["เพลาหลัง (ตัวหน้า)", "เพลาหลัง (ตัวหลัง)"]}
    captions = rear_tags.get(len(digits), [f"เพลาหลัง {i+1}" for i in range(len(digits))])
    for i, d in enumerate(digits):
        lout, lin = f"RLO{d}", f"RLI{d}"
        rin, rout = f"RRI{d}", f"RRO{d}"
        axles.append({
            "tag": captions[i],
            "left":  [_cell(c) for c in (lout, lin) if c in pos],
            "right": [_cell(c) for c in (rin, rout) if c in pos],
        })

    # Trailer axles: TRL_L*1/2 ... grouped by trailing digit
    trl = [p for p in pos if p.startswith("TRL_")]
    tdigits = []
    for p in trl:
        d = "".join(ch for ch in p if ch.isdigit())
        if d not in tdigits:
            tdigits.append(d)
    for i, d in enumerate(tdigits):
        lout, lin = f"TRL_LO{d}", f"TRL_LI{d}"
        rin, rout = f"TRL_RI{d}", f"TRL_RO{d}"
        tag = "หาง · เพลาหน้า" if i == 0 and len(tdigits) > 1 else (
              "หาง · เพลาหลัง" if i == 1 else "หาง")
        axles.append({
            "tag": tag,
            "left":  [_cell(c) for c in (lout, lin) if c in pos],
            "right": [_cell(c) for c in (rin, rout) if c in pos],
        })

    return axles
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_axle_layout.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/services/tire_view.py ProjectYK_System/app/tests/test_axle_layout.py
git commit -m "feat(tire-check): axle_layout helper for top-view grouping"
```

---

### Task 3: `POST /check/add-vehicle` route

**Files:**
- Modify: `ProjectYK_System/app/main.py` (add route near the other `/check/*` handlers)
- Test: `ProjectYK_System/app/tests/test_check_add_vehicle.py`

**Interfaces:**
- Consumes: `_check_link_guard`, `Vehicle`, `_gen_code` (not needed — Vehicle has no `code`), `_parse_*`.
- Produces: `POST /check/add-vehicle` creates a `Vehicle(plate_no, truck_type, vehicle_kind, nickname, status="active", notes="added via check-link")` and 303-redirects to `/check/<role>?t=<tok>&vehicle_id=<id>`. Existing plate → reuse it (no overwrite). Kind derived: `TRL8`→`tail`, else `head`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_add_vehicle.py
from datetime import datetime, timedelta
from sqlmodel import Session, select
from db_config import engine
from models import AccessLink, Vehicle
import services.access_link as al


def _link(role="driver"):
    tok = al.make_token(role, 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        s.commit()
    return tok


def test_add_vehicle_creates_and_redirects(client):
    tok = _link("driver")
    r = client.post(f"/check/add-vehicle?t={tok}",
                    data={"t": tok, "role": "driver", "plate_no": "71-5555",
                          "truck_type": "TRL8", "nickname": "หางA"},
                    follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert "/check/driver" in loc and "vehicle_id=" in loc
    with Session(engine) as s:
        v = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-5555")).first()
        assert v is not None
        assert v.truck_type == "TRL8"
        assert v.vehicle_kind == "tail"


def test_add_existing_plate_reuses_without_overwrite(client):
    tok = _link("driver")
    with Session(engine) as s:
        s.add(Vehicle(plate_no="71-6666", truck_type="10W", vehicle_kind="head"))
        s.commit()
    r = client.post(f"/check/add-vehicle?t={tok}",
                    data={"t": tok, "role": "driver", "plate_no": "71-6666",
                          "truck_type": "6W"}, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        rows = s.exec(select(Vehicle).where(Vehicle.plate_no == "71-6666")).all()
        assert len(rows) == 1
        assert rows[0].truck_type == "10W"   # unchanged


def test_add_vehicle_rejects_bad_token(client):
    r = client.post("/check/add-vehicle?t=bad",
                    data={"t": "bad", "role": "driver", "plate_no": "x", "truck_type": "6W"},
                    follow_redirects=False)
    assert r.status_code in (400, 403)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_add_vehicle.py -v`
Expected: FAIL — route 404.

- [ ] **Step 3: Implement the route**

In `main.py`, after `check_mechanic_job` (before the "Maintenance — Tires" header), add:

```python
@app.post("/check/add-vehicle")
async def check_add_vehicle(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link:
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        role = (form.get("role") or link.role or "driver").strip()
        plate = (form.get("plate_no") or "").strip()
        truck_type = (form.get("truck_type") or "").strip().upper()
        nickname = (form.get("nickname") or "").strip()
        if not plate:
            raise HTTPException(400, "กรอกทะเบียนก่อน")

        existing = s.exec(select(Vehicle).where(Vehicle.plate_no == plate)).first()
        if existing:
            vid = existing.id   # reuse, never overwrite truck_type
        else:
            kind = "tail" if truck_type.startswith("TRL") else "head"
            v = Vehicle(plate_no=plate, truck_type=truck_type or "10W",
                        vehicle_kind=kind, nickname=nickname,
                        status="active", notes="added via check-link")
            s.add(v); s.commit(); s.refresh(v)
            vid = v.id
    dest = "/check/mechanic" if role == "mechanic" else "/check/driver"
    return RedirectResponse(f"{dest}?t={form.get('t')}&vehicle_id={vid}", status_code=303)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_add_vehicle.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/tests/test_check_add_vehicle.py
git commit -m "feat(tire-check): add-vehicle from magic link (reuse existing plate)"
```

---

### Task 4: Top-view driver template + add-vehicle form

**Files:**
- Modify: `ProjectYK_System/app/main.py` (`check_driver_form` — pass `axles` + truck-type options into context)
- Modify: `ProjectYK_System/app/templates/check_driver.html` (replace list grid with top view; add "+ add vehicle" form)
- Test: `ProjectYK_System/app/tests/test_check_driver_topview.py`

**Interfaces:**
- Consumes: `tire_view.axle_layout`, `models.TIRE_POSITIONS_BY_KIND` keys for the add-vehicle type options.
- Produces: GET `/check/driver?vehicle_id=N` renders a top-view diagram (one block per axle, left/right sides) with a `cond_<pos>` select + `photo_<pos>` input per tyre; an add-vehicle form posts to `/check/add-vehicle`. The POST submit handler is unchanged (still reads `cond_<pos>` / `photo_<pos>`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_check_driver_topview.py
from datetime import datetime, timedelta
from sqlmodel import Session
from db_config import engine
from models import AccessLink, Vehicle
import services.access_link as al


def _setup():
    tok = al.make_token("driver", 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role="driver", created_by="t",
                         expires_at=datetime.utcnow() + timedelta(hours=1)))
        v = Vehicle(plate_no="71-2345", truck_type="10W", vehicle_kind="head", status="active")
        s.add(v); s.commit(); s.refresh(v)
        return tok, v.id


def test_topview_renders_axle_tags_and_all_positions(client):
    tok, vid = _setup()
    r = client.get(f"/check/driver?t={tok}&actor_name=x&vehicle_id={vid}")
    assert r.status_code == 200
    # axle captions present
    assert "เพลาหน้า" in r.text
    assert "เพลาหลัง (ตัวหลัง)" in r.text
    # all 10 cond_ inputs present
    for pos in ("FL", "FR", "RLO1", "RLI1", "RRI1", "RRO1",
                "RLO2", "RLI2", "RRI2", "RRO2"):
        assert f'name="cond_{pos}"' in r.text


def test_add_vehicle_form_present(client):
    tok, _vid = _setup()
    r = client.get(f"/check/driver?t={tok}&actor_name=x")
    assert r.status_code == 200
    assert "/check/add-vehicle" in r.text
    assert "เพิ่มทะเบียน" in r.text
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_driver_topview.py -v`
Expected: FAIL — `เพลาหลัง (ตัวหลัง)` / add-vehicle markup not in the current list template.

- [ ] **Step 3: Pass `axles` + type options into context**

In `check_driver_form`, replace the `cells = [...]` line and the `TemplateResponse` context:

```python
        positions = _tire_positions_for_vehicle(v) if v else ()
        axles = tire_view.axle_layout(positions) if positions else []
    return templates.TemplateResponse("check_driver.html", {
        "request": request, "token": request.query_params.get("t"),
        "actor_name": request.query_params.get("actor_name", ""),
        "vehicles": vehicles, "vehicle": v, "axles": axles,
        "conditions": models.TIRE_CONDITION_FLAGS,
        "weekly_items": models.VEHICLE_CHECK_ITEMS,
        "weekly_status": models.VEHICLE_CHECK_STATUS,
        "type_options": [("6W", "6 ล้อ"), ("10W", "10 ล้อ"),
                         ("TRL8", "หาง 8 ล้อ"), ("10WL", "หัว+หาง 10 ล้อ"),
                         ("18W", "18 ล้อ")],
    })
```

(Remove the now-unused `cells` variable.)

- [ ] **Step 4: Rewrite the template grid as a top view + add form**

Replace the body of `templates/check_driver.html` with:

```html
<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ตรวจยาง</title><script src="https://cdn.tailwindcss.com"></script>
<style>
  .tire{width:70px;border-radius:11px;padding:7px 3px 6px;text-align:center;
    background:#1e293b;border:1.5px solid #334155;}
  .tire .lbl{font-size:10px;color:#cbd5e1;line-height:1.15;min-height:24px;
    display:flex;align-items:center;justify-content:center;}
  .tire.sel-ok{border-color:#22c55e;background:#11281b;}
  .tire.sel-problem{border-color:#ef4444;background:#2a1414;}
  .tire.sel-near{border-color:#f59e0b;background:#2a2113;}
  .spine{position:absolute;top:46px;bottom:14px;left:50%;width:16px;
    transform:translateX(-50%);background:#15233c;border-radius:8px;}
</style></head>
<body class="bg-slate-900 text-slate-100 p-4 max-w-md mx-auto">

  <h1 class="text-lg font-bold mb-1">ตรวจยาง / ตรวจรถ</h1>
  <p class="text-sm text-slate-400 mb-3">คนตรวจ: {{ actor_name or "—" }}</p>

  <form method="get" action="/check/driver" class="flex gap-2 mb-2">
    <input type="hidden" name="t" value="{{ token }}">
    <input type="hidden" name="actor_name" value="{{ actor_name }}">
    <select name="vehicle_id" class="flex-1 p-2 rounded bg-slate-800 border border-slate-600"
            onchange="this.form.submit()">
      <option value="">— เลือกทะเบียน —</option>
      {% for v in vehicles %}
        <option value="{{ v.id }}" {{ 'selected' if vehicle and vehicle.id == v.id }}>
          {{ v.plate_no }}{% if v.nickname %} ({{ v.nickname }}){% endif %}</option>
      {% endfor %}
    </select>
  </form>

  <!-- add vehicle -->
  <details class="mb-4 rounded-lg border border-slate-700 bg-slate-800 p-3">
    <summary class="text-sm text-sky-400 cursor-pointer">+ เพิ่มทะเบียนใหม่</summary>
    <form method="post" action="/check/add-vehicle?t={{ token }}" class="mt-3 space-y-2">
      <input type="hidden" name="t" value="{{ token }}">
      <input type="hidden" name="role" value="driver">
      <input name="plate_no" required placeholder="ทะเบียน เช่น 71-2345"
             class="w-full p-2 rounded bg-slate-900 border border-slate-600 text-sm">
      <div class="text-xs text-slate-400">ประเภทรถ (กำหนดจำนวนล้อ)</div>
      <select name="truck_type" class="w-full p-2 rounded bg-slate-900 border border-slate-600 text-sm">
        {% for code, th in type_options %}<option value="{{ code }}">{{ th }}</option>{% endfor %}
      </select>
      <input name="nickname" placeholder="ชื่อเล่น (ไม่บังคับ)"
             class="w-full p-2 rounded bg-slate-900 border border-slate-600 text-sm">
      <button class="w-full p-2 rounded bg-sky-600 font-bold text-sm">บันทึกทะเบียน</button>
    </form>
  </details>

  {% if vehicle %}
  <form method="post" action="/check/driver?t={{ token }}" enctype="multipart/form-data">
    <input type="hidden" name="t" value="{{ token }}">
    <input type="hidden" name="actor_name" value="{{ actor_name }}">
    <input type="hidden" name="vehicle_id" value="{{ vehicle.id }}">

    <div class="flex items-center gap-2 mb-3">
      <span class="font-semibold">{{ vehicle.plate_no }}</span>
      <span class="text-xs text-slate-400">{{ vehicle.truck_type }}</span>
      <span class="ml-auto text-xs text-slate-400"><b id="cnt">0</b> เส้น</span>
    </div>

    <label class="block text-sm mb-3">เลขไมล์วันนี้
      <input name="mile" inputmode="numeric"
             class="w-full p-2 rounded bg-slate-800 border border-slate-600 mt-1"></label>

    <!-- TOP VIEW -->
    <div class="relative bg-slate-950/40 border border-slate-800 rounded-2xl p-3 mb-5">
      <div class="spine"></div>
      <div class="text-center text-xs text-slate-500 mb-1">▲ หน้ารถ</div>
      {% for ax in axles %}
        <div class="text-center text-[10px] text-slate-500 mt-2 mb-1">{{ ax.tag }}</div>
        <div class="flex items-start justify-between gap-1">
          <div class="flex gap-1">
            {% for c in ax.left %}{{ tire_cell(c) }}{% endfor %}
          </div>
          <div class="flex gap-1">
            {% for c in ax.right %}{{ tire_cell(c) }}{% endfor %}
          </div>
        </div>
      {% endfor %}
    </div>

    <!-- weekly -->
    <h2 class="text-sm font-bold mb-2 text-slate-300">ตรวจน้ำมัน/ของเหลว/อุปกรณ์ (รายสัปดาห์)</h2>
    <input type="hidden" name="weekly" value="1">
    <div class="space-y-2 mb-5">
      {% for key, th in weekly_items %}
      <div class="flex items-center justify-between text-sm">
        <span>{{ th }}</span>
        <select name="item_{{ key }}" class="p-1 rounded bg-slate-800 border border-slate-600 text-xs">
          <option value="">—</option>
          {% for code, sth in weekly_status %}<option value="{{ code }}">{{ sth }}</option>{% endfor %}
        </select>
      </div>
      {% endfor %}
    </div>

    <button class="w-full p-3 rounded-lg bg-blue-600 font-bold">ส่งทั้งคัน ▸</button>
  </form>
  {% endif %}

<script>
  // status color + counter from each cond_ select
  function paint(sel){
    var box = sel.closest('.tire');
    box.classList.remove('sel-ok','sel-problem','sel-near');
    if(sel.value) box.classList.add('sel-'+sel.value);
    var n=0; document.querySelectorAll('select[name^="cond_"]').forEach(function(s){ if(s.value)n++; });
    var c=document.getElementById('cnt'); if(c)c.textContent=n;
  }
  document.querySelectorAll('select[name^="cond_"]').forEach(function(s){
    s.addEventListener('change', function(){ paint(s); });
  });
</script>
</body></html>

{% macro tire_cell(c) %}
  <div class="tire">
    <div class="lbl">{{ c.label }}</div>
    <select name="cond_{{ c.pos }}" onchange="paint(this)"
            class="w-full mt-1 p-1 rounded bg-slate-900 border border-slate-600 text-[11px]">
      <option value="">—</option>
      {% for code, th in conditions %}<option value="{{ code }}">{{ th }}</option>{% endfor %}
    </select>
    <input type="file" name="photo_{{ c.pos }}" accept="image/*" capture="environment"
           multiple class="hidden" id="ph_{{ c.pos }}">
    <label for="ph_{{ c.pos }}" class="block text-[9px] text-slate-500 mt-1 cursor-pointer">
      📷 {{ "ข้าง+หน้า" if c.photos == 2 else "หน้ายาง" }}</label>
  </div>
{% endmacro %}
```

> Note: Jinja macros must be defined before use OR imported. Since this is a single self-contained file and the macro is referenced inside the `{% for %}`, move the `{% macro tire_cell(c) %}...{% endmacro %}` block to the TOP of the file (before `<!doctype html>`). Jinja parses macros regardless of position in the same template, but defining before first call is safest — place it at line 1.

- [ ] **Step 5: Run to verify it passes**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_driver_topview.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Regression — driver submit + weekly still work**

Run: `cd ProjectYK_System/app && .venv/Scripts/python.exe -m pytest tests/test_check_driver.py tests/test_check_weekly.py -v`
Expected: PASS (the POST handler and `cond_<pos>`/`photo_<pos>`/`weekly` field names are unchanged).

- [ ] **Step 7: Commit**

```bash
git add ProjectYK_System/app/main.py ProjectYK_System/app/templates/check_driver.html ProjectYK_System/app/tests/test_check_driver_topview.py
git commit -m "feat(tire-check): top-view driver screen + add-vehicle form"
```

---

## Self-Review

**Spec coverage:**
- §3 add vehicle from link (plate + type buttons + reuse existing) → Task 3 + Task 4 form. ✅
- §3 TRL8 mapping in `_tire_positions_for_vehicle` → Task 1. ✅
- §4 top-view driver screen (axles, sides, status color, counter, Thai labels, photo hint) → Task 2 (`axle_layout`) + Task 4 (template). ✅
- §5 `axle_layout` in tire_view; route in main; template rewrite → Tasks 2, 3, 4. ✅
- §6 plate uniqueness/no-overwrite → Task 3 `test_add_existing_plate_reuses_without_overwrite`. ✅
- §6 no schema change → confirmed (no SCHEMA_VERSION touch). ✅
- §8 add-vehicle on both roles → Task 3 `role` param; driver form in Task 4 (mechanic form deferred — driver is the primary, mechanic can use the same route, form can be added later without schema change). type "อื่นๆ" = chosen-from-list (`type_options`) per §8 decision. ✅

**Placeholder scan:** No TBD/TODO. The macro-placement note in Task 4 Step 4 is an explicit instruction, not a placeholder. All code blocks complete.

**Type consistency:** `axle_layout(positions) -> list[{tag,left,right}]` defined in Task 2, consumed in Task 4 template + handler. Cell keys `pos/label/photos/outer` consistent across Task 2 and Task 4 macro. `cond_<pos>` / `photo_<pos>` / `weekly` names match the unchanged POST handler (verified against main.py:6012+). `truck_type` values (`6W/10W/TRL8/10WL/18W`) consistent across Tasks 1, 3, 4.

**Risk note:** Task 4 rewrites the whole driver template — run Task 4 Step 6 regression (existing driver/weekly POST tests) to confirm field names survived the rewrite.
