from pathlib import Path

L = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"
lines = L.read_text(encoding="utf-8").splitlines()
out = Path(__file__).resolve().parent / "_daily_snip.txt"
# find def.*daily_rows or daily_activity
start = None
for i, line in enumerate(lines):
    if "daily_rows" in line and "def " in line:
        start = i
        break
if start is None:
    for i, line in enumerate(lines):
        if "def build_daily" in line or "daily_rows =" in line:
            start = i
            break
if start is None:
    out.write_text("not found", encoding="utf-8")
else:
    a = max(0, start - 5)
    b = min(len(lines), start + 120)
    out.write_text("\n".join(f"{j+1}|{lines[j]}" for j in range(a, b)), encoding="utf-8")
