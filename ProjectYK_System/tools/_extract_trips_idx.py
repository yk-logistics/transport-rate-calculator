from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
i = s.find("trips_html_content = ")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_trips_block.txt").write_text(s[i : i + 3200], encoding="utf-8")
j = s.find("idx = f\"\"\"<!doctype html>")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_idx_block.txt").write_text(s[j : j + 4200], encoding="utf-8")
