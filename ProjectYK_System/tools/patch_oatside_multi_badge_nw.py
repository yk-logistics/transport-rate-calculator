# -*- coding: utf-8 -*-
"""Multi-badge per (plate, dest_date); No-work -> ตีเปล่า; lists for plate pages."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Oatside" / "build_oatside_reports.py"
s = TARGET.read_text(encoding="utf-8")

# 1) Replace plate_dest_day_rows function head through return out
OLD_PD = '''def plate_dest_day_rows(
    trips: list[Trip], fifty_rows: list[dict], cfg: OatsideConfig
) -> list[dict]:
    """Per (plate, Dest_In date): trip count, base line, whether 50% charged (after overrides)."""
    by_pd: dict[tuple[str, date], list[Trip]] = defaultdict(list)
    for t in trips:
        by_pd[(t.plate, t.dest_date)].append(t)
    fifty_key = {(r["plate"], r["dest_date"]): r for r in fifty_rows}
    out: list[dict] = []
    for (plate, d), lst in sorted(by_pd.items(), key=lambda x: (x[0][1], x[0][0])):
        rate = trip_rate_baht(d, cfg)
        n = len(lst)
        base_line = n * rate
        fr = fifty_key.get((plate, d))
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
        )
    return out'''

NEW_PD = '''def plate_dest_day_rows(
    trips: list[Trip],
    fifty_rows: list[dict],
    cfg: OatsideConfig,
    nw_rows: list[dict] | None = None,
) -> list[dict]:
    """Per (plate, Dest_In date): base line + sum surcharges; HTML cell can show multiple badges."""
    by_pd: dict[tuple[str, date], list[Trip]] = defaultdict(list)
    for t in trips:
        by_pd[(t.plate, t.dest_date)].append(t)
    fifty_lists: dict[tuple[str, date], list[dict]] = defaultdict(list)
    for r in fifty_rows:
        p = r.get("plate")
        d = r.get("dest_date")
        if p and isinstance(d, date):
            fifty_lists[(str(p), d)].append(r)
    nw_by: dict[tuple[str, date], dict] = {}
    if nw_rows:
        for nr in nw_rows:
            nw_by[(str(nr["plate"]), nr["dest_date"])] = nr
    out: list[dict] = []
    for (plate, d), lst in sorted(by_pd.items(), key=lambda x: (x[0][1], x[0][0])):
        rate = trip_rate_baht(d, cfg)
        n = len(lst)
        base_line = n * rate
        key = (str(plate), d)
        frs = fifty_lists.get(key, [])
        sur = sum(int(x.get("surcharge_baht", 0) or 0) for x in frs)
        badge_parts: list[str] = []
        for x in frs:
            b = html_fifty_surcharge_badge(x, cfg)
            if b:
                badge_parts.append(b)
        nr = nw_by.get(key)
        if nr:
            ns = int(nr.get("surcharge_baht", 0) or 0)
            if ns > 0:
                sur += ns
                synth = {
                    "plate": plate,
                    "dest_date": d,
                    "trip_rate_baht": int(nr.get("trip_rate_baht", 0) or 0),
                    "surcharge_baht": ns,
                    "fifty_kind": "no_work_outbound",
                }
                b2 = html_fifty_surcharge_badge(synth, cfg)
                if b2:
                    badge_parts.append(b2)
        badge = " ".join(badge_parts) if badge_parts else ""
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
        )
    return out'''

if OLD_PD not in s:
    raise SystemExit("plate_dest_day_rows block not found")
s = s.replace(OLD_PD, NEW_PD, 1)

# 2) html_fifty: add no_work_outbound after blank_run branch
OLD_ELIF = '''    elif kind == "midnight_full" or (not kind and rate > 0 and amt >= rate):'''
# insert no_work branch after blank_run block - read current badge function
needle = '''    if kind == "blank_run":
        label = f"ตีเปล่า +{pct:.0f}%"
        cls = "blankrun"
    elif kind == "midnight_full"'''
if needle not in s:
    raise SystemExit("badge blank_run/midnight anchor missing")
s = s.replace(
    needle,
    '''    if kind == "blank_run":
        label = f"ตีเปล่า +{pct:.0f}%"
        cls = "blankrun"
    elif kind == "no_work_outbound":
        label = f"ตีเปล่า +{pct:.0f}%"
        cls = "blankrun"
    elif kind == "midnight_full"''',
    1,
)

# 3) write_excel pday line
s = s.replace(
    "    pday = plate_dest_day_rows(trips, fifty_rows, cfg)\n",
    "    pday = plate_dest_day_rows(trips, fifty_rows, cfg, nw_rows=no_work_rows)\n",
    1,
)

# 4) main(): move nw before pday_rows + pass nw_rows
old_main = """    base_baht = base_trips_revenue_baht(trips, cfg)
    pday_rows = plate_dest_day_rows(trips, fifty_rows, cfg)
    min_trip_money = int(extra) if cfg.charge_min_trip_shortfall else 0
    if not cfg.charge_min_trip_shortfall:
        bc_a, bc_c, bc_s, bc_e, lc_a, lc_c, lc_s, lc_e = bc_stats
        bc_stats = (bc_a, bc_c, bc_s, 0, lc_a, lc_c, lc_s, 0)
    o_legs_all = parse_legs(origin_path)
    nw_rows, nw_total = no_work_outbound_rows(trips, cfg)"""

new_main = """    base_baht = base_trips_revenue_baht(trips, cfg)
    o_legs_all = parse_legs(origin_path)
    nw_rows, nw_total = no_work_outbound_rows(trips, cfg)
    pday_rows = plate_dest_day_rows(trips, fifty_rows, cfg, nw_rows=nw_rows)
    min_trip_money = int(extra) if cfg.charge_min_trip_shortfall else 0
    if not cfg.charge_min_trip_shortfall:
        bc_a, bc_c, bc_s, bc_e, lc_a, lc_c, lc_s, lc_e = bc_stats
        bc_stats = (bc_a, bc_c, bc_s, 0, lc_a, lc_c, lc_s, 0)"""

if old_main not in s:
    raise SystemExit("main pday/nw block not found")
s = s.replace(old_main, new_main, 1)

# 5) Replace fifty_by_key / fifty_origin_key block in write_html - find unique snippet
old_keys = """    fifty_by_key = {(r["plate"], r["dest_date"]): r for r in fifty_rows}
    fifty_origin_key = {(r["plate"], r["origin_day"]): r for r in fifty_rows if "origin_day" in r}"""

new_keys = """    fifty_by_lists: dict[tuple[str, date], list[dict]] = defaultdict(list)
    for r in fifty_rows:
        fifty_by_lists[(r["plate"], r["dest_date"])].append(r)
    fifty_origin_lists: dict[tuple[str, date], list[dict]] = defaultdict(list)
    for r in fifty_rows:
        if "origin_day" in r:
            fifty_origin_lists[(r["plate"], r["origin_day"])].append(r)"""

if old_keys not in s:
    raise SystemExit("fifty_by_key block not found")
s = s.replace(old_keys, new_keys, 1)

# 6) Plate loop origin branch
old_o = """                fr = fifty_origin_key.get((p, od))
                reason = audit_oday_idx.get((p, od), f"ไม่เก็บ (วันงาน {cnt} เที่ยว)" if cnt != 1 else "ไม่เก็บ (override หรือเงื่อนไขเพิ่ม)")
                badge = ""
                if fr is not None:
                    badge = " " + html_fifty_surcharge_badge(fr, cfg)"""

new_o = """                frs = fifty_origin_lists.get((p, od), [])
                reason = audit_oday_idx.get((p, od), f"ไม่เก็บ (วันงาน {cnt} เที่ยว)" if cnt != 1 else "ไม่เก็บ (override หรือเงื่อนไขเพิ่ม)")
                badge = ""
                if frs:
                    parts = [html_fifty_surcharge_badge(x, cfg) for x in frs if int(x.get("surcharge_baht", 0) or 0) > 0]
                    parts = [b for b in parts if b]
                    if parts:
                        badge = " " + " ".join(parts)"""

if old_o not in s:
    raise SystemExit("plate origin badge block not found")
s = s.replace(old_o, new_o, 1)

# 7) Plate loop dest branch
old_d = """                fr = fifty_by_key.get((p, d))
                badge = ""
                if fr is not None:
                    badge = " " + html_fifty_surcharge_badge(fr, cfg)"""

new_d = """                frs = fifty_by_lists.get((p, d), [])
                badge = ""
                if frs:
                    parts = [html_fifty_surcharge_badge(x, cfg) for x in frs if int(x.get("surcharge_baht", 0) or 0) > 0]
                    parts = [b for b in parts if b]
                    if parts:
                        badge = " " + " ".join(parts)"""

if old_d not in s:
    raise SystemExit("plate dest badge block not found")
s = s.replace(old_d, new_d, 1)

# 8) CSS badge spacing
s = s.replace(
    ".badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700}",
    ".badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;margin:0 6px 4px 0}",
    1,
)

TARGET.write_text(s, encoding="utf-8")
print("patched", TARGET)
