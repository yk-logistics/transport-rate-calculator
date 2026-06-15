# -*- coding: utf-8 -*-
"""
สร้าง HTML แผนจัดคัน LCB จากรายงาน GPS Fuel Level (Wialon export .xlsx)

ใช้งาน:
  python ProjectYK_System/tools/build_lcb_fuel_dispatch_html.py
  python ProjectYK_System/tools/build_lcb_fuel_dispatch_html.py "C:\\Users\\...\\report.xlsx"

ผลลัพธ์: ProjectYK_System/docs/print/lcb_fuel_dispatch_plan.html
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_HTML = ROOT / "docs" / "print" / "lcb_fuel_dispatch_plan.html"
REPORTS_DIR = ROOT / "reports"

SKIP_ASSIGN = {"บษ-2681", "รวมทั้งหมด", "72-1217"}
EXCLUDED_INFO = [
    ("71-8681", "รถเสีย — แผนวันนี้ใช้ 71-8684 แทน (พัฒิยะ)"),
    ("72-1219", "รถเสีย — ไม่จัดงาน"),
    ("72-1217", "วิ่งงานประจำ Oatside — ไม่จัดงานชุดนี้"),
]

JOBS = (
    [("Haier", 100)] * 3
    + [("Conti", 50)] * 5
    + [("KAO", 50)] * 4
    + [("Lacation", 50)]
    + [("คลังวาฬ", 25)] * 2
)

JOB_COLORS = {
    "Haier": "#7c3aed",
    "KAO": "#0369a1",
    "Conti": "#0d9488",
    "Lacation": "#b45309",
    "คลังวาฬ": "#64748b",
}


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


PLATE_IN_GROUP_RE = re.compile(r"(\d{2}-\d{4}|บษ-\d{4})")


def plate_from_wialon_group(val) -> str | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s == "รวมทั้งหมด":
        return None
    m = PLATE_IN_GROUP_RE.search(s)
    return m.group(1) if m else None


def parse_fuel(val) -> float | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s in ("-----", "-", ""):
        return None
    m = re.search(r"([\d.,]+)", s.replace(",", ""))
    return float(m.group(1)) if m else None


def load_trucks(xlsx: Path) -> tuple[list[dict], datetime | None]:
    df = pd.read_excel(xlsx, sheet_name="Fuel Level Sensor (L)")
    trucks = []
    max_ts = None
    current_plate: str | None = None
    for _, r in df.iterrows():
        p = plate_from_wialon_group(r.get("การจัดกลุ่ม"))
        if p:
            current_plate = p
        plate = current_plate
        if not plate:
            continue
        ts = pd.to_datetime(r["Time"], errors="coerce")
        fuel = parse_fuel(r["Fuel Level Sensor (L)"])
        if pd.notna(ts) and (max_ts is None or ts > max_ts):
            max_ts = ts.to_pydatetime()
        if fuel is None or pd.isna(ts):
            continue
        trucks.append(
            {
                "plate": plate,
                "fuel": fuel,
                "time": ts.to_pydatetime(),
                "time_iso": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "time_th": ts.strftime("%d/%m/%Y %H:%M"),
            }
        )
    # latest per plate
    by_plate: dict[str, dict] = {}
    for t in trucks:
        p = t["plate"]
        if p not in by_plate or t["time"] > by_plate[p]["time"]:
            by_plate[p] = t
    return list(by_plate.values()), max_ts


def assign_jobs(pool: list[dict]) -> list[dict]:
    pool = sorted(pool, key=lambda x: -x["fuel"])
    jobs = sorted(JOBS, key=lambda x: -x[1])
    used: set[str] = set()
    rows = []
    for job, need in jobs:
        picked = next(
            (t for t in pool if t["plate"] not in used and t["fuel"] >= need),
            None,
        )
        if not picked:
            rem = [t for t in pool if t["plate"] not in used]
            picked = max(rem, key=lambda x: x["fuel"])
        used.add(picked["plate"])
        left = picked["fuel"] - need
        newest = max(t["time"] for t in pool)
        stale = picked["time"].hour < 12 or (newest - picked["time"]).total_seconds() > 3 * 3600
        risk = left < 10
        rows.append(
            {
                "plate": picked["plate"],
                "job": job,
                "need": need,
                "fuel": picked["fuel"],
                "left": left,
                "time_th": picked["time_th"],
                "time_iso": picked["time_iso"],
                "stale": stale,
                "risk": risk,
            }
        )
    return rows


def fmt_th_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%d/%m/%Y %H:%M")


def render_html(
    rows: list[dict],
    meta: dict,
) -> str:
    data_json = json.dumps(
        {"assignments": rows, "meta": meta, "excluded": EXCLUDED_INFO},
        ensure_ascii=False,
    )
    body_rows = []
    n = 0
    for job in ["Haier", "KAO", "Conti", "Lacation", "คลังวาฬ"]:
        job_rows = [r for r in rows if r["job"] == job]
        for i, r in enumerate(job_rows):
            n += 1
            flags = []
            if r["stale"]:
                flags.append('<span class="badge badge-warn">ข้อมูลเก่า</span>')
            if r["risk"]:
                flags.append('<span class="badge badge-risk">เหลือน้อย</span>')
            flag_html = " ".join(flags)
            body_rows.append(
                f"""<tr class="job-{job}">
  <td class="c-num">{n}</td>
  <td class="c-plate"><strong>{r['plate']}</strong></td>
  <td class="c-job"><span class="job-pill" style="background:{JOB_COLORS[job]}">{job}</span></td>
  <td class="c-num">{r['need']:.0f}</td>
  <td class="c-num">{r['fuel']:.0f}</td>
  <td class="c-num {'low' if r['left'] < 15 else ''}">{r['left']:.0f}</td>
  <td class="c-flags">{flag_html}</td>
  <td class="c-updated">{r['time_th']}</td>
</tr>"""
            )

    excluded_html = "".join(
        f"<li><strong>{p}</strong> — {note}</li>" for p, note in EXCLUDED_INFO
    )

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>แผนจัดคัน LCB — น้ำมันในถัง (ไม่เติมเพิ่ม)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Sarabun", "Tahoma", sans-serif;
      font-size: 14px;
      color: #0f172a;
      background: #f1f5f9;
      line-height: 1.45;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .toolbar {{
      max-width: 1100px;
      margin: 12px auto;
      padding: 14px 18px;
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }}
    .toolbar h2 {{ font-size: 1rem; margin-bottom: 8px; }}
    .toolbar p {{ font-size: 0.85rem; color: #475569; margin-bottom: 10px; }}
    .btn-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .btn {{
      border: none;
      border-radius: 8px;
      padding: 9px 16px;
      font-family: inherit;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .btn-print {{ background: #1e40af; color: #fff; }}
    .btn-png {{ background: #0f766e; color: #fff; }}
    .btn-xlsx {{ background: #166534; color: #fff; }}
    .btn:hover {{ filter: brightness(1.08); }}
    #report {{
      max-width: 1100px;
      margin: 0 auto 24px;
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 2px 10px rgba(0,0,0,.1);
      overflow: hidden;
    }}
    .report-head {{
      padding: 20px 22px 14px;
      border-bottom: 3px solid #1e3a8a;
      background: linear-gradient(135deg, #eff6ff 0%, #fff 60%);
    }}
    .report-head h1 {{
      font-size: 1.45rem;
      font-weight: 800;
      color: #1e3a8a;
    }}
    .report-head .sub {{ color: #64748b; font-size: 0.88rem; margin-top: 4px; }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      padding: 14px 22px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
    }}
    .sum-card {{
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 12px;
    }}
    .sum-card .lbl {{ font-size: 0.75rem; color: #64748b; }}
    .sum-card .val {{ font-size: 1.2rem; font-weight: 800; color: #0f172a; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    thead th {{
      background: #1e3a8a;
      color: #fff;
      font-weight: 700;
      padding: 10px 8px;
      text-align: left;
      white-space: nowrap;
    }}
    thead th.c-updated {{ text-align: right; }}
    tbody td {{
      padding: 9px 8px;
      border-bottom: 1px solid #e2e8f0;
      vertical-align: middle;
    }}
    tbody tr:nth-child(even) {{ background: #f8fafc; }}
    .c-num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .c-plate {{ font-size: 1rem; }}
    .c-updated {{
      text-align: right;
      font-size: 0.82rem;
      color: #475569;
      white-space: nowrap;
    }}
    .c-num.low {{ color: #b91c1c; font-weight: 800; }}
    .job-pill {{
      display: inline-block;
      color: #fff;
      font-size: 0.78rem;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 999px;
    }}
    .badge {{
      display: inline-block;
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      margin-left: 2px;
    }}
    .badge-warn {{ background: #fef3c7; color: #92400e; }}
    .badge-risk {{ background: #fee2e2; color: #991b1b; }}
    .excluded {{
      padding: 14px 22px 18px;
      border-top: 1px solid #e2e8f0;
      font-size: 0.88rem;
    }}
    .excluded h3 {{ font-size: 0.95rem; margin-bottom: 8px; color: #64748b; }}
    .excluded ul {{ margin-left: 18px; color: #475569; }}
    .foot-note {{
      padding: 10px 22px 16px;
      font-size: 0.78rem;
      color: #94a3b8;
    }}
    @media print {{
      body {{ background: #fff; }}
      .toolbar {{ display: none !important; }}
      #report {{
        box-shadow: none;
        border-radius: 0;
        max-width: 100%;
      }}
      thead th {{ background: #1e3a8a !important; }}
    }}
  </style>
</head>
<body>
  <div class="toolbar no-print">
    <h2>แผนจัดคัน LCB — ส่งทีม / พิมพ์</h2>
    <p>อัปเดต HTML: รัน <code>build_lcb_fuel_dispatch.bat</code> หลังโยนไฟล์ .xlsx ใหม่จาก GPS (หรือลากไฟล์มาวางแล้วรัน bat พร้อม path)</p>
    <p>ไฟล์ Excel เต็มอยู่ที่ <code>ProjectYK_System/reports/fuel_dispatch_assign_วันที่.xlsx</code> หลังรัน</p>
    <div class="btn-row">
      <button type="button" class="btn btn-print" onclick="window.print()">🖨️ พิมพ์ / PDF</button>
      <button type="button" class="btn btn-png" onclick="exportPng()">🖼️ บันทึกรูป PNG</button>
      <button type="button" class="btn btn-xlsx" onclick="exportExcel()">📊 ดาวน์โหลด Excel (CSV)</button>
    </div>
  </div>

  <div id="report">
    <header class="report-head">
      <h1>แผนจัดคัน LCB หัวลาก — ตามน้ำมันในถัง</h1>
      <p class="sub">เป้าหมาย: ไม่เติมน้ำมันเพิ่ม (ตามสูตรใช้น้ำมันต่องาน) · สร้างเมื่อ {meta['generated_th']}</p>
      <p class="sub">แหล่งข้อมูล: {meta['source_name']}</p>
    </header>
    <div class="summary">
      <div class="sum-card"><div class="lbl">เที่ยวทั้งหมด</div><div class="val">{meta['trip_count']}</div></div>
      <div class="sum-card"><div class="lbl">น้ำมันตามสูตร</div><div class="val">{meta['fuel_need']:.0f} ล.</div></div>
      <div class="sum-card"><div class="lbl">คันที่จัด</div><div class="val">{meta['truck_count']}</div></div>
      <div class="sum-card"><div class="lbl">เติมเพิ่ม (สูตร)</div><div class="val">{meta['refuel_extra']:.0f} ล.</div></div>
    </div>
    <table id="dispatch-table">
      <thead>
        <tr>
          <th class="c-num">#</th>
          <th>ทะเบียน</th>
          <th>งาน</th>
          <th class="c-num">ใช้ (ล.)</th>
          <th class="c-num">มีในถัง</th>
          <th class="c-num">หลังวิ่ง</th>
          <th>หมายเหตุ</th>
          <th class="c-updated">GPS อัปเดต</th>
        </tr>
      </thead>
      <tbody>
{chr(10).join(body_rows)}
      </tbody>
    </table>
    <section class="excluded">
      <h3>ไม่จัดงานชุดนี้</h3>
      <ul>{excluded_html}</ul>
    </section>
    <p class="foot-note">Project YK · สูตร: Haier 100×3, Conti 50×5, KAO 50×4, Lacation 50×1, คลังวาฬ 25×2 เที่ยว/คัน</p>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script>
    const REPORT_DATA = {data_json};

    async function exportPng() {{
      const el = document.getElementById('report');
      const canvas = await html2canvas(el, {{ scale: 2, backgroundColor: '#ffffff', useCORS: true }});
      const a = document.createElement('a');
      a.download = 'LCB_fuel_dispatch_' + new Date().toISOString().slice(0,10) + '.png';
      a.href = canvas.toDataURL('image/png');
      a.click();
    }}

    function exportExcel() {{
      const rows = REPORT_DATA.assignments;
      const header = ['ลำดับ','ทะเบียน','งาน','ใช้(ล.)','มีในถัง','หลังวิ่ง','หมายเหตุ','GPSอัปเดต'];
      const lines = [header.join(',')];
      rows.forEach((r, i) => {{
        const note = [r.stale ? 'ข้อมูลเก่า' : '', r.risk ? 'เหลือน้อย' : ''].filter(Boolean).join(' ');
        lines.push([
          i+1, r.plate, r.job, r.need, r.fuel, r.left, note, r.time_th
        ].join(','));
      }});
      const blob = new Blob(['\\ufeff' + lines.join('\\n')], {{ type: 'text/csv;charset=utf-8' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'LCB_fuel_dispatch_' + new Date().toISOString().slice(0,10) + '.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    }}
  </script>
</body>
</html>"""


def main() -> int:
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else _find_default_xlsx()
    if not xlsx or not xlsx.exists():
        print("ไม่พบไฟล์ .xlsx — ระบุ path หรือวางไฟล์ *Fuel_Level*LCB*.xlsx ใน Downloads")
        return 1

    all_trucks, report_max = load_trucks(xlsx)
    pool = [t for t in all_trucks if t["plate"] not in SKIP_ASSIGN]
    if len(pool) < len(JOBS):
        print(f"คันในสระน้อยกว่างาน: {len(pool)} < {len(JOBS)}")
        return 1

    rows = assign_jobs(pool)
    refuel = sum(max(0, r["need"] - r["fuel"]) for r in rows)
    meta = {
        "generated_th": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "source_name": xlsx.name,
        "source_path": str(xlsx),
        "report_max_th": fmt_th_datetime(report_max),
        "trip_count": len(JOBS),
        "fuel_need": sum(n for _, n in JOBS),
        "truck_count": len(rows),
        "refuel_extra": refuel,
    }

    html = render_html(rows, meta)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")

    # snapshot CSV for archive
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    snap_csv = REPORTS_DIR / f"fuel_dispatch_assign_{stamp}.csv"
    snap_xlsx = REPORTS_DIR / f"fuel_dispatch_assign_{stamp}.xlsx"
    df_out = pd.DataFrame(rows).rename(
        columns={
            "plate": "ทะเบียน",
            "job": "งาน",
            "need": "ใช้(ล.)",
            "fuel": "มีในถัง",
            "left": "หลังวิ่ง",
            "time_th": "GPSอัปเดต",
        }
    )
    df_out["หมายเหตุ"] = df_out.apply(
        lambda r: " ".join(
            x
            for x in (
                "ข้อมูลเก่า" if r.get("stale") else "",
                "เหลือน้อย" if r.get("risk") else "",
            )
            if x
        ),
        axis=1,
    )
    cols = ["ทะเบียน", "งาน", "ใช้(ล.)", "มีในถัง", "หลังวิ่ง", "หมายเหตุ", "GPSอัปเดต"]
    df_out[cols].to_csv(snap_csv, index=False, encoding="utf-8-sig")
    df_out[cols].to_excel(snap_xlsx, index=False)

    print(f"OK: {OUT_HTML}")
    print(f"     {snap_csv}")
    print(f"     {snap_xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
