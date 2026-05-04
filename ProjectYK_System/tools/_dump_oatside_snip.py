# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = Path(r"c:/Users/Home/Desktop/Project YK/Oatside/build_oatside_reports.py")
lines = P.read_text(encoding="utf-8").splitlines()
ranges = [
    (1, 120, "head imports / Leg"),
    (500, 700, "sample"),
    (2550, 2700, "um_section"),
    (2350, 2450, "main write"),
]
for a, b, label in ranges:
    print(f"\n=== {label} {a}-{b} ===\n")
    for i in range(a - 1, min(b, len(lines))):
        print(f"{i+1}|{lines[i]}")
