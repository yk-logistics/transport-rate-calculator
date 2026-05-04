# -*- coding: utf-8 -*-
from pathlib import Path

B = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
s = B.read_text(encoding="utf-8")

checks = {
    "summary.section-sum-row + width:100%": "summary.section-sum-row{display:flex!important;width:100%" in s,
    "sum-dl margin-left:auto": "sum-dl{margin-left:auto" in s,
    "section-sum-row in idx summaries": "section-sum-row" in s and "_xlsx_dl" in s,
    "Audit (คลิกเพื่อขยาย) หน้า": "(คลิกเพื่อขยาย) Audit Log" in s,
}

print("=== build_oatside_reports.py markers ===")
for k, v in checks.items():
    print(f"{v}\t{k}")

# resolve report path like runtime _root
here = B.resolve().parent  # Oatside
parent = here.parent
report_from_parent = parent / "TransportRateCalculator" / "reports" / "oatside-apr2026"
report_from_here = here / "TransportRateCalculator" / "reports" / "oatside-apr2026"
print("\n=== paths ===")
print("if TransportRateCalculator under repo root:", report_from_parent, report_from_parent.is_dir())
print("else under Oatside:", report_from_here, report_from_here.is_dir())

for p in (report_from_parent, report_from_here):
    idx = p / "index.html"
    if idx.is_file():
        t = idx.read_text(encoding="utf-8")
        print("\nFOUND index:", idx)
        print("  has summary.section-sum-row{width", "width:100%" in t)
        print("  has margin-left:auto", "margin-left:auto" in t)
        print("  has (คลิกเพื่อขยาย) Audit first", "(คลิกเพื่อขยาย) Audit" in t)
        print("  size bytes", idx.stat().st_size)
