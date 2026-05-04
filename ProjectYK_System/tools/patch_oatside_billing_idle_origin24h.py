# -*- coding: utf-8 -*-
"""One-shot patch for Oatside/build_oatside_reports.py (customer idle clip + optional origin-24h 50%)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    orig = s

    # --- 1) Insert CustomerIdleWindow + extend OatsideConfig (after charge_min_trip_shortfall field) ---
    needle = (
        "    enable_origin_chain_merge: bool\n"
        "    charge_min_trip_shortfall: bool\n"
    )
    if needle not in s:
        raise SystemExit("needle1 not found (OatsideConfig fields)")
    s = s.replace(
        needle,
        needle
        + "\n"
        + "@dataclass\n"
        + "class CustomerIdleWindow:\n"
        + '    """Hours at customer site excluded from customer dwell / 24h gap (e.g. factory parking)."""\n'
        + "\n"
        + "    plate: str\n"
        + "    start: datetime\n"
        + "    end: datetime\n"
        + '    note: str = ""\n'
        + "\n"
        + "    def overlaps_dest_interval(self, d_in: datetime, d_out: datetime) -> bool:\n"
        + "        return d_in < self.end and d_out > self.start\n"
        + "\n"
        + "    def overlap_hours(self, d_in: datetime, d_out: datetime) -> float:\n"
        + "        a = max(d_in, self.start)\n"
        + "        b = min(d_out, self.end)\n"
        + "        if b <= a:\n"
        + "            return 0.0\n"
        + "        return (b - a).total_seconds() / 3600.0\n",
        1,
    )

    needle2 = (
        "@dataclass\n"
        "class OatsideConfig:\n"
        "    trip_rates: list[dict]\n"
        "    one_trip_surcharge_pct: float\n"
        "    min_trips_per_truck: int\n"
        "    max_travel_h: float\n"
        "    max_origin_chain_gap_h: float\n"
        "    enable_origin_chain_merge: bool\n"
        "    charge_min_trip_shortfall: bool\n"
    )
    if "class CustomerIdleWindow" not in s or needle2 + "\n" not in s:
        pass
    # OatsideConfig already has charge_min_trip - add new fields after CustomerIdleWindow class block
    # Re-find OatsideConfig block tail
    needle3 = (
        "class OatsideConfig:\n"
        "    trip_rates: list[dict]\n"
        "    one_trip_surcharge_pct: float\n"
        "    min_trips_per_truck: int\n"
        "    max_travel_h: float\n"
        "    max_origin_chain_gap_h: float\n"
        "    enable_origin_chain_merge: bool\n"
        "    charge_min_trip_shortfall: bool\n"
    )
    if needle3 not in s:
        raise SystemExit("OatsideConfig header not found")
    s = s.replace(
        needle3,
        needle3 + "    use_origin_24h_fifty: bool\n" + "    customer_idle_windows: list[CustomerIdleWindow]\n",
        1,
    )

    # --- 2) _DEFAULT_CONFIG ---
    old_dc = (
        "    enable_origin_chain_merge=False,\n"
        "    charge_min_trip_shortfall=False,\n"
        ")\n"
    )
    if old_dc not in s:
        raise SystemExit("_DEFAULT_CONFIG closing not found")
    s = s.replace(
        old_dc,
        "    enable_origin_chain_merge=False,\n"
        "    charge_min_trip_shortfall=False,\n"
        "    use_origin_24h_fifty=False,\n"
        "    customer_idle_windows=[],\n"
        ")\n",
        1,
    )

    # Insert JSON keys before charge_min_trip_shortfall in _DEFAULT_CONFIG_JSON
    jneedle = '"charge_min_trip_shortfall": False,'
    if jneedle not in s:
        raise SystemExit("JSON charge_min not found")
    s = s.replace(
        jneedle,
        '"use_origin_24h_fifty": false,\n'
        '"_note_use_origin_24h_fifty": "true = 50pct downtime from rolling 24h windows anchored at each trip Origin_In chain; false = legacy Dest_In calendar day (1 trip => +50pct)",\n'
        '"customer_idle_windows": [\n'
        "  {\n"
        '    "_note": "71-8967 P&G factory parking — customer-irrelevant dwell (CONTEXT_LOG Session #90–91)",\n'
        '    "plate": "71-8967",\n'
        '    "start": "2026-04-20 14:00:00",\n'
        '    "end": "2026-04-29 17:00:00",\n'
        '    "note": "Parked at customer — clip dest wait from Daily_Time / gap vs 24h"\n'
        "  }\n"
        "],\n"
        + jneedle,
        1,
    )

    # --- 3) load_oatside_config: parse windows + flags ---
    ret_needle = (
        "    chain_merge = bool(raw.get(\"enable_origin_chain_merge\", _DEFAULT_CONFIG.enable_origin_chain_merge))\n"
        "\n"
        "    return OatsideConfig(\n"
        "        trip_rates=trip_rates,\n"
        "        one_trip_surcharge_pct=surcharge_pct,\n"
        "        min_trips_per_truck=min_trips,\n"
        "        max_travel_h=max_travel,\n"
        "        max_origin_chain_gap_h=gap_h,\n"
        "        enable_origin_chain_merge=chain_merge,\n"
        "        charge_min_trip_shortfall=charge_sf,\n"
        "    )\n"
    )
    if ret_needle not in s:
        raise SystemExit("return OatsideConfig block not found")
    s = s.replace(
        ret_needle,
        "    chain_merge = bool(raw.get(\"enable_origin_chain_merge\", _DEFAULT_CONFIG.enable_origin_chain_merge))\n"
        "    use_o24 = bool(raw.get(\"use_origin_24h_fifty\", _DEFAULT_CONFIG.use_origin_24h_fifty))\n"
        "    idle_raw = raw.get(\"customer_idle_windows\", [])\n"
        "    idle_wins: list[CustomerIdleWindow] = []\n"
        "    if isinstance(idle_raw, list):\n"
        "        for w in idle_raw:\n"
        "            if not isinstance(w, dict):\n"
        "                continue\n"
        "            pl = str(w.get(\"plate\", \"\")).strip()\n"
        "            st = _parse_dt(w.get(\"start\"))\n"
        "            en = _parse_dt(w.get(\"end\"))\n"
        "            if not pl or not st or not en or en <= st:\n"
        "                continue\n"
        '            note = str(w.get("note", "")).strip()\n'
        "            idle_wins.append(CustomerIdleWindow(plate=pl, start=st, end=en, note=note))\n"
        "\n"
        "    return OatsideConfig(\n"
        "        trip_rates=trip_rates,\n"
        "        one_trip_surcharge_pct=surcharge_pct,\n"
        "        min_trips_per_truck=min_trips,\n"
        "        max_travel_h=max_travel,\n"
        "        max_origin_chain_gap_h=gap_h,\n"
        "        enable_origin_chain_merge=chain_merge,\n"
        "        charge_min_trip_shortfall=charge_sf,\n"
        "        use_origin_24h_fifty=use_o24,\n"
        "        customer_idle_windows=idle_wins,\n"
        "    )\n",
        1,
    )

    # --- 4) Helpers after hours() ---
    h_needle = (
        "def hours(a: datetime, b: datetime) -> float:\n"
        "    return (b - a).total_seconds() / 3600.0\n"
        "\n"
        "\n"
        "def feasible(o: Leg, d: Leg, max_travel_h: float) -> bool:\n"
    )
    if h_needle not in s:
        raise SystemExit("hours/feasible not found")
    s = s.replace(
        h_needle,
        "def hours(a: datetime, b: datetime) -> float:\n"
        "    return (b - a).total_seconds() / 3600.0\n"
        "\n"
        "\n"
        "def customer_idle_clip_dest_wait_h(trip: Trip, cfg: OatsideConfig) -> float:\n"
        "    \"\"\"Subtract hours of (Dest_In, Dest_Out) overlapping customer_idle_windows for this plate.\"\"\"\n"
        "    raw = hours(trip.d_in, trip.d_out)\n"
        "    sub = 0.0\n"
        "    for w in cfg.customer_idle_windows:\n"
        "        if w.plate != trip.plate:\n"
        "            continue\n"
        "        sub += w.overlap_hours(trip.d_in, trip.d_out)\n"
        "    return max(0.0, raw - sub)\n"
        "\n"
        "\n"
        "def origin24h_windows_for_plate(sorted_trips: list[Trip]) -> list[tuple[datetime, datetime, list[Trip]]]:\n"
        "    \"\"\"Rolling windows: each window [anchor, anchor+24h) collects all trips with Origin_In in range; next anchor = first trip not yet in any window.\"\"\"\n"
        "    out: list[tuple[datetime, datetime, list[Trip]]] = []\n"
        "    if not sorted_trips:\n"
        "        return out\n"
        "    i = 0\n"
        "    trs = sorted_trips\n"
        "    while i < len(trs):\n"
        "        anchor = trs[i].o_in\n"
        "        end = anchor + timedelta(hours=24)\n"
        "        bucket: list[Trip] = []\n"
        "        j = i\n"
        "        while j < len(trs) and trs[j].o_in < end:\n"
        "            bucket.append(trs[j])\n"
        "            j += 1\n"
        "        out.append((anchor, end, bucket))\n"
        "        i = j if j > i else i + 1\n"
        "    return out\n"
        "\n"
        "\n"
        "def feasible(o: Leg, d: Leg, max_travel_h: float) -> bool:\n",
        1,
    )

    # --- 5) one_trip_fifty_pct_details_origin24h before one_trip_fifty_pct_details ---
    fifty_def = (
        "def one_trip_fifty_pct_details(\n"
        "    trips: list[Trip],\n"
        "    overrides: dict[tuple[str, date], dict[str, Any]],\n"
        "    cfg: OatsideConfig,\n"
        ") -> tuple[list[dict], int]:\n"
        '    """50% surcharge on a Dest_In calendar day when exactly 1 matched trip (unless overridden)."""\n'
    )
    if fifty_def not in s:
        raise SystemExit("one_trip_fifty_pct_details not found")
    s = s.replace(
        fifty_def,
        "def one_trip_fifty_pct_details_origin24h(\n"
        "    trips: list[Trip],\n"
        "    overrides: dict[tuple[str, date], dict[str, Any]],\n"
        "    cfg: OatsideConfig,\n"
        ") -> tuple[list[dict], int]:\n"
        '    """+50% of one trip rate when a rolling 24h window from Origin_In contains exactly 1 matched trip."""\n'
        "    from collections import defaultdict as _dd\n"
        "    by_pl: dict[str, list[Trip]] = _dd(list)\n"
        "    for t in trips:\n"
        "        by_pl[t.plate].append(t)\n"
        "    rows: list[dict] = []\n"
        "    total = 0\n"
        "    for plate in sorted(by_pl.keys()):\n"
        "        lst = sorted(by_pl[plate], key=lambda x: x.o_in)\n"
        "        for anchor, end, bucket in origin24h_windows_for_plate(lst):\n"
        "            n = len(bucket)\n"
        "            if n != 1:\n"
        "                continue\n"
        "            t0 = bucket[0]\n"
        "            d = t0.dest_date\n"
        "            key = (plate, d)\n"
        "            ov = overrides.get(key, {})\n"
        "            action = ov.get(\"action\", \"\")\n"
        "            note = ov.get(\"note\", \"\")\n"
        "            if action == \"exclude_50\":\n"
        "                continue\n"
        "            if action == \"include_50\":\n"
        "                pass\n"
        "            rate = trip_rate_baht(d, cfg)\n"
        "            sur = int(round(rate * cfg.one_trip_surcharge_pct / 100))\n"
        "            rows.append(\n"
        "                {\n"
        "                    \"dest_date\": d,\n"
        "                    \"window_anchor\": anchor,\n"
        "                    \"window_end\": end,\n"
        "                    \"plate\": plate,\n"
        "                    \"site\": site_for_plate(plate),\n"
        "                    \"trips_that_day\": n,\n"
        "                    \"auto_1trip\": True,\n"
        "                    \"override_action\": action,\n"
        "                    \"override_note\": note,\n"
        "                    \"trip_rate_baht\": rate,\n"
        "                    \"surcharge_baht\": sur,\n"
        "                }\n"
        "            )\n"
        "            total += sur\n"
        "    return rows, total\n"
        "\n"
        "\n"
        + fifty_def,
        1,
    )

    # --- 6) daily_time_rows signature + body use clip ---
    dtr_old = (
        "def daily_time_rows(trips: list[Trip], unmatched: list[tuple[str, Leg, str]]) -> list[tuple]:\n"
        "    matched_cycle_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    matched_origin_wait_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    matched_dest_wait_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    matched_travel_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    for t in trips:\n"
        "        key = (t.trip_date, t.plate)\n"
        "        matched_cycle_h[key] += t.total_cycle_h\n"
        "        matched_origin_wait_h[key] += t.origin_wait_h\n"
        "        matched_dest_wait_h[key] += t.dest_wait_h\n"
        "        matched_travel_h[key] += t.travel_h\n"
    )
    if dtr_old not in s:
        raise SystemExit("daily_time_rows header block not found")
    s = s.replace(
        dtr_old,
        "def daily_time_rows(\n"
        "    trips: list[Trip], unmatched: list[tuple[str, Leg, str]], cfg: OatsideConfig\n"
        ") -> list[tuple]:\n"
        "    matched_cycle_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    matched_origin_wait_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    matched_dest_wait_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    matched_travel_h: dict[tuple[date, str], float] = defaultdict(float)\n"
        "    for t in trips:\n"
        "        key = (t.trip_date, t.plate)\n"
        "        dw_raw = t.dest_wait_h\n"
        "        dw_adj = customer_idle_clip_dest_wait_h(t, cfg)\n"
        "        cycle_adj = t.total_cycle_h - max(0.0, dw_raw - dw_adj)\n"
        "        matched_cycle_h[key] += max(0.0, cycle_adj)\n"
        "        matched_origin_wait_h[key] += t.origin_wait_h\n"
        "        matched_dest_wait_h[key] += dw_adj\n"
        "        matched_travel_h[key] += t.travel_h\n",
        1,
    )

    # --- 7) main() call ---
    s = s.replace(
        "    daily_time = daily_time_rows(trips, unmatched)\n",
        "    daily_time = daily_time_rows(trips, unmatched, cfg)\n",
        1,
    )
    s = s.replace(
        "    fifty_rows, fifty_total = one_trip_fifty_pct_details(trips, overrides, cfg)\n",
        "    if cfg.use_origin_24h_fifty:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_details_origin24h(trips, overrides, cfg)\n"
        "    else:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_details(trips, overrides, cfg)\n",
        1,
    )

    # --- 8) write_excel Trip_Detail: add clip columns ---
    td_block = (
        "        \"Travel_h(OriginOut->DestIn)\", \"Dest_Wait_h\", \"Total_Cycle_h\",\n"
        '        "Travel_Flag", "Billable_Trip",\n'
        "    ])\n"
        "    for t in sorted(trips, key=lambda x: (x.dest_date, x.plate, x.d_in)):\n"
        "        td.append([\n"
        "            t.trip_date, t.origin_date, t.dest_date,\n"
        "            t.site, t.plate, t.device, t.o_row, t.d_row,\n"
        "            t.o_in, t.o_out, round(t.origin_wait_h, 2),\n"
        "            t.d_in, t.d_out,\n"
        "            round(t.travel_h, 2), round(t.dest_wait_h, 2), round(t.total_cycle_h, 2),\n"
        "            t.travel_flag, 1,\n"
        "        ])\n"
    )
    if td_block not in s:
        raise SystemExit("Trip_Detail block not found")
    s = s.replace(
        td_block,
        '        "Travel_h(OriginOut->DestIn)", "Dest_Wait_h", "Dest_Wait_customer_h", "Customer_idle_clip_h",\n'
        '        "Total_Cycle_h", "Total_Cycle_customer_h",\n'
        '        "Travel_Flag", "Billable_Trip",\n'
        "    ])\n"
        "    for t in sorted(trips, key=lambda x: (x.dest_date, x.plate, x.d_in)):\n"
        "        dw_c = customer_idle_clip_dest_wait_h(t, cfg)\n"
        "        clip = max(0.0, t.dest_wait_h - dw_c)\n"
        "        cyc_c = max(0.0, t.total_cycle_h - clip)\n"
        "        td.append([\n"
        "            t.trip_date, t.origin_date, t.dest_date,\n"
        "            t.site, t.plate, t.device, t.o_row, t.d_row,\n"
        "            t.o_in, t.o_out, round(t.origin_wait_h, 2),\n"
        "            t.d_in, t.d_out,\n"
        "            round(t.travel_h, 2), round(t.dest_wait_h, 2), round(dw_c, 2), round(clip, 2),\n"
        "            round(t.total_cycle_h, 2), round(cyc_c, 2),\n"
        "            t.travel_flag, 1,\n"
        "        ])\n",
        1,
    )

    # --- 9) Info sheet lines ---
    info_needle = '    info.append(["Charge_min_trip_shortfall", cfg.charge_min_trip_shortfall])\n'
    if info_needle not in s:
        raise SystemExit("Info charge_min not found")
    s = s.replace(
        info_needle,
        '    info.append(["Use_origin_24h_fifty", cfg.use_origin_24h_fifty])\n'
        '    info.append(["Customer_idle_windows", len(cfg.customer_idle_windows)])\n'
        + info_needle,
        1,
    )

    # --- 10) Surcharge sheet header extra columns when origin24 ---
    # Append columns to fifty sheet for window - always write if rows have keys
    lt_head = (
        '    lt.append([\n'
        '        "Dest_In_date", "Plate", "Site", "Trips_that_day",\n'
        '        "Auto_1trip_rule_Y/N", "Override_action", "Override_note",\n'
        '        "Trip_rate_baht", f"Surcharge_baht_{cfg.one_trip_surcharge_pct:.0f}pct",\n'
        "    ])\n"
    )
    if lt_head not in s:
        raise SystemExit("lt.append header not found")
    s = s.replace(
        lt_head,
        '    lt.append([\n'
        '        "Dest_In_date", "Plate", "Site", "Trips_that_day",\n'
        '        "Auto_1trip_rule_Y/N", "Override_action", "Override_note",\n'
        '        "Window_Origin_In", "Window_End",\n'
        '        "Trip_rate_baht", f"Surcharge_baht_{cfg.one_trip_surcharge_pct:.0f}pct",\n'
        "    ])\n",
        1,
    )

    lt_row = (
        "        lt.append([\n"
        "            r[\"dest_date\"], r[\"plate\"], r[\"site\"], r[\"trips_that_day\"],\n"
        '            "Y" if r["auto_1trip"] else "N",\n'
        "            r.get(\"override_action\", \"\"), r.get(\"override_note\", \"\"),\n"
        "            r[\"trip_rate_baht\"], r[\"surcharge_baht\"],\n"
        "        ])\n"
    )
    if lt_row not in s:
        raise SystemExit("lt row append not found")
    s = s.replace(
        lt_row,
        "        lt.append([\n"
        "            r[\"dest_date\"], r[\"plate\"], r[\"site\"], r[\"trips_that_day\"],\n"
        '            "Y" if r["auto_1trip"] else "N",\n'
        "            r.get(\"override_action\", \"\"), r.get(\"override_note\", \"\"),\n"
        "            r.get(\"window_anchor\", \"\"),\n"
        "            r.get(\"window_end\", \"\"),\n"
        "            r[\"trip_rate_baht\"], r[\"surcharge_baht\"],\n"
        "        ])\n",
        1,
    )

    # Legacy fifty rows need empty window cols
    old_fifty_append = (
        "        rows.append(\n"
        "            {\n"
        '                "dest_date": d,\n'
        '                "plate": plate,\n'
        '                "site": site_for_plate(plate),\n'
        '                "trips_that_day": n,\n'
        '                "auto_1trip": auto_apply,\n'
        '                "override_action": action or "",\n'
        '                "override_note": note,\n'
        '                "trip_rate_baht": rate,\n'
        '                "surcharge_baht": sur,\n'
        "            }\n"
        "        )\n"
    )
    if old_fifty_append not in s:
        raise SystemExit("legacy fifty rows.append not found")
    s = s.replace(
        old_fifty_append,
        "        rows.append(\n"
        "            {\n"
        '                "dest_date": d,\n'
        '                "plate": plate,\n'
        '                "site": site_for_plate(plate),\n'
        '                "trips_that_day": n,\n'
        '                "auto_1trip": auto_apply,\n'
        '                "override_action": action or "",\n'
        '                "override_note": note,\n'
        '                "window_anchor": "",\n'
        '                "window_end": "",\n'
        '                "trip_rate_baht": rate,\n'
        '                "surcharge_baht": sur,\n'
        "            }\n"
        "        )\n",
        1,
    )

    if s == orig:
        raise SystemExit("No changes applied")
    TARGET.write_text(s, encoding="utf-8")
    print(f"Patched {TARGET} ({len(s) - len(orig):+d} bytes)")


if __name__ == "__main__":
    main()
