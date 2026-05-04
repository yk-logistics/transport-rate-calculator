from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
for i, line in enumerate(s.splitlines(), 1):
    if line.startswith("def ") and ("excel" in line.lower() or "xlsx" in line.lower() or "workbook" in line.lower()):
        print(i, line[:100])
for i, line in enumerate(s.splitlines(), 1):
    if "Workbook(" in line or "load_workbook" in line:
        print("wb", i, line.strip()[:100])
