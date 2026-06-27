import os
import glob
from pathlib import Path

# KB (ใต้โต๊ะ) ต้องไม่โผล่ในแอปคนขับ — guard กันเผลอ render ในอนาคต
TEMPLATES = Path(__file__).resolve().parents[1] / "app" / "templates"


def _driver_templates():
    pats = ["driver_*.html", "check_driver.html", "pwa*.html"]
    files = []
    for p in pats:
        files += glob.glob(str(TEMPLATES / p))
    return files


def test_no_kb_in_driver_templates():
    leaks = []
    for f in _driver_templates():
        txt = Path(f).read_text(encoding="utf-8")
        if "kb_amount" in txt:
            leaks.append(os.path.basename(f))
    assert not leaks, f"KB leaked into driver template(s): {leaks}"
