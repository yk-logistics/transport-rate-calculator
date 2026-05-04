from pathlib import Path
s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
print('html_export_downloads_block' in s)
i = s.find('html_export_downloads_block')
print('idx', i)
if i >= 0:
    Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_html_export_ctx.txt").write_text(
        repr(s[i - 40 : i + 400]), encoding="utf-8"
    )
