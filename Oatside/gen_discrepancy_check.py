"""สร้างหน้า discrepancy_check.html — เทียบเที่ยวรายวันสำหรับ 7 คันที่ Gap ≠ 0."""
import build_oatside_reports as M
from collections import defaultdict
import datetime as dt
from pathlib import Path

cfg = M.load_oatside_config()
folder = M._oatside_dir()
origin_path, dest_path = M.discover_gps_files(folder)
trips, unmatched, _ = M.build_trips(origin_path, dest_path, cfg)
o_legs = M.parse_legs(origin_path)
d_legs = M.parse_legs(dest_path)
overrides = M.load_billing_overrides()
fifty_rows, _ = M.surcharge_billed_day(trips, o_legs, d_legs, overrides, cfg)

trips_by_billed = defaultdict(list)
for t in trips: trips_by_billed[(t.plate, t.trip_date)].append(t)
trips_by_origin = defaultdict(list)
for t in trips: trips_by_origin[(t.plate, t.o_in.date())].append(t)
o_by = defaultdict(list)
for l in o_legs: o_by[(l.plate, l.t_in.date())].append(l)
d_by = defaultdict(list)
for l in d_legs: d_by[(l.plate, l.t_in.date())].append(l)
sur_by = {(r["plate"], r["dest_date"]): r for r in fifty_rows}

discrepancy = {
    "71-5041": (12, 11, "+1", "Daily คีย์เกิน 1"),
    "71-5042": (10,  9, "+1", "Daily คีย์เกิน 1"),
    "71-6802": (3,   4, "-1", "ระบบเก็บเพิ่ม 1 (overnight 5/2 ต้องตรวจ Oatside)"),
    "71-8001": (13, 10, "+3", "Daily คีย์เกิน 3 (ตรวจมือ)"),
    "71-8002": (30, 28, "+2", "Daily คีย์เกิน 2 (ตรวจมือ)"),
    "71-8005": (13, 12, "+1", "Daily คีย์เกิน 1 (ตรวจมือ)"),
    "71-8009": (35, 29, "+6", "Homepro คีย์เกิน 6 (ยืนยันแล้ว)"),
}

def fmt_leg(l):
    dwell = (l.t_out - l.t_in).total_seconds() / 3600
    noise = ' <span class="noise">noise</span>' if dwell < 0.5 else ""
    return f'{l.t_in:%H:%M}→{l.t_out:%H:%M} <span class="dw">({dwell:.1f}h)</span>{noise}'

def classify_day(ols, dls, ot, bt):
    flags = []
    if dls and not ols and len(bt) == 0:
        flags.append('<span class="flag bad">dest-only ไม่ใช่งาน Oatside</span>')
    short_dests = [l for l in dls if (l.t_out - l.t_in).total_seconds() / 3600 < 0.5]
    if short_dests and len(short_dests) == len(dls) and dls:
        flags.append('<span class="flag warn">dest dwell &lt; 30 นาที = gate noise</span>')
    return " ".join(flags)

css = """
body{font-family:Segoe UI,Tahoma,sans-serif;margin:20px;background:#f5f8fc;color:#111}
.nav{margin-bottom:12px;font-size:13px}.nav a{color:#0b57d0}
.h1{font-size:22px;font-weight:800;margin-bottom:4px}
.lead{background:#eff6ff;border-left:4px solid #0b57d0;padding:10px 14px;border-radius:6px;margin:10px 0;font-size:13px;line-height:1.6}
.plate-card{background:#fff;border-radius:10px;padding:14px;margin-bottom:14px;box-shadow:0 2px 8px rgba(16,24,40,.08)}
.plate-hdr{font-size:16px;font-weight:800;margin-bottom:6px}
.plate-sub{font-size:12px;color:#4b5b74;margin-bottom:8px}
.gap-badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700;margin-left:8px}
.gap-bad{background:#fecaca;color:#991b1b}.gap-warn{background:#fef3c7;color:#92400e}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#1f2937;color:#fff;padding:6px 8px;text-align:left;font-size:11px}
td{padding:5px 8px;border-bottom:1px solid #eef2f7;vertical-align:top}
.dw{color:#63758f;font-size:10px}
.noise{display:inline-block;background:#fee;color:#dc2626;font-size:9px;padding:1px 4px;border-radius:3px;font-weight:700}
.flag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700;margin-right:3px}
.flag.warn{background:#fef3c7;color:#92400e}.flag.bad{background:#fecaca;color:#991b1b}
.kind-no_finish_day{background:#fff7ed;color:#c2410c;font-weight:700;padding:1px 6px;border-radius:3px;font-size:10px}
.kind-one_trip_billed_day{background:#dbeafe;color:#1e40af;padding:1px 6px;border-radius:3px;font-size:10px}
.daily-col{background:#fffbeb;width:60px;text-align:center}
"""

parts = [
    '<!doctype html><html lang="th"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width,initial-scale=1">',
    '<title>เทียบเที่ยวที่ไม่ตรง · Oatside พ.ค. 2569</title>',
    f"<style>{css}</style></head><body>",
    '<div class="nav"><a href="index.html">← สรุปภาพรวม</a> · <a href="manual_check.html">ตรวจมือ summary</a></div>',
    '<div class="h1">เทียบเที่ยวที่ไม่ตรงรายวัน · Oatside พ.ค. 2569</div>',
    '<div class="lead">',
    '<b>วิธีใช้:</b> เปิด Daily Excel ไว้ข้าง ๆ — เทียบกับคอลัมน์ <b>Daily?</b> (กรอก ✓ ถ้าวันนั้นมีในไฟล์, X ถ้าไม่มี). Daily บันทึก แต่ระบบไม่มี = Daily คีย์เกิน. ระบบมี แต่ Daily ไม่บันทึก = ขาดเก็บ.<br>',
    '<b>คอลัมน์:</b> GPS Origin (รถเข้า Oatside) / GPS Dest (รถเข้า P&amp;G) — <span class="noise">noise</span> = dwell &lt; 30 นาที (ข้าม geofence ที่ประตู ไม่ใช่เที่ยวจริง)<br>',
    '<b>เที่ยว O-day:</b> เที่ยวที่ Origin_In ตกในวันนั้น. <b>เที่ยว Billed:</b> เที่ยวที่นับเข้าวันนั้นตามกฎใหม่ (= วัน Dest_Out + 06:00 grace)',
    "</div>",
]

for plate, (daily, bill, gap, note) in discrepancy.items():
    gap_class = "bad" if abs(int(gap.replace("+", "").replace("-", ""))) > 2 else "warn"
    parts.append(f'<div class="plate-card"><div class="plate-hdr">{plate} <span class="gap-badge gap-{gap_class}">Gap {gap} ({note})</span></div>')
    parts.append(f'<div class="plate-sub">Daily Excel = {daily} เที่ยว · ระบบ Bill = {bill} (matched + no-finish)</div>')
    parts.append('<table><thead><tr><th>วัน</th><th>GPS Origin (Oatside)</th><th>GPS Dest (P&amp;G)</th><th>O-day</th><th>Billed</th><th>Surcharge</th><th>ข้อสังเกต</th><th class="daily-col">Daily?</th></tr></thead><tbody>')
    all_dates = set()
    for (p, d) in list(o_by.keys()) + list(d_by.keys()) + list(trips_by_billed.keys()) + list(trips_by_origin.keys()) + list(sur_by.keys()):
        if p == plate and dt.date(2026, 5, 1) <= d <= dt.date(2026, 5, 31):
            all_dates.add(d)
    for d in sorted(all_dates):
        ols = o_by.get((plate, d), [])
        dls = d_by.get((plate, d), [])
        ot = trips_by_origin.get((plate, d), [])
        bt = trips_by_billed.get((plate, d), [])
        sur = sur_by.get((plate, d))
        if sur:
            sur_s = f'<span class="kind-{sur["fifty_kind"]}">{sur["fifty_kind"]}</span> ฿{sur["surcharge_baht"]:,}'
        else:
            sur_s = "—"
        flag_s = classify_day(ols, dls, ot, bt)
        ori_html = "; ".join(fmt_leg(l) for l in ols) or "—"
        dest_html = "; ".join(fmt_leg(l) for l in dls) or "—"
        parts.append(f"<tr><td><b>{d:%d/%m}</b></td><td>{ori_html}</td><td>{dest_html}</td><td>{len(ot)}</td><td>{len(bt)}</td><td>{sur_s}</td><td>{flag_s}</td><td class=\"daily-col\"></td></tr>")
    parts.append("</tbody></table></div>")

parts.append('<p style="color:#6b7280;font-size:11px;margin-top:14px">สร้าง 2026-06-05 · เทียบกับ Daily Excel ที่คนคีย์</p>')
parts.append("</body></html>")

out = Path(r"C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\reports\oatside-pg-2026\discrepancy_check.html")
out.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {out} ({len(out.read_text(encoding='utf-8'))} chars)")
