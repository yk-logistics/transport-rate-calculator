from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
buf = []
for i, line in enumerate(lines, 1):
    if line.startswith("def esc("):
        for j in range(i, i + 12):
            buf.append(f"{j}: {lines[j-1]!r}")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_esc_snip.txt").write_text("\n".join(buf), encoding="utf-8")
