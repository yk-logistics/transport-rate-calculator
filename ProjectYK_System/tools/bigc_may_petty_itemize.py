"""BigC พ.ค. — แทนยอดหักสดย่อย "ก้อนเดียว" ด้วย **รายการย่อยจริง** จากไฟล์
สดย่อยวังน้อย.xlsx ชีท MAY 26 (โอ 29มิ.ย.: import รายละเอียดจริง, net ขยับตามจริง).

แหล่ง: col0=วันที่ col1=ชื่อผู้เบิก col2=รายการ col14=พขร.เบิก หัก เงินเดือน.
แต่ละบรรทัด col14≠0 = 1 PettyCashTxn (deduct_from_driver, pending, cycle 2026-05).
match ชื่อ→emp BigC แบบ exact-first-name + กันชน 'สมัย อยุธยา'(AYU) ไม่ใช่ สมัย ราศรี.

idempotent: ลบ source bigc_may_petty_manual (ก้อนเดิม) + bigc_may_petty_itemized
(รันซ้ำ) ก่อนเขียน. recompute payrun #4 ตอนท้าย. net จะขยับ (คนใหม่ 3 ได้สดย่อย).
rollback: ลบ source bigc_may_petty_itemized + restore จาก backup.
"""
import io
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import openpyxl  # noqa: E402
from sqlmodel import Session, select  # noqa: E402
from models import Employee, PayRun, PayRunItem, PettyCashTxn  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402
from services.payroll import compute_pay_run  # noqa: E402

XLSX = Path(r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026"
            r"\6.Jun\BigC\สดย่อยวังน้อย.xlsx")
SHEET = "MAY 26"
TAG = "2026-05"
OLD_SOURCE = "bigc_may_petty_manual"      # ก้อนเดิม (ลบทิ้ง)
SOURCE = "bigc_may_petty_itemized"        # ใหม่ (รายการย่อย)
# คอลัมน์ (0-based) verified
C_DATE, C_NAME, C_ITEM, C_DEDUCT = 0, 1, 2, 14


def first_name(full: str) -> str:
    p = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").split()
    return p[0] if p else ""


def build_name_map(session: Session) -> dict:
    """sheet-name → emp_id (BigC). exact first-name, reject diff-surname collisions."""
    emps = session.exec(select(Employee).where(Employee.home_site_code == "BIGC")).all()
    by_fn = {}
    for e in emps:
        by_fn.setdefault(first_name(e.full_name), []).append(e)
    return by_fn


def resolve(sheet_name: str, by_fn: dict):
    f = first_name(sheet_name)
    hit = by_fn.get(f, [])
    if len(hit) != 1:
        return None
    emp = hit[0]
    # reject if sheet name carries a surname that differs from emp's (สมัย อยุธยา ≠ สมัย ราศรี)
    parts = sheet_name.split()
    if len(parts) > 1:
        emp_parts = emp.full_name.split()
        if len(emp_parts) > 1 and parts[1] != emp_parts[1]:
            return None
    return emp.id


def load_lines():
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    rows = [list(r) for r in wb[SHEET].iter_rows(values_only=True)]
    wb.close()
    out = []
    for r in rows[3:]:
        if len(r) <= C_DEDUCT:
            continue
        nm = str(r[C_NAME]).strip() if r[C_NAME] else ""
        amt = r[C_DEDUCT]
        if not nm or not isinstance(amt, (int, float)) or abs(amt) < 0.001:
            continue
        d = r[C_DATE]
        if isinstance(d, datetime):
            d = d.date()
        elif not isinstance(d, date):
            d = None
        item = str(r[C_ITEM]).strip() if r[C_ITEM] else ""
        out.append({"name": nm, "date": d, "item": item, "amount": round(float(amt), 2)})
    return out


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    lines = load_lines()
    eng = make_engine()
    with Session(eng) as s:
        pr = s.exec(select(PayRun).where(
            PayRun.site_code == "BIGC", PayRun.pay_cycle_tag == TAG)).first()
        by_fn = build_name_map(s)

        # resolve lines → emp, keep only matched BigC drivers
        kept, skipped = [], {}
        per_emp = {}
        for ln in lines:
            eid = resolve(ln["name"], by_fn)
            if eid is None:
                skipped[ln["name"]] = skipped.get(ln["name"], 0) + 1
                continue
            ln["emp_id"] = eid
            kept.append(ln)
            per_emp[eid] = per_emp.get(eid, 0.0) + ln["amount"]

        print(f"=== matched {len(kept)} lines for {len(per_emp)} BigC drivers ===")
        for eid, tot in sorted(per_emp.items(), key=lambda x: -x[1]):
            e = s.get(Employee, eid)
            n = sum(1 for k in kept if k["emp_id"] == eid)
            print(f"  emp{eid:<4}{str(e.full_name)[:20]:<22} รวมหัก {tot:>9,.2f} ({n} รายการ)")
        print(f"  skipped (ไม่ใช่ BigC/ชื่อไม่ตรง): {sum(skipped.values())} lines from {len(skipped)} names")

        old = s.exec(select(PettyCashTxn).where(PettyCashTxn.source.in_([OLD_SOURCE, SOURCE]))).all()
        print(f"\n=== ลบ petty เก่า {len(old)} แถว (ก้อน+itemized เดิม) แล้วเขียนใหม่ {len(kept)} ===")
        if dry:
            print("  (dry-run: ไม่เขียน, ข้าม recompute)")
            return
        for p in old:
            s.delete(p)
        s.flush()
        now = datetime.utcnow()
        for ln in kept:
            s.add(PettyCashTxn(
                txn_date=ln["date"] or pr.period_end, site_code="BIGC", direction="out",
                amount=ln["amount"], requester_raw=ln["name"], driver_id=ln["emp_id"],
                memo=(ln["item"] or "เบิกสดย่อย")[:200], category="driver_advance",
                has_receipt=False, deduct_from_driver=True, deduct_amount=ln["amount"],
                deduction_status="pending", pay_cycle_tag=TAG, source=SOURCE,
                status="active", parsed_confidence=1.0, created_at=now, updated_at=now,
            ))
        s.commit()

        old_net = sum((it.net_pay or 0) for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all())
        s.refresh(pr)
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        new_net = sum((it.net_pay or 0) for it in items)
        print(f"\n=== recompute payrun #4 ===")
        print(f"  net เดิม {old_net:,.2f} → ใหม่ {new_net:,.2f}  (Δ {new_net-old_net:,.2f})")
        for it in sorted(items, key=lambda x: x.employee_id):
            e = s.get(Employee, it.employee_id)
            print(f"  emp{it.employee_id:<4}{str(e.full_name)[:20]:<22}"
                  f" petty={it.petty_cash_deduction:>9,.0f} net={it.net_pay:>10,.2f}")


if __name__ == "__main__":
    main()
