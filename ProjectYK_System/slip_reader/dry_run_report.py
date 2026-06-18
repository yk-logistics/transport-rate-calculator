from __future__ import annotations
import sys
import io
import os
import glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from .engine import get_engine

# repo_root/reports/lcb_slips_0615 — slips saved during the accuracy-proof phase
_HERE = os.path.dirname(__file__)
SLIP_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "reports", "lcb_slips_0615"))
OUT_PATH = os.path.abspath(os.path.join(_HERE, "..", "..", "reports", "slip_reader_dryrun.md"))


def main():
    engine = get_engine()
    with io.open(OUT_PATH, "w", encoding="utf-8") as out:
        out.write("# Slip-reader dry-run (real proof slips)\n\n")
        out.write("| file | is_slip | amount | recipient | memo | time |\n")
        out.write("|---|---|---|---|---|---|\n")
        for f in sorted(glob.glob(os.path.join(SLIP_DIR, "*.jpg"))):
            with open(f, "rb") as fh:
                r = engine.read(fh.read())
            out.write(f"| {os.path.basename(f)} | {r.is_slip} | {r.amount} | "
                      f"{r.recipient_name} | {r.memo} | {r.slip_time} |\n")
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
