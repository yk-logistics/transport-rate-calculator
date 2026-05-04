"""Debug Oatside matching for one plate (import builder by path)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "Oatside" / "build_oatside_reports.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("oatside_build", BUILD)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["oatside_build"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    mod = load_builder()
    cfg = mod.load_oatside_config()
    o_path = ROOT / "Oatside" / "Y.K._Logistics_Solutions_Service_Co.,_Ltd._รายงานการผ่านจุด_02.05.2026_07-15-32 Oatside.xlsx"
    d_path = ROOT / "Oatside" / "Y.K._Logistics_Solutions_Service_Co.,_Ltd._รายงานการผ่านจุด_02.05.2026_06-58-42 P&G.xlsx"
    if not o_path.is_file():
        print("missing origin", o_path)
        sys.exit(1)
    if not d_path.is_file():
        print("missing dest", d_path)
        sys.exit(1)

    plate = "71-6802"
    o_all = mod.parse_legs(o_path)
    d_all = mod.parse_legs(d_path)
    o_legs = [x for x in o_all if x.plate == plate]
    d_legs = [x for x in d_all if x.plate == plate]
    o_legs.sort(key=lambda x: (x.t_out, x.t_in))
    d_legs.sort(key=lambda x: (x.t_in, x.t_out))

    log = ROOT / "ProjectYK_System" / "tools" / "_debug_716802.txt"
    lines: list[str] = []
    lines.append(f"max_travel_h={cfg.max_travel_h} enable_chain={cfg.enable_origin_chain_merge}\n")
    lines.append(f"Origins {len(o_legs)}:\n")
    for x in o_legs:
        lines.append(f"  row={x.row_no} in={x.t_in} out={x.t_out}\n")
    lines.append(f"Dests {len(d_legs)}:\n")
    for x in d_legs:
        lines.append(f"  row={x.row_no} in={x.t_in} out={x.t_out}\n")

    pairs, uo, ud = mod.match_plate(o_legs, d_legs, cfg.max_travel_h)
    lines.append(f"\nAfter match_plate: pairs={len(pairs)} uo={len(uo)} ud={len(ud)}\n")
    for o, d in pairs:
        lines.append(f"  PAIR o row={o.row_no} out={o.t_out} -> d row={d.row_no} in={d.t_in} travel_h={mod.hours(o.t_out, d.t_in):.2f}\n")
    for o in uo:
        lines.append(f"  UO row={o.row_no} {o.t_in}-{o.t_out}\n")
    for d in ud:
        lines.append(f"  UD row={d.row_no} {d.t_in}-{d.t_out}\n")

    trips, unmatched, _ = mod.build_trips(o_path, d_path, cfg)
    t_pl = [t for t in trips if t.plate == plate]
    lines.append(f"\nAfter build_trips (incl demote): matched={len(t_pl)}\n")
    for t in sorted(t_pl, key=lambda x: (x.o_in, x.d_in)):
        lines.append(
            f"  TRIP o_rows={t.o_row} d_row={t.d_row} o_in={t.o_in} o_out={t.o_out} d_in={t.d_in} d_out={t.d_out} tr={t.travel_h:.2f}h\n"
        )
    um = [(k, lg) for k, lg, p in unmatched if p == plate]
    lines.append(f"unmatched count={len(um)}\n")
    for k, lg in um:
        lines.append(f"  {k} row={lg.row_no} {lg.t_in}-{lg.t_out}\n")

    log.write_text("".join(lines), encoding="utf-8")
    print("wrote", log)


if __name__ == "__main__":
    main()
