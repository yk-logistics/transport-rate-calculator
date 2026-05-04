from pathlib import Path
import re

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
# sheet names in quotes after append or title=
names = set(re.findall(r"\.title\s*=\s*[\"']([^\"']+)[\"']", s))
names2 = set(re.findall(r"create_sheet\([\"']([^\"']+)[\"']", s))
print("title=", sorted(names)[:40], "count", len(names))
print("create_sheet", sorted(names2))
