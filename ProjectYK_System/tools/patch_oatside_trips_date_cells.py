# Refine matched trip rows: date + HH:MM line; Thai headers (avoid duplicating full In columns).
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "Oatside" / "build_oatside_reports.py"
t = P.read_text(encoding="utf-8")

old1 = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.o_in}</td><td>{t.d_in}</td>\"\n"
    "            f\"<td><span class='badge {'bigc' if t.site=='BigC' else 'lcb'}'>{t.site}</span></td>\"\n"
)
new1 = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.origin_date}<br>"
    "<span class='note'>{t.o_in:%H:%M}</span></td><td>{t.dest_date}<br>"
    "<span class='note'>{t.d_in:%H:%M}</span></td>\"\n"
    "            f\"<td><span class='badge {'bigc' if t.site=='BigC' else 'lcb'}'>{t.site}</span></td>\"\n"
)
if old1 not in t:
    raise SystemExit("trip_row block not found")
t = t.replace(old1, new1, 1)

old2 = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.o_in}</td><td>{t.d_in}</td><td>{t.site}{ab}</td>\"\n"
    "            f\"<td>{t.o_in}</td><td>{t.o_out}</td><td>{t.d_in}</td><td>{t.d_out}</td>\"\n"
)
new2 = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.origin_date}<br>"
    "<span class='note'>{t.o_in:%H:%M}</span></td><td>{t.dest_date}<br>"
    "<span class='note'>{t.d_in:%H:%M}</span></td><td>{t.site}{ab}</td>\"\n"
    "            f\"<td>{t.o_in}</td><td>{t.o_out}</td><td>{t.d_in}</td><td>{t.d_out}</td>\"\n"
)
if old2 not in t:
    raise SystemExit("trip_row_plate block not found")
t = t.replace(old2, new2, 1)

old_th = (
    "<div class='table-scroll'><table id='tripsAllTable'><thead><tr>"
    "<th title='เวลาเข้าโหลดที่ Origin'>เข้า Origin</th>"
    "<th title='เวลาเข้าปลายทาง'>เข้า Dest</th><th>Site</th>"
)
new_th = (
    "<div class='table-scroll'><table id='tripsAllTable'><thead><tr>"
    "<th title='วันงานที่ Origin + เวลาเข้าโหลด'>วัน Origin</th>"
    "<th title='วันงานที่ปลายทาง + เวลาเข้า'>วัน Dest</th><th>Site</th>"
)
if old_th not in t:
    raise SystemExit("thead tripsAllTable not found")
t = t.replace(old_th, new_th, 1)

old_pl = (
    "<div class='table-scroll'><table><thead><tr>"
    "<th title='เวลาเข้าโหลดที่ Origin'>เข้า Origin</th>"
    "<th title='เวลาเข้าปลายทาง'>เข้า Dest</th><th>Site</th><th>Origin In</th>"
)
new_pl = (
    "<div class='table-scroll'><table><thead><tr>"
    "<th title='วันงานที่ Origin + เวลาเข้าโหลด'>วัน Origin</th>"
    "<th title='วันงานที่ปลายทาง + เวลาเข้า'>วัน Dest</th><th>Site</th><th>Origin In</th>"
)
if old_pl not in t:
    raise SystemExit("thead plate not found")
t = t.replace(old_pl, new_pl, 1)

P.write_text(t, encoding="utf-8")
print("OK")
