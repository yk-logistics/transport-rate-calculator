"""Import AYU office staff (18 people) + their MAR 2026 salaries from
'data/Salary/AYU/บันทึกประจำเดือน YK.xls' sheet 'รวม YK'.

Creates Employee records with role='office', pay_mode='office_monthly'.
Each employee's base_salary is the 'ฐานเงินเดือน' column; the monthly
bonus (พิเศษ) is recorded as a MonthlyOfficePay snapshot by the pay_run
engine (reads base_salary + guarantee_monthly_amount as the "bonus").

For validation we seed AYU MAR (tag=2026-03) directly: base + bonus - SSO
- income tax - advance = net.

Idempotent: employees matched by full_name + home_site_code. Re-runs update
base_salary/notes rather than duplicating.
"""
from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, SALARY_DIR  # noqa: E402

sys.path.insert(0, str(APP_DIR))

import xlrd  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

import main  # noqa: E402
from models import Employee, PettyCashTxn  # noqa: E402


SRC = SALARY_DIR / "AYU" / "บันทึกประจำเดือน YK.xls"
SITE = "AYU"
SHEET = "รวม YK"
IMPORT_SOURCE = "ayu_office_mar_2026"

# Columns (R3 header):
# col1=ชื่อ  col2=ฐานเงินเดือน  col3=พิเศษ  col4=วันทำงาน
# col5=รับเงินเดือน  col6=รับเงินพิเศษ  col7=อื่นๆ(SSO)  col8=รวม(gross)
# col11=ปกส  col13=เงินเบิก  col15=Net  col16=ชื่อเล่น col17=หมายเหตุ


def _s(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _f(v) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def next_code(session: Session, prefix: str) -> str:
    """Next free employee code (e.g. 'OA-001')."""
    rows = session.exec(select(Employee.code).where(Employee.code.like(f"{prefix}%"))).all()
    used = set()
    for r in rows:
        tail = (r or "").split("-")[-1]
        if tail.isdigit():
            used.add(int(tail))
    i = 1
    while i in used:
        i += 1
    return f"{prefix}-{i:03d}"


def main_run():
    if not SRC.exists():
        print(f"ERROR: not found {SRC}")
        return
    wb = xlrd.open_workbook(str(SRC))
    ws = wb.sheet_by_name(SHEET)

    # Office staff are rows R4 through the subtotal R22 (exclusive).
    OFFICE_ROW_START = 4
    OFFICE_ROW_END = 21  # inclusive (R22 is the subtotal)

    with Session(main.engine) as s:
        added = 0
        updated = 0
        advance_rows = 0

        for r in range(OFFICE_ROW_START, OFFICE_ROW_END + 1):
            row = [ws.cell_value(r, c) for c in range(ws.ncols)]
            full_name = _s(row[1])
            if not full_name or full_name in ("0", "0.0"):
                continue

            base = _f(row[2])
            bonus = _f(row[3])      # พิเศษ
            sso = _f(row[11])       # ปกส
            advance = _f(row[13])   # เงินเบิก
            nickname = _s(row[16])  # ชื่อเล่น
            notes = _s(row[17])     # หมายเหตุ

            emp = s.exec(
                select(Employee).where(
                    Employee.home_site_code == SITE,
                    Employee.full_name == full_name,
                )
            ).first()
            if emp is None:
                code = next_code(s, "OA")
                emp = Employee(
                    code=code,
                    full_name=full_name,
                    nickname=nickname,
                    home_site_code=SITE,
                    role="office",
                    pay_mode="office_monthly",
                    base_salary=base,
                    guarantee_monthly_amount=bonus,  # re-used as "fixed bonus"
                    has_guarantee=True,
                    social_security_base=(base if sso > 0 else 0.0),
                    social_security_rate=(0.05 if sso > 0 else 0.0),
                    deposit_target=0.0,
                    status="active",
                    notes=notes,
                )
                s.add(emp)
                s.flush()
                added += 1
                print(f"  + {code}  {full_name[:30]:<30}  base={base:>8.0f}  bonus={bonus:>8.0f}")
            else:
                emp.role = "office"
                emp.pay_mode = "office_monthly"
                emp.base_salary = base
                emp.guarantee_monthly_amount = bonus
                emp.has_guarantee = True
                emp.social_security_base = base if sso > 0 else 0.0
                emp.social_security_rate = 0.05 if sso > 0 else 0.0
                emp.deposit_target = 0.0
                if not emp.nickname and nickname:
                    emp.nickname = nickname
                if not emp.notes and notes:
                    emp.notes = notes
                s.add(emp)
                updated += 1
                print(f"  = {emp.code}  {full_name[:30]:<30}  base={base:>8.0f}  bonus={bonus:>8.0f}")

            # advance → PettyCashTxn(category='driver_advance') for this AYU MAR cycle
            if advance > 0:
                period_end = date(2026, 3, 25)
                memo = f"เงินเบิก (AYU MAR 2026) — {full_name}"
                # Avoid duplicate import
                dup = s.exec(
                    select(PettyCashTxn).where(
                        PettyCashTxn.driver_id == emp.id,
                        PettyCashTxn.source == IMPORT_SOURCE,
                        PettyCashTxn.pay_cycle_tag == "2026-03",
                    )
                ).first()
                if dup is None:
                    txn = PettyCashTxn(
                        txn_date=period_end,
                        site_code=SITE,
                        amount=advance,
                        direction="out",
                        category="driver_advance",
                        requester_raw=full_name,
                        driver_id=emp.id,
                        deduct_from_driver=True,
                        pay_cycle_tag="2026-03",
                        memo=memo,
                        source=IMPORT_SOURCE,
                    )
                    s.add(txn)
                    advance_rows += 1

        s.commit()
        print(f"\nAdded: {added}  Updated: {updated}  Advances: {advance_rows}")


if __name__ == "__main__":
    main_run()
