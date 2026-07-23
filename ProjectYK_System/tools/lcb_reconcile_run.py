"""Reconcile สองทาง payrun LCB ↔ ไฟล์เดลี่ (กฎเหล็กงานเงินข้อ 4) — ใช้ได้ทุกรอบ.

ทางที่ 1: อ่านไฟล์ xlsx เอง (โค้ดอิสระจาก importer) รวมต่อคน: ค่าเที่ยวพขร. + OT/พิเศษ/รับตู้
ทางที่ 2: PayRunItem จาก DB (โหมดเหมาเก็บ Σค่าเที่ยวลง fuel_share_income — บวกสองช่องเสมอ)
ตรงกันทุกคน = หลักฐาน; ต่างกันสตางค์เดียวก็ต้องไล่ (ห้ามปัด)

Run (บน server):  python lcb_reconcile_run.py --run-id 19 --xlsx lcb_import_2026-07.xlsx [--sheet Daily]
"""
import io
import sys
from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import openpyxl
from sqlmodel import Session, select

from models import PayRunItem, Employee
from import_bigc_daily import make_engine


def main():
    ap = ArgumentParser()
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--sheet", default="Daily")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, data_only=True, read_only=True)
    ws = wb[args.sheet]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr = rows[1]  # row1=totals, row2=header (โครงไฟล์ LCB)

    def col(name):
        for i, h in enumerate(hdr):
            if h and name in str(h):
                return i
        return None

    c_drv, c_fee = col("พนักงานขับรถ"), col("ค่าเที่ยวพขร.")
    c_ot, c_sp, c_pk = col("OT"), col("พิเศษ"), col("รับตู้/คืนตู้แทน")

    def f(v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    def g(r, i):
        return r[i] if i is not None and i < len(r) else 0

    file_sum = defaultdict(lambda: [0.0, 0.0])  # [fee, ot+พิเศษ+รับตู้]
    for r in rows[2:]:
        d = str(g(r, c_drv) or "").strip()
        if not d:
            continue
        d = " ".join(d.split())
        file_sum[d][0] += f(g(r, c_fee))
        file_sum[d][1] += f(g(r, c_ot)) + f(g(r, c_sp)) + f(g(r, c_pk))

    eng = make_engine()
    bad = 0
    with Session(eng) as s:
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == args.run_id)).all()
        print(f"{'คนขับ':<30} {'ไฟล์:ค่าเที่ยว':>13} {'engine':>13} {'diff':>9} | {'ไฟล์:OT+พศ+รับตู้':>16} {'engine':>13} {'diff':>9}")
        for i in sorted(items, key=lambda x: -(x.trip_fee_total + x.fuel_share_income)):
            e = s.get(Employee, i.employee_id)
            nm = " ".join(e.full_name.split())
            fs = file_sum.get(nm, [0.0, 0.0])
            eng_fee = i.trip_fee_total + i.fuel_share_income
            eng_extra = i.ot_income + i.special_income + i.pickup_return_income
            d1, d2 = fs[0] - eng_fee, fs[1] - eng_extra
            flag = ""
            if abs(d1) > 0.01 or abs(d2) > 0.01:
                flag = "  ← DIFF"
                bad += 1
            print(f"{nm:<30} {fs[0]:>13,.2f} {eng_fee:>13,.2f} {d1:>9,.2f} | "
                  f"{fs[1]:>16,.2f} {eng_extra:>13,.2f} {d2:>9,.2f}{flag}")
        linked = {" ".join(s.get(Employee, i.employee_id).full_name.split()) for i in items}
        outside = [(nm, fs) for nm, fs in file_sum.items() if nm not in linked and (fs[0] or fs[1])]
        if outside:
            print(f"\n-- ชื่อในไฟล์ที่ไม่อยู่ใน run {args.run_id} (คนใหม่/inactive — เงินยังไม่เข้ารอบ) --")
            for nm, fs in sorted(outside, key=lambda x: -x[1][0]):
                print(f"  {nm:<28} fee={fs[0]:>10,.2f} ot/พศ/รับตู้={fs[1]:>8,.2f}")
    print(f"\nRESULT: {'OK ทุกคนตรง' if bad == 0 else f'{bad} คนไม่ตรง — ห้ามปัด ต้องไล่ทีละคน'}")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
