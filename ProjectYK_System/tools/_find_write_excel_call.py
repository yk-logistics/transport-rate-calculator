from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
for i, line in enumerate(s.splitlines(), 1):
    if "write_excel(" in line and not line.strip().startswith("def "):
        print(i, line.strip()[:120])
