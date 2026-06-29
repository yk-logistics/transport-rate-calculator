"""Mark AYU DailyJob ที่เป็น "เที่ยวซ้ำ cross-site" — แถวที่ driver_raw_name ตรงกับ
พนักงาน home_site_code = LCB/BigC (พี่หวานใส่เผื่อให้หมิววางบิล AYU เห็น, ไม่ใช่
งาน AYU จริง). โอยืนยัน 29มิ.ย.: เป็นเที่ยวซ้ำ ไม่นับรายได้ AYU.

วิธี: เปลี่ยน source ของแถวพวกนี้ → '<source>_xsite' เพื่อให้ CFO กรองออก
(revenue_drilldown / monthly_pnl exclude source LIKE '%_xsite'). เก็บแถวไว้ หมิว
ยังเห็น/วางบิลได้. ไม่ผูก driver_id (ไม่กระทบเงินเดือนอยู่แล้ว).

FUTURE: ทำให้ ayu_link_drivers.py auto-tag ตอน import ครั้งหน้า (คนชื่อ home≠AYU
→ _xsite) จะได้ไม่ต้อง mark มือ; และพอหมิวทำในระบบ (เห็นทุกไซต์) ก็ไม่ต้องใส่ซ้ำอีก.

--dry-run นับ ไม่เขียน.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select  # noqa: E402
from models import DailyJob, Employee  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402


def first_name(full: str) -> str:
    p = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").replace("นางสาว", "").split()
    return p[0] if p else ""


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    eng = make_engine()
    with Session(eng) as s:
        # first names of non-AYU (LCB/BigC) employees → these are the cross-site people
        non_ayu_fn = set()
        for e in s.exec(select(Employee).where(Employee.home_site_code != "AYU")).all():
            f = first_name(e.full_name)
            if f:
                non_ayu_fn.add(f)
        ayu_fn = {first_name(e.full_name) for e in
                  s.exec(select(Employee).where(Employee.home_site_code == "AYU")).all()}

        jobs = s.exec(select(DailyJob).where(DailyJob.site_code == "AYU")).all()
        marked, by_name, rev = 0, {}, 0.0
        for j in jobs:
            f = first_name(j.driver_raw_name)
            # cross-site = ชื่ออยู่ใน non-AYU แต่ไม่ใช่คน AYU (กันชื่อซ้ำที่มีทั้งสองฝั่ง)
            if f and f in non_ayu_fn and f not in ayu_fn and j.driver_id is None:
                if not (j.source or "").endswith("_xsite"):
                    marked += 1
                    by_name[j.driver_raw_name] = by_name.get(j.driver_raw_name, 0) + 1
                    rev += (j.revenue_customer or 0.0)
                    if not dry:
                        j.source = (j.source or "") + "_xsite"
                        s.add(j)
        if not dry:
            s.commit()
        print(f"AYU cross-site duplicate rows {'(would mark)' if dry else 'marked'}: {marked}")
        for nm in sorted(by_name, key=lambda x: -by_name[x]):
            print(f"  {by_name[nm]:>4}  {nm}")
        print(f"  รวมค่าขนส่งที่กันออกจาก CFO AYU: {rev:,.2f}")


if __name__ == "__main__":
    main()
