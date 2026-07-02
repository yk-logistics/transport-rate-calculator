# -*- coding: utf-8 -*-
"""CLI ครอบ services/kb_payout.py — ตรรกะจริงอยู่ใน app (หน้า /kb-payout ใช้ตัวเดียวกัน).

ใช้ (จากราก repo, python ของ app venv):
  python ProjectYK_System/tools/kb_payout.py list                  # ทุกเจ้า + KB ต่อใบ
  python ProjectYK_System/tools/kb_payout.py match 19027.98        # ยอดโอน CY → ชุดใบ
  python ProjectYK_System/tools/kb_payout.py match 5881 NHL        # ระบุเจ้าอื่นได้
runbook สำหรับโมเดลถูก: docs/KB_PAYOUT_RUNBOOK.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from services.kb_payout import KB_OUR_CUT, KB_WHT, kb_of, load_all, match_amount  # noqa: E402


def cmd_list():
    rows = load_all()
    tot_kb = 0.0
    print(f"{'invoice':<14} {'customer':<10} {'ตู้':>3} {'ค่าขนส่ง':>10} {'เสนอ':>7} {'OT':>5} {'KB':>8}")
    for r in rows:
        tot_kb += r["kb"]
        flag = "" if r["kb"] >= 0 else "  << ติดลบ ตรวจ!"
        print(f"{r['inv']:<14} {r['customer']:<10} {r['qty']:>3.0f} {r['transport']:>10,.2f} "
              f"{r['quote']:>7,.0f} {r['ot']:>5,.0f} {r['kb']:>8,.2f}{flag}")
    print(f"\nรวม {len(rows)} ใบ · KB รวม {tot_kb:,.2f} · โอนคืน 90% = {tot_kb*(1-KB_OUR_CUT):,.2f} "
          f"· ใบ ณ ที่จ่าย 3% = {tot_kb*KB_WHT:,.2f}")


def cmd_match(amount: float, cust: str = "CY"):
    rows = [r for r in load_all() if r["cust"] == cust]
    res = match_amount(rows, amount)
    if not res["combos"]:
        print(f"ไม่เจอชุดอินวอยที่รวมได้ {amount:,.2f} เป๊ะ (ลองเต็ม/−1%ขนส่ง/−1%/−3%) — "
              "อาจข้ามเดือน/มีส่วนลด/โอนหลายก้อนรวมกัน")
        return
    print(f"== เจอแบบ [{res['variant']}] — {len(res['combos'])} ชุดที่เป็นไปได้")
    for c in res["combos"]:
        print(f"\n  ชุด {len(c['invoices'])} ใบ (ยอดโอน {amount:,.2f}):")
        for r in c["invoices"]:
            print(f"    {r['inv']:<14} {r['customer']:<10} วางบิล {r['grand_total']:>9,.2f} "
                  f"รับจริง {c['receipts'][r['inv']]:>9,.2f} · KB {r['kb']:>8,.2f}")
        print(f"    → KB รวม {c['kb_total']:,.2f} · โอนคืนเจ้าของงาน 90% = {c['payout']:,.2f} "
              f"· ใบ ณ ที่จ่าย 3% = {c['wht_cert']:,.2f}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "match":
        cmd_match(float(sys.argv[2].replace(",", "")),
                  sys.argv[3] if len(sys.argv) >= 4 else "CY")
    else:
        cmd_list()
