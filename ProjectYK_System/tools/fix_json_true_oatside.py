from pathlib import Path

p = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"
t = p.read_text(encoding="utf-8")
t2 = t.replace('"long_dest_wait_midnight_fifty": true,', '"long_dest_wait_midnight_fifty": True,', 1)
if t2 == t:
    raise SystemExit("pattern not found")
p.write_text(t2, encoding="utf-8")
print("ok")
