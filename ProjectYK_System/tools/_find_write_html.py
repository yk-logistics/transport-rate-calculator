from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(lines, 1):
    if line.startswith("def write_html"):
        print("write_html at", i)
        break
out = []
for j in range(i, min(i + 140, len(lines))):
    out.append(f"{j:5d}|{lines[j-1]}")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_write_html_head.txt").write_text("\n".join(out), encoding="utf-8")
