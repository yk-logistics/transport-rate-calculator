# -*- coding: utf-8 -*-
"""
Wave 3: default use_origin_24h_fifty=True; customer_no_work + recovery outbound 50%;
phantom zero-trip candidates; double-Origin UM hints; Customer_Summary line D; new Excel sheets.
Patches Oatside/build_oatside_reports.py in place.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Oatside" / "build_oatside_reports.py"
CONFIG_JSON = ROOT / "Oatside" / "oatside_config.json"

INSERT_BEFORE_EXCEL = '''
_DEFAULT_NO_WORK_RANGES: list[tuple[date, date, str]] = [
    (date(2026, 4, 23), date(2026, 4, 24), "customer no-work"),
    (date(2026, 4, 27), date(2026, 4, 28), "customer no-work"),
    (date(2026, 5, 1), date(2026, 5, 1), "customer no-work"),
]


def _recovery_dest_dates_from_no_work(ranges: list[tuple[date, date, str]]) -> frozenset[date]:
    """First calendar day after each no-work block ends (Dest_In date for first trip surcharge)."""
    return frozenset(b + timedelta(days=1) for _a, b, _n in ranges)


_DEFAULT_OUTBOUND_HALF_DATES: frozenset[date] = _recovery_dest_dates_from_no_work(_DEFAULT_NO_WORK_RANGES)


def _parse_no_work_entries(raw: object) -> list[tuple[date, date, str]]:
    out: list[tuple[date, date, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        a = _parse_dt(item.get("from") or item.get("start"))
        b = _parse_dt(item.get("to") or item.get("end"))
        if not a or not b:
            continue
        da, db = a.date(), b.date()
        if db < da:
            da, db = db, da
        note = str(item.get("note", "")).strip()
        out.append((da, db, note))
    return out


def _parse_date_set(raw: object) -> frozenset[date]:
    if not isinstance(raw, list) or not raw:
        return frozenset()
    s: set[date] = set()
    for x in raw:
        if isinstance(x, str) and len(x) >= 10:
            try:
                s.add(datetime.strptime(x[:10], "%Y-%m-%d").date())
            except ValueError:
                continue
    return frozenset(s)


def first_matched_trip_by_plate_dest(trips: list[Trip]) -> dict[tuple[str, date], Trip]:
    by: dict[tuple[str, date], list[Trip]] = defaultdict(list)
    for t in trips:
        by[(t.plate, t.dest_date)].append(t)
    return {k: min(lst, key=lambda x: x.d_in) for k, lst in by.items()}


def no_work_outbound_rows(trips: list[Trip], cfg: OatsideConfig) -> tuple[list[dict], int]:
    """+50pct of trip rate on first matched trip of (plate, Dest_In day) when dest_date is a recovery day."""
    firsts = first_matched_trip_by_plate_dest(trips)
    rows: list[dict] = []
    total = 0
    pct = float(cfg.one_trip_surcharge_pct)
    for (plate, d), t0 in sorted(firsts.items(), key=lambda x: (x[0][1], x[0][0])):
        if d not in cfg.outbound_half_dest_dates:
            continue
        rate = trip_rate_baht(d, cfg)
        sur = int(round(rate * pct / 100.0))
        rows.append(
            {
                "dest_date": d,
                "plate": plate,
                "site": site_for_plate(plate),
                "d_row": t0.d_row,
                "trip_rate_baht": rate,
                "surcharge_baht": sur,
                "note": "No-work recovery: first trip that Dest_In day (50pct of trip rate, outbound rule)",
            }
        )
        total += sur
    return rows, total


def phantom_zero_trip_candidates(origin_legs: list[Trip] | list, trips: list[Trip], cfg: OatsideConfig) -> list[dict]:
    """Days with Origin legs but no matched trip on that trip_date (suggest 1 full trip charge)."""
    matched_origin_days = {(t.plate, t.trip_date) for t in trips}
    hours_by: dict[tuple[str, date], float] = defaultdict(float)
    for leg in origin_legs:
        d = leg.t_in.date()
        hours_by[(leg.plate, d)] += hours(leg.t_in, leg.t_out)
    rows: list[dict] = []
    for (plate, d), h in sorted(hours_by.items(), key=lambda x: (x[0][1], x[0][0])):
        if (plate, d) in matched_origin_days:
            continue
        if h < 1.0:
            continue
        rate = trip_rate_baht(d, cfg)
        rows.append(
            {
                "plate": plate,
                "calendar_date": d,
                "origin_hours_on_day": round(h, 2),
                "suggest_full_trip_baht": rate,
                "note": "No matched trip on this trip_date; OAT rule: charge 1 full trip (review before adding to grand total)",
            }
        )
    return rows


def double_origin_um_hints(unmatched: list[tuple[str, Leg, str]]) -> list[dict]:
    """Flag days with 2+ unmatched Origin segments (possible double hub in/out)."""
    by: dict[tuple[str, date], int] = defaultdict(int)
    for src, leg, plate in unmatched:
        if src != "Origin":
            continue
        by[(plate, leg.t_in.date())] += 1
    return [
        {
            "plate": plate,
            "calendar_date": d,
            "um_origin_segments": n,
            "note": "2+ unmatched Origin rows same calendar day — review",
        }
        for (plate, d), n in sorted(by.items(), key=lambda x: (x[0][1], x[0][0]))
        if n >= 2
    ]


def trip_no_work_outbound_baht(t: Trip, firsts: dict[tuple[str, date], Trip], cfg: OatsideConfig) -> int:
    if t.dest_date not in cfg.outbound_half_dest_dates:
        return 0
    ft = firsts.get((t.plate, t.dest_date))
    if ft is None or id(ft) != id(t):
        return 0
    rate = trip_rate_baht(t.dest_date, cfg)
    return int(round(rate * float(cfg.one_trip_surcharge_pct) / 100.0))


'''


def patch_file() -> None:
    s = TARGET.read_text(encoding="utf-8")
    if "_DEFAULT_NO_WORK_RANGES" in s:
        print("Already patched wave3 markers present; skip")
        return

    marker = "\n\n# ---------------------------------------------------------------------------\n# Excel export\n# ---------------------------------------------------------------------------\n\n"
    if marker not in s:
        raise SystemExit("Excel export marker not found")
    s = s.replace(marker, "\n\n" + INSERT_BEFORE_EXCEL + marker, 1)

    # OatsideConfig: add two fields before CustomerIdleWindow
    s = s.replace(
        "    use_origin_24h_fifty: bool\n"
        "    customer_idle_windows: list[CustomerIdleWindow]\n\n"
        "@dataclass\n"
        "class CustomerIdleWindow:",
        "    use_origin_24h_fifty: bool\n"
        "    customer_idle_windows: list[CustomerIdleWindow]\n"
        "    customer_no_work_ranges: list[tuple[date, date, str]]\n"
        "    outbound_half_dest_dates: frozenset[date]\n\n"
        "@dataclass\n"
        "class CustomerIdleWindow:",
        1,
    )

    # _DEFAULT_CONFIG: True + new fields
    s = s.replace("    use_origin_24h_fifty=False,\n", "    use_origin_24h_fifty=True,\n", 1)
    s = s.replace(
        '            note="Factory parked CONTEXT_LOG 90-91",\n'
        "        ),\n"
        "    ],\n"
        ")\n",
        '            note="Factory parked CONTEXT_LOG 90-91",\n'
        "        ),\n"
        "    ],\n"
        "    customer_no_work_ranges=list(_DEFAULT_NO_WORK_RANGES),\n"
        "    outbound_half_dest_dates=_DEFAULT_OUTBOUND_HALF_DATES,\n"
        ")\n",
        1,
    )

    # JSON default: use_origin true + customer_no_work
    old_json_snip = '"use_origin_24h_fifty": False,'
    new_json_snip = '"use_origin_24h_fifty": True,'
    if old_json_snip not in s:
        if '"use_origin_24h_fifty": True,' in s:
            pass
        else:
            raise SystemExit("JSON use_origin false not found")
    else:
        s = s.replace(old_json_snip, new_json_snip, 1)

    # Insert customer_no_work in _DEFAULT_CONFIG_JSON after customer_idle_windows array - find unique closing
    needle = '    "charge_min_trip_shortfall": False,'
    if needle not in s:
        raise SystemExit("charge_min_trip_shortfall line not found for JSON insert")
    json_no_work = '''    "customer_no_work": [
        {"from": "2026-04-23", "to": "2026-04-24", "note": "customer no-work"},
        {"from": "2026-04-27", "to": "2026-04-28", "note": "customer no-work"},
        {"from": "2026-05-01", "to": "2026-05-01", "note": "customer no-work"}
    ],
    "_note_outbound_half": "If outbound_half_dest_dates omitted, recovery = day after each no-work block end; surcharge 50pct on first matched trip that Dest_In day",
'''
    s = s.replace(needle, json_no_work + needle, 1)

    # load_oatside_config return block - extend before return OatsideConfig(
    ret_idle = (
        "            idle_wins.append(CustomerIdleWindow(plate=pl, start=st, end=en, note=note))\n\n"
        "    return OatsideConfig(\n"
    )
    if ret_idle not in s:
        raise SystemExit("load return idle block not found")
    repl_idle = (
        "            idle_wins.append(CustomerIdleWindow(plate=pl, start=st, end=en, note=note))\n\n"
        '    if "customer_no_work" not in raw:\n'
        "        nwr = list(_DEFAULT_NO_WORK_RANGES)\n"
        "    else:\n"
        "        nwr = _parse_no_work_entries(raw.get(\"customer_no_work\"))\n"
        "        if not nwr:\n"
        "            nwr = list(_DEFAULT_NO_WORK_RANGES)\n"
        "    ohd = _parse_date_set(raw.get(\"outbound_half_dest_dates\"))\n"
        "    if not ohd:\n"
        "        ohd = frozenset(_recovery_dest_dates_from_no_work(nwr))\n\n"
        "    return OatsideConfig(\n"
    )
    s = s.replace(ret_idle, repl_idle, 1)

    s = s.replace(
        "        use_origin_24h_fifty=use_o24,\n"
        "        customer_idle_windows=idle_wins,\n"
        "    )\n",
        "        use_origin_24h_fifty=use_o24,\n"
        "        customer_idle_windows=idle_wins,\n"
        "        customer_no_work_ranges=nwr,\n"
        "        outbound_half_dest_dates=ohd,\n"
        "    )\n",
        1,
    )

    # Fix phantom_zero_trip_candidates type hint list[Trip] wrong for legs - use list[Leg]
    s = s.replace(
        "def phantom_zero_trip_candidates(origin_legs: list[Trip] | list, trips: list[Trip], cfg: OatsideConfig)",
        "def phantom_zero_trip_candidates(origin_legs: list[Leg], trips: list[Trip], cfg: OatsideConfig)",
        1,
    )

    # write_excel signature
    old_sig = (
        "def write_excel(\n"
        "    path: Path,\n"
        "    origin_name: str,\n"
        "    dest_name: str,\n"
        "    trips: list[Trip],\n"
        "    unmatched: list[tuple[str, Leg, str]],\n"
        "    daily_time: list[tuple],\n"
        "    daily_rows: list[tuple[date, dict]],\n"
        "    fifty_rows: list[dict],\n"
        "    fifty_total_baht: int,\n"
        "    min_trip_extra_baht: int,\n"
        "    audit_rows: list[dict],\n"
        "    cfg: OatsideConfig,\n"
        ") -> None:\n"
        "    base_baht = base_trips_revenue_baht(trips, cfg)\n"
        "    customer_grand_baht = int(base_baht) + int(min_trip_extra_baht) + int(fifty_total_baht)\n"
    )
    new_sig = (
        "def write_excel(\n"
        "    path: Path,\n"
        "    origin_name: str,\n"
        "    dest_name: str,\n"
        "    trips: list[Trip],\n"
        "    unmatched: list[tuple[str, Leg, str]],\n"
        "    daily_time: list[tuple],\n"
        "    daily_rows: list[tuple[date, dict]],\n"
        "    fifty_rows: list[dict],\n"
        "    fifty_total_baht: int,\n"
        "    min_trip_extra_baht: int,\n"
        "    audit_rows: list[dict],\n"
        "    cfg: OatsideConfig,\n"
        "    customer_grand_baht: int,\n"
        "    no_work_rows: list[dict],\n"
        "    no_work_total_baht: int,\n"
        "    phantom_rows: list[dict],\n"
        "    hint_rows: list[dict],\n"
        ") -> None:\n"
        "    base_baht = base_trips_revenue_baht(trips, cfg)\n"
    )
    if old_sig not in s:
        raise SystemExit("write_excel sig block not found")
    s = s.replace(old_sig, new_sig, 1)

    # Customer_Summary C + TOTAL
    old_cs = (
        '    cs.append(["C", f",S,,1O,^ {cfg.one_trip_surcharge_pct:.0f}%,,,T,-,1^,,\'1^,؅1,,"1% 11?,-,1^,, (,,,, override)", fifty_total_baht])\n'
        '    tot_lbl = ",,,1?,,T,-,,1,?,,1%, (A+B+C)" if cfg.charge_min_trip_shortfall else ",,,1?,,T,-,,1,?,,1%, (A+C)"\n'
        '    cs.append(["TOTAL", tot_lbl, customer_grand_baht])\n'
    )
    # File may have mojibake - match English parts only via smaller unique strings
    s = s.replace(
        '    cs.append(["TOTAL", tot_lbl, customer_grand_baht])\n',
        '    cs.append(\n'
        '        [\n'
        '            "D",\n'
        '            "No-work recovery outbound 50pct (first matched trip that Dest_In day on recovery dates)",\n'
        '            no_work_total_baht,\n'
        '        ]\n'
        "    )\n"
        '    tot_lbl = (\n'
        '        "Grand (A+B+C+D)"\n'
        '        if cfg.charge_min_trip_shortfall\n'
        '        else "Grand (A+C+D)"\n'
        "    )\n"
        '    cs.append(["TOTAL", tot_lbl, customer_grand_baht])\n',
        1,
    )

    # Info sheet after fifty total
    s = s.replace(
        '    info.append(["Fifty_pct_surcharge_total_baht", fifty_total_baht])\n',
        '    info.append(["Fifty_pct_surcharge_total_baht", fifty_total_baht])\n'
        '    info.append(["No_work_outbound_50pct_total_baht", no_work_total_baht])\n'
        '    info.append(["Phantom_zero_trip_candidates", len(phantom_rows)])\n'
        '    info.append(["Double_origin_um_hints", len(hint_rows)])\n',
        1,
    )

    # wb.save(path) - insert sheets before
    old_save = "    wb.save(path)\n"
    new_sheets = (
        "    nw = wb.create_sheet(\"NoWork_Outbound_50pct\")\n"
        "    nw.append(\n"
        '        ["Dest_In_date", "Plate", "Site", "Dest_Row", "Trip_rate_baht", "Surcharge_baht_50pct", "Note"]\n'
        "    )\n"
        "    for r in no_work_rows:\n"
        "        nw.append(\n"
        "            [\n"
        '                r["dest_date"],\n'
        '                r["plate"],\n'
        '                r["site"],\n'
        '                r["d_row"],\n'
        '                r["trip_rate_baht"],\n'
        '                r["surcharge_baht"],\n'
        '                r.get("note", ""),\n'
        "            ]\n"
        "        )\n"
        "    ph = wb.create_sheet(\"Phantom_Trip_Candidates\")\n"
        "    ph.append(\n"
        '        ["Plate", "Calendar_date", "Origin_hours", "Suggest_full_trip_baht", "Note"]\n'
        "    )\n"
        "    for r in phantom_rows:\n"
        "        ph.append(\n"
        "            [\n"
        '                r["plate"],\n'
        '                r["calendar_date"],\n'
        '                r["origin_hours_on_day"],\n'
        '                r["suggest_full_trip_baht"],\n'
        '                r.get("note", ""),\n'
        "            ]\n"
        "        )\n"
        "    hi = wb.create_sheet(\"Hints_DoubleOrigin\")\n"
        '    hi.append(["Plate", "Calendar_date", "UM_Origin_segments", "Note"])\n'
        "    for r in hint_rows:\n"
        "        hi.append(\n"
        "            [r[\"plate\"], r[\"calendar_date\"], r[\"um_origin_segments\"], r.get(\"note\", \"\")]\n"
        "        )\n\n"
        "    wb.save(path)\n"
    )
    if old_save not in s:
        raise SystemExit("wb.save not found")
    s = s.replace(old_save, new_sheets, 1)

    # Trip_Detail: add Nw_outbound50_baht column
    s = s.replace(
        '"Travel_Flag", "Billable_Trip",\n'
        "    ])\n"
        "    for t in sorted(trips, key=lambda x: (x.dest_date, x.plate, x.d_in)):\n",
        '"Travel_Flag", "Billable_Trip", "Nw_outbound50_baht",\n'
        "    ])\n"
        "    firsts = first_matched_trip_by_plate_dest(trips)\n"
        "    for t in sorted(trips, key=lambda x: (x.dest_date, x.plate, x.d_in)):\n",
        1,
    )
    s = s.replace(
        "            round(t.total_cycle_h, 2), round(cyc_c, 2),\n"
        "            t.travel_flag, 1,\n"
        "        ])\n",
        "            round(t.total_cycle_h, 2), round(cyc_c, 2),\n"
        "            t.travel_flag, 1, trip_no_work_outbound_baht(t, firsts, cfg),\n"
        "        ])\n",
        1,
    )

    # main(): parse origin legs, compute rows, grand, write_excel args
    old_main_block = (
        "    grand_extra = min_trip_money + int(fifty_total)\n"
        "    customer_grand_baht = int(base_baht) + int(grand_extra)\n\n"
        "    xlsx_out = folder / \"Oatside_PG_Trip_Summary_By_Site.xlsx\"\n"
        "    write_excel(\n"
        "        xlsx_out,\n"
        "        origin_path.name,\n"
        "        dest_path.name,\n"
        "        trips,\n"
        "        unmatched,\n"
        "        daily_time,\n"
        "        daily_rows,\n"
        "        fifty_rows,\n"
        "        int(fifty_total),\n"
        "        min_trip_money,\n"
        "        audit_rows,\n"
        "        cfg,\n"
        "    )\n"
    )
    new_main_block = (
        "    grand_extra = min_trip_money + int(fifty_total)\n"
        "    o_legs_all = parse_legs(origin_path)\n"
        "    nw_rows, nw_total = no_work_outbound_rows(trips, cfg)\n"
        "    phantom_rows = phantom_zero_trip_candidates(o_legs_all, trips, cfg)\n"
        "    hint_rows = double_origin_um_hints(unmatched)\n"
        "    customer_grand_baht = int(base_baht) + int(grand_extra) + int(nw_total)\n\n"
        "    xlsx_out = folder / \"Oatside_PG_Trip_Summary_By_Site.xlsx\"\n"
        "    write_excel(\n"
        "        xlsx_out,\n"
        "        origin_path.name,\n"
        "        dest_path.name,\n"
        "        trips,\n"
        "        unmatched,\n"
        "        daily_time,\n"
        "        daily_rows,\n"
        "        fifty_rows,\n"
        "        int(fifty_total),\n"
        "        min_trip_money,\n"
        "        audit_rows,\n"
        "        cfg,\n"
        "        int(customer_grand_baht),\n"
        "        nw_rows,\n"
        "        int(nw_total),\n"
        "        phantom_rows,\n"
        "        hint_rows,\n"
        "    )\n"
    )
    if old_main_block not in s:
        raise SystemExit("main write_excel block not found")
    s = s.replace(old_main_block, new_main_block, 1)

    # write_html customer_grand - passed already - update call write_html(... customer_grand_baht) - same variable name in main
    old_wh = (
        "        int(base_baht),\n"
        "        int(customer_grand_baht),\n"
        "        pday_rows,\n"
    )
    # customer_grand now includes nw_total before write_html - order ok

    TARGET.write_text(s, encoding="utf-8")
    print("wave3 patched", TARGET)


def merge_config_json() -> None:
    if not CONFIG_JSON.is_file():
        print("no oatside_config.json to merge")
        return
    import json

    raw = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    changed = False
    if "use_origin_24h_fifty" not in raw:
        raw["use_origin_24h_fifty"] = True
        changed = True
    if "customer_no_work" not in raw:
        raw["customer_no_work"] = [
            {"from": "2026-04-23", "to": "2026-04-24", "note": "customer no-work"},
            {"from": "2026-04-27", "to": "2026-04-28", "note": "customer no-work"},
            {"from": "2026-05-01", "to": "2026-05-01", "note": "customer no-work"},
        ]
        changed = True
    if changed:
        CONFIG_JSON.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print("merged", CONFIG_JSON)


if __name__ == "__main__":
    patch_file()
    merge_config_json()
