# -*- coding: utf-8 -*-
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    old = (
        "    lt_rows_html = \"\".join(\n"
        "        f\"<tr><td>{r['dest_date']}</td><td><a href='plates/{esc(r['plate'])}.html'>{esc(r['plate'])}</a></td>\"\n"
        "        f\"<td><span class='badge {'bigc' if r['site']=='BigC' else 'lcb'}'>{r['site']}</span></td>\"\n"
        "        f\"<td>{r['trips_that_day']}</td><td>{'Y' if r['auto_1trip'] else 'N'}</td>\"\n"
        "        f\"<td>{esc(r.get('override_action',''))}</td><td>{esc(r.get('override_note',''))}</td>\"\n"
        "        f\"<td>{r['trip_rate_baht']:,}</td><td class='money'>{r['surcharge_baht']:,}</td></tr>\"\n"
        "        for r in fifty_rows\n"
        "    )\n"
    )
    new = (
        "    lt_rows_html = \"\".join(\n"
        "        f\"<tr><td>{r['dest_date']}</td><td><a href='plates/{esc(r['plate'])}.html'>{esc(r['plate'])}</a></td>\"\n"
        "        f\"<td><span class='badge {'bigc' if r['site']=='BigC' else 'lcb'}'>{r['site']}</span></td>\"\n"
        "        f\"<td>{r['trips_that_day']}</td><td>{'Y' if r['auto_1trip'] else 'N'}</td>\"\n"
        "        f\"<td>{esc(r.get('override_action',''))}</td><td>{esc(r.get('override_note',''))}</td>\"\n"
        "        f\"<td>{esc(r.get('window_anchor',''))}</td><td>{esc(r.get('window_end',''))}</td>\"\n"
        "        f\"<td>{r['trip_rate_baht']:,}</td><td class='money'>{r['surcharge_baht']:,}</td></tr>\"\n"
        "        for r in fifty_rows\n"
        "    )\n"
    )
    if old not in s:
        raise SystemExit("lt_rows_html block not found")
    s = s.replace(old, new, 1)

    c1 = s.count("Override</th><th>Note</th><th>")
    if c1 != 1:
        raise SystemExit(f"Override+Note header count={c1}")
    s = s.replace(
        "Override</th><th>Note</th><th>",
        "Override</th><th>Note</th><th>Window_Origin_In</th><th>Window_End</th><th>",
        1,
    )

    needle = "lt_rows_html if lt_rows_html else f\"<tr><td colspan=9>"
    c2 = s.count(needle)
    if c2 != 1:
        raise SystemExit(f"lt colspan9 count={c2}")
    s = s.replace(needle, 'lt_rows_html if lt_rows_html else f"<tr><td colspan=11>', 1)

    TARGET.write_text(s, encoding="utf-8")
    print("html lt patched")


if __name__ == "__main__":
    main()
