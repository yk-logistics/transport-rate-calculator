from pathlib import Path

lines = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8").splitlines()
a, b = 1715, 2350
chunk = "\n".join(f"{i+1:5d}|{lines[i]}" for i in range(a, min(b, len(lines))))
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_write_excel_chunk.txt").write_text(chunk, encoding="utf-8")
