# -*- coding: utf-8 -*-
"""
LCB fuel dispatch from LINE plan .txt + GPS fuel (CSV or Wialon .xlsx).

  python ProjectYK_System/tools/build_lcb_fuel_dispatch_from_plan.py plan.txt
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
DEFAULT_FUEL_CSV = REPORTS_DIR / "fuel_level_latest_LCB_2026-05-20.csv"

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


def _find_default_xlsx() -> Path | None:
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return None
    candidates = sorted(
        downloads.glob("*Fuel_Level*LCB*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


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
    df = pd.read_excel(path, sheet_name="Fuel Level Sensor (L)")
    by: dict[str, dict] = {}
    for _, r in df.iterrows():
        grp = str(r["การจัดกลุ่ม"]).split()[0] if pd.notna(r["การจัดกลุ่ม"]) else ""
        if not grp or grp == "รวมทั้งหมด":
            continue
        fuel = parse_fuel_cell(r["Fuel Level Sensor (L)"])
        ts = pd.to_datetime(r["Time"], errors="coerce")
        if fuel is None or pd.isna(ts):
            continue
        row = {
            "fuel": fuel,
            "time_th": ts.strftime("%d/%m/%Y %H:%M"),
            "time_iso": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": "",
        }
        if grp not in by or ts > pd.to_datetime(by[grp].get("_ts", ts), errors="coerce"):
            row["_ts"] = ts
            by[grp] = row
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
                "driver": a.driver,
                "time_th": gps.get("time_th", "-"),
                "time_iso": gps.get("time_iso", ""),
                "location": gps.get("location", ""),
                "notes": " ".join(a.notes),
                "stale": False,
            }
        )
    return rows


def render_html(rows: list[dict], meta: dict, excluded: list[tuple[str, str]]) -> str:
    data_json = json.dumps(
        {"assignments": rows, "meta": meta, "excluded": excluded},
        ensure_ascii=False,
    )
    body_rows = []
    job_order = ["Haier", "KAO", "Conti", "Lacation", "คลังวาฬ", "Oatside"]
    n = 0
    for job in job_order:
        job_rows = [r for r in rows if r["job"] == job]
        for r in job_rows:
            n += 1
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
            body_rows.append(
                f"""<tr class="job-{job}">
  <td class="c-num">{n}</td>
  <td class="c-plate"><strong>{r['plate']}</strong><div class="sub">{r.get('driver','')}</div></td>
  <td class="c-job"><span class="job-pill" style="background:{JOB_COLORS.get(job,'#334155')}">{job}</span> <span class="trips">{r['trips']} เที่ยว</span></td>
  <td class="c-num">{r['need']:.0f}</td>
  <td class="c-num">{gps_col}</td>
  <td class="c-num">{r['fuel']:.0f}</td>
  <td class="c-num {'low' if r['left'] < REFUEL_BUFFER_L else ''}">{r['left']:.0f}</td>
  <td class="c-flags">{flag_html}</td>
  <td class="c-updated">{r['time_th']}</td>
</tr>"""
            )

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
      <p class="cost-line">ประมาณเติมถึง buffer: <strong>{meta.get('refuel_buffer_total_l', 0):.0f} ล.</strong>
        ≈ <strong>{meta.get('refuel_buffer_total_baht', 0):,.0f} บาท</strong> (@ {meta.get('diesel_price', 32):.2f} บาท/ล.)</p>
    </section>"""

    tonight_html = ""
    if meta.get("tonight_refuel_l", 0) > 0:
        tonight_html = f"""
    <section class="tonight-box">
      <h3>เติมคืนนี้แล้ว (ตามที่โอแจ้ง)</h3>
      <p>{meta.get('tonight_refuel_detail', '')}</p>
      <p class="cost-line">รวม <strong>{meta['tonight_refuel_l']:.0f} ล.</strong>
        ≈ <strong>{meta['tonight_refuel_baht']:,.0f} บาท</strong></p>
    </section>"""

    excluded_html = "".join(
        f"<li><strong>{p}</strong> — {note}</li>" for p, note in excluded
    )

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
    .toolbar {{ max-width: 1140px; margin: 12px auto; padding: 14px 18px; background: #fff; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .toolbar h2 {{ font-size: 1rem; margin-bottom: 8px; }}
    .toolbar p {{ font-size: 0.85rem; color: #475569; margin-bottom: 8px; }}
    .btn {{ border: none; border-radius: 8px; padding: 9px 16px; font-family: inherit; font-weight: 600; cursor: pointer; background: #1e40af; color: #fff; }}
    #report {{ max-width: 1140px; margin: 0 auto 24px; background: #fff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,.1); overflow: hidden; }}
    .report-head {{ padding: 20px 22px 14px; border-bottom: 3px solid #1e3a8a; background: linear-gradient(135deg, #eff6ff 0%, #fff 60%); }}
    .report-head h1 {{ font-size: 1.4rem; font-weight: 800; color: #1e3a8a; }}
    .report-head .sub {{ color: #64748b; font-size: 0.88rem; margin-top: 4px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; padding: 14px 22px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
    .sum-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; }}
    .sum-card .lbl {{ font-size: 0.75rem; color: #64748b; }}
    .sum-card .val {{ font-size: 1.15rem; font-weight: 800; }}
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
    <h2>แผน LCB — จากแผน LINE + GPS</h2>
    <p>รัน <code>build_lcb_fuel_dispatch.bat</code> พร้อม path แผน .txt และ (ถ้ามี) ไฟล์ fuel .csv / .xlsx</p>
    <button type="button" class="btn" onclick="window.print()">พิมพ์ / PDF</button>
  </div>
  <div id="report">
    <header class="report-head">
      <h1>แผนจัดคัน LCB — แผน LINE + น้ำมัน GPS</h1>
      <p class="sub">แผน {meta.get('plan_file', '')} · สร้าง {meta['generated_th']}</p>
      <p class="sub">แหล่งน้ำมัน: {meta.get('fuel_source', '')} · เที่ยวตู้ (ไม่รวม Oatside): {meta.get('container_trips_dispatch', 0)} · หัวแผน LINE วิ่ง: {meta.get('header_running', '—')}</p>
      <p class="sub">กติกาเติม: แจ้งเมื่อหลังวิ่งเหลือ &lt; {REFUEL_BUFFER_L:.0f} ล. · ราคา diesel สมมติ {meta.get('diesel_price', 32):.2f} บาท/ล. {meta.get('price_note', '')}</p>
    </header>
    <div class="summary">
      <div class="sum-card"><div class="lbl">เที่ยวตู้ / หัวแผนวิ่ง</div><div class="val">{meta.get('container_trips_dispatch', 0)} / {meta.get('header_running', '—')}</div></div>
      <div class="sum-card"><div class="lbl">ใช้ตามสูตร</div><div class="val">{meta.get('fuel_need', 0):.0f} ล.</div></div>
      <div class="sum-card"><div class="lbl">เติมคืนนี้</div><div class="val">{meta.get('tonight_refuel_baht', 0):,.0f} ฿</div></div>
      <div class="sum-card"><div class="lbl">ยังต้องเติม (buffer)</div><div class="val">{meta.get('refuel_buffer_total_baht', 0):,.0f} ฿</div></div>
      <div class="sum-card"><div class="lbl">งบรวมคืนนี้</div><div class="val">{meta.get('total_spend_baht', 0):,.0f} ฿</div></div>
    </div>
    {tonight_html}
    <table>
      <thead><tr>
        <th class="c-num">#</th><th>ทะเบียน</th><th>งาน</th>
        <th class="c-num">ใช้(ล.)</th><th class="c-num">GPS</th><th class="c-num">หลังเติม</th>
        <th class="c-num">หลังวิ่ง</th><th>สถานะ</th><th class="c-updated">GPS อัปเดต</th>
      </tr></thead>
      <tbody>
{chr(10).join(body_rows)}
      </tbody>
    </table>
    {refuel_html}
    <section class="excluded"><h3>ไม่จัด / พิเศษ</h3><ul>{excluded_html}</ul></section>
    <p class="foot-note">สูตร: KAO/Conti/Lacation 50·Haier 100·คลังวาฬ 25/เที่ยว·Oatside ~110/วัน · Project YK</p>
  </div>
  <script>const REPORT_DATA = {data_json};</script>
</body>
</html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="LCB fuel dispatch from LINE plan + GPS")
    ap.add_argument("plan_txt", type=Path, help="Junior plan .txt from LINE")
    ap.add_argument("--fuel-csv", type=Path, default=None)
    ap.add_argument("--fuel-xlsx", type=Path, default=None)
    ap.add_argument("--add-fuel", action="append", default=[], metavar="PLATE=L")
    ap.add_argument("--diesel-price", type=float, default=DEFAULT_DIESEL_BAHT)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

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
    elif DEFAULT_FUEL_CSV.exists():
        fuel_by = load_fuel_csv(DEFAULT_FUEL_CSV)
        fuel_source = DEFAULT_FUEL_CSV.name
    else:
        xlsx = _find_default_xlsx()
        if xlsx:
            fuel_by = load_fuel_xlsx(xlsx)
            fuel_source = xlsx.name
        else:
            print("ไม่พบ fuel CSV/xlsx — ใช้ --fuel-csv หรือวาง CSV ใน reports/")
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
        "budget_cap_low": 5000,
        "budget_cap_high": 10000,
        "within_budget": total_spend <= 10000,
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
                "GPSอัปเดต": r["time_th"],
            }
            for r in rows
        ]
    )
    df.to_excel(snap_xlsx, index=False)

    print(f"OK HTML: {OUT_HTML}")
    print(f"OK Pages: {pages_index}")
    print(
        f"GitHub (หลัง commit + push): "
        f"{GITHUB_PAGES_BASE}/reports/{PAGES_SLUG}/"
    )
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
