from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
buf = []
for i, line in enumerate(lines, 1):
    if "def trip_row(t: Trip)" in line or "def trip_row_plate(t: Trip)" in line:
        for j in range(i, min(i + 25, len(lines) + 1)):
            buf.append(f"{j}: {lines[j-1]}")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_trip_row_lines.txt").write_text("\n".join(buf), encoding="utf-8")
