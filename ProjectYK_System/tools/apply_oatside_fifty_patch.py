# -*- coding: utf-8 -*-
"""Patch Oatside/build_oatside_reports.py: fifty_kind, +100%% badge, HTML labels."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    if "def html_fifty_surcharge_badge" in s:
        print("already patched")
        return

    helper = """

def html_fifty_surcharge_badge(fr: dict, cfg: OatsideConfig) -> str:
    \"\"\"Badge: label + baht. midnight_full -> +100%%; blank_run = ตีเปล่า; origin24h/dest = ค่าเสียเวลา.\"\"\"
    amt = int(fr.get("surcharge_baht", 0) or 0)
    rate = int(fr.get("trip_rate_baht", 0) or 0)
    kind = str(fr.get("fifty_kind") or "")
    pct = float(cfg.one_trip_surcharge_pct)
    if kind == "midnight_full" or (not kind and rate > 0 and amt >= rate):
        label = "+100%"
        cls = "fulltrip"
    elif kind == "midnight_pct":
        label = f"+{pct:.0f}%"
        cls = "dwell"
    elif kind == "blank_run":
        label = f"ตีเปล่า +{pct:.0f}%"
        cls = "blankrun"
    elif kind in ("origin24h", "downtime_dest"):
        label = f"ค่าเสียเวลา +{pct:.0f}%"
        cls = "dwell"
    else:
        label = f"+{pct:.0f}%"
        cls = "abn"
    return f"<span class='badge {cls}'>{label} ฿{amt:,}</span>"


"""
    anchor = "def esc(x) -> str:\n    return html_module.escape(str(x), quote=True)\n\n\n"
    if anchor not in s:
        raise SystemExit("esc anchor missing")
    s = s.replace(anchor, anchor + helper, 1)

    old_css = (
        '        ".note{color:#4b5b74;font-size:13px}.wait-hi{background:#fff3cd;font-weight:600}'
        '.wait-hi-dest{background:#ffe0b2;font-weight:600}"\n'
        '        "tr.um td{color:#5a3b00}"'
    )
    new_css = (
        '        ".note{color:#4b5b74;font-size:13px}.wait-hi{background:#fff3cd;font-weight:600}'
        '.wait-hi-dest{background:#ffe0b2;font-weight:600}"\n'
        '        ".fulltrip{background:#e3f2fd;color:#0d47a1}.blankrun{background:#ede7f6;color:#4a148c}'
        '.dwell{background:#fff3e0;color:#bf360c}"\n'
        '        "tr.um td{color:#5a3b00}"'
    )
    if old_css not in s:
        raise SystemExit("css block missing")
    s = s.replace(old_css, new_css, 1)

    s2 = (
        '"surcharge_baht": sur,\n'
        "                }\n"
        "            )\n"
        "            total += sur\n"
        "    return rows, total\n\n\n"
        "def one_trip_fifty_pct_details"
    )
    if s2 not in s:
        raise SystemExit("origin24h block missing")
    s = s.replace(
        s2,
        '"surcharge_baht": sur,\n'
        '                    "fifty_kind": "origin24h",\n'
        "                }\n"
        "            )\n"
        "            total += sur\n"
        "    return rows, total\n\n\n"
        "def one_trip_fifty_pct_details",
        1,
    )

    s3 = (
        '"surcharge_baht": sur,\n'
        "            }\n"
        "        )\n"
        "        total += sur\n"
        "    return rows, total\n\n\n"
        "def plate_dest_day_rows"
    )
    if s3 not in s:
        raise SystemExit("details block missing")
    s = s.replace(
        s3,
        '"surcharge_baht": sur,\n'
        '                "fifty_kind": "downtime_dest",\n'
        "            }\n"
        "        )\n"
        "        total += sur\n"
        "    return rows, total\n\n\n"
        "def plate_dest_day_rows",
        1,
    )

    s4 = (
        '"surcharge_baht": sur,\n'
        "        })\n"
        "        total += sur\n"
        "    return rows, total\n\n\n\n\n"
        "def supplement_long_dest_wait_midnight_fifty"
    )
    if s4 not in s:
        raise SystemExit("origin_day block missing")
    s = s.replace(
        s4,
        '"surcharge_baht": sur,\n'
        '            "fifty_kind": "blank_run",\n'
        "        })\n"
        "        total += sur\n"
        "    return rows, total\n\n\n\n\n"
        "def supplement_long_dest_wait_midnight_fifty",
        1,
    )

    s5 = (
        '"surcharge_baht": sur,\n'
        "            }\n"
        "        )\n"
        "        charged[key] = sur\n"
        "        total += sur\n"
        "    return extra, total\n\n\n"
        "def origin_day_audit_rows"
    )
    if s5 not in s:
        raise SystemExit("supplement block missing")
    s = s.replace(
        s5,
        '"surcharge_baht": sur,\n'
        '                "fifty_kind": ("midnight_full" if full_trip else "midnight_pct"),\n'
        "            }\n"
        "        )\n"
        "        charged[key] = sur\n"
        "        total += sur\n"
        "    return extra, total\n\n\n"
        "def origin_day_audit_rows",
        1,
    )

    old_pd = """        fr = fifty_key.get((plate, d))
        sur = int(fr["surcharge_baht"]) if fr else 0
        out.append(
            {
                "dest_date": d,
                "plate": plate,
                "site": site_for_plate(plate),
                "matched_trips": n,
                "trip_rate_baht": rate,
                "base_line_baht": base_line,
                "fifty_pct_baht": sur,
                "customer_day_baht": base_line + sur,
            }
        )"""
    if old_pd not in s:
        raise SystemExit("plate_dest_day block missing")
    new_pd = """        fr = fifty_key.get((plate, d))
        sur = int(fr["surcharge_baht"]) if fr else 0
        badge = html_fifty_surcharge_badge(fr, cfg) if fr and sur > 0 else ""
        out.append(
            {
                "dest_date": d,
                "plate": plate,
                "site": site_for_plate(plate),
                "matched_trips": n,
                "trip_rate_baht": rate,
                "base_line_baht": base_line,
                "fifty_pct_baht": sur,
                "fifty_badge_html": badge,
                "customer_day_baht": base_line + sur,
            }
        )"""
    s = s.replace(old_pd, new_pd, 1)

    needle = (
        "<td class='{'money' if r['fifty_pct_baht'] else ''}'>{r['fifty_pct_baht']:,}</td>"
        "<td class='money'>{r['customer_day_baht']:,}</td></tr>"
    )
    repl = (
        "<td>{(r['fifty_badge_html'] if r.get('fifty_badge_html') else "
        "f\"<span class='money'>{r['fifty_pct_baht']:,}</span>\")}</td>"
        "<td class='money'>{r['customer_day_baht']:,}</td></tr>"
    )
    if needle not in s:
        raise SystemExit("pday needle missing")
    s = s.replace(needle, repl, 1)

    b1 = (
        "badge = f\" <span class='badge abn'>+{cfg.one_trip_surcharge_pct:.0f}% "
        "฿{fr['surcharge_baht']:,}</span>\""
    )
    b1_alt = (
        "badge = f\" <span class='badge abn'>+{cfg.one_trip_surcharge_pct:.0f}% "
        "?{fr['surcharge_baht']:,}</span>\""
    )
    rep_b = 'badge = " " + html_fifty_surcharge_badge(fr, cfg)'
    if b1 in s:
        s = s.replace(b1, rep_b, 1)
    elif b1_alt in s:
        s = s.replace(b1_alt, rep_b, 1)
    else:
        raise SystemExit("plate badge line not found")

    b2 = (
        "badge = f\" <span class='badge abn'>+{cfg.one_trip_surcharge_pct:.0f}% "
        "{fr['surcharge_baht']:,}</span>\""
    )
    if b2 in s:
        s = s.replace(b2, rep_b, 1)

    old_lt = """    lt_rows_html = "".join(
        f"<tr><td>{r['dest_date']}</td><td><a href='plates/{esc(r['plate'])}.html'>{esc(r['plate'])}</a></td>"
        f"<td><span class='badge {'bigc' if r['site']=='BigC' else 'lcb'}'>{r['site']}</span></td>"
        f"<td>{r['trips_that_day']}</td><td>{'Y' if r['auto_1trip'] else 'N'}</td>"
        f"<td>{esc(r.get('override_action',''))}</td><td>{esc(r.get('override_note',''))}</td>"
        f"<td>{esc(r.get('window_anchor',''))}</td><td>{esc(r.get('window_end',''))}</td>"
        f"<td>{r['trip_rate_baht']:,}</td><td class='money'>{r['surcharge_baht']:,}</td></tr>"
        for r in fifty_rows
    )"""
    if old_lt not in s:
        raise SystemExit("lt_rows block missing")
    new_lt = """    lt_rows_html = "".join(
        f"<tr><td>{r['dest_date']}</td><td><a href='plates/{esc(r['plate'])}.html'>{esc(r['plate'])}</a></td>"
        f"<td><span class='badge {'bigc' if r['site']=='BigC' else 'lcb'}'>{r['site']}</span></td>"
        f"<td class='note'>{esc(str(r.get('fifty_kind','')))}</td>"
        f"<td>{r['trips_that_day']}</td><td>{'Y' if r['auto_1trip'] else 'N'}</td>"
        f"<td>{esc(r.get('override_action',''))}</td><td>{esc(r.get('override_note',''))}</td>"
        f"<td>{esc(r.get('window_anchor',''))}</td><td>{esc(r.get('window_end',''))}</td>"
        f"<td>{r['trip_rate_baht']:,}</td><td class='money'>{r['surcharge_baht']:,}</td>"
        f"<td>{html_fifty_surcharge_badge(r, cfg)}</td></tr>"
        for r in fifty_rows
    )"""
    s = s.replace(old_lt, new_lt, 1)

    old_x = """    lt.append([
        "Dest_In_date", "Plate", "Site", "Trips_that_day",
        "Auto_1trip_rule_Y/N", "Override_action", "Override_note",
        "Window_Origin_In", "Window_End",
        "Trip_rate_baht", f"Surcharge_baht_{cfg.one_trip_surcharge_pct:.0f}pct",
    ])
    for r in fifty_rows:
        lt.append([
            r["dest_date"], r["plate"], r["site"], r["trips_that_day"],
            "Y" if r["auto_1trip"] else "N",
            r.get("override_action", ""), r.get("override_note", ""),
            r.get("window_anchor", ""),
            r.get("window_end", ""),
            r["trip_rate_baht"], r["surcharge_baht"],
        ])"""
    if old_x not in s:
        raise SystemExit("excel lt block missing")
    new_x = """    lt.append([
        "Dest_In_date", "Plate", "Site", "Fifty_kind",
        "Trips_that_day",
        "Auto_1trip_rule_Y/N", "Override_action", "Override_note",
        "Window_Origin_In", "Window_End",
        "Trip_rate_baht", f"Surcharge_baht_{cfg.one_trip_surcharge_pct:.0f}pct",
    ])
    for r in fifty_rows:
        lt.append([
            r["dest_date"], r["plate"], r["site"], str(r.get("fifty_kind", "")),
            r["trips_that_day"],
            "Y" if r["auto_1trip"] else "N",
            r.get("override_action", ""), r.get("override_note", ""),
            r.get("window_anchor", ""),
            r.get("window_end", ""),
            r["trip_rate_baht"], r["surcharge_baht"],
        ])"""
    s = s.replace(old_x, new_x, 1)

    s = s.replace(
        "<th>+{cfg.one_trip_surcharge_pct:.0f}%(฿)</th><th>รวมวัน(฿)</th></tr></thead><tbody>",
        "<th>ส่วนเพิ่ม (฿)</th><th>รวมวัน(฿)</th></tr></thead><tbody>",
        1,
    )
    s = s.replace(
        "<div class='card'><div class='label'>+{cfg.one_trip_surcharge_pct:.0f}% วัน 1 เที่ยว (C)</div>",
        "<div class='card'><div class='label'>ชาร์จเสริม ตีเปล่า/เสียเวลา/ข้ามคืน (C)</div>",
        1,
    )
    s = s.replace(
        'day_thead = "<tr><th>วันงาน</th><th>เที่ยว</th><th>+50% billing</th><th>เหตุผล</th><th>Nw+50%</th></tr>"',
        'day_thead = "<tr><th>วันงาน</th><th>เที่ยว</th><th>ส่วนเพิ่ม</th><th>เหตุผล</th><th>Nw+50%</th></tr>"',
        1,
    )

    TARGET.write_text(s, encoding="utf-8")
    print("patched", TARGET)


if __name__ == "__main__":
    main()
