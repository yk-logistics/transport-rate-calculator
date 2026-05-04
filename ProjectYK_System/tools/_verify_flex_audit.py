from pathlib import Path

t = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\TransportRateCalculator\reports\oatside-apr2026\index.html").read_text(
    encoding="utf-8"
)
print("summary.section-sum-row{width", "summary.section-sum-row{width" in t)
print("margin-left:auto", "margin-left:auto" in t)
print("audit order", "(คลิกเพื่อขยาย) Audit" in t)
print("bad old order", "× ทะเบียน (คลิกเพื่อขยาย)" in t)
