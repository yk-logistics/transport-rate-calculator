#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
READ-ONLY: เช็คว่าเดลี่ LCB (ชีทสดเล่มวางบิล YK VOLVO) คีย์ครบทุกวันของรอบหรือยัง
— ใช้ก่อนปิดรอบทุกเดือน (runbook §2 ข้อ 0) + เคสเฉพาะ: เดลี่ 21/6 ขาดทั้งวัน
(memory project-lcb-jul-preclose-audit) ต้องตามทีมคีย์ก่อนปิด 15/7.

นับต่อวัน: จำนวนแถวทั้งหมด / แถวที่ลงค่าเที่ยวพขร. (>0) — วันที่ 0 แถวเลย = วันขาด/วันหยุด
(เทคนิคเช็คไขว้: วันว่างให้ไปดูสดย่อยวันเดียวกันว่ามีงานรถไหม)

รันจากราก repo:
  python ProjectYK_System/tools/check_lcb_daily_keyed.py [--tab "Daily 16.06.69 - 15.07.69"]
"""
import argparse
import io
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import gspread

KEY_FILE = "noble-history-446303-e4-c36409a0122c.json"
SHEET_ID = "1Tm1i7kHGkiYtNwM-HQWEnQReg6VZmLzj7T1DjXr8zqg"
DEFAULT_TAB = "Daily 16.06.69 - 15.07.69"   # รอบ 2026-07 (พ.ศ. 69)
CYCLE_START = date(2026, 6, 16)
CYCLE_END = date(2026, 7, 15)


def parse_thai_date(txt: str):
    """'16/6' | '16/06/2569' | '16/6/69' → date (พ.ศ. → ค.ศ.); คืน None ถ้าไม่ใช่วันที่"""
    txt = (txt or "").strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", txt)
    if not m:
        return None
    d, mo = int(m.group(1)), int(m.group(2))
    y = m.group(3)
    if y is None:
        year = CYCLE_START.year if mo >= CYCLE_START.month else CYCLE_END.year
    else:
        year = int(y)
        if year < 100:
            year += 2500          # 69 → 2569
        if year > 2200:
            year -= 543           # พ.ศ. → ค.ศ.
    try:
        return date(year, mo, d)
    except ValueError:
        return None


def to_num(txt: str) -> float:
    try:
        return float((txt or "").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tab", default=DEFAULT_TAB)
    args = ap.parse_args()

    gc = gspread.service_account(filename=KEY_FILE)
    ws = gc.open_by_key(SHEET_ID).worksheet(args.tab)
    rows = ws.get_all_values()
    if len(rows) < 3:
        print("!! แท็บว่าง/สั้นผิดปกติ"); return

    # header อยู่แถว 2 (index 1) — หา col จากข้อความ header อย่าอิงตัวอักษร (layout เปลี่ยนตามปี)
    header = rows[1]
    col_date, tfd_cols = None, []
    for i, h in enumerate(header):
        h2 = (h or "").replace(" ", "").replace("\n", "")
        if col_date is None and "วันที่" in h2:
            col_date = i
        if "ค่าเที่ยวพขร" in h2:
            tfd_cols.append(i)
    if col_date is None or not tfd_cols:
        print(f"!! หา header ไม่เจอ (วันที่={col_date}, ค่าเที่ยวพขร={tfd_cols}) — ดู header แถว 2:")
        print(header); return
    if len(tfd_cols) > 1:
        print("⚠ header 'ค่าเที่ยวพขร' มีหลายคอลัมน์:",
              ", ".join(f"{c + 1}='{header[c].strip()}'" for c in tfd_cols),
              "→ ใช้ตัวแรก (ตรง runbook คอลัมน์ 37)")
    col_tfd = tfd_cols[0]

    per_day = defaultdict(lambda: [0, 0])     # d -> [แถวทั้งหมด, แถวที่ tfd>0]
    for r in rows[2:]:
        d = parse_thai_date(r[col_date] if col_date < len(r) else "")
        if d is None or not (CYCLE_START <= d <= CYCLE_END):
            continue
        per_day[d][0] += 1
        if col_tfd < len(r) and to_num(r[col_tfd]) > 0:
            per_day[d][1] += 1

    print(f"เดลี่ LCB แท็บ '{args.tab}' — รอบ {CYCLE_START} → {CYCLE_END}")
    print(f"คอลัมน์: วันที่={col_date + 1}, ค่าเที่ยวพขร.={col_tfd + 1} (1-based)\n")
    print(f"{'วันที่':<12}{'แถว':>6}{'ลงค่าเที่ยว':>12}")
    empty_days, zero_tfd_days = [], []
    d = CYCLE_START
    while d <= CYCLE_END:
        n, k = per_day.get(d, [0, 0])
        mark = ""
        if n == 0:
            mark = "  ← ไม่มีแถวเลย"; empty_days.append(d)
        elif k == 0:
            mark = "  ← มีแถวแต่ยังไม่ลงค่าเที่ยว"; zero_tfd_days.append(d)
        print(f"{d.strftime('%d/%m/%Y'):<12}{n:>6}{k:>12}{mark}")
        d += timedelta(days=1)

    print()
    if empty_days:
        print(f"🔴 วันไม่มีแถวเลย {len(empty_days)} วัน: "
              + ", ".join(x.strftime("%d/%m") for x in empty_days))
    if zero_tfd_days:
        print(f"🟡 มีแถวแต่ค่าเที่ยว=0 ทั้งวัน {len(zero_tfd_days)} วัน: "
              + ", ".join(x.strftime("%d/%m") for x in zero_tfd_days))
    if not empty_days and not zero_tfd_days:
        print("✅ ทุกวันในรอบมีแถว + มีค่าเที่ยวลงแล้ว")


if __name__ == "__main__":
    main()
