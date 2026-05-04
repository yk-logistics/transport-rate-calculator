# -*- coding: utf-8 -*-
from pathlib import Path

P = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
s = P.read_text(encoding="utf-8")

def hit(label, needle):
    print(label, "->", (needle in s), "at", s.find(needle))

hit("tripsPlateFilter", "tripsPlateFilter")
hit("_TRIPS_FILTER_JS", "_TRIPS_FILTER_JS")
hit("html_export", "html_export_downloads_block")
hit("write_split_excel", "write_split_excel_exports")
hit("beautify_oatside", "beautify_oatside_workbook")
hit("section-fold", "section-fold")
hit("def write_html", "def write_html(")

# main block snippet
i = s.find("def main()")
print("\nmain() first 80 lines:")
for k, line in enumerate(s[i:].splitlines()[:80], 1):
    print(f"{k:3d}|{line}")
