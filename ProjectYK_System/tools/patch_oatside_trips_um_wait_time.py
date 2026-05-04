# Patch: Oatside trips page — UM rows show Orig/Travel/Dest wait; date cols show datetime.
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "Oatside" / "build_oatside_reports.py"
text = P.read_text(encoding="utf-8")

old_prev = (
    "    if idx is None or idx + 1 >= len(timeline):\n"
    "        return dwell, None\n"
    "    gap = hours(leg.t_out, timeline[idx + 1].t_in)\n"
    "    return dwell, gap\n\n\n"
    "def customer_idle_clip_dest_wait_h"
)
new_prev = (
    "    if idx is None or idx + 1 >= len(timeline):\n"
    "        return dwell, None\n"
    "    gap = hours(leg.t_out, timeline[idx + 1].t_in)\n"
    "    return dwell, gap\n\n\n"
    "def um_leg_prev_gap_h(leg: Leg, timeline: list[Leg] | None) -> float | None:\n"
    "    \"\"\"Hours from previous leg's Out to this leg's In (same plate).\"\"\"\n"
    "    if not timeline:\n"
    "        return None\n"
    "    idx = next((i for i, L in enumerate(timeline) if L is leg), None)\n"
    "    if idx is None or idx == 0:\n"
    "        return None\n"
    "    return hours(timeline[idx - 1].t_out, leg.t_in)\n\n\n"
    "def customer_idle_clip_dest_wait_h"
)
if old_prev not in text:
    raise SystemExit("anchor1 not found")
text = text.replace(old_prev, new_prev, 1)

old_sig = (
    "def unmatched_merged_trip_one_row_html(\n"
    "    src: str,\n"
    "    leg: Leg,\n"
    "    *,\n"
    "    dwell_h: float,\n"
    "    gap_h: float | None,\n"
    "    include_plate_link: bool = True,\n"
    "    include_plate_column: bool = True,\n"
    ") -> str:"
)
new_sig = (
    "def unmatched_merged_trip_one_row_html(\n"
    "    src: str,\n"
    "    leg: Leg,\n"
    "    *,\n"
    "    dwell_h: float,\n"
    "    gap_h: float | None,\n"
    "    prev_gap_h: float | None,\n"
    "    include_plate_link: bool = True,\n"
    "    include_plate_column: bool = True,\n"
    ") -> str:"
)
if old_sig not in text:
    raise SystemExit("anchor sig not found")
text = text.replace(old_sig, new_sig, 1)

old_body = (
    "    if src == \"Origin\":\n"
    "        od, dd = leg.t_in.date(), dash\n"
    "        oi, oo = leg.t_in, leg.t_out\n"
    "        di, do = dash, dash\n"
    "    else:\n"
    "        od, dd = dash, leg.t_in.date()\n"
    "        oi, oo = dash, dash\n"
    "        di, do = leg.t_in, leg.t_out\n"
    "    return (\n"
    "        f\"<tr class='um' data-plate='{esc(leg.plate)}'><td>{od}</td><td>{dd}</td>{site_plate}\"\n"
    "        f\"<td>{oi}</td><td>{oo}</td><td>{di}</td><td>{do}</td>\"\n"
    "        f\"<td>{dash}</td><td>{dash}</td><td>{dash}</td>\"\n"
    "        f\"<td>{fmt_hm(dwell_h)}</td><td>{fmt_hm(gap_h) if gap_h is not None else dash}</td>\"\n"
)
new_body = (
    "    _pg = fmt_hm(prev_gap_h) if prev_gap_h is not None else dash\n"
    "    if src == \"Origin\":\n"
    "        od, dd = leg.t_in, dash\n"
    "        oi, oo = leg.t_in, leg.t_out\n"
    "        di, do = dash, dash\n"
    "        ow, trv, dw = fmt_hm(dwell_h), _pg, dash\n"
    "    else:\n"
    "        od, dd = dash, leg.t_in\n"
    "        oi, oo = dash, dash\n"
    "        di, do = leg.t_in, leg.t_out\n"
    "        ow, trv, dw = dash, _pg, fmt_hm(dwell_h)\n"
    "    return (\n"
    "        f\"<tr class='um' data-plate='{esc(leg.plate)}'><td>{od}</td><td>{dd}</td>{site_plate}\"\n"
    "        f\"<td>{oi}</td><td>{oo}</td><td>{di}</td><td>{do}</td>\"\n"
    "        f\"<td>{ow}</td><td>{trv}</td><td>{dw}</td>\"\n"
    "        f\"<td>{fmt_hm(dwell_h)}</td><td>{fmt_hm(gap_h) if gap_h is not None else dash}</td>\"\n"
)
if old_body not in text:
    raise SystemExit("anchor body not found")
text = text.replace(old_body, new_body, 1)

old_call = (
    "        _dw, _gp = um_leg_dwell_gap_h(\n"
    "            leg, leg_timeline_by_plate.get(leg.plate) if leg_timeline_by_plate else None\n"
    "        )\n"
    "        um_html = unmatched_merged_trip_one_row_html(\n"
    "            src,\n"
    "            leg,\n"
    "            dwell_h=_dw,\n"
    "            gap_h=_gp,\n"
    "            include_plate_link=include_plate_link,\n"
    "            include_plate_column=include_plate_column,\n"
    "        )\n"
)
new_call = (
    "        _tl = leg_timeline_by_plate.get(leg.plate) if leg_timeline_by_plate else None\n"
    "        _dw, _gp = um_leg_dwell_gap_h(leg, _tl)\n"
    "        _pre = um_leg_prev_gap_h(leg, _tl)\n"
    "        um_html = unmatched_merged_trip_one_row_html(\n"
    "            src,\n"
    "            leg,\n"
    "            dwell_h=_dw,\n"
    "            gap_h=_gp,\n"
    "            prev_gap_h=_pre,\n"
    "            include_plate_link=include_plate_link,\n"
    "            include_plate_column=include_plate_column,\n"
    "        )\n"
)
if old_call not in text:
    raise SystemExit("anchor call not found")
text = text.replace(old_call, new_call, 1)

old_trip = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.origin_date}</td><td>{t.dest_date}</td>\"\n"
    "            f\"<td><span class='badge {'bigc' if t.site=='BigC' else 'lcb'}'>{t.site}</span></td>\"\n"
    "            f\"<td><a href='plates/{esc(t.plate)}.html'>{esc(t.plate)}</a>{ab}</td>\"\n"
)
new_trip = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.o_in}</td><td>{t.d_in}</td>\"\n"
    "            f\"<td><span class='badge {'bigc' if t.site=='BigC' else 'lcb'}'>{t.site}</span></td>\"\n"
    "            f\"<td><a href='plates/{esc(t.plate)}.html'>{esc(t.plate)}</a>{ab}</td>\"\n"
)
if old_trip not in text:
    raise SystemExit("anchor trip_row not found")
text = text.replace(old_trip, new_trip, 1)

old_plate = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.origin_date}</td><td>{t.dest_date}</td><td>{t.site}{ab}</td>\"\n"
    "            f\"<td>{t.o_in}</td><td>{t.o_out}</td><td>{t.d_in}</td><td>{t.d_out}</td>\"\n"
)
new_plate = (
    "            f\"<tr data-plate='{esc(t.plate)}'><td>{t.o_in}</td><td>{t.d_in}</td><td>{t.site}{ab}</td>\"\n"
    "            f\"<td>{t.o_in}</td><td>{t.o_out}</td><td>{t.d_in}</td><td>{t.d_out}</td>\"\n"
)
if old_plate not in text:
    raise SystemExit("anchor trip_row_plate not found")
text = text.replace(old_plate, new_plate, 1)

old_th = (
    "<div class='table-scroll'><table id='tripsAllTable'><thead><tr><th>Origin Date</th><th>Dest Date</th><th>Site</th>"
)
new_th = (
    "<div class='table-scroll'><table id='tripsAllTable'><thead><tr>"
    "<th title='เวลาเข้าโหลดที่ Origin'>เข้า Origin</th>"
    "<th title='เวลาเข้าปลายทาง'>เข้า Dest</th><th>Site</th>"
)
if old_th not in text:
    raise SystemExit("anchor thead not found")
text = text.replace(old_th, new_th, 1)

old_th2 = (
    "<div class='table-scroll'><table><thead><tr><th>Origin Date</th><th>Dest Date</th><th>Site</th><th>Origin In</th>"
)
new_th2 = (
    "<div class='table-scroll'><table><thead><tr>"
    "<th title='เวลาเข้าโหลดที่ Origin'>เข้า Origin</th>"
    "<th title='เวลาเข้าปลายทาง'>เข้า Dest</th><th>Site</th><th>Origin In</th>"
)
if old_th2 not in text:
    raise SystemExit("anchor thead2 not found")
text = text.replace(old_th2, new_th2, 1)

P.write_text(text, encoding="utf-8")
print("OK:", P)
