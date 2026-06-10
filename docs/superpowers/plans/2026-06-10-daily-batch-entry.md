# Daily Batch Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เปลี่ยน `/daily/new` จากฟอร์มยาว 28 ช่อง เป็นตารางคีย์หลายแถวแบบ Excel บันทึกทีเดียวผ่าน `POST /daily/batch`

**Architecture:** แยก logic การ apply ฟิลด์จาก `daily_save` เดิมเป็น helper `_apply_daily_fields()` แล้วให้ทั้งฟอร์มเดิม (edit) และ endpoint batch ใหม่เรียกตัวเดียวกัน — template ใหม่ `daily_batch.html` เป็นตาราง + vanilla JS (ไม่มี Node build) ส่ง JSON ไป batch endpoint

**Tech Stack:** FastAPI + SQLModel + Jinja2 + Tailwind CDN (ตามสแต็กเดิม ห้ามเพิ่ม dependency)

**Spec:** `docs/superpowers/specs/2026-06-10-daily-batch-entry-design.md`

**หมายเหตุการทดสอบ:** repo นี้**ไม่มี pytest/test suite** (ดู CLAUDE.md) — ทุก task ตรวจด้วยการรันแอปจริง + PowerShell `Invoke-RestMethod` + เช็คใน browser แทน TDD ปกติ ห้ามสร้าง test framework ใหม่

**การรันแอประหว่างทำ:** จากราก repo:
```powershell
cd ProjectYK_System\app; .venv\Scripts\python.exe main.py
```
แอปอยู่ที่ `http://127.0.0.1:8010` (ถ้า venv ยังไม่มี ใช้ `start.bat` ครั้งแรก) — DB คือ SQLite `ProjectYK_System/app/app.db` (ข้อมูลจริง! แถวทดสอบต้องลบทิ้งเสมอ)

---

### Task 1: แยก helper `_apply_daily_fields` ใน main.py

**Files:**
- Modify: `ProjectYK_System/app/main.py` (ฟังก์ชัน `daily_save` ~บรรทัด 959-1057)

`daily_save` เดิมรับ Form 30 ตัวแล้ว assign ลง row ทีละฟิลด์ (บรรทัด ~1008-1037) — แยกส่วน assign ออกเป็น helper ที่รับ dict เพื่อให้ batch endpoint (Task 2) ใช้ร่วมได้ **พฤติกรรมต้องเหมือนเดิม 100%**

- [ ] **Step 1: เพิ่ม helper เหนือ `daily_new_form` (~บรรทัด 927)**

```python
def _apply_daily_fields(row: DailyJob, f: dict) -> None:
    """Apply ค่าฟอร์ม (string ทั้งหมด) ลง DailyJob — ใช้ร่วมระหว่างฟอร์มเดี่ยวและ /daily/batch"""
    row.driver_id = _parse_int(f.get("driver_id", ""))
    row.driver_raw_name = f.get("driver_raw_name", "").strip()
    row.head_vehicle_id = _parse_int(f.get("head_vehicle_id", ""))
    row.tail_vehicle_id = _parse_int(f.get("tail_vehicle_id", ""))
    row.plate_no_raw = f.get("plate_no_raw", "").strip()
    row.tail_plate_raw = f.get("tail_plate_raw", "").strip()
    row.customer_id = _parse_int(f.get("customer_id", ""))
    row.customer_name_raw = f.get("customer_name_raw", "").strip()
    row.trip_type_code = f.get("trip_type_code", "").strip()
    row.status_code = f.get("status_code", "").strip()
    row.leave_status = f.get("leave_status", "").strip()
    row.origin = f.get("origin", "").strip()
    row.destination = f.get("destination", "").strip()
    row.doc_no = f.get("doc_no", "").strip()
    row.job_ref = f.get("job_ref", "").strip()
    row.container_no = f.get("container_no", "").strip()
    row.container_size = f.get("container_size", "").strip()
    row.revenue_customer = _parse_float(f.get("revenue_customer", "0"))
    row.trip_fee_driver = _parse_float(f.get("trip_fee_driver", "0"))
    row.fuel_liter = _parse_float(f.get("fuel_liter", "0"))
    row.fuel_amount = _parse_float(f.get("fuel_amount", "0"))
    row.fuel_station = f.get("fuel_station", "").strip()
    row.fuel_rate_km_per_l = _parse_float(f.get("fuel_rate_km_per_l", "0"))
    row.mile_snapshot = _parse_float(f.get("mile_snapshot", "0"))
    row.invoice_no = f.get("invoice_no", "").strip()
    row.invoice_date = _parse_date(f.get("invoice_date", ""))
    row.wht_53 = _parse_float(f.get("wht_53", "0"))
    row.remark = f.get("remark", "").strip()
    row.updated_at = datetime.utcnow()
```

(`_parse_float("")` คืน 0.0 และ `_parse_int("")` คืน None อยู่แล้ว — ดู main.py:146-170 — พฤติกรรมตรงกับโค้ดเดิม)

- [ ] **Step 2: แทนที่บล็อก assign ใน `daily_save`**

ลบบรรทัด `row.driver_id = _parse_int(driver_id)` จนถึง `row.updated_at = datetime.utcnow()` (เดิม ~1008-1037 **ยกเว้น**บรรทัด `driver_obj = ...` ให้คงไว้) แล้วแทนด้วย:

```python
        _apply_daily_fields(row, {
            "driver_id": driver_id, "driver_raw_name": driver_raw_name,
            "head_vehicle_id": head_vehicle_id, "tail_vehicle_id": tail_vehicle_id,
            "plate_no_raw": plate_no_raw, "tail_plate_raw": tail_plate_raw,
            "customer_id": customer_id, "customer_name_raw": customer_name_raw,
            "trip_type_code": trip_type_code, "status_code": status_code,
            "leave_status": leave_status, "origin": origin, "destination": destination,
            "doc_no": doc_no, "job_ref": job_ref,
            "container_no": container_no, "container_size": container_size,
            "revenue_customer": revenue_customer, "trip_fee_driver": trip_fee_driver,
            "fuel_liter": fuel_liter, "fuel_amount": fuel_amount,
            "fuel_station": fuel_station, "fuel_rate_km_per_l": fuel_rate_km_per_l,
            "mile_snapshot": mile_snapshot, "invoice_no": invoice_no,
            "invoice_date": invoice_date, "wht_53": wht_53, "remark": remark,
        })
        driver_obj = s.get(Employee, row.driver_id) if row.driver_id else None
```

(บรรทัด `driver_obj` เดิมอยู่ก่อนบล็อก assign — ย้ายมาอยู่หลัง helper ได้เพราะค่า `row.driver_id` เซ็ตเหมือนกัน และ `driver_obj` ไม่ถูกใช้ในบล็อก assign)

- [ ] **Step 3: ตรวจ syntax + แอปสตาร์ท**

```powershell
ProjectYK_System\app\.venv\Scripts\python.exe -c "import ast; ast.parse(open(r'ProjectYK_System\app\main.py', encoding='utf-8').read())"
```
Expected: ไม่มี output (parse ผ่าน) — แล้วรันแอป เปิด `http://127.0.0.1:8010/daily` ต้องโหลดได้

- [ ] **Step 4: ตรวจ edit เดิมไม่พัง**

เปิด `/daily` เลือกงานใดก็ได้ → กดแก้ไข → เปลี่ยน "หมายเหตุ" เป็นค่าเดิม+`.` → บันทึก → เปิดแก้ไขซ้ำ ตรวจว่าทุกช่อง (เงิน, คนขับ, ทะเบียน) ค่าเดิมไม่เพี้ยน → ลบ `.` ออกแล้วบันทึกคืน

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/app/main.py
git commit -m "refactor: extract _apply_daily_fields from daily_save (no behavior change)"
```

---

### Task 2: เพิ่ม `POST /daily/batch`

**Files:**
- Modify: `ProjectYK_System/app/main.py` (เพิ่ม endpoint ใต้ `daily_save` ก่อน `daily_delete` ~บรรทัด 1060)

- [ ] **Step 1: เพิ่ม endpoint**

```python
@app.post("/daily/batch")
async def daily_batch_save(request: Request):
    """รับ JSON {work_date, site_code, rows:[{...}]} จากหน้า batch entry — บันทึกทีละแถว
    แถวที่พังไม่ล้มทั้งชุด: คืนผลรายแถว {ok, id|error}"""
    payload = await request.json()
    wd = _parse_date(str(payload.get("work_date") or ""))
    site = str(payload.get("site_code") or "").strip().upper()
    if not wd:
        raise HTTPException(400, "work_date invalid")
    if site not in models.SITE_CODES:
        raise HTTPException(400, "site_code invalid")
    rows_in = payload.get("rows") or []
    if not isinstance(rows_in, list) or len(rows_in) > 200:
        raise HTTPException(400, "rows invalid")
    results = []
    with Session(engine) as s:
        for f in rows_in:
            try:
                clean = {k: ("" if v is None else str(v)) for k, v in dict(f).items()}
                row = DailyJob(work_date=wd, site_code=site, source="manual")
                _apply_daily_fields(row, clean)
                s.add(row)
                s.commit()
                s.refresh(row)
                # Auto-learn rates — เหมือน daily_save ทุกประการ
                try:
                    rate_record_from_daily(s, row)
                    s.commit()
                except Exception:
                    s.rollback()
                results.append({"ok": True, "id": row.id})
            except Exception as e:
                s.rollback()
                results.append({"ok": False, "error": str(e)[:200]})
    return {"results": results}
```

(`models.SITE_CODES` ใช้อยู่แล้วที่ main.py:409 · `rate_record_from_daily` import อยู่แล้วเพราะ `daily_save` เรียก)

- [ ] **Step 2: รันแอปแล้วยิงทดสอบ 2 แถว (แถวดี + แถวว่างบางส่วน)**

```powershell
$body = @{ work_date = "2026-06-10"; site_code = "LCB"; rows = @(
  @{ driver_raw_name = "ทดสอบBATCH"; origin = "A"; destination = "B"; revenue_customer = "1"; trip_fee_driver = "1"; remark = "TEST-BATCH-DELETE-ME" },
  @{ driver_raw_name = "ทดสอบBATCH2"; remark = "TEST-BATCH-DELETE-ME" }
) } | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri "http://127.0.0.1:8010/daily/batch" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```
Expected: `results` มี 2 รายการ `ok=True` พร้อม `id` — จด id ทั้งสองไว้

- [ ] **Step 3: ตรวจ + ลบแถวทดสอบ (ห้ามทิ้งไว้ใน DB จริง)**

เปิด `http://127.0.0.1:8010/daily?d=2026-06-10` เห็น 2 แถว remark TEST-BATCH-DELETE-ME แล้วลบ:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8010/daily/<id1>/delete" -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8010/daily/<id2>/delete" -Method Post
```
Expected: เปิด `/daily?d=2026-06-10` ซ้ำ ไม่เหลือแถว TEST-BATCH

- [ ] **Step 4: ทดสอบ input พัง**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8010/daily/batch" -Method Post -ContentType "application/json" -Body '{"work_date":"", "site_code":"LCB", "rows":[]}'
```
Expected: HTTP 400 (work_date invalid)

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/app/main.py
git commit -m "feat: POST /daily/batch - save multiple daily jobs in one request"
```

---

### Task 3: Template `daily_batch.html` + เปลี่ยน GET `/daily/new`

**Files:**
- Create: `ProjectYK_System/app/templates/daily_batch.html`
- Modify: `ProjectYK_System/app/main.py` (`daily_new_form` ~บรรทัด 927-943)

`daily_form.html` **ห้ามแก้** — ยังใช้กับ `/daily/{id}/edit` (mode='edit')

- [ ] **Step 1: แก้ `daily_new_form` ให้ส่ง masters เป็น JSON**

แทนที่ฟังก์ชันเดิมทั้งหมด:

```python
@app.get("/daily/new", response_class=HTMLResponse)
def daily_new_form(request: Request):
    import json as _json
    with Session(engine) as s:
        employees, vehicles, customers = _load_masters(s)
    masters_json = _json.dumps({
        "employees": [{"id": e.id, "name": e.full_name, "site": e.home_site_code} for e in employees],
        "heads": [{"id": v.id, "plate": v.plate_no, "type": v.truck_type} for v in vehicles if v.vehicle_kind != "tail"],
        "tails": [{"id": v.id, "plate": v.plate_no} for v in vehicles if v.vehicle_kind == "tail"],
        "customers": [{"id": c.id, "name": c.name} for c in customers],
    }, ensure_ascii=False)
    ctx = base_context(request)
    ctx.update({"masters_json": masters_json})
    return templates.TemplateResponse("daily_batch.html", ctx)
```

(`base_context` มี `site_codes`, `leave_status_choices`, `today` อยู่แล้ว — main.py:405-416)

- [ ] **Step 2: สร้าง `daily_batch.html`**

```html
{% extends "base.html" %}
{% block title %}เพิ่มงานประจำวัน (หลายแถว){% endblock %}
{% block content %}
<style>
  .col-lcb, .col-bigc { display: none; }
  table.site-LCB .col-lcb { display: table-cell; }
  table.site-BIGC .col-bigc { display: table-cell; }
  #batchTable td input, #batchTable td select { width: 100%; border: 1px solid #e2e8f0; border-radius: 4px; padding: 2px 6px; min-width: 5rem; }
  #batchTable td input[type=number] { text-align: right; }
  .lnk-ok { background: #dcfce7; }
  .lnk-raw { background: #fef9c3; }
  tr.saved input, tr.saved select { background: #f8fafc; color: #94a3b8; }
  tr.rowerr { background: #fef2f2; }
</style>

<div class="flex items-center justify-between mb-3 flex-wrap gap-2">
  <h1 class="text-2xl font-bold">เพิ่มงานประจำวัน</h1>
  <div class="text-xs text-slate-500">Enter=ช่องถัดไป (สุดแถว=ขึ้นแถวใหม่) · Ctrl+D=ก๊อปจากแถวบน · <span class="lnk-ok px-1 rounded">เขียว=ตรง master</span> <span class="lnk-raw px-1 rounded">เหลือง=เก็บชื่อดิบ (ยังไม่ลิงก์)</span></div>
</div>

<div class="bg-white rounded-lg border p-3 mb-3 flex items-end gap-3 flex-wrap sticky top-0 z-10 shadow-sm">
  <div>
    <label class="block text-xs text-slate-500 mb-1">วันที่ (ทุกแถว) *</label>
    <input type="date" id="hdrDate" value="{{ today }}" required class="border rounded px-2 py-1.5 text-sm" />
  </div>
  <div>
    <label class="block text-xs text-slate-500 mb-1">ไซต์ (ทุกแถว) *</label>
    <select id="hdrSite" class="border rounded px-2 py-1.5 text-sm">
      {% for sc in site_codes %}<option value="{{ sc }}">{{ sc }}</option>{% endfor %}
    </select>
  </div>
  <button id="saveAllBtn" class="bg-slate-900 text-white px-5 py-2 rounded-lg hover:bg-slate-700 text-sm">บันทึกทั้งหมด (<span id="rowCount">0</span> แถว)</button>
  <button id="addRowBtn" class="border px-3 py-2 rounded-lg text-sm hover:bg-slate-50">+ แถว</button>
  <a href="/daily" class="px-3 py-2 rounded-lg border text-sm hover:bg-slate-50">กลับ List</a>
  <span id="saveMsg" class="text-sm"></span>
</div>

<div class="overflow-x-auto bg-white rounded-lg border">
<table id="batchTable" class="text-sm w-full">
  <thead class="bg-slate-50 text-xs text-slate-600">
    <tr>
      <th class="px-2 py-2 w-10">#</th>
      <th class="px-2 py-2 text-left">คนขับ</th>
      <th class="px-2 py-2 text-left">ทะเบียน</th>
      <th class="px-2 py-2 text-left col-bigc">หาง</th>
      <th class="px-2 py-2 text-left">เที่ยว</th>
      <th class="px-2 py-2 text-left">ลูกค้า</th>
      <th class="px-2 py-2 text-left">ต้นทาง</th>
      <th class="px-2 py-2 text-left">ปลายทาง</th>
      <th class="px-2 py-2 text-right">ขนส่ง</th>
      <th class="px-2 py-2 text-right">ค่าเที่ยว</th>
      <th class="px-2 py-2 text-left col-lcb">JobRef</th>
      <th class="px-2 py-2 text-left col-lcb">เบอร์ตู้</th>
      <th class="px-2 py-2 text-left col-lcb">ขนาด</th>
      <th class="px-2 py-2 text-left col-lcb">Doc no</th>
      <th class="px-2 py-2 w-8"></th>
      <th class="px-2 py-2 w-8"></th>
    </tr>
  </thead>
  <tbody id="batchBody"></tbody>
</table>
</div>

<datalist id="dl_drv"></datalist>
<datalist id="dl_head"></datalist>
<datalist id="dl_tail"></datalist>
<datalist id="dl_cust"></datalist>
<datalist id="dl_trip"></datalist>

<script>
const M = {{ masters_json | safe }};
const LEAVE = [{% for c, l in leave_status_choices %}["{{ c }}", "{{ l }}"],{% endfor %}];
const TRIP_HINTS = { AYU: ["mao", "trip"], BIGC: ["รับรถ", "1DH", "1Big c", "1+", "2BigC", "2++"], LCB: ["Export", "Import", "Domestic"] };

const tbody = document.getElementById("batchBody");
const table = document.getElementById("batchTable");
const hdrDate = document.getElementById("hdrDate");
const hdrSite = document.getElementById("hdrSite");
const saveMsg = document.getElementById("saveMsg");
let rowSeq = 0;

function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;"); }
function fillDatalist(id, items, key) {
  document.getElementById(id).innerHTML = items.map(x => `<option value="${esc(x[key])}">`).join("");
}
fillDatalist("dl_drv", M.employees, "name");
fillDatalist("dl_head", M.heads, "plate");
fillDatalist("dl_tail", M.tails, "plate");
fillDatalist("dl_cust", M.customers, "name");

function applySite() {
  table.className = table.className.replace(/site-\S+/g, "").trim() + " site-" + hdrSite.value;
  fillDatalist("dl_trip", (TRIP_HINTS[hdrSite.value] || []).map(t => ({ t })), "t");
}
hdrSite.addEventListener("change", applySite);

function rowHtml(n) {
  return `
<tr class="job border-t" data-n="${n}">
  <td class="px-2 py-1 text-center text-slate-400 text-xs stat">${n}</td>
  <td><input name="driver" list="dl_drv" data-link="employees:name" autocomplete="off"></td>
  <td><input name="head" list="dl_head" data-link="heads:plate" autocomplete="off"></td>
  <td class="col-bigc"><input name="tail" list="dl_tail" data-link="tails:plate" autocomplete="off"></td>
  <td><input name="trip_type_code" list="dl_trip" autocomplete="off"></td>
  <td><input name="customer" list="dl_cust" data-link="customers:name" autocomplete="off"></td>
  <td><input name="origin"></td>
  <td><input name="destination"></td>
  <td><input name="revenue_customer" type="number" step="0.01"></td>
  <td><input name="trip_fee_driver" type="number" step="0.01"></td>
  <td class="col-lcb"><input name="job_ref"></td>
  <td class="col-lcb"><input name="container_no"></td>
  <td class="col-lcb"><input name="container_size" placeholder="20/40"></td>
  <td class="col-lcb"><input name="doc_no"></td>
  <td class="text-center"><button type="button" class="moreBtn text-slate-400 hover:text-slate-700" tabindex="-1" title="ช่องเพิ่มเติม">⋯</button></td>
  <td class="text-center"><button type="button" class="delBtn text-rose-400 hover:text-rose-600" tabindex="-1" title="ลบแถว">✕</button></td>
</tr>
<tr class="extra hidden bg-slate-50 border-t text-xs">
  <td></td>
  <td colspan="15" class="px-2 py-2">
    <div class="grid md:grid-cols-4 gap-2">
      <label>สถานะงาน<input name="status_code" placeholder="MOL, รถจอด"></label>
      <label>สถานะลา<select name="leave_status">${LEAVE.map(([c, l]) => `<option value="${esc(c)}">${esc(l)}</option>`).join("")}</select></label>
      <label>น้ำมัน (ลิตร)<input name="fuel_liter" type="number" step="0.01"></label>
      <label>น้ำมัน (บาท)<input name="fuel_amount" type="number" step="0.01"></label>
      <label>ปั้ม<input name="fuel_station"></label>
      <label>เรท กม./ล.<input name="fuel_rate_km_per_l" type="number" step="0.01"></label>
      <label>เลขไมล์<input name="mile_snapshot" type="number" step="0.01"></label>
      <label>เลขใบแจ้งหนี้<input name="invoice_no"></label>
      <label>วันที่ใบแจ้งหนี้<input name="invoice_date" type="date"></label>
      <label>ภงด.53<input name="wht_53" type="number" step="0.01"></label>
      <label class="md:col-span-2">หมายเหตุ<input name="remark"></label>
    </div>
  </td>
</tr>`;
}

function addRow() {
  rowSeq += 1;
  tbody.insertAdjacentHTML("beforeend", rowHtml(rowSeq));
  updateCount();
  return tbody.querySelector(`tr.job[data-n="${rowSeq}"]`);
}
function updateCount() {
  document.getElementById("rowCount").textContent = tbody.querySelectorAll("tr.job:not(.saved)").length;
}

function linkPaint(inp) {
  const [coll, key] = inp.dataset.link.split(":");
  const v = inp.value.trim();
  inp.classList.remove("lnk-ok", "lnk-raw");
  if (!v) return;
  inp.classList.add(M[coll].some(x => String(x[key]) === v) ? "lnk-ok" : "lnk-raw");
}
tbody.addEventListener("input", e => { if (e.target.dataset.link) linkPaint(e.target); });

// ── keyboard ──
function visibleInputs(scope) {
  return [...scope.querySelectorAll("input, select")].filter(el => !el.disabled && el.offsetParent !== null);
}
tbody.addEventListener("keydown", e => {
  const el = e.target;
  if (!el.matches("input, select")) return;
  if (e.key === "Enter") {
    e.preventDefault();
    const all = visibleInputs(tbody);
    const i = all.indexOf(el);
    if (i === all.length - 1) {
      // ช่องสุดท้ายของตาราง → ขึ้นแถวใหม่
      visibleInputs(addRow())[0].focus();
    } else if (i >= 0) {
      all[i + 1].focus();
    }
  }
  if (e.ctrlKey && e.key.toLowerCase() === "d") {
    e.preventDefault();
    // หาแถวชนิดเดียวกัน (job↔job, extra↔extra) ก่อนหน้า แล้วก๊อปช่องชื่อเดียวกัน
    const tr = el.closest("tr");
    const kind = tr.classList.contains("job") ? "job" : "extra";
    let prev = tr.previousElementSibling;
    while (prev && !prev.classList.contains(kind)) prev = prev.previousElementSibling;
    if (prev) {
      const src = prev.querySelector(`[name="${el.name}"]`);
      if (src) { el.value = src.value; if (el.dataset.link) linkPaint(el); }
    }
  }
});

// ── ปุ่มในแถว ──
tbody.addEventListener("click", e => {
  if (e.target.classList.contains("moreBtn")) {
    e.target.closest("tr.job").nextElementSibling.classList.toggle("hidden");
  }
  if (e.target.classList.contains("delBtn")) {
    const tr = e.target.closest("tr.job");
    if (tr.classList.contains("saved")) return;
    tr.nextElementSibling.remove();
    tr.remove();
    updateCount();
  }
});

// ── serialize + save ──
function rowData(tr) {
  const extra = tr.nextElementSibling;
  const g = n => (tr.querySelector(`[name="${n}"]`) || extra.querySelector(`[name="${n}"]`) || { value: "" }).value.trim();
  const link = (name, coll, key, idField, rawField) => {
    const v = g(name);
    const m = M[coll].find(x => String(x[key]) === v);
    return { [idField]: m ? String(m.id) : "", [rawField]: m ? "" : v };
  };
  const d = {
    ...link("driver", "employees", "name", "driver_id", "driver_raw_name"),
    ...link("head", "heads", "plate", "head_vehicle_id", "plate_no_raw"),
    ...link("tail", "tails", "plate", "tail_vehicle_id", "tail_plate_raw"),
    ...link("customer", "customers", "name", "customer_id", "customer_name_raw"),
  };
  ["trip_type_code", "origin", "destination", "revenue_customer", "trip_fee_driver",
   "job_ref", "container_no", "container_size", "doc_no",
   "status_code", "leave_status", "fuel_liter", "fuel_amount", "fuel_station",
   "fuel_rate_km_per_l", "mile_snapshot", "invoice_no", "invoice_date", "wht_53", "remark"
  ].forEach(n => d[n] = g(n));
  return d;
}
function isEmptyRow(d) {
  return Object.entries(d).every(([k, v]) => !v || (k === "leave_status" && v === LEAVE[0][0]));
}

document.getElementById("addRowBtn").addEventListener("click", () => visibleInputs(addRow())[0].focus());

document.getElementById("saveAllBtn").addEventListener("click", async () => {
  if (!hdrDate.value) { saveMsg.textContent = "ใส่วันที่ก่อน"; saveMsg.className = "text-sm text-rose-600"; return; }
  const trs = [...tbody.querySelectorAll("tr.job:not(.saved)")];
  const rows = [], map = [];
  trs.forEach(tr => {
    tr.classList.remove("rowerr");
    const d = rowData(tr);
    if (!isEmptyRow(d)) { rows.push(d); map.push(tr); }
  });
  if (!rows.length) { saveMsg.textContent = "ไม่มีแถวให้บันทึก"; saveMsg.className = "text-sm text-slate-500"; return; }
  saveMsg.textContent = "กำลังบันทึก…"; saveMsg.className = "text-sm text-slate-500";
  let data;
  try {
    const r = await fetch("/daily/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ work_date: hdrDate.value, site_code: hdrSite.value, rows }),
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    data = await r.json();
  } catch (err) {
    saveMsg.textContent = "บันทึกไม่สำเร็จ: " + err.message + " (ข้อมูลยังอยู่ ลองใหม่ได้)";
    saveMsg.className = "text-sm text-rose-600";
    return;
  }
  let ok = 0, bad = 0;
  data.results.forEach((res, i) => {
    const tr = map[i];
    const stat = tr.querySelector(".stat");
    if (res.ok) {
      ok += 1;
      tr.classList.add("saved");
      stat.innerHTML = `<span class="text-emerald-600">✓ #${res.id}</span>`;
      [tr, tr.nextElementSibling].forEach(t => t.querySelectorAll("input, select").forEach(el => el.disabled = true));
    } else {
      bad += 1;
      tr.classList.add("rowerr");
      stat.innerHTML = `<span class="text-rose-600" title="${esc(res.error)}">✗</span>`;
    }
  });
  updateCount();
  saveMsg.textContent = `บันทึกแล้ว ${ok} แถว` + (bad ? ` · ติดปัญหา ${bad} แถว (แถวแดง — แก้แล้วกดบันทึกซ้ำ)` : "");
  saveMsg.className = bad ? "text-sm text-rose-600" : "text-sm text-emerald-600";
});

// init
applySite();
visibleInputs(addRow())[0].focus();
</script>
{% endblock %}
```

- [ ] **Step 3: รันแอป เปิด `http://127.0.0.1:8010/daily/new` ตรวจ UI**

ตรวจตามนี้ (ไม่ต้องกดบันทึก):
1. เปิดมาเห็นตาราง + แถวแรกพร้อมพิมพ์ โฟกัสที่ช่องคนขับ
2. ไซต์ default แรกใน list — สลับไป LCB → คอลัมน์ JobRef/ตู้/ขนาด/Doc โผล่ · สลับ BIGC → คอลัมน์หางโผล่ แทน
3. พิมพ์ชื่อคนขับที่มีจริง (เลือกจาก autocomplete) → ช่องเขียว · พิมพ์มั่ว → เหลือง
4. Enter วิ่งช่องถัดไป, Enter ช่องสุดท้าย → แถวใหม่ · Ctrl+D ก๊อปจากแถวบน
5. ปุ่ม ⋯ เปิด/ปิดแผงช่องเพิ่มเติม · ปุ่ม ✕ ลบแถว
6. หัวตาราง (วันที่/ไซต์/ปุ่มบันทึก) ลอยติดบนเมื่อเลื่อนจอ

- [ ] **Step 4: ทดสอบบันทึกจริง + ลบทิ้ง**

คีย์ 2 แถว (remark ใส่ `TEST-BATCH-DELETE-ME` ผ่านแผง ⋯) → กดบันทึก → ทั้งสองขึ้น ✓ เขียว + id → เปิด `/daily?d=<วันที่>` เห็น 2 แถว → ลบทั้งสองผ่านปุ่มลบใน `/daily` → ตรวจ `/daily/{id}/edit` ของงานเก่ายังเปิดได้ปกติ

- [ ] **Step 5: Commit**

```powershell
git add ProjectYK_System/app/templates/daily_batch.html ProjectYK_System/app/main.py
git commit -m "feat: /daily/new batch entry table replaces single-job form"
```

---

### Task 4: ตรวจเกณฑ์ผ่านตาม spec + อัปเดต changelog

**Files:**
- Modify: `ProjectYK_System/CHANGELOG_MASTER.md` (เพิ่มหัวข้อ `##` ใหม่บนสุด ตาม format เดิมในไฟล์)

- [ ] **Step 1: ไล่เกณฑ์ผ่าน 4 ข้อจาก spec**

1. คีย์งาน LCB 3 แถวจากหน้าเดียวโดยไม่เลื่อนจอ → บันทึกทีเดียว → `/daily` มี 3 แถวใหม่ (source=manual) → ลบทิ้งหลังตรวจ
2. แถวที่พิมพ์ชื่อคนขับไม่ตรง master → ช่องเหลือง → หลังบันทึก เปิด `/daily/{id}/edit` เห็นชื่ออยู่ในช่อง "หรือพิมพ์ชื่อ (ยังไม่มีใน master)" (driver_raw_name)
3. แก้งานเก่า 1 รายการผ่าน `/daily/{id}/edit` → ค่าทุกช่องคงเดิมหลังบันทึก
4. ปิดแอปแล้วสตาร์ทใหม่ด้วย `ProjectYK_System\app\start.bat` → ขึ้นปกติ

- [ ] **Step 2: เพิ่ม changelog**

เปิด `ProjectYK_System/CHANGELOG_MASTER.md` ดู format หัวข้อ `##` ล่าสุด แล้วเพิ่มหัวข้อใหม่ตาม format เดิม สรุป: `/daily/new` เป็นตารางคีย์หลายแถว + `POST /daily/batch` + refactor `_apply_daily_fields` (ฟอร์ม edit เดิมไม่กระทบ)

- [ ] **Step 3: Commit**

```powershell
git add ProjectYK_System/CHANGELOG_MASTER.md
git commit -m "docs: changelog for daily batch entry"
```
