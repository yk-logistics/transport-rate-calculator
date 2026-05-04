# -*- coding: utf-8 -*-
"""
Add long dest wait crossing midnight -> supplemental +50% keyed by dest_date
when no fifty row yet for (plate, dest_date). Fixes e.g. 71-6802 Apr 21 dwell.

Also extend OatsideConfig + load + JSON defaults + main() merge after base fifty.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "Oatside" / "build_oatside_reports.py"

FUNC = '''

def supplement_long_dest_wait_midnight_fifty(
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
            f"ปลายทางรอข้ามคืน Dest_In→Dest_Out ({t.dest_wait_h:.2f}h); "
            f"+{cfg.one_trip_surcharge_pct:.0f}% เรทวัน Dest_In"
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

INSERT_BEFORE = "def origin_day_audit_rows("


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    if "def supplement_long_dest_wait_midnight_fifty" in s:
        print("already patched")
        return

    if INSERT_BEFORE not in s:
        raise SystemExit("insert anchor not found")

    s = s.replace(INSERT_BEFORE, FUNC + INSERT_BEFORE, 1)

    s = s.replace(
        "    outbound_half_dest_dates: frozenset[date]\n\n@dataclass\nclass CustomerIdleWindow:",
        "    outbound_half_dest_dates: frozenset[date]\n"
        "    long_dest_wait_midnight_fifty: bool\n"
        "    long_dest_wait_midnight_min_h: float\n\n"
        "@dataclass\nclass CustomerIdleWindow:",
        1,
    )

    s = s.replace(
        "    outbound_half_dest_dates=_DEFAULT_OUTBOUND_HALF_DATES,\n)\n\n_DEFAULT_CONFIG_JSON",
        "    outbound_half_dest_dates=_DEFAULT_OUTBOUND_HALF_DATES,\n"
        "    long_dest_wait_midnight_fifty=True,\n"
        "    long_dest_wait_midnight_min_h=12.0,\n)\n\n_DEFAULT_CONFIG_JSON",
        1,
    )

    needle_json = '"_note_outbound_half":'
    if needle_json not in s:
        raise SystemExit("json note outbound not found")
    s = s.replace(
        needle_json,
        '"long_dest_wait_midnight_fifty": true,\n'
        '    "long_dest_wait_midnight_min_h": 12,\n'
        '    "_note_long_dest_wait_midnight": "If Dest_In and Dest_Out cross midnight and dwell >= min_h, add +50pct by dest_date when no fifty row yet (origin_day mode gap)",\n'
        "    " + needle_json,
        1,
    )

    s = s.replace(
        "        outbound_half_dest_dates=ohd,\n    )\n\n\ndef trip_rate_baht",
        "        outbound_half_dest_dates=ohd,\n"
        "        long_dest_wait_midnight_fifty=bool(\n"
        "            raw.get(\"long_dest_wait_midnight_fifty\", _DEFAULT_CONFIG.long_dest_wait_midnight_fifty)\n"
        "        ),\n"
        "        long_dest_wait_midnight_min_h=float(\n"
        "            raw.get(\"long_dest_wait_midnight_min_h\", _DEFAULT_CONFIG.long_dest_wait_midnight_min_h)\n"
        "        ),\n"
        "    )\n\n\ndef trip_rate_baht",
        1,
    )

    old_main = (
        "    if cfg.use_origin_day_fifty:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_origin_day(trips, overrides, cfg)\n"
        "        audit_rows = origin_day_audit_rows(trips, fifty_rows, overrides, cfg)\n"
        "    elif cfg.use_origin_24h_fifty:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_details_origin24h(trips, overrides, cfg)\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
        "    else:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_details(trips, overrides, cfg)\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
    )
    new_main = (
        "    if cfg.use_origin_day_fifty:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_origin_day(trips, overrides, cfg)\n"
        "    elif cfg.use_origin_24h_fifty:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_details_origin24h(trips, overrides, cfg)\n"
        "    else:\n"
        "        fifty_rows, fifty_total = one_trip_fifty_pct_details(trips, overrides, cfg)\n"
        "    add_fr, add_tot = supplement_long_dest_wait_midnight_fifty(trips, fifty_rows, overrides, cfg)\n"
        "    fifty_rows = fifty_rows + add_fr\n"
        "    fifty_total += add_tot\n"
        "    if cfg.use_origin_day_fifty:\n"
        "        audit_rows = origin_day_audit_rows(trips, fifty_rows, overrides, cfg)\n"
        "    elif cfg.use_origin_24h_fifty:\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
        "    else:\n"
        "        audit_rows = audit_log_rows(trips, fifty_rows, overrides, cfg)\n"
    )
    if old_main not in s:
        raise SystemExit("main fifty block not found")
    s = s.replace(old_main, new_main, 1)

    TARGET.write_text(s, encoding="utf-8")
    print("patched", TARGET)


if __name__ == "__main__":
    main()
