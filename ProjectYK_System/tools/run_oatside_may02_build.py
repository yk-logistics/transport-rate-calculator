"""Run Oatside report build with fixed GPS paths (UTF-8). Update ORIGIN/DEST when exports change."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = ROOT / "Oatside" / "Y.K._Logistics_Solutions_Service_Co.,_Ltd._รายงานการผ่านจุด_02.05.2026_07-15-32 Oatside.xlsx"
DEST = ROOT / "Oatside" / "Y.K._Logistics_Solutions_Service_Co.,_Ltd._รายงานการผ่านจุด_02.05.2026_06-58-42 P&G.xlsx"


def main() -> None:
    for label, p in (("OATSIDE_ORIGIN", ORIGIN), ("OATSIDE_DEST", DEST)):
        if not p.is_file():
            sys.stderr.write(f"Missing {label}: {p}\n")
            sys.exit(1)
    env = os.environ.copy()
    env["OATSIDE_ORIGIN"] = str(ORIGIN)
    env["OATSIDE_DEST"] = str(DEST)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        [sys.executable, str(ROOT / "Oatside" / "build_oatside_reports.py")],
        cwd=str(ROOT),
        env=env,
    )
    raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
