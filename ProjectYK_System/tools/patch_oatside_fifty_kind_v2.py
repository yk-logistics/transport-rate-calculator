# -*- coding: utf-8 -*-
"""Fix fifty_kind: default origin-day = downtime; blank_run only when marked; badge ค่าเสียเวลา +100%%/+50%%."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Oatside" / "build_oatside_reports.py"

OLD_ORIGIN_BLOCK = """        rate = trip_rate_baht(t0.dest_date, cfg)
        sur = int(round(rate * cfg.one_trip_surcharge_pct / 100))
        rows.append({
            "origin_day": origin_day,
            "dest_date": t0.dest_date,
            "plate": plate,
            "site": site_for_plate(plate),
            "trips_that_day": n,
            "auto_1trip": True,
            "override_action": action,
            "override_note": note,
            "window_anchor": str(origin_day),
            "window_end": "",
            "trip_rate_baht": rate,
            "surcharge_baht": sur,
            "fifty_kind": "blank_run",
        })"""

NEW_ORIGIN_BLOCK = """        rate = trip_rate_baht(t0.dest_date, cfg)
        sur = int(round(rate * cfg.one_trip_surcharge_pct / 100))
        note_l = (note or "").lower()
        fifty_kind = (
            "blank_run"
            if (action == "blank_run" or "ตีเปล่า" in note_l)
            else "downtime_origin_day"
        )
        rows.append({
            "origin_day": origin_day,
            "dest_date": t0.dest_date,
            "plate": plate,
            "site": site_for_plate(plate),
            "trips_that_day": n,
            "auto_1trip": True,
            "override_action": action,
            "override_note": note,
            "window_anchor": str(origin_day),
            "window_end": "",
            "trip_rate_baht": rate,
            "surcharge_baht": sur,
            "fifty_kind": fifty_kind,
        })"""

OLD_BADGE = '''def html_fifty_surcharge_badge(fr: dict, cfg: OatsideConfig) -> str:
    """Badge: label + baht. midnight_full -> +100%%; blank_run = ตีเปล่า; origin24h/dest = ค่าเสียเวลา."""
    amt = int(fr.get("surcharge_baht", 0) or 0)
    if amt <= 0:
        return ""
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
    return f"<span class='badge {cls}'>{label} ฿{amt:,}</span>"'''

NEW_BADGE = '''def html_fifty_surcharge_badge(fr: dict, cfg: OatsideConfig) -> str:
    """Badge: ตีเปล่า (เฉพาะที่ mark) vs ค่าเสียเวลา (+50%% / +100%% รวมข้ามคืน)."""
    amt = int(fr.get("surcharge_baht", 0) or 0)
    if amt <= 0:
        return ""
    rate = int(fr.get("trip_rate_baht", 0) or 0)
    kind = str(fr.get("fifty_kind") or "")
    pct = float(cfg.one_trip_surcharge_pct)
    if kind == "blank_run":
        label = f"ตีเปล่า +{pct:.0f}%"
        cls = "blankrun"
    elif kind == "midnight_full" or (not kind and rate > 0 and amt >= rate):
        label = "ค่าเสียเวลา +100%"
        cls = "fulltrip"
    elif kind == "midnight_pct":
        label = f"ค่าเสียเวลา +{pct:.0f}%"
        cls = "dwell"
    elif kind in ("origin24h", "downtime_dest", "downtime_origin_day"):
        label = f"ค่าเสียเวลา +{pct:.0f}%"
        cls = "dwell"
    else:
        if rate > 0 and amt >= rate:
            label = "ค่าเสียเวลา +100%"
            cls = "fulltrip"
        else:
            label = f"ค่าเสียเวลา +{pct:.0f}%"
            cls = "dwell"
    return f"<span class='badge {cls}'>{label} ฿{amt:,}</span>"'''


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    if OLD_ORIGIN_BLOCK not in s:
        raise SystemExit("origin_day block not found (already patched?)")
    s = s.replace(OLD_ORIGIN_BLOCK, NEW_ORIGIN_BLOCK, 1)
    if OLD_BADGE not in s:
        raise SystemExit("html_fifty_surcharge_badge block not found")
    s = s.replace(OLD_BADGE, NEW_BADGE, 1)
    TARGET.write_text(s, encoding="utf-8")
    print("patched", TARGET)


if __name__ == "__main__":
    main()
