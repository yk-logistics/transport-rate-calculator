# -*- coding: utf-8 -*-
"""Trips: filter/search by plate. Index: collapsible sections (details/summary)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "Oatside" / "build_oatside_reports.py"
IDX_SEG = ROOT / "ProjectYK_System" / "tools" / "_idx_segment_raw.txt"


def main() -> None:
    s = P.read_text(encoding="utf-8")
    if "tripsPlateFilter" in s and "section-fold" in s:
        print("already patched")
        return

    anchor_esc = (
        "def esc(x) -> str:\n"
        "    return html_module.escape(str(x), quote=True)\n\n\n\n\n"
        "def html_fifty_surcharge_badge(fr: dict, cfg: OatsideConfig) -> str:\n"
    )
    if anchor_esc not in s:
        raise SystemExit("esc/html_fifty anchor missing (expected 5 blank lines after esc)")

    ins = (
        "def esc(x) -> str:\n"
        "    return html_module.escape(str(x), quote=True)\n\n\n"
        "_TRIPS_FILTER_JS = (\n"
        "    \"<script>(function(){\"\n"
        "    \"var sel=document.getElementById('tripsPlateFilter');\"\n"
        "    \"var qel=document.getElementById('tripsPlateQuery');\"\n"
        "    \"var tb=document.querySelector('#tripsAllTable tbody');\"\n"
        "    \"if(!tb)return;\"\n"
        "    \"function run(){\"\n"
        "    \"var v=sel?(sel.value||'').trim():'';\"\n"
        "    \"var q=qel?(qel.value||'').trim().toLowerCase():'';\"\n"
        "    \"var rows=tb.querySelectorAll('tr');\"\n"
        "    \"for(var i=0;i<rows.length;i++){\"\n"
        "    \"var r=rows[i];\"\n"
        "    \"var p=(r.getAttribute('data-plate')||'');\"\n"
        "    \"var pok=!v||p===v;\"\n"
        "    \"var qok=!q||p.toLowerCase().indexOf(q)>=0;\"\n"
        "    \"r.style.display=(pok&&qok)?'':'none';\"\n"
        "    \"}\"\n"
        "    \"}\"\n"
        "    \"if(sel)sel.addEventListener('change',run);\"\n"
        "    \"if(qel)qel.addEventListener('input',run);\"\n"
        "    \"})();</script>\"\n"
        ")\n\n\n"
        "def html_fifty_surcharge_badge(fr: dict, cfg: OatsideConfig) -> str:\n"
    )
    s = s.replace(anchor_esc, ins, 1)

    s = s.replace(
        '      return (\n'
        '            f"<tr><td>{t.origin_date}</td><td>{t.dest_date}</td>"\n',
        '      return (\n'
        '            f"<tr data-plate=\'{esc(t.plate)}\'><td>{t.origin_date}</td><td>{t.dest_date}</td>"\n',
        1,
    )
    s = s.replace(
        '      return (\n'
        '            f"<tr><td>{t.origin_date}</td><td>{t.dest_date}</td><td>{t.site}{ab}</td>"\n',
        '      return (\n'
        '            f"<tr data-plate=\'{esc(t.plate)}\'><td>{t.origin_date}</td><td>{t.dest_date}</td><td>{t.site}{ab}</td>"\n',
        1,
    )
    s = s.replace(
        "        f\"<tr class='um'><td>{od}</td><td>{dd}</td>{site_plate}\"",
        "        f\"<tr class='um' data-plate='{esc(leg.plate)}'><td>{od}</td><td>{dd}</td>{site_plate}\"",
        1,
    )

    s = s.replace(
        'tr.day-band-1 td.wait-hi-dest{background:#ffdfba;font-weight:600}"\n    )',
        'tr.day-band-1 td.wait-hi-dest{background:#ffdfba;font-weight:600}"'
        '"details.section-fold{margin-bottom:10px}"'
        '"summary.section-sum{cursor:pointer;padding:10px 14px;background:#fff;border-radius:10px;font-weight:600;margin-bottom:6px;display:block;box-shadow:0 2px 8px rgba(16,24,40,.08);list-style:none}"'
        '"summary.section-sum::-webkit-details-marker{display:none}"'
        '".filter-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0 14px}"'
        '".filter-bar label{font-size:13px;color:#4b5b74}"'
        '".filter-bar select,.filter-bar input[type=search]{font:inherit;padding:6px 10px;border-radius:8px;border:1px solid #c5d0e0;background:#fff;min-width:160px}"'
        "\n    )",
        1,
    )

    old_mid = IDX_SEG.read_text(encoding="utf-8")
    if old_mid not in s:
        raise SystemExit("idx middle segment missing — regenerate ProjectYK_System/tools/_idx_segment_raw.txt")

    raw_lines = old_mid.splitlines(True)
    if len(raw_lines) < 16:
        raise SystemExit("_idx_segment_raw.txt too short")
    join_line = raw_lines[9]

    new_mid = (
        "<details class='section-fold'><summary class='section-sum'>คำอธิบายสี / ไฮไลต์ชั่วโมงรอ</summary>\n"
        + raw_lines[0]
        + "</details>\n"
        "<details class='section-fold'><summary class='section-sum'>(1) จำนวนเที่ยวต่อวัน (matched Dest_In)</summary>\n"
        "<div class='panel'>\n"
        + raw_lines[2]
        + raw_lines[3]
        + raw_lines[4]
        + raw_lines[5]
        + "</details>\n"
        "<details class='section-fold'><summary class='section-sum'>(2) เดลี่รถทุกคัน — Dest_In × ทะเบียน</summary>\n"
        "<div class='panel'>\n"
        + raw_lines[7]
        + raw_lines[8]
        + join_line
        + raw_lines[10]
        + "</details>\n"
        "<details class='section-fold'><summary class='section-sum'>(3) Unmatched — {len(unmatched)} legs เรียงตามเวลา</summary>\n"
        "<div class='panel'>\n"
        + raw_lines[12]
        + raw_lines[13]
        + raw_lines[14]
        + raw_lines[15]
        + "</details>\n"
    )
    s = s.replace(old_mid, new_mid, 1)

    old_audit_open = (
        "<details><summary style='cursor:pointer;padding:10px 14px;background:#fff;border-radius:10px;"
        "font-weight:600;margin-bottom:10px;display:block;box-shadow:0 2px 8px rgba(16,24,40,.08)'>"
        "Audit Log — เหตุผลการคิดเงิน รายวัน × ทะเบียน (คลิกเพื่อขยาย)</summary>"
    )
    new_audit_open = (
        "<details class='section-fold'><summary class='section-sum'>"
        "Audit Log — เหตุผลการคิดเงิน รายวัน × ทะเบียน (คลิกเพื่อขยาย)</summary>"
    )
    if old_audit_open not in s:
        raise SystemExit("audit <details> opening not found")
    s = s.replace(old_audit_open, new_audit_open, 1)

    plates_marker = "<div class='panel'><h3>รายทะเบียน</h3><ul>"
    pi = s.find(plates_marker)
    if pi < 0:
        raise SystemExit("plates panel marker not found")
    pj = s.find("</ul></div>", pi)
    if pj < 0:
        raise SystemExit("plates panel end not found")
    pj += len("</ul></div>")
    if s[pj : pj + 1] == "\n":
        pj += 1
    old_plates_block = s[pi:pj]
    new_plates_block = (
        "<details class='section-fold'><summary class='section-sum'>รายทะเบียน</summary>\n"
        "<div class='panel'><ul>{''.join(f\"<li><a href='plates/{esc(p)}.html'>{esc(p)}</a></li>\" for p in plates)}</ul></div>\n"
        "</details>"
    )
    s = s.replace(old_plates_block, new_plates_block, 1)

    old_trips = (
        "    trips_html_content = f\"\"\"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>\n"
        "<title>Trips</title><style>{css}</style></head><body>\n"
        "<div class='h1'>เที่ยวทั้งหมด</div>\n"
        "<div class='nav'><a href='index.html'>&larr; กลับสรุป</a></div>\n"
        "<div class='panel'><h3>เที่ยวทั้งหมด (matched + unmatched)</h3>\n"
        "<p class='sub'>เรียงตามเวลา (matched ใช้ Origin In · unmatched ใช้เวลาขา Origin/Destination) — UM-O/UM-D เว้นฝั่งที่ยังไม่มีคู่เป็น —<br>\n"
        "<b>ค่าเงิน:</b> ค่าขนส่ง = เรทวัน Dest_In ของเที่ยวนั้น · <b>เสียเวลา+50%/+100%</b> = ยอดรวมส่วนเพิ่ม fifty ของ (ทะเบียน×วัน Dest_In) แสดงที่แถวแรกของวันนั้น — <b>ไม่ได้คิดจากชั่วโมงในช่อง Dest Wait โดยตรง</b> (สีส้ม = แค่เตือนว่ารอปลายทางเกินเกณฑ์)</p>\n"
        "<div class='table-scroll'><table><thead><tr><th>Origin Date</th><th>Dest Date</th><th>Site</th><th>ทะเบียน</th><th>Origin In</th><th>Origin Out</th><th>Dest In</th><th>Dest Out</th><th>Orig Wait</th><th>Travel</th><th>Dest Wait</th><th>ค่าขนส่ง(฿)</th><th>เสียเวลา+50%(฿)</th><th>เสียเวลา+100%(฿)</th><th>ตีเปล่า+50%(฿)</th></tr></thead><tbody>\n"
        "{merged_all_rows}\n"
        "</tbody></table></div></div>\n"
        "</body></html>\"\"\""
    )
    if old_trips not in s:
        raise SystemExit("trips_html_content block not found")

    new_trips = (
        "    _trips_plate_opts = \"\".join(f\"<option value='{esc(p)}'>{esc(p)}</option>\" for p in plates)\n"
        "    trips_html_content = (\n"
        "        f\"\"\"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>\n"
        "<title>Trips</title><style>{css}</style></head><body>\n"
        "<div class='h1'>เที่ยวทั้งหมด</div>\n"
        "<div class='nav'><a href='index.html'>&larr; กลับสรุป</a></div>\n"
        "<div class='panel'><h3>เที่ยวทั้งหมด (matched + unmatched)</h3>\n"
        "<p class='sub'>เรียงตามเวลา (matched ใช้ Origin In · unmatched ใช้เวลาขา Origin/Destination) — UM-O/UM-D เว้นฝั่งที่ยังไม่มีคู่เป็น —<br>\n"
        "<b>ค่าเงิน:</b> ค่าขนส่ง = เรทวัน Dest_In ของเที่ยวนั้น · <b>เสียเวลา+50%/+100%</b> = ยอดรวมส่วนเพิ่ม fifty ของ (ทะเบียน×วัน Dest_In) แสดงที่แถวแรกของวันนั้น — <b>ไม่ได้คิดจากชั่วโมงในช่อง Dest Wait โดยตรง</b> (สีส้ม = แค่เตือนว่ารอปลายทางเกินเกณฑ์)</p>\n"
        "<div class='filter-bar'><label for='tripsPlateFilter'>กรองทะเบียน</label><select id='tripsPlateFilter'><option value=''>ทุกคัน</option>{_trips_plate_opts}</select><label for='tripsPlateQuery' style='margin-left:6px'>ค้นหา</label><input id='tripsPlateQuery' type='search' placeholder='พิมพ์ค้นหา...' autocomplete='off'></div>\n"
        "<div class='table-scroll'><table id='tripsAllTable'><thead><tr><th>Origin Date</th><th>Dest Date</th><th>Site</th><th>ทะเบียน</th><th>Origin In</th><th>Origin Out</th><th>Dest In</th><th>Dest Out</th><th>Orig Wait</th><th>Travel</th><th>Dest Wait</th><th>ค่าขนส่ง(฿)</th><th>เสียเวลา+50%(฿)</th><th>เสียเวลา+100%(฿)</th><th>ตีเปล่า+50%(฿)</th></tr></thead><tbody>\n"
        "{merged_all_rows}\n"
        "</tbody></table></div></div>\n"
        "\"\"\"\n"
        "        + _TRIPS_FILTER_JS\n"
        "        + \"\\n</body></html>\"\n"
        "    )\n"
    )
    s = s.replace(old_trips, new_trips, 1)

    P.write_text(s, encoding="utf-8")
    print("patched", P)


if __name__ == "__main__":
    main()
