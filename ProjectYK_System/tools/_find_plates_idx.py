from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
needle = "รายทะเบียน"
i = s.find(needle)
print("first", i)
# find details for plates
j = s.find("<details class='section-fold'><summary class='section-sum'>รายทะเบียน", i - 500)
print("j", j)
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_plates_block.txt").write_text(s[j : j + 500], encoding="utf-8")
