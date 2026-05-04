from pathlib import Path

t = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\TransportRateCalculator\reports\oatside-apr2026\index.html").read_text(
    encoding="utf-8"
)
i = t.find("summary.section-sum-row")
print("idx", i)
print(t[i : i + 200] if i >= 0 else "missing")
