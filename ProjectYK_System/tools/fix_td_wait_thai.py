# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"
t = p.read_text(encoding="utf-8")
old = '''    def _td_wait_h(val: float, th: float, dest: bool) -> str:
        cls = "wait-hi-dest" if dest else "wait-hi"
        if val >= th:
            lab = "???????" if dest else "??????"
            return f"<td class='{cls}' title='??{lab} {th:g} ??. (???????????)'>{fmt_hm(val)}</td>"
        return f"<td>{fmt_hm(val)}</td>"'''
new = '''    def _td_wait_h(val: float, th: float, dest: bool) -> str:
        cls = "wait-hi-dest" if dest else "wait-hi"
        if val >= th:
            lab = "ปลายทาง" if dest else "ต้นทาง"
            return (
                f"<td class='{cls}' title='รอ{lab} ≥ {th:g} ชม. (ตรวจพิจารณาเก็บลูกค้า)'>"
                f"{fmt_hm(val)}</td>"
            )
        return f"<td>{fmt_hm(val)}</td>"'''
if old not in t:
    raise SystemExit("old block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
