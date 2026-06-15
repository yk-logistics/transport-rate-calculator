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
import html as html_module
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
from parse_pump_credit_pdf import (  # noqa: E402
    DEFAULT_CREDIT_LIMIT,
    find_latest_pump_pdf,
    load_snapshot,
    parse_pump_credit_pdf,
    pump_summary_for_ui,
    save_snapshot,
)

OUT_HTML = ROOT / "docs" / "print" / "lcb_fuel_dispatch_plan.html"
REPORTS_DIR = ROOT / "reports"
GPS_INBOX = REPORTS_DIR / "gps_inbox"
PUMP_INBOX = REPORTS_DIR / "pump_inbox"
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

REFUEL_BUFFER_L = 10.0  # หลังวิ่ง(แผน) อยากเหลือ ~10+ ล.
REFILL_ROUND_L = 10  # แนะนำเติมปัดเป็นหน่วย 10 ล. (ขึ้น)
FULL_TANK_TARGET_L = 200  # ความจุเต็มถัง (ล.)
DEFAULT_PUMP_TRAVEL_L = 3  # บางคันใช้ไปปั๊ม ~1–5 ล. (แก้บนหน้าได้)

LINE_BRANCH_KEYS: list[tuple[str, str]] = [
    ("จุกกะเฌอ", "จุกกะเฌอ"),
    ("ปิ่นทอง1", "ปิ่นทอง1"),
    ("ปิ่นทอง2", "ปิ่นทอง2"),
    ("ศรีไทย", "ศรีไทย"),
    ("สาขา16", "สาขา 16"),
    ("ทวีทรัพย์", "ทวีทรัพย์"),
    ("บ้านเก่า", "บ้านเก่า"),
]
DEFAULT_LINE_BRANCH = "จุกกะเฌอ"


def _line_branch_select(plate: str, selected: str = DEFAULT_LINE_BRANCH) -> str:
    opts = "".join(
        f'<option value="{k}"{" selected" if k == selected else ""}>{label}</option>'
        for k, label in LINE_BRANCH_KEYS
    )
    return (
        f'<select class="line-branch-row" data-plate="{plate}" '
        f'title="สาขาเติม (แจ้ง LINE)">{opts}</select>'
    )
DEFAULT_DIESEL_BAHT = 42.20

JOB_COLORS = {
    "Haier": "#7c3aed",
    "KAO": "#0369a1",
    "Conti": "#0d9488",
    "Lacation": "#b45309",
    "KATOEN": "#d97706",
    "คลังวาฬ": "#64748b",
    "ฟรีโซน": "#0891b2",
    "เหรินเหอ": "#c2410c",
    "Oatside": "#be185d",
    "Unknown": "#475569",
}

JOB_DISPLAY_ORDER = [
    "Haier",
    "KAO",
    "Conti",
    "Lacation",
    "KATOEN",
    "คลังวาฬ",
    "ฟรีโซน",
    "เหรินเหอ",
    "Oatside",
    "Unknown",
]

EXCLUDED_DEFAULT: list[tuple[str, str]] = []  # ใช้จาก Remark ในแผนวันนั้นเท่านั้น


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


def _collect_gps_xlsx_candidates() -> list[Path]:
    """รายการไฟล์ Wialon .xlsx เรียงใหม่→เก่า (mtime)"""
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
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)


def _find_default_xlsx() -> Path | None:
    """ไฟล์ Wialon .xlsx ล่าสุด — ห้ามใช้ CSV เก่าแทนโดยไม่รู้ตัว"""
    candidates = _collect_gps_xlsx_candidates()
    return candidates[0] if candidates else None


def merge_fuel_gps_with_fallback(
    primary_path: Path,
    plan_plates: list[str],
    *,
    max_older_files: int = 12,
) -> tuple[dict[str, dict], list[str]]:
    """โหลด GPS จากไฟล์หลัก; คันที่ไม่มีในไฟล์ล่าสุด → ดึงจากไฟล์เก่าถัดไป (รถหยุด/ลา)."""
    primary_data = load_fuel_xlsx(primary_path)
    out: dict[str, dict] = {}
    for plate, rec in primary_data.items():
        merged = dict(rec)
        merged["gps_source"] = primary_path.name
        merged["stale"] = False
        out[plate] = merged

    need = {
        p
        for p in plan_plates
        if p not in out or out[p].get("fuel") is None
    }
    log_lines: list[str] = []
    if not need:
        return out, log_lines

    primary_resolved = primary_path.resolve()
    older_files = [
        p
        for p in _collect_gps_xlsx_candidates()
        if p.resolve() != primary_resolved
    ][:max_older_files]

    for older_path in older_files:
        if not need:
            break
        try:
            older_data = load_fuel_xlsx(older_path)
        except Exception as exc:
            print(f"[WARN] อ่าน GPS เก่าไม่ได้: {older_path.name} ({exc})")
            continue
        filled: list[str] = []
        for plate in list(need):
            rec = older_data.get(plate)
            if not rec or rec.get("fuel") is None:
                continue
            merged = dict(rec)
            merged["gps_source"] = older_path.name
            merged["gps_fallback_from"] = older_path.name
            merged["stale"] = True
            out[plate] = merged
            need.discard(plate)
            filled.append(plate)
            log_lines.append(
                f"  {plate}: จากไฟล์เก่า {older_path.name} "
                f"({rec.get('time_th', '-')})"
            )
        if filled:
            print(
                f"GPS fallback ← {older_path.name}: "
                + ", ".join(filled)
            )

    if need:
        print(
            "ไม่พบ GPS (ล่าสุด+เก่า): "
            + ", ".join(sorted(need))
        )
    return out, log_lines


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
    """Wialon Group export: แถวย่อย สืบทะเบียนจากแถวหัวกลุ่ม
    ใช้ค่าเฉลี่ยน้ำมัน 60 วินาทีก่อนรถหยุด (Speed→0) ป้องกัน sensor drift หลังดับเครื่อง
    fallback: ค่าล่าสุดถ้าไม่มีแถว Speed > 0
    """
    df = pd.read_excel(path, sheet_name="Fuel Level Sensor (L)")
    has_speed = "Speed" in df.columns
    loc_col = "Location" if "Location" in df.columns else None

    # รวบทุกแถวต่อทะเบียน
    rows_by_plate: dict[str, list[dict]] = {}
    current_plate: str | None = None
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
        speed = None
        if has_speed:
            try:
                speed = float(r["Speed"])
            except (TypeError, ValueError):
                speed = None
        loc = ""
        if loc_col and pd.notna(r.get(loc_col)):
            loc = str(r[loc_col]).strip()
        rows_by_plate.setdefault(plate, []).append(
            {"ts": ts, "fuel": fuel, "speed": speed, "loc": loc}
        )

    by: dict[str, dict] = {}
    for plate, rows in rows_by_plate.items():
        rows.sort(key=lambda x: x["ts"])

        # หา t_stop = timestamp ล่าสุดที่ speed > 0
        moving = [x for x in rows if x["speed"] is not None and x["speed"] > 0]
        if moving:
            t_stop = moving[-1]["ts"]
            window_start = t_stop - pd.Timedelta(seconds=60)
            window = [x for x in rows if window_start <= x["ts"] <= t_stop]
            fuel_val = sum(x["fuel"] for x in window) / len(window)
            ref_row = moving[-1]
        else:
            # fallback: ใช้แถวล่าสุด
            ref_row = rows[-1]
            fuel_val = ref_row["fuel"]

        ts = ref_row["ts"]
        by[plate] = {
            "fuel": round(fuel_val, 1),
            "time_th": ts.strftime("%d/%m/%Y %H:%M"),
            "time_iso": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": ref_row["loc"],
        }
    return by


def _suggest_refill_liters(need: float, fuel_eff: float) -> int:
    """ลิตรเติมแนะนำ — หลังวิ่ง(แผน) >= REFUEL_BUFFER_L, ปัดขึ้นเป็นหน่วย 10."""
    import math

    if fuel_eff - need >= REFUEL_BUFFER_L:
        return 0
    raw = need - fuel_eff + REFUEL_BUFFER_L
    if raw <= 0:
        return 0
    return int(math.ceil(raw / REFILL_ROUND_L) * REFILL_ROUND_L)


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

        label = (a.customer_label or a.job).strip()
        rows.append(
            {
                "plate": a.plate,
                "job": a.job,
                "job_display": label,
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
                "suggested_refill_l": _suggest_refill_liters(a.need_liters, fuel_eff),
                "driver": a.driver,
                "time_th": gps.get("time_th", "-"),
                "time_iso": gps.get("time_iso", ""),
                "location": gps.get("location", ""),
                "notes": " ".join(a.notes),
                "stale": bool(gps.get("stale")),
                "gps_fallback_from": gps.get("gps_fallback_from", ""),
                "gps_source": gps.get("gps_source", ""),
            }
        )
    return rows


def _row_sort_key(r: dict) -> tuple:
    job = r.get("job", "")
    try:
        idx = JOB_DISPLAY_ORDER.index(job)
    except ValueError:
        idx = 99
    return (idx, r.get("job_display", job), r.get("plate", ""))


def _render_table_row(r: dict, n: int, job_display: str) -> str:
    job = r.get("job", job_display)
    added = int(r.get("fuel_added") or 0)
    auto_need = "1" if r["needs_refuel"] else "0"
    auto_done = "1" if added > 0 else "0"
    auto_stale = "1" if r.get("stale") else "0"
    flag_html = (
        f'<select class="status-row" data-plate="{r["plate"]}" '
        f'data-auto-need="{auto_need}" data-auto-done="{auto_done}" '
        f'data-auto-stale="{auto_stale}" title="เลือกสถานะเอง หรืออัตโนมัติ">'
        f'<option value="auto">อัตโนมัติ</option>'
        f'<option value="done">เติมแล้ว</option>'
        f'<option value="need">ต้องเติม</option>'
        f'<option value="ok">ปกติ</option>'
        f"</select>"
        f'<div class="status-badges" data-plate="{r["plate"]}"></div>'
        f'<div class="status-tonight" data-plate="{r["plate"]}" style="display:none">'
        f'<input class="tonight-in" type="number" min="0" step="1" '
        f'value="{added}" data-plate="{r["plate"]}" '
        f'title="ลิตรที่เติมแล้ววันนี้" /> ล.</div>'
    )
    gps_col = f'{r["fuel_gps"]:.0f}' if r["fuel_gps"] is not None else "—"
    suggest = int(r.get("suggested_refill_l") or 0)
    row_cls = f"job-{job}" + (" row-must-refuel" if r["needs_refuel"] else "")
    if added > 0:
        val_attr = f' value="{added}"'
        already_attr = f' data-already-fueled="{added}"'
        title = f"เติมแล้ว +{added} ล. (แก้ได้)"
    elif suggest > 0:
        val_attr = f' value="{suggest}"'
        already_attr = ''
        title = f"แนะนำ {suggest} ล. (หล่วย 10, หลังวิ่งเหลือ ~{REFUEL_BUFFER_L:.0f}+ ล.)"
    else:
        val_attr = ""
        already_attr = ''
        title = "ไม่บังคับเติม — ใส่ 0 ถ้าไม่เติม"
    fuel_gps_val = r["fuel_gps"] if r["fuel_gps"] is not None else 0.0
    plan_refill = added if added > 0 else suggest
    after_refill_plan = fuel_gps_val + plan_refill
    after_trip_plan = after_refill_plan - r["need"]
    low_plan = after_trip_plan < REFUEL_BUFFER_L
    driver_attr = html_module.escape(r.get("driver", ""), quote=True)
    time_cell = r["time_th"]
    if r.get("gps_fallback_from"):
        fb = html_module.escape(r["gps_fallback_from"])
        time_cell += (
            f' <span class="gps-fb-hint" title="ไม่มีในไฟล์ล่าสุด — ใช้ค่าจากไฟล์เก่า">'
            f"↩ {fb}</span>"
        )
    return f"""<tr class="{row_cls}" data-plate="{r['plate']}" data-driver="{driver_attr}">
  <td class="c-num c-num-n">{n}</td>
  <td class="c-plate c-sticky-plate"><strong>{r['plate']}</strong><div class="sub" title="{html_module.escape(r.get('driver',''))}">{r.get('driver','')}</div></td>
  <td class="c-job c-sticky-job"><span class="job-pill" style="background:{JOB_COLORS.get(job, JOB_COLORS.get(job_display, '#334155'))}">{job_display}</span> <span class="trips">{r['trips']} เที่ยว</span></td>
  <td class="c-num c-col-narrow">{r['need']:.0f}</td>
  <td class="c-num c-col-narrow">{gps_col}</td>
  <td class="c-num c-col-narrow">{r['fuel']:.0f}</td>
  <td class="c-num c-col-narrow {{'low' if r['left'] < REFUEL_BUFFER_L else ''}}">{r['left']:.0f}</td>
  <td class="c-refill c-col-refill">
    <div class="refill-cell">
      <input type="number" class="refill-in" min="0" step="10" data-plate="{r['plate']}" data-need="{r['need']:.0f}" data-fuel-base="{fuel_gps_val:.0f}"{val_attr}{already_attr} title="{title}" aria-label="เติมลิตร {r['plate']}" />
      <label class="full-tank-lbl" title="LINE แจ้งเต็มถัง · ลิตรเติม = 200−GPS+ไปปั๊ม"><input type="checkbox" class="line-full-row" data-plate="{r['plate']}" /> เต็มถัง</label>
    </div>
  </td>
  <td class="c-branch no-print">{_line_branch_select(r['plate'])}</td>
  <td class="c-num c-col-narrow after-refill-plan" data-plate="{r['plate']}">{after_refill_plan:.0f}</td>
  <td class="c-num c-col-narrow after-trip-plan {{'low' if low_plan else ''}}" data-plate="{r['plate']}">{after_trip_plan:.0f}</td>
  <td class="c-num c-col-narrow refill-cost" data-plate="{r['plate']}">0</td>
  <td class="c-flags c-col-status">{flag_html}</td>
  <td class="c-updated c-col-gps-time">{time_cell}</td>
  <td class="c-line c-col-action no-print"><button type="button" class="btn-line-one" data-plate="{r['plate']}" title="คัดลอกข้อความแจ้งเติม LINE">LINE</button></td>
</tr>"""


def _fmt_baht(n: float) -> str:
    return f"{n:,.0f}"


def _render_pump_credit_panel(pump_ui: dict | None) -> str:
    if not pump_ui or not pump_ui.get("ok"):
        return f"""
    <section class="pump-credit-panel pump-missing no-print">
      <h3>บัญชีปั๊มเต็กย้ง (PDF เช้า)</h3>
      <p class="pump-hint">ยังไม่มีรายงานปั๊ม — วาง PDF ลง <code>{PUMP_INBOX.name}/</code>
        (ชื่อมี &quot;เติมน้ำมัน&quot; หรือ &quot;วายเค&quot;) แล้วรัน build ใหม่</p>
    </section>"""

    closing = pump_ui["closing_balance_baht"]
    debt = pump_ui["debt_baht"]
    headroom = pump_ui["headroom_before_limit_baht"]
    limit = pump_ui["credit_limit_baht"]
    min_bal = pump_ui["min_balance_baht"]
    risk_cls = " pump-at-risk" if pump_ui.get("at_risk") else ""
    bal_cls = "neg" if closing < 0 else "pos"
    src = html_module.escape(pump_ui.get("source_file", ""))
    ref_th = pump_ui.get("last_fuel_date_th") or pump_ui.get("last_fuel_date_iso", "")

    yday_rows = pump_ui.get("yesterday_fills") or []
    if yday_rows:
        yday_tr = "".join(
            f"<tr><td><strong>{html_module.escape(r['plate'])}</strong></td>"
            f"<td>{html_module.escape(r.get('station', ''))}</td>"
            f'<td class="c-num">{r.get("liters", 0):.0f}</td>'
            f'<td class="c-num">{_fmt_baht(r.get("amount_baht", 0))}</td></tr>'
            for r in yday_rows
        )
        yday_table = f"""
      <table class="pump-subtable">
        <thead><tr><th>ทะเบียน</th><th>สถานี</th><th class="c-num">ลิตร</th><th class="c-num">บาท</th></tr></thead>
        <tbody>{yday_tr}</tbody>
      </table>"""
        yday_title = f"เติมล่าสุดในรายงาน ({html_module.escape(ref_th)}) — คันในแผนวันนี้"
    else:
        yday_table = "<p class=\"pump-hint\">ไม่มีรายการเติมของคันในแผนวันนี้ในวันล่าสุดของ PDF</p>"
        yday_title = "เติมล่าสุดในรายงาน (คันในแผน)"

    topups = pump_ui.get("recent_topups") or []
    topup_li = "".join(
        f"<li>{html_module.escape(t.get('date_th', ''))} "
        f"{html_module.escape(t.get('station', ''))}: "
        f"<strong>{_fmt_baht(t.get('amount_baht', 0))} ฿</strong></li>"
        for t in topups
    )
    topup_html = (
        f"<ul class=\"pump-topups\">{topup_li}</ul>" if topup_li else ""
    )
    return f"""
    <section class="pump-credit-panel{risk_cls} no-print">
      <div class="pump-head">
        <h3>บัญชีปั๊มเต็กย้ง</h3>
        <span class="pump-src">จาก PDF: {src}</span>
      </div>
      <div class="pump-kpis">
        <div class="pump-kpi">
          <div class="lbl">ยอดบัญชีปั๊ม (ปิดรายงาน)</div>
          <div class="val {bal_cls}">{closing:,.2f} ฿</div>
        </div>
        <div class="pump-kpi">
          <div class="lbl">หนี้ปั๊ม (ถ้าติดลบ)</div>
          <div class="val neg">{_fmt_baht(debt)} ฿</div>
        </div>
        <div class="pump-kpi highlight">
          <div class="lbl">เหลือก่อนถึงเพดาน {_fmt_baht(limit)} ฿</div>
          <div class="val" id="pump-headroom">{_fmt_baht(headroom)} ฿</div>
        </div>
        <div class="pump-kpi">
          <div class="lbl">ต่ำสุดในรายงานเดือนนี้</div>
          <div class="val neg">{min_bal:,.2f} ฿</div>
        </div>
        <div class="pump-kpi wide">
          <div class="lbl">หลังเติมตามแผนวันนี้ (ประมาณ)</div>
          <div class="val" id="pump-projected-balance">—</div>
          <div class="sub" id="pump-projected-note">อัปเดตตามช่องเติม + ราคา diesel</div>
        </div>
      </div>
      {"<p class=\"pump-alert\">ใกล้เพดานติดลบ — พิจารณาโอนเติมวงเงินปั๊ม</p>" if pump_ui.get("at_risk") else ""}
      <div class="pump-cols">
        <div>
          <h4>{yday_title}</h4>
          {yday_table}
        </div>
        <div>
          <h4>โอนเติมวงเงินล่าสุด</h4>
          {topup_html}
        </div>
      </div>
      <p class="pump-hint">เพดานติดลบตั้งไว้ {_fmt_baht(limit)} ฿ (ปรับได้ตอน build) · ยอดปั๊ม ≠ ลิตรในถัง GPS</p>
    </section>"""


def render_html(
    rows: list[dict],
    meta: dict,
    excluded: list[tuple[str, str]],
    *,
    pump_ui: dict | None = None,
) -> str:
    pump_json = json.dumps(pump_ui or {}, ensure_ascii=False)
    data_json = json.dumps(
        {"assignments": rows, "meta": meta, "excluded": excluded},
        ensure_ascii=False,
    )
    pump_panel_html = _render_pump_credit_panel(pump_ui)
    body_rows = []
    n = 0
    for r in sorted(rows, key=_row_sort_key):
        n += 1
        body_rows.append(_render_table_row(r, n, r.get("job_display", r.get("job", ""))))

    refuel_rows = [r for r in rows if r["needs_refuel"]]
    refuel_html = ""
    if refuel_rows:
        refuel_lines = [
            f"<li><strong>{r['plate']}</strong> ({r.get('job_display', r['job'])}) — หลังวิ่งเหลือ {r['left']:.0f} ล. "
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
    #report {{ max-width: 1280px; margin: 0 auto 24px; background: #fff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,.1); overflow: visible; }}
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
    .table-scroll-wrap {{
      overflow-x: auto;
      overflow-y: visible;
      -webkit-overflow-scrolling: touch;
      border-top: 1px solid #e2e8f0;
      scrollbar-gutter: stable;
    }}
    .table-scroll-hint {{
      display: none;
      padding: 6px 14px;
      font-size: 0.75rem;
      color: #64748b;
      background: #f1f5f9;
      border-bottom: 1px solid #e2e8f0;
      text-align: center;
    }}
    @media (max-width: 1100px) {{
      .table-scroll-hint {{ display: block; }}
    }}
    #dispatch-table {{
      width: max-content;
      min-width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      font-size: 0.86rem;
    }}
    #dispatch-table thead th {{
      background: #1e3a8a;
      color: #fff;
      padding: 8px 6px;
      text-align: left;
      font-size: 0.78rem;
      font-weight: 700;
      line-height: 1.25;
      white-space: nowrap;
      vertical-align: bottom;
      border-bottom: 2px solid #1e40af;
    }}
    #dispatch-table thead th.c-num {{ text-align: right; }}
    #dispatch-table tbody td {{
      padding: 8px 6px;
      border-bottom: 1px solid #e2e8f0;
      vertical-align: top;
      background: #fff;
    }}
    #dispatch-table tbody tr:nth-child(even) td {{ background: #f8fafc; }}
    #dispatch-table .c-num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    #dispatch-table .c-num.low {{ color: #b91c1c; font-weight: 800; }}
    #dispatch-table th.c-num-n {{ width: 34px; min-width: 34px; max-width: 34px; }}
    #dispatch-table td.c-num-n, #dispatch-table th.c-num-n {{
      position: sticky;
      left: 0;
      z-index: 2;
    }}
    #dispatch-table th.c-sticky-plate, #dispatch-table td.c-sticky-plate {{
      position: sticky;
      left: 34px;
      z-index: 2;
      min-width: 96px;
      max-width: 110px;
      box-shadow: 4px 0 6px -4px rgba(15, 23, 42, 0.12);
    }}
    #dispatch-table th.c-sticky-job, #dispatch-table td.c-sticky-job {{
      position: sticky;
      left: 130px;
      z-index: 2;
      min-width: 100px;
      max-width: 120px;
      box-shadow: 4px 0 6px -4px rgba(15, 23, 42, 0.1);
    }}
    #dispatch-table thead th.c-num-n,
    #dispatch-table thead th.c-sticky-plate,
    #dispatch-table thead th.c-sticky-job {{
      z-index: 5;
      background: #1e3a8a;
    }}
    #dispatch-table tbody tr:nth-child(even) td.c-num-n,
    #dispatch-table tbody tr:nth-child(even) td.c-sticky-plate,
    #dispatch-table tbody tr:nth-child(even) td.c-sticky-job {{ background: #f8fafc; }}
    #dispatch-table th.c-col-narrow, #dispatch-table td.c-col-narrow {{ min-width: 52px; }}
    #dispatch-table th.c-col-refill, #dispatch-table td.c-col-refill {{ min-width: 88px; }}
    #dispatch-table th.c-col-status, #dispatch-table td.c-col-status {{ min-width: 108px; max-width: 130px; }}
    #dispatch-table th.c-col-gps-time, #dispatch-table td.c-col-gps-time {{
      min-width: 118px;
      max-width: 200px;
      font-size: 0.76rem;
      line-height: 1.35;
      white-space: normal;
      word-break: break-word;
    }}
    #dispatch-table th.c-col-action, #dispatch-table td.c-col-action {{
      position: sticky;
      right: 0;
      z-index: 4;
      width: 52px;
      min-width: 52px;
      max-width: 52px;
      padding: 6px 4px !important;
      text-align: center;
      vertical-align: middle;
      box-shadow: -6px 0 8px -2px rgba(15, 23, 42, 0.14);
    }}
    #dispatch-table thead th.c-col-action {{
      z-index: 6;
      background: #1e3a8a;
    }}
    #dispatch-table tbody tr:nth-child(even) td.c-col-action {{ background: #f8fafc; }}
    tr.row-must-refuel td.c-col-action {{ background: #fffbeb !important; }}
    .c-num.low {{ color: #b91c1c; font-weight: 800; }}
    .c-plate .sub {{
      font-size: 0.7rem;
      color: #64748b;
      font-weight: 400;
      line-height: 1.25;
      max-width: 100px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .trips {{ font-size: 0.75rem; color: #64748b; }}
    .job-pill {{ display: inline-block; color: #fff; font-size: 0.78rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
    .badge {{ display: inline-block; font-size: 0.68rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; }}
    .badge-risk {{ background: #fee2e2; color: #991b1b; }}
    .badge-warn {{ background: #fef3c7; color: #92400e; }}
    .badge-ok {{ background: #dcfce7; color: #166534; }}
    .status-row {{ font-size: 0.78rem; padding: 4px 6px; border-radius: 6px; border: 1px solid #cbd5e1; max-width: 100%; margin-bottom: 4px; }}
    .status-badges {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }}
    .status-tonight {{ margin-top: 4px; font-size: 0.8rem; }}
    .status-tonight input {{ width: 52px; padding: 2px 4px; border-radius: 4px; border: 1px solid #86efac; }}
    .gps-fb-hint {{ display: block; font-size: 0.72rem; color: #b45309; margin-top: 2px; }}
    .tonight-badge {{ display: inline-flex; align-items: center; gap: 2px; }}
    .tonight-in {{ width: 40px; padding: 1px 3px; border: 1px solid #86efac; border-radius: 3px; background: #f0fdf4; color: #166534; font-size: 0.85em; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; font-family: inherit; }}
    .c-refill input.refill-in {{ width: 64px; padding: 5px 6px; border: 1px solid #cbd5e1; border-radius: 6px; text-align: right; font-variant-numeric: tabular-nums; font-family: inherit; }}
    tr.row-must-refuel .c-refill input {{ border-color: #f97316; background: #fff7ed; }}
    tr.row-must-refuel td {{ background: #fffbeb; }}
    .refuel-box, .tonight-box, .excluded {{ padding: 14px 22px; border-top: 1px solid #e2e8f0; }}
    .refuel-box {{ background: #fff7ed; }}
    .tonight-box {{ background: #ecfdf5; }}
    .cost-line {{ margin-top: 8px; font-size: 0.95rem; }}
    .excluded ul {{ margin-left: 18px; color: #475569; }}
    .foot-note {{ padding: 10px 22px 16px; font-size: 0.78rem; color: #94a3b8; }}
    .line-notify {{ max-width: 1200px; margin: 0 auto 12px; padding: 14px 18px; background: #ecfdf5; border: 1px solid #86efac; border-radius: 10px; }}
    .line-notify h3 {{ font-size: 1rem; color: #166534; margin-bottom: 8px; }}
    .line-notify .hint {{ font-size: 0.82rem; color: #475569; margin-bottom: 10px; }}
    .line-notify-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 10px; }}
    .line-notify-row label {{ font-size: 0.88rem; display: flex; align-items: center; gap: 6px; }}
    .line-notify-row select {{ padding: 7px 10px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: inherit; }}
    .btn-line {{ background: #15803d; font-size: 0.88rem; padding: 8px 14px; }}
    .btn-line-all {{ background: #166534; }}
    .btn-line-one {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
      width: 44px;
      min-width: 44px;
      max-width: 44px;
      height: 28px;
      margin: 0 auto;
      padding: 0;
      background: #16a34a;
      color: #fff;
      border: none;
      border-radius: 5px;
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.03em;
      line-height: 1;
      cursor: pointer;
      font-family: inherit;
      white-space: nowrap;
      overflow: hidden;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.15);
    }}
    .btn-line-one:hover {{ filter: brightness(1.08); }}
    .btn-line-one.ok {{ background: #14532d; font-size: 0.62rem; }}
    #line-preview {{ width: 100%; min-height: 72px; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-family: inherit; font-size: 0.9rem; resize: vertical; background: #fff; }}
    .refill-cell {{ display: flex; flex-direction: column; gap: 4px; align-items: stretch; min-width: 76px; }}
    .full-tank-lbl {{ font-size: 0.72rem; color: #64748b; display: flex; align-items: center; gap: 4px; white-space: nowrap; cursor: pointer; }}
    .line-branch-row {{ max-width: 108px; font-size: 0.78rem; padding: 4px 6px; border-radius: 6px; border: 1px solid #cbd5e1; font-family: inherit; }}
    tr.row-line-full-tank .refill-in {{ background: #f1f5f9; color: #94a3b8; }}
    tr.row-line-full-tank .refill-in:disabled {{ opacity: 0.7; }}
    .c-branch {{ min-width: 100px; }}
    .line-toast {{ position: fixed; bottom: 16px; right: 16px; background: #166534; color: #fff; padding: 10px 16px; border-radius: 8px; font-weight: 600; z-index: 9999; display: none; box-shadow: 0 4px 12px rgba(0,0,0,.2); }}
    .pump-credit-panel {{ margin: 0; padding: 16px 22px; background: linear-gradient(135deg, #fefce8 0%, #fff 55%); border-bottom: 2px solid #eab308; }}
    .pump-credit-panel.pump-at-risk {{ background: linear-gradient(135deg, #fef2f2 0%, #fff 55%); border-bottom-color: #ef4444; }}
    .pump-credit-panel.pump-missing {{ background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
    .pump-head {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px; margin-bottom: 12px; }}
    .pump-head h3 {{ font-size: 1.05rem; color: #854d0e; font-weight: 800; }}
    .pump-at-risk .pump-head h3 {{ color: #b91c1c; }}
    .pump-src {{ font-size: 0.78rem; color: #64748b; }}
    .pump-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 12px; }}
    .pump-kpi {{ background: #fff; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 12px; }}
    .pump-kpi.wide {{ grid-column: 1 / -1; }}
    .pump-at-risk .pump-kpi {{ border-color: #fecaca; }}
    .pump-kpi .lbl {{ font-size: 0.72rem; color: #78716c; margin-bottom: 4px; }}
    .pump-kpi .val {{ font-size: 1.2rem; font-weight: 800; font-variant-numeric: tabular-nums; }}
    .pump-kpi .val.pos {{ color: #166534; }}
    .pump-kpi .val.neg {{ color: #b91c1c; }}
    .pump-kpi .sub {{ font-size: 0.72rem; color: #94a3b8; margin-top: 4px; }}
    .pump-kpi.highlight {{ border-color: #f59e0b; background: #fffbeb; }}
    .pump-alert {{ color: #b91c1c; font-weight: 700; font-size: 0.88rem; margin-bottom: 10px; }}
    .pump-cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 800px) {{ .pump-cols {{ grid-template-columns: 1fr; }} }}
    .pump-cols h4 {{ font-size: 0.82rem; color: #57534e; margin-bottom: 6px; }}
    .pump-subtable {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
    .pump-subtable th {{ background: #fef3c7; padding: 6px; text-align: left; }}
    .pump-subtable td {{ padding: 5px 6px; border-bottom: 1px solid #fde68a; }}
    .pump-topups {{ margin-left: 18px; font-size: 0.82rem; color: #44403c; }}
    .pump-hint {{ font-size: 0.75rem; color: #78716c; margin-top: 8px; }}
    @media print {{
      .toolbar, .line-notify, .no-print, .table-scroll-hint {{ display: none !important; }}
      body {{ background: #fff; }}
      #report {{ box-shadow: none; max-width: none; }}
      .table-scroll-wrap {{ overflow: visible; }}
      #dispatch-table {{ font-size: 0.72rem; }}
      #dispatch-table th.c-col-action, #dispatch-table td.c-col-action,
      #dispatch-table th.c-num-n, #dispatch-table td.c-num-n,
      #dispatch-table th.c-sticky-plate, #dispatch-table td.c-sticky-plate,
      #dispatch-table th.c-sticky-job, #dispatch-table td.c-sticky-job {{
        position: static;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="toolbar no-print">
    <h2>LCB fuel dispatch — LINE plan + GPS</h2>
    <p>Build: <code>build_lcb_fuel_dispatch.bat</code> · ตารางแสดง<strong>ทุกคันในแผน</strong> · <strong>PDF ปั๊ม</strong> วางใน <code>pump_inbox/</code> · สถานะเลือกเองได้ · GPS เก่า fallback อัตโนมัติ</p>
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
  <section class="line-notify no-print" id="line-notify-panel">
    <h3>แจ้งเติมน้ำมัน LINE (คัดลอกวาง)</h3>
    <p class="hint"><strong>สาขา</strong> ในแต่ละแถว · <strong>ลิตร</strong> ช่องส้ม (หน่วย 10) · <strong>เต็มถัง</strong> = 200 ล. − GPS + ไปปั๊ม (~1–5 ล.) · LINE ยังพิมพ์คำว่า <em>เต็มถัง</em></p>
    <div class="line-notify-row">
      <label>สาขาเริ่มต้น (ใส่ทุกแถว)
        <select id="line-branch-default">{"".join(f'<option value="{k}">{label}</option>' for k, label in LINE_BRANCH_KEYS)}</select>
      </label>
      <button type="button" class="btn btn-line" onclick="applyDefaultBranchToAllRows()">ใส่สาขาเริ่มต้นทุกแถว</button>
      <label>ลงท้าย
        <select id="line-particle"><option value="ค่ะ" selected>ค่ะ</option><option value="ครับ">ครับ</option></select>
      </label>
      <span class="hint" style="margin:0">รูปแบบ: <strong>2 บรรทัด</strong> (คงที่)</span>
      <label>เต็มถัง =
        <input type="number" id="line-full-tank-target" min="50" step="10" value="{int(FULL_TANK_TARGET_L)}" style="width:64px;padding:6px;border-radius:6px;border:1px solid #cbd5e1" /> ล.
      </label>
      <label>ไปปั๊มประมาณ
        <input type="number" id="line-pump-travel" min="0" max="20" step="1" value="{int(DEFAULT_PUMP_TRAVEL_L)}" style="width:48px;padding:6px;border-radius:6px;border:1px solid #cbd5e1" /> ล.
      </label>
    </div>
    <textarea id="line-preview" readonly placeholder="ตัวอย่างข้อความจะขึ้นที่นี่…"></textarea>
    <div class="line-notify-row" style="margin-top:10px">
      <button type="button" class="btn btn-line btn-line-all" onclick="copyAllLineMessages()">คัดลอกทั้งหมด (คันที่มีลิตรเติม)</button>
      <button type="button" class="btn btn-line" onclick="copyLinePreview()">คัดลอกตัวอย่างด้านบน</button>
    </div>
  </section>
  <div id="line-toast" class="line-toast no-print"></div>
  <div id="report">
    <header class="report-head">
      <h1>แผนจัดคัน LCB — แผน LINE + น้ำมัน GPS</h1>
      <p class="sub">แผน {meta.get('plan_file', '')} · สร้าง {meta['generated_th']}</p>
      <p class="sub">แหล่งน้ำมัน: {meta.get('fuel_source', '')} · เที่ยวตู้ (ไม่รวม Oatside): {meta.get('container_trips_dispatch', 0)} · หัวแผน LINE วิ่ง: {meta.get('header_running', '—')}</p>
      {(
        '<p class="sub" style="color:#b45309">GPS จากไฟล์เก่า (รถไม่ขยับในไฟล์ล่าสุด): '
        + "<br>".join(meta.get("gps_fallback_log") or [])
        + "</p>"
      ) if meta.get("gps_fallback_count") else ""}
      <p class="sub">{meta.get('nhl_summary', '')}</p>
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
    {pump_panel_html}
    <p class="table-scroll-hint no-print">← เลื่อนซ้าย–ขวาดูทุกคอลัมน์ · คอลัมน์ # ทะเบียน งาน และปุ่ม LINE ติดขอบ →</p>
    <div class="table-scroll-wrap no-print-scroll">
      <table id="dispatch-table">
        <thead><tr>
          <th class="c-num c-num-n">#</th>
          <th class="c-sticky-plate">ทะเบียน</th>
          <th class="c-sticky-job">งาน</th>
          <th class="c-num c-col-narrow" title="น้ำมันที่คาดใช้วิ่ง">ใช้</th>
          <th class="c-num c-col-narrow">GPS</th>
          <th class="c-num c-col-narrow" title="GPS+เติมแล้ว">หลังเติม</th>
          <th class="c-num c-col-narrow" title="หลังเติม−ใช้">หลังวิ่ง</th>
          <th class="c-num c-col-refill">เติมวันนี้</th>
          <th class="no-print c-branch">สาขา</th>
          <th class="c-num c-col-narrow" title="GPS+แผนเติม">เติม(แผน)</th>
          <th class="c-num c-col-narrow" title="หลังเติมแผน−ใช้">วิ่ง(แผน)</th>
          <th class="c-num c-col-narrow">฿</th>
          <th class="c-col-status" title="เลือกเองหรืออัตโนมัติ">สถานะ</th>
          <th class="c-col-gps-time">GPS อัปเดต</th>
          <th class="no-print c-col-action">LINE</th>
        </tr></thead>
        <tbody>
{chr(10).join(body_rows)}
        </tbody>
      </table>
    </div>
    {refuel_html}
    <section class="excluded"><h3>ไม่จัด / พิเศษ</h3><ul>{excluded_html}</ul></section>
    <p class="foot-note">สูตร: KAO/Conti/Lacation 50·KATOEN 40·Haier 100·คลังวาฬ/ฟรีโซน 25·เหรินเหอ 70·Oatside ~110/วัน · Project YK</p>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script>
    const REPORT_DATA = {data_json};
    const PUMP_CREDIT = {pump_json};
    const REFUEL_BUFFER_L = {REFUEL_BUFFER_L};
    let BUDGET_LOW = {budget_low};
    let BUDGET_HIGH = {budget_high};
    const TONIGHT_BAHT_INIT = {meta.get('tonight_refuel_baht', 0)};  // ค่าเริ่มต้นจาก build — แก้ได้ใน UI

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

    function setPlanFuelCells(inp, planL, plateArg) {{
      const plate = plateArg || inp.dataset.plate;
      const base = parseFloat(inp.dataset.fuelBase) || 0;
      const need = parseFloat(inp.dataset.need) || 0;
      const full = isFullTankRow(plate);
      const ar = document.querySelector('.after-refill-plan[data-plate="' + plate + '"]');
      const at = document.querySelector('.after-trip-plan[data-plate="' + plate + '"]');
      if (full && planL > 0) {{
        const target = getFullTankTarget();
        const afterRefill = Math.min(target, base + planL);
        const afterTrip = afterRefill - need;
        if (ar) ar.textContent = 'เต็ม~' + fmtLiters(afterRefill);
        if (at) {{
          at.textContent = fmtLiters(afterTrip);
          at.classList.toggle('low', afterTrip < REFUEL_BUFFER_L);
        }}
        return;
      }}
      const afterRefill = base + planL;
      const afterTrip = afterRefill - need;
      const low = afterTrip < REFUEL_BUFFER_L;
      if (ar) ar.textContent = fmtLiters(afterRefill);
      if (at) {{
        at.textContent = fmtLiters(afterTrip);
        at.classList.toggle('low', low);
      }}
    }}

    function getTonightLiters(plate) {{
      const t = document.querySelector('.tonight-in[data-plate="' + plate + '"]');
      return t ? Math.max(0, parseFloat(t.value) || 0) : 0;
    }}

    function statusStorageKey() {{
      const plan = (REPORT_DATA.meta && REPORT_DATA.meta.plan_file) || 'plan';
      return 'yk_fuel_status_v2_' + plan.replace(/[^a-zA-Z0-9._-]+/g, '_');
    }}

    function loadSavedStatuses() {{
      try {{
        return JSON.parse(localStorage.getItem(statusStorageKey()) || '{{}}');
      }} catch (e) {{
        return {{}};
      }}
    }}

    function saveRowStatus(plate, value) {{
      const all = loadSavedStatuses();
      if (value === 'auto') delete all[plate];
      else all[plate] = value;
      try {{ localStorage.setItem(statusStorageKey(), JSON.stringify(all)); }} catch (e) {{}}
    }}

    function getAutoStatus(plate) {{
      const sel = document.querySelector('.status-row[data-plate="' + plate + '"]');
      if (!sel) return 'ok';
      if (sel.dataset.autoDone === '1') return 'done';
      if (sel.dataset.autoNeed === '1') return 'need';
      return 'ok';
    }}

    function getRowStatusMode(plate) {{
      const sel = document.querySelector('.status-row[data-plate="' + plate + '"]');
      return sel ? sel.value : 'auto';
    }}

    function getEffectiveStatus(plate) {{
      const mode = getRowStatusMode(plate);
      if (mode === 'auto') return getAutoStatus(plate);
      return mode;
    }}

    function statusLabel(eff) {{
      if (eff === 'done') return 'เติมแล้ว';
      if (eff === 'need') return 'ต้องเติม';
      return 'ปกติ';
    }}

    function syncStatusRow(plate) {{
      const tr = document.querySelector('tr[data-plate="' + plate + '"]');
      const sel = document.querySelector('.status-row[data-plate="' + plate + '"]');
      const badges = document.querySelector('.status-badges[data-plate="' + plate + '"]');
      const tonightWrap = document.querySelector('.status-tonight[data-plate="' + plate + '"]');
      if (!sel || !badges) return;
      const eff = getEffectiveStatus(plate);
      const parts = [];
      if (eff === 'done') parts.push('<span class="badge badge-ok">' + statusLabel('done') + '</span>');
      else if (eff === 'need') parts.push('<span class="badge badge-risk">' + statusLabel('need') + '</span>');
      else parts.push('<span class="badge badge-ok" style="background:#e2e8f0;color:#475569">ปกติ</span>');
      if (sel.dataset.autoStale === '1') {{
        parts.push('<span class="badge badge-warn">GPS เก่า</span>');
      }}
      if (getRowStatusMode(plate) !== 'auto') {{
        parts.push('<span class="badge" style="background:#e0e7ff;color:#3730a3">กำหนดเอง</span>');
      }}
      badges.innerHTML = parts.join(' ');
      if (tr) tr.classList.toggle('row-must-refuel', eff === 'need');
      if (tonightWrap) tonightWrap.style.display = eff === 'done' ? 'block' : 'none';
    }}

    function syncAllStatuses() {{
      document.querySelectorAll('.status-row').forEach(sel => syncStatusRow(sel.dataset.plate));
    }}

    function initRowStatuses() {{
      const saved = loadSavedStatuses();
      document.querySelectorAll('.status-row').forEach(sel => {{
        const plate = sel.dataset.plate;
        if (saved[plate]) sel.value = saved[plate];
        syncStatusRow(plate);
      }});
    }}

    function recalcAll() {{
      getBudgetCaps();
      const price = getDieselPrice();
      let tonightL = 0;
      document.querySelectorAll('.tonight-in').forEach(t => {{
        tonightL += Math.max(0, parseFloat(t.value) || 0);
      }});
      const tonightB = tonightL * price;
      let plannedL = 0;
      let plannedB = 0;
      document.querySelectorAll('.refill-in').forEach(inp => {{
        const plate = inp.dataset.plate;
        const L = effectivePlanLiters(plate);
        const alreadyFueled = getTonightLiters(plate);
        const extraL = Math.max(0, L - alreadyFueled);
        const cost = extraL * price;
        plannedL += extraL;
        plannedB += cost;
        setPlanFuelCells(inp, L, plate);
        const cell = document.querySelector('.refill-cost[data-plate="' + plate + '"]');
        if (cell) cell.textContent = extraL > 0 ? fmtBaht(cost) : '0';
      }});
      const totalB = tonightB + plannedB;
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
      let msg = 'รวมงบ <strong>' + fmtBaht(totalB) + ' ฿</strong> (เติมแล้ว ' + fmtBaht(tonightB) + ' + แผนเติม ' + fmtBaht(plannedB) + ')';
      if (totalB < BUDGET_LOW) msg += ' · ต่ำกว่าเป้า ' + fmtBaht(BUDGET_LOW);
      else if (totalB <= BUDGET_HIGH) msg += ' · <span style="color:#166534">อยู่ในช่วง ' + fmtBaht(BUDGET_LOW) + '–' + fmtBaht(BUDGET_HIGH) + '</span>';
      else msg += ' · <span style="color:#b91c1c">เกิน ' + fmtBaht(BUDGET_HIGH) + ' ฿</span>';
      if (status) status.innerHTML = msg;
      const bufL = REPORT_DATA.assignments.filter(r => r.needs_refuel).reduce((s, r) => s + (r.refuel_buffer_l || 0), 0);
      const hintL = document.getElementById('buffer-liters-hint');
      const hintB = document.getElementById('buffer-baht-hint');
      if (hintL) hintL.textContent = bufL.toFixed(0) + ' ล.';
      if (hintB) hintB.textContent = fmtBaht(bufL * price) + ' บาท';
      updatePumpProjection(plannedB);
    }}

    function updatePumpProjection(plannedBaht) {{
      if (!PUMP_CREDIT || !PUMP_CREDIT.ok) return;
      const closing = PUMP_CREDIT.closing_balance_baht;
      const limit = PUMP_CREDIT.credit_limit_baht || 50000;
      const proj = closing - plannedBaht;
      const debt = Math.max(0, -proj);
      const headroom = Math.max(0, limit - debt);
      const elB = document.getElementById('pump-projected-balance');
      const elH = document.getElementById('pump-headroom');
      const elN = document.getElementById('pump-projected-note');
      if (elB) {{
        elB.textContent = fmtBaht(proj) + ' ฿';
        elB.className = 'val ' + (proj < 0 ? 'neg' : 'pos');
      }}
      if (elH) {{
        elH.textContent = fmtBaht(headroom) + ' ฿';
        elH.className = 'val' + (headroom < limit * 0.15 ? ' neg' : '');
      }}
      if (elN) {{
        let note = 'หลังหักแผนเติมวันนี้ ~' + fmtBaht(plannedBaht) + ' ฿';
        if (debt >= limit * 0.85) note += ' · ใกล้เพดานติดลบ';
        elN.textContent = note;
      }}
    }}

    document.getElementById('diesel-price').addEventListener('input', recalcAll);
    document.getElementById('budget-low')?.addEventListener('input', recalcAll);
    document.getElementById('budget-high')?.addEventListener('input', recalcAll);
    document.querySelectorAll('.refill-in').forEach(inp => inp.addEventListener('input', recalcAll));
    document.querySelectorAll('.tonight-in').forEach(inp => inp.addEventListener('input', () => {{
      recalcAll();
      syncStatusRow(inp.dataset.plate);
    }}));
    document.querySelectorAll('.status-row').forEach(sel => {{
      sel.addEventListener('change', () => {{
        saveRowStatus(sel.dataset.plate, sel.value);
        syncStatusRow(sel.dataset.plate);
        recalcAll();
      }});
    }});
    initRowStatuses();
    recalcAll();

    const LINE_BRANCHES = {{
      'ศรีไทย': {{ notify: 'แจ้งเติมน้ำมันคาล์เท็กซ์ศรีไทย' }},
      'จุกกะเฌอ': {{ notify: 'แจ้งเติมน้ำมันคาล์เท็กซ์จุกกะเฌอ' }},
      'ปิ่นทอง1': {{ notify: 'แจ้งเติมน้ำมันคาล์เท็กซ์ปิ่นทอง1' }},
      'ปิ่นทอง2': {{ notify: 'แจ้งเติมน้ำมันคาล์เท็กซ์ปิ่นทอง2' }},
      'สาขา16': {{ notify: 'แจ้งเติมCaltex เต็กย้ง กรุ๊ป สาขา 16', singleTail: 'Caltex สาขา 16' }},
      'ทวีทรัพย์': {{ notify: 'แจ้งเติมน้ำมันคาล์เท็กซ์ทวีทรัพย์' }},
      'บ้านเก่า': {{ notify: 'แจ้งเติมน้ำมันคาล์เท็กซ์บ้านเก่า' }},
    }};

    function lineToast(msg) {{
      const el = document.getElementById('line-toast');
      if (!el) return;
      el.textContent = msg;
      el.style.display = 'block';
      clearTimeout(lineToast._t);
      lineToast._t = setTimeout(() => {{ el.style.display = 'none'; }}, 2200);
    }}

    function driverForLine(driver) {{
      if (!driver) return '';
      let d = driver.replace(/\\d[\\d\\-\\s]+$/, '').trim();
      const m = d.match(/^นาย(\\S+)/);
      if (m) {{
        const name = m[1];
        if (name.length <= 5) return name;
        return 'นาย' + name;
      }}
      return d.split(/\\s+/)[0] || '';
    }}

    function getRefillLitersForPlate(plate) {{
      const inp = document.querySelector('.refill-in[data-plate="' + plate + '"]');
      return inp ? refillLiters(inp) : 0;
    }}

    function getFullTankTarget() {{
      const el = document.getElementById('line-full-tank-target');
      const v = parseFloat(el && el.value);
      return Number.isFinite(v) && v > 0 ? v : {int(FULL_TANK_TARGET_L)};
    }}

    function getPumpTravelLiters() {{
      const el = document.getElementById('line-pump-travel');
      const v = parseFloat(el && el.value);
      return Number.isFinite(v) && v >= 0 ? v : {int(DEFAULT_PUMP_TRAVEL_L)};
    }}

    function roundUp10(n) {{
      return Math.ceil(Math.max(0, n) / 10) * 10;
    }}

    function calcFullTankRefillLiters(plate) {{
      const inp = document.querySelector('.refill-in[data-plate="' + plate + '"]');
      const gps = inp ? (parseFloat(inp.dataset.fuelBase) || 0) : 0;
      const target = getFullTankTarget();
      const travel = getPumpTravelLiters();
      return roundUp10(target - gps + travel);
    }}

    function isFullTankRow(plate) {{
      const cb = document.querySelector('.line-full-row[data-plate="' + plate + '"]');
      return !!(cb && cb.checked);
    }}

    function getBranchForPlate(plate) {{
      const sel = document.querySelector('.line-branch-row[data-plate="' + plate + '"]');
      return sel ? sel.value : (document.getElementById('line-branch-default')?.value || 'จุกกะเฌอ');
    }}

    function effectivePlanLiters(plate) {{
      if (isFullTankRow(plate)) return calcFullTankRefillLiters(plate);
      return getRefillLitersForPlate(plate);
    }}

    function rowWantsLineNotify(plate) {{
      return isFullTankRow(plate) || getRefillLitersForPlate(plate) > 0;
    }}

    function syncFullTankRow(plate) {{
      const tr = document.querySelector('tr[data-plate="' + plate + '"]');
      const inp = document.querySelector('.refill-in[data-plate="' + plate + '"]');
      const cb = document.querySelector('.line-full-row[data-plate="' + plate + '"]');
      if (!inp || !cb) return;
      const on = cb.checked;
      inp.disabled = on;
      if (on) {{
        const calc = calcFullTankRefillLiters(plate);
        inp.value = calc > 0 ? String(calc) : '';
        inp.title = 'เต็มถัง: ' + getFullTankTarget() + ' − GPS ' + (parseFloat(inp.dataset.fuelBase)||0) +
          ' + ไปปั๊ม ' + getPumpTravelLiters() + ' ล. (ปัดหน่วย 10)';
      }} else {{
        inp.title = 'ไม่บังคับเติม — ใส่ 0 ถ้าไม่เติม';
      }}
      if (tr) tr.classList.toggle('row-line-full-tank', on);
      recalcAll();
      updateLinePreview();
    }}

    function applyDefaultBranchToAllRows() {{
      const def = document.getElementById('line-branch-default')?.value || 'จุกกะเฌอ';
      document.querySelectorAll('.line-branch-row').forEach(sel => {{ sel.value = def; }});
      try {{ localStorage.setItem('yk_line_branch_v1', def); }} catch (e) {{}}
      lineToast('ใส่สาขา ' + def + ' ทุกแถวแล้ว');
      updateLinePreview();
    }}

    function buildLineMessage(plate, driver, liters, opts) {{
      const branchKey = opts.branch || 'จุกกะเฌอ';
      const cfg = LINE_BRANCHES[branchKey] || LINE_BRANCHES['จุกกะเฌอ'];
      const particle = opts.particle || 'ค่ะ';
      const drv = driverForLine(driver);
      const fullTank = !!opts.fullTank;
      if (!fullTank && (!liters || liters <= 0)) return null;
      const amount = fullTank ? 'เต็มถัง' : (Math.round(liters) + ' ลิตร');
      const line1 = plate + ' ' + drv + ' ดีเซล ' + amount;
      if (opts.format === 'single') {{
        if (cfg.singleTail) return line1 + ' ' + cfg.singleTail + ' ' + particle;
        return line1 + ' ' + cfg.notify + ' ' + particle;
      }}
      return line1 + '\\n' + cfg.notify + ' ' + particle;
    }}

    function getLineOptsForPlate(plate) {{
      return {{
        branch: getBranchForPlate(plate),
        particle: document.getElementById('line-particle')?.value || 'ค่ะ',
        format: 'double',
        fullTank: isFullTankRow(plate),
      }};
    }}

    function updateLinePreview() {{
      const preview = document.getElementById('line-preview');
      if (!preview) return;
      let plate = '', driver = '', liters = 0;
      document.querySelectorAll('#dispatch-table tbody tr').forEach(row => {{
        const p = row.dataset.plate;
        if (!rowWantsLineNotify(p) || plate) return;
        plate = p;
        driver = row.dataset.driver || '';
        liters = getRefillLitersForPlate(p);
      }});
      if (!plate) {{
        const first = document.querySelector('#dispatch-table tbody tr');
        if (first) {{
          plate = first.dataset.plate;
          driver = first.dataset.driver || '';
          liters = getRefillLitersForPlate(plate);
        }}
      }}
      const msg = buildLineMessage(plate, driver, liters, getLineOptsForPlate(plate));
      preview.value = msg || '(เลือกสาขาในแถว + กรอกลิตร หรือติ๊กเต็มถัง)';
    }}

    async function copyText(text) {{
      if (!text) {{ lineToast('ไม่มีข้อความ'); return false; }}
      try {{
        await navigator.clipboard.writeText(text);
        return true;
      }} catch (e) {{
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        return true;
      }}
    }}

    async function copyLineForPlate(plate, btn) {{
      const tr = document.querySelector('tr[data-plate="' + plate + '"]');
      const driver = tr ? tr.dataset.driver || '' : '';
      const liters = getRefillLitersForPlate(plate);
      const msg = buildLineMessage(plate, driver, liters, getLineOptsForPlate(plate));
      if (!msg) {{ lineToast(plate + ': กรอกลิตร หรือติ๊กเต็มถัง'); return; }}
      if (await copyText(msg)) {{
        lineToast('คัดลอกแล้ว: ' + plate);
        if (btn) {{ btn.classList.add('ok'); btn.textContent = 'OK'; setTimeout(() => {{ btn.classList.remove('ok'); btn.textContent = 'LINE'; }}, 1500); }}
      }}
    }}

    async function copyLinePreview() {{
      const t = document.getElementById('line-preview')?.value;
      if (t && !t.startsWith('(') && await copyText(t)) lineToast('คัดลอกตัวอย่างแล้ว');
    }}

    async function copyAllLineMessages() {{
      const blocks = [];
      document.querySelectorAll('#dispatch-table tbody tr').forEach(tr => {{
        const plate = tr.dataset.plate;
        if (!rowWantsLineNotify(plate)) return;
        const liters = getRefillLitersForPlate(plate);
        const msg = buildLineMessage(plate, tr.dataset.driver || '', liters, getLineOptsForPlate(plate));
        if (msg) blocks.push(msg);
      }});
      if (!blocks.length) {{ lineToast('ไม่มีคัน — กรอกลิตรหรือติ๊กเต็มถัง'); return; }}
      if (await copyText(blocks.join('\\n\\n'))) lineToast('คัดลอก ' + blocks.length + ' ข้อความ');
    }}

    document.getElementById('line-particle')?.addEventListener('change', updateLinePreview);
    document.getElementById('line-branch-default')?.addEventListener('change', () => {{
      try {{ localStorage.setItem('yk_line_branch_v1', document.getElementById('line-branch-default')?.value || ''); }} catch (e) {{}}
    }});
    function onFullTankSettingsChange() {{
      document.querySelectorAll('.line-full-row:checked').forEach(cb => {{
        syncFullTankRow(cb.dataset.plate);
      }});
      recalcAll();
      updateLinePreview();
    }}
    document.getElementById('line-full-tank-target')?.addEventListener('input', onFullTankSettingsChange);
    document.getElementById('line-pump-travel')?.addEventListener('input', onFullTankSettingsChange);
    try {{
      const saved = localStorage.getItem('yk_line_branch_v1');
      if (saved && LINE_BRANCHES[saved]) {{
        const d = document.getElementById('line-branch-default');
        if (d) d.value = saved;
      }}
    }} catch (e) {{}}
    document.querySelectorAll('.btn-line-one').forEach(btn => {{
      btn.addEventListener('click', () => copyLineForPlate(btn.dataset.plate, btn));
    }});
    document.querySelectorAll('.line-full-row').forEach(cb => {{
      cb.addEventListener('change', () => syncFullTankRow(cb.dataset.plate));
    }});
    document.querySelectorAll('.line-branch-row').forEach(sel => {{
      sel.addEventListener('change', updateLinePreview);
    }});
    document.querySelectorAll('.refill-in').forEach(inp => {{
      inp.addEventListener('input', () => {{ recalcAll(); updateLinePreview(); }});
    }});
    updateLinePreview();

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
        const notes = [statusLabel(getEffectiveStatus(plate))];
        if (getRowStatusMode(plate) !== 'auto') notes.push('กำหนดเอง');
        if (r.stale) notes.push('GPS เก่า');
        if (r.gps_fallback_from) notes.push('↩' + r.gps_fallback_from);
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
    ap.add_argument("--pump-pdf", type=Path, default=None, help="รายงานปั๊ม PDF (default: ล่าสุดใน pump_inbox)")
    ap.add_argument("--no-pump", action="store_true", help="ไม่โหลด PDF ปั๊ม")
    ap.add_argument(
        "--credit-limit",
        type=float,
        default=DEFAULT_CREDIT_LIMIT,
        help="เพดานติดลบปั๊ม (฿) — default 50000",
    )
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
    gps_fallback_log: list[str] = []
    plan_plates = [a.plate for a in plan.assignments]
    if args.fuel_xlsx and args.fuel_xlsx.exists():
        fuel_by, gps_fallback_log = merge_fuel_gps_with_fallback(
            args.fuel_xlsx, plan_plates
        )
        fuel_source = args.fuel_xlsx.name
        n_fb = sum(1 for p in plan_plates if fuel_by.get(p, {}).get("gps_fallback_from"))
        if n_fb:
            fuel_source += f" (+{n_fb} คันจากไฟล์เก่า)"
    elif args.fuel_csv and args.fuel_csv.exists():
        fuel_by = load_fuel_csv(args.fuel_csv)
        fuel_source = args.fuel_csv.name
    else:
        xlsx = _find_default_xlsx()
        if xlsx:
            fuel_by, gps_fallback_log = merge_fuel_gps_with_fallback(
                xlsx, plan_plates
            )
            n_fb = sum(
                1 for p in plan_plates if fuel_by.get(p, {}).get("gps_fallback_from")
            )
            fuel_source = f"{xlsx.name} ({xlsx.parent.name})"
            if n_fb:
                fuel_source += f" (+{n_fb} คันจากไฟล์เก่า)"
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

    pump_ui: dict | None = None
    if not args.no_pump:
        pump_raw: dict | None = None
        if args.pump_pdf and args.pump_pdf.exists():
            pump_raw = parse_pump_credit_pdf(
                args.pump_pdf, credit_limit_baht=args.credit_limit
            )
            print(f"ปั๊ม PDF: {args.pump_pdf.name}")
        else:
            latest_pump = find_latest_pump_pdf()
            if latest_pump:
                pump_raw = parse_pump_credit_pdf(
                    latest_pump, credit_limit_baht=args.credit_limit
                )
                print(f"ปั๊ม PDF (auto): {latest_pump.name}")
            else:
                pump_raw = load_snapshot()
                if pump_raw and pump_raw.get("ok"):
                    print("ปั๊ม: ใช้ pump_credit_latest.json (ไม่พบ PDF ใหม่)")
        if pump_raw and pump_raw.get("ok"):
            save_snapshot(pump_raw)
            pump_ui = pump_summary_for_ui(pump_raw, plan_plates)
            print(
                f"  ยอดปั๊มปิด: {pump_raw['closing_balance_baht']:,.2f} ฿ | "
                f"หนี้ {pump_raw['debt_baht']:,.0f} ฿ | "
                f"เหลือก่อนเพดาน {args.credit_limit:,.0f}: "
                f"{pump_raw['headroom_before_limit_baht']:,.0f} ฿"
            )
        elif pump_raw:
            print(f"[WARN] อ่าน PDF ปั๊มไม่ได้: {pump_raw.get('error', '?')}")

    tonight_l = sum(add_fuel.values())
    tonight_baht = tonight_l * args.diesel_price
    refuel_buffer_l = sum(r["refuel_buffer_l"] for r in dispatch_rows if r["needs_refuel"])
    refuel_buffer_baht = refuel_buffer_l * args.diesel_price
    total_spend = tonight_baht + refuel_buffer_baht

    tstats = plan_trip_stats(plan)
    trip_count = tstats["container_trips_dispatch"]
    fuel_need = sum(a.need_liters for a in plan.assignments if a.job != "Oatside")

    excluded = list(EXCLUDED_DEFAULT)
    for old, new in sorted(plan.replacements.items()):
        excluded.append((old, f"แผนใช้ {new} แทน"))
    for p in sorted(plan.broken_plates):
        if p not in plan.replacements and not any(p == x[0] for x in excluded):
            excluded.append((p, "รถเสีย — ไม่จัดงาน"))

    tonight_detail = ", ".join(
        f"{p} +{v:.0f} ล." for p, v in sorted(add_fuel.items())
    )

    nhl_whale = [a for a in plan.assignments if a.job == "คลังวาฬ"]
    nhl_fz = [a for a in plan.assignments if a.job == "ฟรีโซน"]
    nhl_whale_trips = sum(a.trips for a in nhl_whale)
    nhl_fz_trips = sum(a.trips for a in nhl_fz)
    nhl_summary = ""
    if nhl_whale_trips or nhl_fz_trips:
        nhl_summary = (
            f"NHL: คลังวาฬ {nhl_whale_trips} ตู้ ({len(nhl_whale)} คัน)"
            f" + ฟรีโซน {nhl_fz_trips} ตู้ ({len(nhl_fz)} คัน)"
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
        "nhl_summary": nhl_summary,
        "gps_fallback_count": sum(
            1 for p in plan_plates if fuel_by.get(p, {}).get("gps_fallback_from")
        ),
        "gps_fallback_log": gps_fallback_log,
        "pump_source": (pump_ui or {}).get("source_file", ""),
        "pump_closing_baht": (pump_ui or {}).get("closing_balance_baht"),
        "pump_headroom_baht": (pump_ui or {}).get("headroom_before_limit_baht"),
    }

    html = render_html(rows, meta, excluded, pump_ui=pump_ui)
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
                "งาน": r.get("job_display", r["job"]),
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
                f"  {r['plate']} {r.get('job_display', r['job'])}: เหลือ {r['left']:.0f} ล. "
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
