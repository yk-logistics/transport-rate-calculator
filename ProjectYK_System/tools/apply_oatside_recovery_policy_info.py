# -*- coding: utf-8 -*-
"""Append Info sheet row: recovery day may charge both fifty and no-work (user policy เก็บคู่)."""
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"

NEEDLE = '    info.append(["No_work_outbound_50pct_total_baht", no_work_total_baht])\n'
INSERT = (
    NEEDLE
    + '    info.append(\n'
    + '        [\n'
    + '            "Policy_recovery_plus_fifty",\n'
    + '            "เก็บคู่: วัน recovery เที่ยวแรกอาจได้ทั้ง surcharge fifty (ดาวน์ไทม์) และ '
    + "No-work outbound 50pct — บวกทั้งคู่ตามนโยบายผู้ใช้ 2026-05-01\",\n"
    + "        ]\n"
    + "    )\n"
)


def main() -> None:
    t = TARGET.read_text(encoding="utf-8")
    if "Policy_recovery_plus_fifty" in t:
        print("already present")
        return
    if NEEDLE not in t:
        raise SystemExit("needle not found")
    TARGET.write_text(t.replace(NEEDLE, INSERT, 1), encoding="utf-8")
    print("patched", TARGET)


if __name__ == "__main__":
    main()
