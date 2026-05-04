from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
start = s.find('trips_html_content = f"""')
end = s.find('(report_dir / "trips.html").write_text', start)
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_trips_assign.txt").write_text(s[start:end], encoding="utf-8")
