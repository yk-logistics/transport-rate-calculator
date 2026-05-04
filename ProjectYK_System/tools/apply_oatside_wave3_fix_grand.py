# -*- coding: utf-8 -*-
"""Fix grand_extra to include no-work; remove dead tot_lbl; update cg_note."""
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")

    old = (
        "    grand_extra = min_trip_money + int(fifty_total)\n"
        "    o_legs_all = parse_legs(origin_path)\n"
        "    nw_rows, nw_total = no_work_outbound_rows(trips, cfg)\n"
        "    phantom_rows = phantom_zero_trip_candidates(o_legs_all, trips, cfg)\n"
        "    hint_rows = double_origin_um_hints(unmatched)\n"
        "    customer_grand_baht = int(base_baht) + int(grand_extra) + int(nw_total)\n"
    )
    new = (
        "    o_legs_all = parse_legs(origin_path)\n"
        "    nw_rows, nw_total = no_work_outbound_rows(trips, cfg)\n"
        "    phantom_rows = phantom_zero_trip_candidates(o_legs_all, trips, cfg)\n"
        "    hint_rows = double_origin_um_hints(unmatched)\n"
        "    grand_extra = min_trip_money + int(fifty_total) + int(nw_total)\n"
        "    customer_grand_baht = int(base_baht) + int(grand_extra)\n"
    )
    if old not in s:
        raise SystemExit("main grand block not found")
    s = s.replace(old, new, 1)

    old2 = (
        '    cs.append(["C", f"ชาร์จ {cfg.one_trip_surcharge_pct:.0f}% ดาวน์ไทม์ 1 เที่ยว (ดู override)", fifty_total_baht])\n'
        '    tot_lbl = "รวมยอดลูกค้า (A+B+C)" if cfg.charge_min_trip_shortfall else "รวมยอดลูกค้า (A+C)"\n'
        "    cs.append(\n"
    )
    # File may have mojibake in C line - match without Thai in C line
    old2b = (
        "    cs.append(\n"
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
    )
    # Remove dead tot_lbl before D: find pattern cs C then tot_lbl then cs D start
    import re

    s = re.sub(
        r'(    cs\.append\(\["C",[^\n]+\n)'
        r'    tot_lbl = "[^"]+" if cfg\.charge_min_trip_shortfall else "[^"]+"\n'
        r'(    cs\.append\(\n\s+\[\n\s+"D",)',
        r"\1\2",
        s,
        count=1,
    )

    old3 = (
        '    cg_note = "base + min_trips + fifty" if cfg.charge_min_trip_shortfall else "base + fifty (min-trip shortfall not charged)"\n'
    )
    new3 = (
        '    cg_note = (\n'
        '        "base + min_trips + fifty + no_work_recovery"\n'
        '        if cfg.charge_min_trip_shortfall\n'
        '        else "base + fifty + no_work_recovery (min-trip shortfall not charged)"\n'
        "    )\n"
    )
    if old3 not in s:
        raise SystemExit("cg_note block not found")
    s = s.replace(old3, new3, 1)

    TARGET.write_text(s, encoding="utf-8")
    print("patched grand + cg_note + dead tot_lbl")


if __name__ == "__main__":
    main()
