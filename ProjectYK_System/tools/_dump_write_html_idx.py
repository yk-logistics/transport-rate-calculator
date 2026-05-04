# -*- coding: utf-8 -*-
from pathlib import Path

P = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
lines = P.read_text(encoding="utf-8").splitlines()
# find def write_html
for i, ln in enumerate(lines):
    if ln.startswith("def write_html("):
        a = i
        break
else:
    raise SystemExit("no write_html")
# find idx = f
for j, ln in enumerate(lines):
    if "idx = f" in ln and "html" in ln:
        b = j
        break
else:
    b = None

out = []
out.append(f"write_html starts line {a+1}")
out.extend(lines[a : a + 25])
out.append("")
if b:
    out.append(f"idx starts line {b+1}")
    out.extend(lines[b : b + 45])

Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_write_html_dump.txt").write_text("\n".join(out), encoding="utf-8")
