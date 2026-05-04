import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "bo",
    Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py"),
)
m = importlib.util.module_from_spec(spec)
# exec until _root only would fail - run snippet

src = Path(r"c:\Users\Home\Desktop\Project YK\Oatside\build_oatside_reports.py").read_text(encoding="utf-8")
start = src.find("def _root()")
print(src[start : start + 350])
