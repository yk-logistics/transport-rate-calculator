# -*- coding: utf-8 -*-
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"


def main() -> None:
    s = TARGET.read_text(encoding="utf-8")
    old = "    customer_idle_windows=[],\n)\n"
    new = (
        "    customer_idle_windows=[\n"
        "        CustomerIdleWindow(\n"
        '            plate="71-8967",\n'
        "            start=datetime(2026, 4, 20, 14, 0, 0),\n"
        "            end=datetime(2026, 4, 29, 17, 0, 0),\n"
        '            note="Factory parked CONTEXT_LOG 90-91",\n'
        "        ),\n"
        "    ],\n"
        ")\n"
    )
    if old not in s:
        raise SystemExit("customer_idle_windows=[] block not found")
    idx = s.find("class CustomerIdleWindow")
    idx2 = s.find("_DEFAULT_CONFIG = OatsideConfig")
    if idx == -1 or idx2 == -1 or idx > idx2:
        raise SystemExit("class order: CustomerIdleWindow must precede _DEFAULT_CONFIG")
    s = s.replace(old, new, 1)

    needle = '    idle_raw = raw.get("customer_idle_windows", [])\n'
    rep = (
        '    if "customer_idle_windows" not in raw:\n'
        '        idle_raw = _DEFAULT_CONFIG_JSON["customer_idle_windows"]\n'
        "    else:\n"
        '        idle_raw = raw.get("customer_idle_windows") or []\n'
    )
    if needle not in s:
        raise SystemExit("idle_raw line not found")
    s = s.replace(needle, rep, 1)

    TARGET.write_text(s, encoding="utf-8")
    print("patched default idle + load merge")


if __name__ == "__main__":
    main()
