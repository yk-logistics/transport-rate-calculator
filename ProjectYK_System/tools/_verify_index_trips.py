from pathlib import Path

idx = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\TransportRateCalculator\reports\oatside-apr2026\index.html").read_text(
    encoding="utf-8"
)
trips = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\TransportRateCalculator\reports\oatside-apr2026\trips.html").read_text(
    encoding="utf-8"
)
checks = [
    ("index no color legend", "คำอธิบายสี / ไฮไลต์ชั่วโมงรอ" not in idx),
    ("index hero", "hero-trips" in idx),
    ("index no export-panel", "export-panel" not in idx),
    ("index section-sum-row", "section-sum-row" in idx),
    ("index xlsx in summary", "_xlsx_dl" not in idx and "xlsx-dl" in idx),
    ("trips panel-title-row", "panel-title-row" in trips),
    ("trips tag", "trips-tag" in trips),
]
for name, ok in checks:
    print(name, ok)
Path(r"c:\Users\Home\Desktop\Project YK\ProjectYK_System\tools\_idx_head_verify.txt").write_text(idx[:2200], encoding="utf-8")
