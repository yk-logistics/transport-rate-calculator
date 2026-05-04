from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(lines, 1):
    if line.startswith("def html_export_downloads_block"):
        a = i
        break
else:
    raise SystemExit("not found")
out = "\n".join(f"{j:5d}|{lines[j-1]}" for j in range(a, min(a + 25, len(lines))))
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_html_export_def.txt").write_text(out, encoding="utf-8")
