from pathlib import Path

p = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
t = p.read_text(encoding="utf-8")
n = t.count('}"""')
print("count }\"\"\"", n)
if n:
    t2 = t.replace('}"""', '}""')
    p.write_text(t2, encoding="utf-8")
    print("replaced all")
else:
    print("nothing to do")
