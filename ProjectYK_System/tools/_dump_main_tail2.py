# -*- coding: utf-8 -*-
from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
for i, ln in enumerate(lines, 1):
    if ln.startswith("def write_excel("):
        a = i
        break
else:
    raise SystemExit("no write_excel")
chunk = "\n".join(f"{j:5d}|{lines[j-1]}" for j in range(a - 1, min(a + 120, len(lines))))
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_write_excel_head.txt").write_text(chunk, encoding="utf-8")

for i, ln in enumerate(lines, 1):
    if ln.startswith("def main("):
        m = i
        break
chunk2 = "\n".join(f"{j:5d}|{lines[j-1]}" for j in range(m - 1, min(m + 95, len(lines))))
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_main_full.txt").write_text(chunk2, encoding="utf-8")
