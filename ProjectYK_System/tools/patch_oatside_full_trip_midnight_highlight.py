# -*- coding: utf-8 -*-
"""Full-trip surcharge for midnight dest dwell; HTML highlight long origin/dest waits."""
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


OLD_SUPP = '''def supplement_long_dest_wait_midnight_fifty(
    trips: list[Trip],
    fifty_rows: list[dict],
    overrides: dict[tuple[str, date], dict[str, Any]],
    cfg: OatsideConfig,
) -> tuple[list[dict], int]:
    """If Dest_In->Dest_Out crosses calendar midnight and dwell >= min hours, add +50pct
    keyed by (plate, dest_date) when no surcharge row exists yet for that dest_date.

    Covers origin_day billing where Apr 21 has no Origin_In but long customer wait."""
    if not getattr(cfg, "long_dest_wait_midnight_fifty", True):
        return [], 0
    min_h = float(getattr(cfg, "long_dest_wait_midnight_min_h", 12.0))
    charged: dict[tuple[str, date], int] = {}
    for r in fifty_rows:
        p = r.get("plate")
        d = r.get("dest_date")
        if p and isinstance(d, date):
            charged[(str(p), d)] = int(r.get("surcharge_baht", 0) or 0)
    extra: list[dict] = []
    total = 0
    for t in trips:
        if t.d_in.date() >= t.d_out.date():
            continue
        if t.dest_wait_h < min_h:
            continue
        key = (t.plate, t.dest_date)
        if charged.get(key, 0) > 0:
            continue
        ov = overrides.get(key, {})
        if ov.get("action") == "exclude_50":
            continue
        rate = trip_rate_baht(t.dest_date, cfg)
        sur = int(round(rate * float(cfg.one_trip_surcharge_pct) / 100.0))
        note = (
            f"???????????????? Dest_InDest_Out ({t.dest_wait_h:.2f}h); "
            f"+{cfg.one_trip_surcharge_pct:.0f}% ?????? Dest_In"
        )
        extra.append(
            {
                "origin_day": t.o_in.date(),
                "dest_date": t.dest_date,
                "plate": t.plate,
                "site": site_for_plate(t.plate),
                "trips_that_day": 1,
                "auto_1trip": False,
                "override_action": ov.get("action", "") or "",
                "override_note": (ov.get("note", "") or "") + ("; " if ov.get("note") else "") + note,
                "window_anchor": str(t.d_in),
                "window_end": str(t.d_out),
                "trip_rate_baht": rate,
                "surcharge_baht": sur,
            }
        )
        charged[key] = sur
        total += sur
    return extra, total
'''

NEW_SUPP = '''def supplement_long_dest_wait_midnight_fifty(
    trips: list[Trip],
    fifty_rows: list[dict],
    overrides: dict[tuple[str, date], dict[str, Any]],
    cfg: OatsideConfig,
) -> tuple[list[dict], int]:
    """Dest_In->Dest_Out crosses midnight, dwell >= min_h: add surcharge keyed by (plate, dest_date)
    when no fifty row yet. Default: full 1-trip rate (not 50pct) — idle calendar day at customer."""
    if not getattr(cfg, "long_dest_wait_midnight_fifty", True):
        return [], 0
    min_h = float(getattr(cfg, "long_dest_wait_midnight_min_h", 12.0))
    full_trip = bool(getattr(cfg, "long_dest_wait_midnight_full_trip", True))
    charged: dict[tuple[str, date], int] = {}
    for r in fifty_rows:
        p = r.get("plate")
        d = r.get("dest_date")
        if p and isinstance(d, date):
            charged[(str(p), d)] = int(r.get("surcharge_baht", 0) or 0)
    extra: list[dict] = []
    total = 0
    for t in trips:
        if t.d_in.date() >= t.d_out.date():
            continue
        if t.dest_wait_h < min_h:
            continue
        key = (t.plate, t.dest_date)
        if charged.get(key, 0) > 0:
            continue
        ov = overrides.get(key, {})
        if ov.get("action") == "exclude_50":
            continue
        rate = trip_rate_baht(t.dest_date, cfg)
        if full_trip:
            sur = int(rate)
            pct_note = "เต็ม 1 เที่ยว (เรทวัน Dest_In)"
        else:
            sur = int(round(rate * float(cfg.one_trip_surcharge_pct) / 100.0))
            pct_note = f"+{cfg.one_trip_surcharge_pct:.0f}% เรทวัน Dest_In"
        note = (
            f"รอปลายทางข้ามคืน Dest_In→Dest_Out ({t.dest_wait_h:.2f}h); {pct_note}"
        )
        extra.append(
            {
                "origin_day": t.o_in.date(),
                "dest_date": t.dest_date,
                "plate": t.plate,
                "site": site_for_plate(t.plate),
                "trips_that_day": 1,
                "auto_1trip": False,
                "override_action": ov.get("action", "") or "",
                "override_note": (ov.get("note", "") or "") + ("; " if ov.get("note") else "") + note,
                "window_anchor": str(t.d_in),
                "window_end": str(t.d_out),
                "trip_rate_baht": rate,
                "surcharge_baht": sur,
            }
        )
        charged[key] = sur
        total += sur
    return extra, total
'''


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    if "long_dest_wait_midnight_full_trip" in s and ".wait-hi" in s:
        print("already patched v2")
        return

    if OLD_SUPP not in s:
        # fuzzy: replace from def supplement to return extra, total before origin_day_audit
        i0 = s.find("def supplement_long_dest_wait_midnight_fifty(")
        i1 = s.find("def origin_day_audit_rows(")
        if i0 < 0 or i1 < 0:
            raise SystemExit("supplement block not found")
        s = s[:i0] + NEW_SUPP + "\n\n" + s[i1:]
    else:
        s = s.replace(OLD_SUPP, NEW_SUPP, 1)

    s = s.replace(
        "    long_dest_wait_midnight_min_h: float\n\n@dataclass\nclass CustomerIdleWindow:",
        "    long_dest_wait_midnight_min_h: float\n"
        "    long_dest_wait_midnight_full_trip: bool\n"
        "    highlight_origin_wait_h: float\n"
        "    highlight_dest_wait_h: float\n\n"
        "@dataclass\nclass CustomerIdleWindow:",
        1,
    )

    s = s.replace(
        "    long_dest_wait_midnight_fifty=True,\n"
        "    long_dest_wait_midnight_min_h=12.0,\n)\n\n_DEFAULT_CONFIG_JSON",
        "    long_dest_wait_midnight_fifty=True,\n"
        "    long_dest_wait_midnight_min_h=12.0,\n"
        "    long_dest_wait_midnight_full_trip=True,\n"
        "    highlight_origin_wait_h=8.0,\n"
        "    highlight_dest_wait_h=8.0,\n)\n\n_DEFAULT_CONFIG_JSON",
        1,
    )

    s = s.replace(
        '    "_note_long_dest_wait_midnight": "If Dest_In and Dest_Out cross midnight and dwell >= min_h, add +50pct by dest_date when no fifty row yet (origin_day mode gap)",\n',
        '    "long_dest_wait_midnight_full_trip": True,\n'
        '    "_note_long_dest_wait_midnight_full": "true = charge full 1-trip rate on dest_date when midnight dwell rule fires; false = charge one_trip_surcharge_pct of rate",\n'
        '    "highlight_origin_wait_h": 8,\n'
        '    "highlight_dest_wait_h": 8,\n'
        '    "_note_long_dest_wait_midnight": "If Dest_In and Dest_Out cross midnight and dwell >= min_h, add surcharge by dest_date when no fifty row yet (origin_day mode gap)",\n',
        1,
    )

    s = s.replace(
        "        long_dest_wait_midnight_min_h=float(\n"
        '            raw.get("long_dest_wait_midnight_min_h", _DEFAULT_CONFIG.long_dest_wait_midnight_min_h)\n'
        "        ),\n"
        "    )\n\n\ndef trip_rate_baht",
        "        long_dest_wait_midnight_min_h=float(\n"
        '            raw.get("long_dest_wait_midnight_min_h", _DEFAULT_CONFIG.long_dest_wait_midnight_min_h)\n'
        "        ),\n"
        "        long_dest_wait_midnight_full_trip=bool(\n"
        '            raw.get("long_dest_wait_midnight_full_trip", _DEFAULT_CONFIG.long_dest_wait_midnight_full_trip)\n'
        "        ),\n"
        "        highlight_origin_wait_h=float(\n"
        '            raw.get("highlight_origin_wait_h", _DEFAULT_CONFIG.highlight_origin_wait_h)\n'
        "        ),\n"
        "        highlight_dest_wait_h=float(\n"
        '            raw.get("highlight_dest_wait_h", _DEFAULT_CONFIG.highlight_dest_wait_h)\n'
        "        ),\n"
        "    )\n\n\ndef trip_rate_baht",
        1,
    )

    # CSS: after .note{color:
    needle = ".note{color:#4b5b74;font-size:13px}"
    if needle in s and ".wait-hi" not in s:
        s = s.replace(
            needle,
            needle
            + ".wait-hi{background:#fff3cd;font-weight:600}"
            + ".wait-hi-dest{background:#ffe0b2;font-weight:600}",
            1,
        )

    # Insert th_o th_d and td_wait after sub += block - unique anchor
    anchor = (
        "    if not cfg.charge_min_trip_shortfall:\n"
        "        sub += \" | ???????????????????????????? (min trips) - ???????? % ????? 1 ?????????\"\n\n\n"
        "    def trip_row(t: Trip) -> str:"
    )
    replacement = (
        "    if not cfg.charge_min_trip_shortfall:\n"
        "        sub += \" | ???????????????????????????? (min trips) - ???????? % ????? 1 ?????????\"\n\n"
        "    _hi_o = float(getattr(cfg, \"highlight_origin_wait_h\", 8.0))\n"
        "    _hi_d = float(getattr(cfg, \"highlight_dest_wait_h\", 8.0))\n\n"
        "    def _td_wait_h(val: float, th: float, dest: bool) -> str:\n"
        "        cls = \" wait-hi-dest\" if dest else \" wait-hi\"\n"
        "        if val >= th:\n"
        "            return f\"<td class='{cls.strip()}' title='รอ {\"ปลายทาง\" if dest else \"ต้นทาง\"} ≥ {th:g} ชม. (ตรวจพิจารณา)'>{fmt_hm(val)}</td>\"\n"
        "        return f\"<td>{fmt_hm(val)}</td>\"\n\n"
        "    def trip_row(t: Trip) -> str:"
    )
    if anchor in s:
        s = s.replace(anchor, replacement, 1)
    else:
        # try English sub tail from file variant
        a2 = "    def trip_row(t: Trip) -> str:"
        idx = s.find(a2)
        if idx < 0:
            raise SystemExit("trip_row anchor not found")
        ins = (
            "    _hi_o = float(getattr(cfg, \"highlight_origin_wait_h\", 8.0))\n"
            "    _hi_d = float(getattr(cfg, \"highlight_dest_wait_h\", 8.0))\n\n"
            "    def _td_wait_h(val: float, th: float, dest: bool) -> str:\n"
            "        cls = \"wait-hi-dest\" if dest else \"wait-hi\"\n"
            "        if val >= th:\n"
            "            lab = \"ปลายทาง\" if dest else \"ต้นทาง\"\n"
            "            return f\"<td class='{cls}' title='รอ{lab} ≥ {th:g} ชม. (ตรวจพิจารณา)'>{fmt_hm(val)}</td>\"\n"
            "        return f\"<td>{fmt_hm(val)}</td>\"\n\n"
        )
        s = s[:idx] + ins + s[idx:]

    # Replace origin/dest wait td in trip_row
    s = s.replace(
        "f\"<td>{fmt_hm(t.origin_wait_h)}</td><td>{fmt_hm(t.travel_h)}</td><td>{fmt_hm(t.dest_wait_h)}</td>{nw_cell}</tr>\"\n        )\n\n    merged_all_rows",
        "f\"{_td_wait_h(t.origin_wait_h, _hi_o, False)}<td>{fmt_hm(t.travel_h)}</td>{_td_wait_h(t.dest_wait_h, _hi_d, True)}{nw_cell}</tr>\"\n        )\n\n    merged_all_rows",
        1,
    )
    s = s.replace(
        "f\"<td>{fmt_hm(t.origin_wait_h)}</td><td>{fmt_hm(t.travel_h)}</td><td>{fmt_hm(t.dest_wait_h)}</td>{nw_cell}</tr>\"\n        )\n\n    daily_act_rows_html",
        "f\"{_td_wait_h(t.origin_wait_h, _hi_o, False)}<td>{fmt_hm(t.travel_h)}</td>{_td_wait_h(t.dest_wait_h, _hi_d, True)}{nw_cell}</tr>\"\n        )\n\n    daily_act_rows_html",
        1,
    )

    # Legend in index.html body - find first panel after nav
    legend = (
        "<div class='panel'><p class='sub'><b>สีไฮไลต์:</b> เหลืองอ่อน = รอต้นทางนาน ≥ "
        "{_hi_o:g} ชม.; ส้มอ่อน = รอปลายทางนาน ≥ {_hi_d:g} ชม. (ตรวจก่อนตัดสินใจเก็บลูกค้า)</p></div>\n"
        "<div class='panel'><h3>"
    )
    if "{_hi_o:g}" in legend and "<div class='panel'><h3>" in s:
        s = s.replace("<div class='panel'><h3>", legend, 1)

    TARGET.write_text(s, encoding="utf-8")
    print("patched v2", TARGET)


if __name__ == "__main__":
    main()
