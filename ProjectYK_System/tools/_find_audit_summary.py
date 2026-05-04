from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
needle = "คลิกเพื่อขยาย"
i = s.find(needle)
print("idx", i)
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_audit_ctx.txt").write_text(s[max(0, i - 120) : i + 80], encoding="utf-8")
