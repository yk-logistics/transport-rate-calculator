from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
for line in s.splitlines():
    if "report_dir" in line and "=" in line and "Path" in line or "report_dir" in line and "TransportRateCalculator" in line:
        if "report_dir" in line and not line.strip().startswith("#"):
            print(line)
