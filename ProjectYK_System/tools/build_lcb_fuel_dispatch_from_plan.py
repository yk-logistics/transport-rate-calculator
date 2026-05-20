# -*- coding: utf-8 -*-
"""
LCB fuel dispatch from LINE plan .txt + GPS fuel (CSV or Wialon .xlsx).

  python ProjectYK_System/tools/build_lcb_fuel_dispatch_from_plan.py plan.txt
  python ... plan.txt fuel_gps.xlsx
  python ... plan.txt --fuel-csv reports/fuel_level_latest_LCB_2026-05-20.csv
  python ... plan.txt --add-fuel 72-0420=30 --add-fuel 71-6803=20 --diesel-price 42.20

Output:
  docs/print/lcb_fuel_dispatch_plan.html
  TransportRateCalculator/reports/lcb-fuel-dispatch/index.html  (GitHub Pages source)
  reports/lcb-fuel-dispatch/index.html  (repo root — publish on push)
  reports/fuel_dispatch_assign_*.xlsx
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from parse_lcb_plan_txt import (  # noqa: E402
    L_PER_TRIP,
    ParsedPlan,
    TruckAssignment,
    parse_plan_file,
    plan_trip_stats,
)

OUT_HTML = ROOT / "docs" / "print" / "lcb_fuel_dispatch_plan.html"
REPORTS_DIR = ROOT / "reports"
GPS_INBOX = REPORTS_DIR / "gps_inbox"
DEFAULT_FUEL_CSV = REPORTS_DIR / "fuel_level_latest_LCB_2026-05-20.csv"

GPS_XLSX_GLOBS = (
    "*Fuel_Level*LCB*.xlsx",
    "*LCB*Fuel*Level*.xlsx",
    "*Fuel*Level*LCB*.xlsx",
    "*tracking_report*Group*.xlsx",
    "*หัวลาก*LCB*.xlsx",
    "*หัวลาก*Fuel*.xlsx",
    "*.xlsx",
)

PAGES_SLUG = "lcb-fuel-dispatch"
GITHUB_PAGES_BASE = "https://yk-logistics.github.io/transport-rate-calculator"
OUT_PAGES_PATHS = (
    ROOT / "TransportRateCalculator" / "reports" / PAGES_SLUG / "index.html",
    ROOT.parent / "reports" / PAGES_SLUG / "index.html",
)


def publish_pages_html(html: str) -> Path:
    """Mirror static report to paths served by GitHub Pages after push."""
    last = OUT_PAGES_PATHS[0]
    for dest in OUT_PAGES_PATHS:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        last = dest
    return last

REFUEL_BUFFER_L = 12.5  # midpoint 10–15 L after trip
DEFAULT_DIESEL_BAHT = 42.20

JOB_COLORS = {
    "Haier": "#7c3aed",
    "KAO": "#0369a1",
    "Conti": "#0d9488",
    "Lacation": "#b45309",
    "คลังวาฬ": "#64748b",
    "Oatside": "#be185d",
}

EXCLUDED_DEFAULT = [
    ("71-8681", "รถเสีย — แผนใช้ 71-8684 แทน (พัฒิยะ)"),
    ("72-1219", "รถเสีย — ไม่จัดงาน"),
]


def _gps_search_dirs() -> list[Path]:
    home = Path.home()
    dirs = [
        GPS_INBOX,
        REPORTS_DIR,
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
    ]
    return [d for d in dirs if d.is_dir()]


def _find_default_xlsx() -> Path | None:
    """ไฟล์ Wialon .xlsx ล่าสุด — ห้ามใช้ CSV เก่าแทนโดยไม่รู้ตัว"""
    seen: set[str] = set()
    candidates: list[Path] = []
    for folder in _gps_search_dirs():
        for pattern in GPS_XLSX_GLOBS:
            for p in folder.glob(pattern):
                key = str(p.resolve()).lower()
                if key in seen:
                    continue
                seen.add(key)
                name = p.name.lower()
                if "fuel_dispatch_assign" in name:
                    continue
                if "fuel" not in name and "lcb" not in name and "tracking" not in name:
                    if folder != GPS_INBOX:
                        continue
                candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


PLATE_IN_GROUP_RE = re.compile(r"(\d{2}-\d{4}|บษ-\d{4})")


def plate_from_wialon_group(val) -> str | None:
    """ดึงทะเบียนจากคอลัมน์ การจัดกลุ่ม (แถวหัวกลุ่ม); แถวย่อย 7.1 ไม่มีทะเบียน"""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s == "รวมทั้งหมด":
        return None
    m = PLATE_IN_GROUP_RE.search(s)
    return m.group(1) if m else None


def parse_fuel_cell(val) -> float | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s in ("-----", "-", ""):
        return None
    m = re.search(r"([\d.,]+)", s.replace(",", ""))
    return float(m.group(1)) if m else None


def load_fuel_csv(path: Path) -> dict[str, dict]:
    df = pd.read_csv(path, encoding="utf-8-sig")
    out: dict[str, dict] = {}
    for _, r in df.iterrows():
        plate = str(r.get("plate", "")).strip()
        if not plate or plate in ("รวมทั้งหมด",):
            continue
        fuel = parse_fuel_cell(r.get("fuel_liters"))
        if fuel is None:
            continue
        ts_raw = r.get("latest_time", "")
        ts = pd.to_datetime(ts_raw, errors="coerce")
        out[plate] = {
            "fuel": fuel,
            "time_th": ts.strftime("%d/%m/%Y %H:%M") if pd.notna(ts) else str(ts_raw),
            "time_iso": ts.strftime("%Y-%m-%dT%H:%M:%S") if pd.notna(ts) else "",
            "location": str(r.get("location", "") or ""),
        }
    return out


def load_fuel_xlsx(path: Path) -> dict[str, dict]:
    """Wialon Group export: แถวย่อย (7.1) สืบทะเบียนจากแถวหัวกลุ่ม — ใช้ Time ล่าสุดจริง"""
    df = pd.read_excel(path, sheet_name="Fuel Level Sensor (L)")
    by: dict[str, dict] = {}
    current_plate: str | None = None
    loc_col = "Location" if "Location" in df.columns else None
    for _, r in df.iterrows():
        p = plate_from_wialon_group(r.get("การจัดกลุ่ม"))
        if p:
            current_plate = p
        plate = current_plate
        if not plate:
            continue
        fuel = parse_fuel_cell(r["Fuel Level Sensor (L)"])
        ts = pd.to_datetime(r["Time"], errors="coerce")
        if fuel is None or pd.isna(ts):
            continue
        loc = ""
        if loc_col and pd.notna(r.get(loc_col)):
            loc = str(r[loc_col]).strip()
        row = {
            "fuel": fuel,
            "time_th": ts.strftime("%d/%m/%Y %H:%M"),
            "time_iso": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": loc,
        }
        if plate not in by or ts > pd.to_datetime(by[plate].get("_ts", ts), errors="coerce"):
            row["_ts"] = ts
            by[plate] = row
    for v in by.values():
        v.pop("_ts", None)
    return by


def parse_add_fuel(items: list[str]) -> dict[str, float]:
    adj: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            continue
        plate, val = item.split("=", 1)
        plate = plate.strip()
        adj[plate] = adj.get(plate, 0.0) + float(val.strip())
    return adj


def build_rows(
    plan: ParsedPlan,
    fuel_by_plate: dict[str, dict],
    add_fuel: dict[str, float],
    *,
    include_oatside: bool = True,
) -> list[dict]:
    rows: list[dict] = []
    for a in plan.assignments:
        if a.job == "Oatside" and not include_oatside:
            continue
        gps = fuel_by_plate.get(a.plate, {})
        fuel_gps = gps.get("fuel")
        added = add_fuel.get(a.plate, 0.0)
        fuel_eff = (fuel_gps if fuel_gps is not None else 0.0) + added
        left = fuel_eff - a.need_liters
        needs_refuel = left < REFUEL_BUFFER_L
        min_refuel = max(0.0, a.need_liters - fuel_eff)
        refuel_to_buffer = max(0.0, a.need_liters + REFUEL_BUFFER_L - fuel_eff)

        rows.append(
            {
                "plate": a.plate,
                "job": a.job,
                "trips": a.trips,
                "liters_per_trip": a.liters_per_trip,
                "need": a.need_liters,
                "fuel_gps": fuel_gps,
                "fuel_added": added,
                "fuel": fuel_eff,
                "left": left,
                "needs_refuel": needs_refuel,
                "refuel_min_l": min_refuel,
                "refuel_buffer_l": refuel_to_buffer,
                "suggested_refill_l": round(refuel_to_buffer) if needs_refuel else 0,
                "driver": a.driver,
                "time_th": gps.get("time_th", "-"),
                "time_iso": gps.get("time_iso", ""),
                "location": gps.get("location", ""),
                "notes": " ".join(a.notes),
                "stale": False,
            }
        )
    return rows


def _render_table_row(r: dict, n: int, job: str) -> str:
    flags = []
    if r.get("fuel_added", 0) > 0:
        flags.append(
            f'<span class="badge badge-ok">เติมแล้ว +{r["fuel_added"]:.0f}ล.</span>'
        )
    if r["needs_refuel"]:
        flags.append('<span class="badge badge-risk">ต้องเติม</span>')
    if r.get("stale"):
        flags.append('<span class="badge badge-warn">ข้อมูลเก่า</span>')
    flag_html = " ".join(flags)
    gps_col = f'{r["fuel_gps"]:.0f}' if r["fuel_gps"] is not None else "—"
    added = int(r.get("fuel_added") or 0)
    suggest = int(r.get("suggested_refill_l") or 0)
    row_cls = f"job-{job}" + (" row-must-refuel" if r["needs_refuel"] else "")
    if added > 0:
        val_attr = f' value="{added}"'
        already_attr = f' data-already-fueled="{added}"'
        title = f"เติมแล้ว +{added} ล. (แก้ได้)"
    elif suggest > 0:
        val_attr = f' value="{suggest}"'
        already_attr = ''
        title = f"แนะนำ ~{suggest} ล. (ถึง buffer {REFUEL_BUFFER_L:.0f} ล.)"
    else:
        val_attr = ""
        already_attr = ''
        title = "ไม่บังคับเติม — ใส่ 0 ถ้าไม่เติม"
    fuel_gps_val = r["fuel_gps"] if r["fuel_gps"] is not None else 0.0
    plan_refill = added if added > 0 else suggest
    after_refill_plan = fuel_gps_val + plan_refill
    after_trip_plan = after_refill_plan - r["need"]
    low_plan = after_trip_plan < REFUEL_BUFFER_L
    return f"""<tr class="{row_cls}" data-plate="{r['plate']}">
  <td class="c-num">{n}</td>
  <td class="c-plate"><strong>{r['plate']}</strong><div class="sub">{r.get('driver','')}</div></td>
  <td class="c-job"><span class="job-pill" style="background:{JOB_COLORS.get(job,'#334155')}">{job}</span> <span class="trips">{r['trips']} เที่ยว</span></td>
  <td class="c-num">{r['need']:.0f}</td>
  <td class="c-num">{gps_col}</td>
  <td class="c-num">{r['fuel']:.0f}</td>
  <td class="c-num {'low' if r['left'] < REFUEL_BUFFER_L else ''}">{r['left']:.0f}</td>
  <td class="c-refill"><input type="number" class="refill-in" min="0" step="1" data-plate="{r['plate']}" data-need="{r['need']:.0f}" data-fuel-base="{fuel_gps_val:.0f}"{val_attr}{already_attr} title="{title}" aria-label="เติมลิตร {r['plate']}" /></td>
  <td class="c-num after-refill-plan" data-plate="{r['plate']}">{after_refill_plan:.0f}</td>
  <td class="c-num after-trip-plan {'low' if low_plan else ''}" data-plate="{r['plate']}">{after_trip_plan:.0f}</td>
  <td class="c-num refill-cost" data-plate="{r['plate']}">0</td>
  <td class="c-flags">{flag_html}</td>
  <td class="c-updated">{r['time_th']}</td>
</tr>"""


def render_html(rows: list[dict], meta: dict, excluded: list[tuple[str, str]]) -> str:
    data_json = json.dumps(
        {"assignments": rows, "meta": meta, "excluded": excluded},
        ensure_ascii=False,
    )
    body_rows = []
    job_order = ["Haier", "KAO", "Conti", "Lacation", "คลังวาฬ", "Oatside"]
    n = 0
    for job in job_order:
        for r in [x for x in rows if x["job"] == job]:
            n += 1
            body_rows.append(_render_table_row(r, n, job))

    refuel_rows = [r for r in rows if r["needs_refuel"]]
    refuel_html = ""
    if refuel_rows:
        refuel_lines = [
            f"<li><strong>{r['plate']}</strong> ({r['job']}) — หลังวิ่งเหลือ {r['left']:.0f} ล. "
            f"เติมขั้นต่ำ ~{r['refuel_min_l']:.0f} ล. / ถึง buffer ~{r['refuel_buffer_l']:.0f} ล.</li>"
            for r in refuel_rows
        ]
        refuel_html = f"""
    <section class="refuel-box">
      <h3>ยังต้องเติม (หลังวิ่ง &lt; {REFUEL_BUFFER_L:.0f} ล.)</h3>
      <ul>{''.join(refuel_lines)}</ul>
      <p class="cost-line">ประมาณเติมถึง buffer (ราคาเริ่มต้น): <strong id="buffer-liters-hint">{meta.get('refuel_buffer_total_l', 0):.0f} ล.</strong>
        ≈ <strong id="buffer-baht-hint">{meta.get('refuel_buffer_total_baht', 0):,.0f} บาท</strong></p>
    </section>"""

    tonight_html = ""
    if meta.get("tonight_refuel_l", 0) > 0:
        tonight_html = f"""
    <section class="tonight-box">
      <h3>เติมคืนนี้แล้ว (ตามที่โอแจ้ง)</h3>
      <p>{meta.get('tonight_refuel_detail', '')}</p>
      <p class="cost-line">รวม <strong>{meta['tonight_refuel_l']:.0f} ล.</strong>
        ≈ <strong id="tonight-baht">{meta['tonight_refuel_baht']:,.0f} บาท</strong></p>
    </section>"""

    excluded_html = "".join(
        f"<li><strong>{p}</strong> — {note}</li>" for p, note in excluded
    )

    diesel_default = meta.get("diesel_price", DEFAULT_DIESEL_BAHT)
    budget_low = meta.get("budget_cap_low", 5000)
    budget_high = meta.get("budget_cap_high", 10000)

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>แผน LCB จากแผน LINE + GPS น้ำมัน</title>
  <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: "Sarabun", "Tahoma", sans-serif; font-size: 14px; color: #0f172a; background: #f1f5f9; line-height: 1.45;
      -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .toolbar {{ max-width: 1200px; margin: 12px auto; padding: 14px 18px; background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .toolbar h2 {{ font-size: 1rem; margin-bottom: 8px; }}
    .toolbar p {{ font-size: 0.85rem; color: #475569; margin-bottom: 8px; }}
    .toolbar-row {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 10px; }}
    .price-box {{ display: flex; align-items: center; gap: 8px; font-size: 0.9rem; }}
    .price-box input {{ width: 88px; padding: 7px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: inherit; font-weight: 700; }}
    .btn-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .btn {{ border: none; border-radius: 8px; padding: 9px 16px; font-family: inherit; font-weight: 600; cursor: pointer; color: #fff; }}
    .btn-print {{ background: #1e40af; }}
    .btn-png {{ background: #0f766e; }}
    .btn-xlsx {{ background: #166534; }}
    .btn:hover {{ filter: brightness(1.08); }}
    #report {{ max-width: 1200px; margin: 0 auto 24px; background: #fff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,.1); overflow: hidden; }}
    .report-head {{ padding: 20px 22px 14px; border-bottom: 3px solid #1e3a8a; background: linear-gradient(135deg, #eff6ff 0%, #fff 60%); }}
    .report-head h1 {{ font-size: 1.4rem; font-weight: 800; color: #1e3a8a; }}
    .report-head .sub {{ color: #64748b; font-size: 0.88rem; margin-top: 4px; }}
    .pages-url-note {{ background: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px; padding: 8px 10px; margin-top: 8px; }}
    .pages-url-note a {{ color: #1d4ed8; font-weight: 700; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; padding: 14px 22px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
    .sum-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; }}
    .sum-card .lbl {{ font-size: 0.75rem; color: #64748b; }}
    .sum-card .val {{ font-size: 1.15rem; font-weight: 800; }}
    .sum-card .val.live {{ color: #1d4ed8; }}
    .sum-card.highlight {{ border-color: #93c5fd; background: #eff6ff; }}
    .budget-wrap {{ padding: 12px 22px 6px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
    .budget-wrap h3 {{ font-size: 0.85rem; color: #64748b; margin-bottom: 8px; font-weight: 700; }}
    .budget-labels {{ display: flex; justify-content: space-between; font-size: 0.72rem; color: #64748b; margin-bottom: 4px; }}
    .budget-track {{ position: relative; height: 14px; border-radius: 999px; background: linear-gradient(90deg, #dcfce7 0%, #fef9c3 50%, #fee2e2 100%); overflow: visible; }}
    .budget-marker {{ position: absolute; top: -4px; width: 4px; height: 22px; background: #1e3a8a; border-radius: 2px; transform: translateX(-50%); box-shadow: 0 0 0 2px #fff; }}
    .budget-status {{ margin-top: 6px; font-size: 0.82rem; color: #475569; }}
    .budget-status strong {{ color: #0f172a; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    thead th {{ background: #1e3a8a; color: #fff; padding: 10px 8px; text-align: left; }}
    tbody td {{ padding: 9px 8px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
    tbody tr:nth-child(even) {{ background: #f8fafc; }}
    .c-num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .c-num.low {{ color: #b91c1c; font-weight: 800; }}
    .c-plate .sub {{ font-size: 0.75rem; color: #64748b; font-weight: 400; }}
    .trips {{ font-size: 0.75rem; color: #64748b; }}
    .job-pill {{ display: inline-block; color: #fff; font-size: 0.78rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
    .badge {{ display: inline-block; font-size: 0.68rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; }}
    .badge-risk {{ background: #fee2e2; color: #991b1b; }}
    .badge-warn {{ background: #fef3c7; color: #92400e; }}
    .badge-ok {{ background: #dcfce7; color: #166534; }}
    .c-refill input.refill-in {{ width: 64px; padding: 5px 6px; border: 1px solid #cbd5e1; border-radius: 6px; text-align: right; font-variant-numeric: tabular-nums; font-family: inherit; }}
    tr.row-must-refuel .c-refill input {{ border-color: #f97316; background: #fff7ed; }}
    tr.row-must-refuel td {{ background: #fffbeb; }}
    .refuel-box, .tonight-box, .excluded {{ padding: 14px 22px; border-top: 1px solid #e2e8f0; }}
    .refuel-box {{ background: #fff7ed; }}
    .tonight-box {{ background: #ecfdf5; }}
    .cost-line {{ margin-top: 8px; font-size: 0.95rem; }}
    .excluded ul {{ margin-left: 18px; color: #475569; }}
    .foot-note {{ padding: 10px 22px 16px; font-size: 0.78rem; color: #94a3b8; }}
    @media print {{ .toolbar {{ display: none !important; }} body {{ background: #fff; }} #report {{ box-shadow: none; }} }}
  </style>
</head>
<body>
  <div class="toolbar no-print">
    <h2>LCB fuel dispatch — LINE plan + GPS</h2>
    <p>Build: <code>build_lcb_fuel_dispatch.bat</code> · ตารางแสดง<strong>ทุกคันในแผน</strong> (ไม่กรองเฉพาะต้องเติม) · แถวส้ม = ต้องเติม</p>
    <p>Pages: <a href="{GITHUB_PAGES_BASE}/reports/{PAGES_SLUG}/" target="_blank" rel="noopener">{GITHUB_PAGES_BASE}/reports/{PAGES_SLUG}/</a>
      (ไม่ใช่หน้าแรก transport-rate-calculator)</p>
    <div class="toolbar-row">
      <label class="price-box">Diesel price (฿/L)
        <input type="number" id="diesel-price" min="0" step="0.01" value="{diesel_default:.2f}" />
      </label>
      <label class="price-box">งบต่ำสุด (฿)
        <input type="number" id="budget-low" min="0" step="100" value="{int(budget_low)}" />
      </label>
      <label class="price-box">งบสูงสุด (฿)
        <input type="number" id="budget-high" min="0" step="100" value="{int(budget_high)}" />
      </label>
      <div class="btn-row">
        <button type="button" class="btn btn-print" onclick="window.print()">Print / PDF</button>
        <button type="button" class="btn btn-png" onclick="exportPng()">Save PNG</button>
        <button type="button" class="btn btn-xlsx" onclick="exportExcel()">Download Excel (CSV)</button>
      </div>
    </div>
  </div>
  <div id="report">
    <header class="report-head">
      <h1>แผนจัดคัน LCB — แผน LINE + น้ำมัน GPS</h1>
      <p class="sub">แผน {meta.get('plan_file', '')} · สร้าง {meta['generated_th']}</p>
      <p class="sub">แหล่งน้ำมัน: {meta.get('fuel_source', '')} · เที่ยวตู้ (ไม่รวม Oatside): {meta.get('container_trips_dispatch', 0)} · หัวแผน LINE วิ่ง: {meta.get('header_running', '—')}</p>
      <p class="sub">กติกาเติม: แจ้งเมื่อหลังวิ่งเหลือ &lt; {REFUEL_BUFFER_L:.0f} ล. · ราคา diesel สมมติ {meta.get('diesel_price', 32):.2f} บาท/ล. {meta.get('price_note', '')}</p>
      <p class="sub pages-url-note"><strong>ลิงก์สาธารณะ (GitHub Pages):</strong>
        <a href="{GITHUB_PAGES_BASE}/reports/{PAGES_SLUG}/">{GITHUB_PAGES_BASE}/reports/{PAGES_SLUG}/</a>
        — ไม่ใช่หน้า <a href="{GITHUB_PAGES_BASE}/">{GITHUB_PAGES_BASE}/</a> (เครื่องคิดเรทขนส่ง)
        · ไฟล์ HTML ในเครื่อง/โฟลเดอร์โปรเจกต์ = สำเนาหลัง build — ต้อง push ถึงจะอัปเดตบนเน็ต</p>
    </header>
    <div class="summary">
      <div class="sum-card"><div class="lbl">เที่ยวตู้ / หัวแผนวิ่ง</div><div class="val">{meta.get('container_trips_dispatch', 0)} / {meta.get('header_running', '—')}</div></div>
      <div class="sum-card"><div class="lbl">ใช้ตามสูตร</div><div class="val">{meta.get('fuel_need', 0):.0f} ล.</div></div>
      <div class="sum-card"><div class="lbl">เติมคืนนี้</div><div class="val">{meta.get('tonight_refuel_baht', 0):,.0f} ฿</div></div>
      <div class="sum-card"><div class="lbl">ยังต้องเติม (buffer)</div><div class="val">{meta.get('refuel_buffer_total_baht', 0):,.0f} ฿</div></div>
      <div class="sum-card highlight"><div class="lbl">แผนเติมวันนี้ (ที่กรอก)</div><div class="val live" id="sum-planned-liters">0 ล.</div></div>
      <div class="sum-card highlight"><div class="lbl">ค่าแผนเติมวันนี้</div><div class="val live" id="sum-planned-baht">0 ฿</div></div>
      <div class="sum-card"><div class="lbl">งบรวม (เติมแล้ว+แผน)</div><div class="val" id="sum-total-baht">{meta.get('total_spend_baht', 0):,.0f} ฿</div></div>
    </div>
    <div class="budget-wrap">
      <h3>Budget helper (<span id="budget-range-label">{budget_low:,} – {budget_high:,}</span> ฿)</h3>
      <div class="budget-labels"><span id="budget-label-low">{budget_low:,} ฿</span><span id="budget-label-high">{budget_high:,} ฿</span></div>
      <div class="budget-track"><div class="budget-marker" id="budget-marker" style="left:0%"></div></div>
      <p class="budget-status" id="budget-status">—</p>
    </div>
    {tonight_html}
    <table id="dispatch-table">
      <thead><tr>
        <th class="c-num">#</th><th>ทะเบียน</th><th>งาน</th>
        <th class="c-num">ใช้(ล.)</th><th class="c-num">GPS</th><th class="c-num">หลังเติม</th>
        <th class="c-num">หลังวิ่ง</th><th class="c-num">เติมวันนี้(ล.)</th>
        <th class="c-num" title="GPS+เติมแล้ว+ที่กรอก">หลังเติม(แผน)</th>
        <th class="c-num" title="หลังเติม(แผน)−ใช้(ล.)">หลังวิ่ง(แผน)</th>
        <th class="c-num">ค่าเติม(฿)</th>
        <th>สถานะ</th><th class="c-updated">GPS อัปเดต</th>
      </tr></thead>
      <tbody>
{chr(10).join(body_rows)}
      </tbody>
    </table>
    {refuel_html}
    <section class="excluded"><h3>ไม่จัด / พิเศษ</h3><ul>{excluded_html}</ul></section>
    <p class="foot-note">สูตร: KAO/Conti/Lacation 50·Haier 100·คลังวาฬ 25/เที่ยว·Oatside ~110/วัน · หลังเติม/หลังวิ่ง(แผน) = หลังเติมระบบ + ลิตรที่กรอก · Project YK</p>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script>
    const REPORT_DATA = {data_json};
    const REFUEL_BUFFER_L = {REFUEL_BUFFER_L};
    let BUDGET_LOW = {budget_low};
    let BUDGET_HIGH = {budget_high};
    const TONIGHT_BAHT = {meta.get('tonight_refuel_baht', 0)};

    function getBudgetCaps() {{
      const lo = parseFloat(document.getElementById('budget-low')?.value);
      const hi = parseFloat(document.getElementById('budget-high')?.value);
      if (Number.isFinite(lo) && lo >= 0) BUDGET_LOW = lo;
      if (Number.isFinite(hi) && hi > 0) BUDGET_HIGH = hi;
      if (BUDGET_HIGH < BUDGET_LOW) BUDGET_HIGH = BUDGET_LOW + 1000;
      const lbl = document.getElementById('budget-range-label');
      const ll = document.getElementById('budget-label-low');
      const lh = document.getElementById('budget-label-high');
      const fmt = n => Math.round(n).toLocaleString('th-TH');
      if (lbl) lbl.textContent = fmt(BUDGET_LOW) + ' – ' + fmt(BUDGET_HIGH);
      if (ll) ll.textContent = fmt(BUDGET_LOW) + ' ฿';
      if (lh) lh.textContent = fmt(BUDGET_HIGH) + ' ฿';
    }}

    function getDieselPrice() {{
      const el = document.getElementById('diesel-price');
      const v = parseFloat(el && el.value);
      return Number.isFinite(v) && v >= 0 ? v : {diesel_default};
    }}

    function refillLiters(inp) {{
      const v = parseFloat(inp && inp.value);
      return Number.isFinite(v) && v > 0 ? v : 0;
    }}

    function fmtBaht(n) {{
      return Math.round(n).toLocaleString('th-TH');
    }}

    function fmtLiters(n) {{
      return Math.round(n).toLocaleString('th-TH');
    }}

    function setPlanFuelCells(inp, planL) {{
      const plate = inp.dataset.plate;
      const base = parseFloat(inp.dataset.fuelBase) || 0;
      const need = parseFloat(inp.dataset.need) || 0;
      const afterRefill = base + planL;
      const afterTrip = afterRefill - need;
      const low = afterTrip < REFUEL_BUFFER_L;
      const ar = document.querySelector('.after-refill-plan[data-plate="' + plate + '"]');
      const at = document.querySelector('.after-trip-plan[data-plate="' + plate + '"]');
      if (ar) ar.textContent = fmtLiters(afterRefill);
      if (at) {{
        at.textContent = fmtLiters(afterTrip);
        at.classList.toggle('low', low);
      }}
    }}

    function recalcAll() {{
      getBudgetCaps();
      const price = getDieselPrice();
      let plannedL = 0;
      let plannedB = 0;
      document.querySelectorAll('.refill-in').forEach(inp => {{
        const L = refillLiters(inp);
        const alreadyFueled = parseFloat(inp.dataset.alreadyFueled || 0);
        const extraL = Math.max(0, L - alreadyFueled);
        const cost = extraL * price;
        plannedL += extraL;
        plannedB += cost;
        setPlanFuelCells(inp, L);
        const cell = document.querySelector('.refill-cost[data-plate="' + inp.dataset.plate + '"]');
        if (cell) cell.textContent = extraL > 0 ? fmtBaht(cost) : '0';
      }});
      const totalB = TONIGHT_BAHT + plannedB;
      const elL = document.getElementById('sum-planned-liters');
      const elB = document.getElementById('sum-planned-baht');
      const elT = document.getElementById('sum-total-baht');
      if (elL) elL.textContent = plannedL.toFixed(0) + ' ล.';
      if (elB) elB.textContent = fmtBaht(plannedB) + ' ฿';
      if (elT) elT.textContent = fmtBaht(totalB) + ' ฿';
      const marker = document.getElementById('budget-marker');
      const status = document.getElementById('budget-status');
      const pct = Math.min(100, Math.max(0, (totalB / BUDGET_HIGH) * 100));
      if (marker) marker.style.left = pct + '%';
      let msg = 'รวมงบ <strong>' + fmtBaht(totalB) + ' ฿</strong> (เติมคืนนี้ ' + fmtBaht(TONIGHT_BAHT) + ' + แผนเติม ' + fmtBaht(plannedB) + ')';
      if (totalB < BUDGET_LOW) msg += ' · ต่ำกว่าเป้า ' + fmtBaht(BUDGET_LOW);
      else if (totalB <= BUDGET_HIGH) msg += ' · <span style="color:#166534">อยู่ในช่วง ' + fmtBaht(BUDGET_LOW) + '–' + fmtBaht(BUDGET_HIGH) + '</span>';
      else msg += ' · <span style="color:#b91c1c">เกิน ' + fmtBaht(BUDGET_HIGH) + ' ฿</span>';
      if (status) status.innerHTML = msg;
      const bufL = REPORT_DATA.assignments.filter(r => r.needs_refuel).reduce((s, r) => s + (r.refuel_buffer_l || 0), 0);
      const hintL = document.getElementById('buffer-liters-hint');
      const hintB = document.getElementById('buffer-baht-hint');
      if (hintL) hintL.textContent = bufL.toFixed(0) + ' ล.';
      if (hintB) hintB.textContent = fmtBaht(bufL * price) + ' บาท';
    }}

    document.getElementById('diesel-price').addEventListener('input', recalcAll);
    document.getElementById('budget-low')?.addEventListener('input', recalcAll);
    document.getElementById('budget-high')?.addEventListener('input', recalcAll);
    document.querySelectorAll('.refill-in').forEach(inp => inp.addEventListener('input', recalcAll));
    recalcAll();

    async function exportPng() {{
      const el = document.getElementById('report');
      const canvas = await html2canvas(el, {{ scale: 2, backgroundColor: '#ffffff', useCORS: true }});
      const a = document.createElement('a');
      a.download = 'LCB_fuel_dispatch_' + new Date().toISOString().slice(0, 10) + '.png';
      a.href = canvas.toDataURL('image/png');
      a.click();
    }}

    function exportExcel() {{
      const price = getDieselPrice();
      const header = ['ลำดับ','ทะเบียน','งาน','เที่ยว','ใช้(ล.)','GPS(ล.)','หลังเติม(ล.)','หลังวิ่ง(ล.)','เติมวันนี้(ล.)','หลังเติม(แผน)','หลังวิ่ง(แผน)','ค่าเติม(฿)','แนะนำเติม(ล.)','สถานะ','GPSอัปเดต'];
      const lines = [header.join(',')];
      const byPlate = Object.fromEntries(REPORT_DATA.assignments.map(r => [r.plate, r]));
      document.querySelectorAll('#dispatch-table tbody tr').forEach((tr, i) => {{
        const plate = tr.dataset.plate;
        const r = byPlate[plate] || {{}};
        const inp = tr.querySelector('.refill-in');
        const L = refillLiters(inp);
        const notes = [];
        if (r.fuel_added > 0) notes.push('เติมแล้ว+' + r.fuel_added);
        if (r.needs_refuel) notes.push('ต้องเติม');
        if (r.stale) notes.push('ข้อมูลเก่า');
        const gps = r.fuel_gps != null ? r.fuel_gps : '';
        const baseGps = r.fuel_gps != null ? r.fuel_gps : 0;
        const afterRefill = baseGps + L;
        const afterTrip = afterRefill - (r.need || 0);
        lines.push([
          i + 1, plate, r.job || '', r.trips || '', r.need || '', gps, r.fuel || '', r.left || '',
          L, Math.round(afterRefill), Math.round(afterTrip),
          Math.round(L * price), r.suggested_refill_l || 0, notes.join(' '), r.time_th || ''
        ].join(','));
      }});
      const blob = new Blob(['\\ufeff' + lines.join('\\n')], {{ type: 'text/csv;charset=utf-8' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'LCB_fuel_dispatch_' + new Date().toISOString().slice(0, 10) + '.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    }}
  </script>
</body>
</html>"""


def _apply_fuel_path(path: Path | None, *, fuel_csv: Path | None, fuel_xlsx: Path | None) -> tuple[Path | None, Path | None]:
    """Map positional fuel file or keep explicit --fuel-* flags."""
    if path is None or not path.exists():
        return fuel_csv, fuel_xlsx
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return fuel_csv, path
    return path, fuel_xlsx


def main() -> int:
    ap = argparse.ArgumentParser(description="LCB fuel dispatch from LINE plan + GPS")
    ap.add_argument("plan_txt", type=Path, help="Junior plan .txt from LINE")
    ap.add_argument(
        "fuel_file",
        nargs="?",
        type=Path,
        default=None,
        help="GPS fuel .xlsx/.csv (optional; same as --fuel-xlsx/--fuel-csv)",
    )
    ap.add_argument("--fuel-csv", type=Path, default=None)
    ap.add_argument("--fuel-xlsx", type=Path, default=None)
    ap.add_argument("--add-fuel", action="append", default=[], metavar="PLATE=L")
    ap.add_argument("--diesel-price", type=float, default=DEFAULT_DIESEL_BAHT)
    ap.add_argument("--budget-low", type=float, default=5000, help="งบขั้นต่ำ (฿)")
    ap.add_argument("--budget-high", type=float, default=10000, help="งบสูงสุด (฿)")
    ap.add_argument(
        "--allow-stale-csv",
        action="store_true",
        help="อนุญาตใช้ fuel_level_latest_*.csv ใน reports (ไม่แนะนำ)",
    )
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    args.fuel_csv, args.fuel_xlsx = _apply_fuel_path(
        args.fuel_file, fuel_csv=args.fuel_csv, fuel_xlsx=args.fuel_xlsx
    )

    if not args.plan_txt.exists():
        print(f"ไม่พบแผน: {args.plan_txt}")
        return 1

    plan = parse_plan_file(args.plan_txt)
    add_fuel = parse_add_fuel(args.add_fuel)

    fuel_by: dict[str, dict] = {}
    fuel_source = ""
    if args.fuel_xlsx and args.fuel_xlsx.exists():
        fuel_by = load_fuel_xlsx(args.fuel_xlsx)
        fuel_source = args.fuel_xlsx.name
    elif args.fuel_csv and args.fuel_csv.exists():
        fuel_by = load_fuel_csv(args.fuel_csv)
        fuel_source = args.fuel_csv.name
    else:
        xlsx = _find_default_xlsx()
        if xlsx:
            fuel_by = load_fuel_xlsx(xlsx)
            fuel_source = f"{xlsx.name} ({xlsx.parent.name})"
            print(f"GPS: {xlsx}")
        elif args.allow_stale_csv and DEFAULT_FUEL_CSV.exists():
            fuel_by = load_fuel_csv(DEFAULT_FUEL_CSV)
            fuel_source = f"{DEFAULT_FUEL_CSV.name} (CSV เก่า)"
            print(f"[WARN] ใช้ CSV เก่า: {DEFAULT_FUEL_CSV.name}")
        else:
            print("ไม่พบไฟล์ GPS .xlsx")
            print(f"  วางไฟล์ Wialon ลง: {GPS_INBOX}")
            print("  หรือลาก .xlsx มาวางบน build_lcb_fuel_dispatch.bat")
            print("  หรือรัน: python ... plan.txt \"C:\\path\\to\\report.xlsx\"")
            return 1

    rows = build_rows(plan, fuel_by, add_fuel)
    dispatch_rows = [r for r in rows if r["job"] != "Oatside"]

    tonight_l = sum(add_fuel.values())
    tonight_baht = tonight_l * args.diesel_price
    refuel_buffer_l = sum(r["refuel_buffer_l"] for r in dispatch_rows if r["needs_refuel"])
    refuel_buffer_baht = refuel_buffer_l * args.diesel_price
    total_spend = tonight_baht + refuel_buffer_baht

    tstats = plan_trip_stats(plan)
    trip_count = tstats["container_trips_dispatch"]
    fuel_need = sum(a.need_liters for a in plan.assignments if a.job != "Oatside")

    excluded = list(EXCLUDED_DEFAULT)
    if plan.broken_plates:
        for p in sorted(plan.broken_plates):
            if not any(p == x[0] for x in excluded):
                excluded.append((p, "รถเสีย/ไม่วิ่งตาม Remark"))

    tonight_detail = ", ".join(
        f"{p} +{v:.0f} ล." for p, v in sorted(add_fuel.items())
    )

    meta = {
        "generated_th": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "plan_file": args.plan_txt.name,
        "fuel_source": fuel_source,
        "trip_count": trip_count,
        "container_trips_dispatch": trip_count,
        "container_trips_all": tstats["container_trips_all"],
        "trucks_dispatch": tstats["trucks_dispatch"],
        "trucks_with_oatside": tstats["trucks_with_oatside"],
        "header_running": plan.header_running,
        "header_continuity": plan.header_continuity,
        "header_repair": plan.header_repair,
        "header_truck_mismatch": (
            plan.header_running is not None
            and tstats["trucks_with_oatside"] != plan.header_running
        ),
        "header_container_mismatch": (
            plan.header_running is not None and trip_count != plan.header_running
        ),
        "fuel_need": fuel_need,
        "diesel_price": args.diesel_price,
        "price_note": "(ค่าเริ่มต้น — ปรับด้วย --diesel-price หรือดู FuelPriceIndex ในแอป)",
        "tonight_refuel_l": tonight_l,
        "tonight_refuel_baht": tonight_baht,
        "tonight_refuel_detail": tonight_detail or "—",
        "refuel_buffer_total_l": refuel_buffer_l,
        "refuel_buffer_total_baht": refuel_buffer_baht,
        "total_spend_baht": total_spend,
        "budget_cap_low": args.budget_low,
        "budget_cap_high": args.budget_high,
        "within_budget": args.budget_low <= total_spend <= args.budget_high,
    }

    html = render_html(rows, meta, excluded)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    pages_index = publish_pages_html(html)

    stamp = datetime.now().strftime("%Y-%m-%d")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    snap_xlsx = REPORTS_DIR / f"fuel_dispatch_assign_{stamp}.xlsx"
    df = pd.DataFrame(
        [
            {
                "ทะเบียน": r["plate"],
                "งาน": r["job"],
                "เที่ยว": r["trips"],
                "ใช้(ล.)": r["need"],
                "GPS(ล.)": r["fuel_gps"],
                "เติมเพิ่ม(ล.)": r["fuel_added"],
                "หลังเติม(ล.)": r["fuel"],
                "หลังวิ่ง(ล.)": r["left"],
                "ต้องเติม": "ใช่" if r["needs_refuel"] else "",
                "เติมขั้นต่ำ(ล.)": r["refuel_min_l"],
                "เติมถึงbuffer(ล.)": r["refuel_buffer_l"],
                "แนะนำเติม(ล.)": r.get("suggested_refill_l", 0),
                "เติมวันนี้(ล.)": "",
                "GPSอัปเดต": r["time_th"],
            }
            for r in rows
        ]
    )
    df.to_excel(snap_xlsx, index=False)

    print(f"OK HTML: {OUT_HTML}")
    print(f"OK Pages: {pages_index}")
    print(f"GitHub Pages (after commit + push): {GITHUB_PAGES_BASE}/reports/{PAGES_SLUG}/")
    print(f"OK XLSX: {snap_xlsx}")
    print(
        f"เที่ยวตู้ (ไม่รวม Oatside): {trip_count} | หัวแผน LINE วิ่ง: {plan.header_running or '—'}"
    )
    print(
        f"คันงาน: {tstats['trucks_dispatch']} คัน (ไม่รวม Oatside) + Oatside {len([a for a in plan.assignments if a.job == 'Oatside'])} = {tstats['trucks_with_oatside']} คัน"
    )
    if plan.header_running is not None:
        if tstats["trucks_with_oatside"] == plan.header_running:
            print(f"✓ จำนวนคันตรงหัวแผน (งาน/วิ่ง {plan.header_running} คัน รวม Oatside)")
        else:
            print(
                f"⚠ คันงาน {tstats['trucks_with_oatside']} ต่างจากหัวแผน {plan.header_running}"
            )
        if trip_count != plan.header_running:
            print(
                f"  เที่ยวตู้ {trip_count} ต่างจากหัวแผน {plan.header_running} +1 — "
                "คลังวาฬ 2 หัว × 2 ตู้ (งบน้ำมันนับตู้จริง)"
            )
    print(f"เติมคืนนี้: {tonight_l:.0f} ล. ≈ {tonight_baht:,.0f} บาท")
    still = [r for r in dispatch_rows if r["needs_refuel"]]
    if still:
        print("ยังต้องเติม (หลังวิ่ง < buffer):")
        for r in still:
            print(
                f"  {r['plate']} {r['job']}: เหลือ {r['left']:.0f} ล. "
                f"→ เติมขั้นต่ำ {r['refuel_min_l']:.0f} ล. / ถึง buffer {r['refuel_buffer_l']:.0f} ล."
            )
        print(
            f"รวมถึง buffer ≈ {refuel_buffer_l:.0f} ล. ≈ {refuel_buffer_baht:,.0f} บาท"
        )
    else:
        print("ไม่มีคันที่หลังวิ่งต่ำกว่า buffer (หลังเติมคืนนี้)")
    print(
        f"งบรวมคืนนี้ (เติมแล้ว + ยังต้องเติมถึง buffer): ≈ {total_spend:,.0f} บาท "
        f"(เป้าไม่เกิน 5,000–10,000 บาท)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
