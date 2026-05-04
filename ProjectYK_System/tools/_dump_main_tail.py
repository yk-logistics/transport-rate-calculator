from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
out = []
for i in range(2685, min(2805, len(lines))):
    out.append(f"{i+1:5d}|{lines[i]}")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_main_tail.txt").write_text("\n".join(out), encoding="utf-8")
