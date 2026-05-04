from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(lines, 1):
    if line.strip().startswith("idx = f"):
        a = i
        break
else:
    raise SystemExit("not found")
out = []
for j in range(a - 5, min(a + 35, len(lines))):
    out.append(f"{j:5d}|{lines[j-1]}")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_idx_assign_snip.txt").write_text("\n".join(out), encoding="utf-8")
