# Fuel Pump Reconcile — Design Spec

**Date:** 2026-06-27
**Status:** Approved (โอ), ready for implementation
**Author:** Claude (with โอ)

## Purpose

A read-only CLI that reconciles **pump fuel bills (PDF)** against the system's **FuelTxn** records for one LCB pay cycle. Confirms the system's fuel data (which drives เหมา drivers' `fuel_cost_self` deduction) matches what the pump actually billed — so payroll can be finalized with confidence. Reusable every cycle.

Replaces the LINE-message source (data-starved, see `tools/lcb_fuel_crosscheck/`) with the **monthly pump PDF report** (covers the whole cycle). Both tools can coexist.

## Scope (โอ-confirmed decisions)

- **(ค) Both views:** reconcile ALL bills (every plate/driver, เหมา + เที่ยว), then **highlight payroll-affecting drivers** (lcb_mao / lcb_mixed) specially.
- **(ก) Match within cycle, allow date drift ±3 days**, key = plate + amount. Pump dates the fill-day; system dates the work-day → 1–2 day drift is normal and must not show as a mismatch.
- **(ก) User points at PDF file(s) at run time** + cycle date window. A cycle spans 2 calendar-month PDFs (e.g. May + June). User picks the version (latest).
- **(ค) CLI first**, prove matching logic with tests; MVP web page deferred.
- **(ก) System side = FuelTxn** (`source` tag + cycle dates), already driver-linked. This is exactly what payroll uses (`fuel_cost_self`), so diffs map straight to money impact.
- **Read-only.** Writes nothing to any DB. Output = report files only. Does not guess/fix money.

## Architecture

```
tools/fuel_pump_reconcile/
  pdf_parser.py      parse PDF → list[FuelBill]
  db_loader.py       load FuelTxn → list[SysFuel]
  matcher.py         reconcile → MatchResult
  report.py          render HTML + MD
  run_reconcile.py   CLI orchestrator
  tests/             unit tests per module
```

Data flow:
```
PDF file(s) ─pdf_parser─> [FuelBill] ┐
                                      ├─matcher─> MatchResult ─report─> reports/fuel_reconcile_<cycle>.{html,md}
app.db FuelTxn ─db_loader─> [SysFuel] ┘
```

Each module is independently testable; `matcher.py` (the complex part) is tested with synthetic lists, no PDF/DB needed.

## Data structures

```python
@dataclass
class FuelBill:        # one pump line
    date: date
    plate: str         # raw, e.g. "71-9629"
    station: str       # รุ่งโรจน์ / ทวีโชค / เพิ่มทรัพย์ ...
    ftype: str         # "Diesel B7" / "Diesel B20"
    liter: float
    price: float       # ฿/L
    amount: float

@dataclass
class SysFuel:         # one FuelTxn row
    date: date
    plate: str
    liter: float
    amount: float
    driver_id: Optional[int]
    driver_name: str
    pay_mode: str      # lcb_mao / lcb_trip / lcb_mixed / "" — resolved from PayRun item if available
```

## pdf_parser.py

- `parse_pdf(path) -> list[FuelBill]` using pypdf (installed in app venv).
- Line regex (proven 2026-06-27):
  `^\s*(\d+)\s+(\d{2}\.\d{2}\.\d{4})\s+(\S+)\s+(.+?)\s+(Diesel\s+\S+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+(-?[\d,]+\.\d+)$`
  Groups: seq, date(dd.mm.yyyy), plate, station, ftype, liter, price, amount, balance.
- **Skip** payment/top-up lines (วายเครูดบัตร / วายเคแสกน) — they have no plate/liter and won't match the regex anyway.
- `parse_pdfs(paths) -> list[FuelBill]` concatenates multiple files (May + June).
- Thai date `dd.mm.yyyy` is already CE (2026), no Buddhist-year conversion.

## db_loader.py

- `load_sys_fuel(db_path, source_tag, start, end) -> list[SysFuel]`
- Query FuelTxn where `source=source_tag` and `txn_date` in [start,end]; LEFT JOIN employee for name; resolve `pay_mode` from the matching PayRun item (site=LCB, cycle tag) when present, else "".
- driver_id may be null (e.g. (ว่าง)) — keep, pay_mode="".

## matcher.py (core)

`reconcile(bills, sysfuel, start, end, drift_days=3, amount_tol=1.0, boundary_days=2) -> MatchResult`

Algorithm (greedy, per plate):
1. Group both sides by plate.
2. For each FuelBill, find the unused SysFuel with same plate and `|amount-amount| <= amount_tol`, choosing the **smallest date distance**; accept if `<= drift_days`. Mark both consumed.
3. Remaining bills → `pump_only`; remaining sysfuel → `system_only`.
4. Tag each unmatched item `near_boundary=True` if its date is within `boundary_days` of `start` or `end` (a fill whose pair likely sits in the adjacent cycle / outside the PDF window).

`MatchResult` holds: matched count, matched total ฿ (pump & system), pump_only list, system_only list, and per-(plate/driver) aggregates with pay_mode.

**Note (documented limitation):** date-drift matching by plate+amount can mis-pair two same-amount fills on the same plate within the window. This is acceptable for a reconciliation aid; the report shows raw unmatched bills so a human makes the call. The tool never edits money.

## report.py

`render(result, cycle_tag, out_dir) -> (html_path, md_path)` writes `reports/fuel_reconcile_<cycle_tag>.{html,md}`.

Sections:
1. **Summary:** pump total ฿, system total ฿, Δ (฿ and %), counts matched / pump_only / system_only, how many unmatched are near-boundary.
2. **Unmatched tables** (pump_only, system_only): date, plate, amount, near_boundary flag.
3. **🔴 Payroll-affecting (lcb_mao / lcb_mixed):** per-driver table of net unmatched Δ, with estimated money impact ≈ `Δ × 0.60` (the เหมา share). Drivers with Δ≈0 listed as ✅ to show they reconcile. เที่ยว drivers shown separately as "P&L only, no pay impact".

Thai labels in report; English keys in code/data.

## run_reconcile.py (CLI)

```
python tools/fuel_pump_reconcile/run_reconcile.py \
    --pdf "<may.pdf>" --pdf "<june.pdf>" \
    --cycle-start 2026-05-16 --cycle-end 2026-06-15 \
    --source-tag lcb_may-jun2026 \
    --cycle-tag 2026-06 \
    [--drift-days 3] [--amount-tol 1.0] [--out reports]
```
Orchestrates: parse PDFs → load FuelTxn → reconcile → render → print summary + report path. No DB writes.

## Testing

- `pdf_parser`: parse a tiny fixture text → expected FuelBill list; verify payment lines skipped.
- `db_loader`: in-memory sqlite with a few FuelTxn rows → expected SysFuel.
- `matcher` (most tests): synthetic lists covering exact match, ±1/±2/±3 day drift match, beyond-drift → unmatched, near-boundary tagging, same-amount-same-plate edge, pump_only/system_only totals.
- `report`: render runs without error and contains key numbers.
- One integration test against the real May+June PDFs + current app.db is optional/manual (paths are local).

## Out of scope (YAGNI)

- Writing to DB / auto-fixing fuel. No.
- MVP web page (deferred — CLI first per โอ).
- GPS, liter-rate validation beyond what reconcile surfaces.
- Auto-discovering newest PDF version (user points at file).
```
