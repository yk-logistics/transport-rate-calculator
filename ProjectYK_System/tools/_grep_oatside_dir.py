from pathlib import Path
import re
s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
for m in re.finditer(r"def _oatside_dir\([^)]*\)[^:]*:", s):
    i = m.start()
    print(s[i:i+400])
