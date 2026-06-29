"""ไล่งวดเงินประกันตน LCB ใหม่จากไฟล์ SSO (โออัปเดตงวดถูกต้องให้แล้ว).

ไฟล์: บันทึกประจำเดือน หัวลาก.xlsm ชีท SSO.
  col0/1 = ชื่อ, col4 = งวด X (=จำนวนงวดที่ **จ่ายครบแล้ว**), col7 = total (10), col6 = ครั้งล่ะ (1000).
  "X/10" = จ่ายไปแล้ว X งวด. ถ้า X=total → ผ่อนครบ ไม่ต้องหักอีก.

set employee.deposit_balance = X × per_install (จ่ายแล้วจริง), deposit_target = total × per_install.
engine หัก min(1000, target−balance) เอง:
  - X=10 → balance=10000=target → หัก 0 (จ่ายครบ) ✓
  - X=4  → balance=4000 → หักงวดที่ 5 (1000) ✓  (สลิปโชว์ "5/10" = งวดที่กำลังหัก)
แก้ 29มิ.ย.(รอบ2): เดิม (X−1)×1000 ล่าช้า 1 งวด → คน 10/10 ยังโดนหัก. โอยืนยัน X=งวดที่จ่ายครบ.

match: เฉพาะคนที่อยู่ใน LCB payrun รอบนี้ + first-name (SSO เป็น LCB ล้วน).
idempotent. recompute LCB payrun ตอนท้าย. rollback: restore backup.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import openpyxl  # noqa: E402
from sqlmodel import Session, select  # noqa: E402
from models import Employee, PayRun, PayRunItem  # noqa: E402
from import_bigc_daily import make_engine  # noqa: E402
from services.payroll import compute_pay_run  # noqa: E402

XLSX = Path(r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026"
            r"\6.Jun\LCB\บันทึกประจำเดือน หัวลาก.xlsm")
SHEET = "SSO"
TAG = "2026-06"
C_NAME0, C_NAME1, C_GUAD, C_PER, C_TOTAL = 0, 1, 4, 6, 7


def first_name(full: str) -> str:
    p = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").split()
    return p[0] if p else ""


def load_sso() -> dict:
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    rows = [list(r) for r in wb[SHEET].iter_rows(values_only=True)]
    wb.close()
    out = {}
    for r in rows[2:]:
        if len(r) <= C_TOTAL:
            continue
        nm = r[C_NAME0] if (r[C_NAME0] and str(r[C_NAME0]).strip() not in ("ทำหักต่อ", "")) else r[C_NAME1]
        if not nm:
            continue
        gw = r[C_GUAD]
        if not isinstance(gw, (int, float)):
            continue
        per = r[C_PER] if isinstance(r[C_PER], (int, float)) else 1000
        total = r[C_TOTAL] if isinstance(r[C_TOTAL], (int, float)) else 10
        out[first_name(str(nm).strip())] = (int(gw), float(per), int(total))
    return out


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    sso = load_sso()
    eng = make_engine()
    with Session(eng) as s:
        pr = s.exec(select(PayRun).where(
            PayRun.site_code == "LCB", PayRun.pay_cycle_tag == TAG)).first()
        members = {it.employee_id for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()}

        print(f"{'emp':<5}{'name':<16}{'งวด':>5}{'old_bal':>9}{'new_bal':>9}{'target':>8}")
        changed = 0
        for eid in sorted(members):
            e = s.get(Employee, eid)
            f = first_name(e.full_name)
            if f not in sso:
                continue
            gw, per, total = sso[f]
            new_bal = gw * per  # งวด X = จ่ายครบแล้ว X งวด (เดิม (X−1) ล่าช้า 1 งวด)
            new_tgt = total * per
            old_bal = e.deposit_balance or 0
            if abs(old_bal - new_bal) > 0.5 or abs((e.deposit_target or 0) - new_tgt) > 0.5:
                changed += 1
                print(f"{eid:<5}{f:<16}{gw:>5}{old_bal:>9,.0f}{new_bal:>9,.0f}{new_tgt:>8,.0f}")
                if not dry:
                    e.deposit_balance = new_bal
                    e.deposit_target = new_tgt
                    s.add(e)
        print(f"\nemployees updated: {changed}")
        if dry:
            print("(dry-run: ไม่เขียน, ข้าม recompute)")
            return
        s.commit()
        old_net = sum((it.net_pay or 0) for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all())
        s.refresh(pr)
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        new_net = sum((it.net_pay or 0) for it in items)
        ndep = sum(1 for it in items if (it.deposit_install or 0) > 0)
        print(f"\nrecompute LCB #{pr.id}: net {old_net:,.2f} → {new_net:,.2f} (Δ {new_net-old_net:,.2f})")
        print(f"คนที่ยังหักเงินประกันรอบนี้: {ndep}")


if __name__ == "__main__":
    main()
