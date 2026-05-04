from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
i = s.find("section-sum-row")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_css_section.txt").write_text(s[i - 80 : i + 450], encoding="utf-8")

j = s.find("Audit Log —")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_audit_snip.txt").write_text(s[j : j + 200], encoding="utf-8")
