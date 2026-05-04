from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
start = s.find('idx = f"""')
if start < 0:
    raise SystemExit("start")
# find end: """\n\n    report_dir.mkdir
end = s.find('"""\n\n    report_dir.mkdir(parents=True, exist_ok=True)', start)
if end < 0:
    raise SystemExit("end")
chunk = s[start:end + 3]
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_idx_full.txt").write_text(chunk, encoding="utf-8")
print("len", len(chunk))
