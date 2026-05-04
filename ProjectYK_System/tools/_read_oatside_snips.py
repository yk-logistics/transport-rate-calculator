from pathlib import Path

p = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py")
s = p.read_text(encoding="utf-8")

def grab(label, start, end):
    Path(rf"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_snip_{label}.txt").write_text(
        s[start:end], encoding="utf-8"
    )

i = s.find("idx = f\"\"\"")
grab("idx_start", i, i + 3500)

j = s.find("trips_html_content = (")
grab("trips_start", j, j + 2200)

k = s.find("def html_export_downloads_block")
grab("export_fn", k, k + 1200)
