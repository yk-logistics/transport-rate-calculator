import os

from _paths import SALARY_DIR

folder = SALARY_DIR / "LCB"
for name in os.listdir(str(folder)):
    if name.lower().endswith(".xlsx"):
        full = str(folder / name)
        size = os.path.getsize(full)
        print(f"  [{size:>10,}]  {name!r}")
