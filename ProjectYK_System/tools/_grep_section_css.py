from pathlib import Path

s = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
for needle in [
    "section-sum-row",
    "Audit Log —",
    "คลิกเพื่อขยาย",
]:
    print("---", needle, s.find(needle))
