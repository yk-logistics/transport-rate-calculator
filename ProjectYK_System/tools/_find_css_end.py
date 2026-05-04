from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
i = s.find('css = (')
j = s.find(")\n\n    idx =", i)
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_css_tail.txt").write_text(s[j-400 : j+40], encoding="utf-8")
