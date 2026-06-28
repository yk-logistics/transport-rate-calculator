"""Read-only: BIGC daily driver_raw_name → Employee(home_site_code='BIGC') ตรงไหม.
ไม่เขียน DB — ส่งรายชื่อ unlinked ให้โอยืนยันก่อนผูกจริง (ไม่เดา map)."""
import io, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from sqlmodel import Session, select
from models import DailyJob, Employee
from import_bigc_daily import make_engine


# Employee fields (verified 2026-06-28): full_name="ชื่อ นามสกุล", home_site_code="BIGC"
def first_name(full: str) -> str:
    parts = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").split()
    return parts[0] if parts else ""


eng = make_engine()
with Session(eng) as s:
    raws = sorted({j.driver_raw_name for j in
                   s.exec(select(DailyJob).where(DailyJob.site_code == "BIGC")).all()
                   if j.driver_raw_name})
    bigc_emps = s.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all()
    linked, unlinked = [], []
    for raw in raws:
        rfn = first_name(raw)
        hit = [e for e in bigc_emps if first_name(e.full_name) == rfn and rfn]
        if hit:
            linked.append((raw, hit[0].full_name, hit[0].code))
        else:
            unlinked.append(raw)
    print(f"BIGC daily distinct drivers: {len(raws)}")
    print(f"  LINKED ({len(linked)}):")
    for raw, full, code in linked:
        print(f"    {raw!r:18} -> {full!r} (code={code})")
    print(f"  UNLINKED — ให้โอยืนยัน ({len(unlinked)}): {unlinked}")
    print(f"BIGC employees ในระบบ: {len(bigc_emps)} (home_site_code='BIGC')")
    # emp ที่ไม่เจอในเดลี่เลย (อาจออกแล้ว/ชื่อไม่ตรง)
    daily_fns = {first_name(r) for r in raws}
    emp_no_daily = [e.full_name for e in bigc_emps if first_name(e.full_name) not in daily_fns]
    print(f"  emp BIGC ที่ไม่โผล่ในเดลี่ ({len(emp_no_daily)}): {emp_no_daily}")
