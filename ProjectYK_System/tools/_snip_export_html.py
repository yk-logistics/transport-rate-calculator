from pathlib import Path

t = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\TransportRateCalculator\reports\oatside-apr2026\index.html").read_text(
    encoding="utf-8"
)
i = t.find("export-panel")
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_export_html_snip.txt").write_text(t[i : i + 900], encoding="utf-8")
