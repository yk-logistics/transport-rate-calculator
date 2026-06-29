"""แทนยอดหักสดย่อย "ก้อนเดียว" ด้วย **รายการย่อยจริง** จากไฟล์ สดย่อยวังน้อย.xlsx
ต่อไซต์/รอบ (โอ 29มิ.ย.: import รายละเอียดจริง, net ขยับตามจริง).

ชีท: col0=วันที่ col1=ชื่อผู้เบิก col2=รายการ col14=พขร.เบิก หัก เงินเดือน.
แต่ละบรรทัด col14≠0 = 1 PettyCashTxn (deduct_from_driver, pending, cycle).

**กฎ match ที่ปลอดภัย:** match ชื่อ→emp เฉพาะคนที่ **อยู่ใน payrun รอบนี้จริง**
(มี payrunitem) — กันชนชื่อซ้ำ (วิโรจน์ 2 คน, สมัย ราศรี vs สมัย อยุธยา) และ
คนที่ลาออก/ไม่ได้จ่ายรอบนี้. exact-first-name + reject diff-surname.

idempotent: ลบ source=<site>_petty_manual + <site>_petty_itemized เดิม ก่อนเขียน.
recompute payrun ตอนท้าย. rollback: ลบ source itemized + restore backup.

usage: python petty_itemize.py --site BIGC|LCB [--dry-run]
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

SALARY = r"C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026\6.Jun"
SITES = {
    "BIGC": {"xlsx": rf"{SALARY}\BigC\สดย่อยวังน้อย.xlsx", "sheet": "MAY 26", "tag": "2026-05"},
    "LCB":  {"xlsx": rf"{SALARY}\LCB\สดย่อยวังน้อย.xlsx",  "sheet": "JUN 26", "tag": "2026-06"},
}
C_DATE, C_NAME, C_ITEM, C_DEDUCT = 0, 1, 2, 14


def first_name(full: str) -> str:
    p = str(full or "").replace("นาย", "").replace("นาง", "").replace("น.ส.", "").split()
    return p[0] if p else ""


def load_lines(cfg):
    wb = openpyxl.load_workbook(cfg["xlsx"], data_only=True, read_only=True)
    rows = [list(r) for r in wb[cfg["sheet"]].iter_rows(values_only=True)]
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
        d = d.date() if isinstance(d, datetime) else (d if isinstance(d, date) else None)
        out.append({"name": nm, "date": d,
                    "item": (str(r[C_ITEM]).strip() if r[C_ITEM] else ""),
                    "amount": round(float(amt), 2)})
    return out


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("--site", required=True, choices=list(SITES))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    site, dry, cfg = args.site, args.dry_run, SITES[args.site]
    new_src = f"{site.lower()}_petty_itemized"
    # ลบ "ยอดก้อนเดิม" ทุก source ที่เคย import มาต่อไซต์ + itemized เดิม (รันซ้ำ)
    OLD_BY_SITE = {
        "BIGC": ["bigc_may_petty_manual", "bigc_may_petty_itemized"],
        "LCB":  ["lcb_jun2026_petty_O", "lcb_petty_itemized"],
    }
    old_sources = OLD_BY_SITE[site] + [new_src]

    lines = load_lines(cfg)
    eng = make_engine()
    with Session(eng) as s:
        pr = s.exec(select(PayRun).where(
            PayRun.site_code == site, PayRun.pay_cycle_tag == cfg["tag"])).first()
        if pr is None:
            raise SystemExit(f"no payrun {site} {cfg['tag']}")

        # only employees who are IN this payrun (safe against name collisions / resigned)
        member_ids = {it.employee_id for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()}
        by_fn = {}
        for e in s.exec(select(Employee).where(Employee.home_site_code == site)).all():
            if e.id in member_ids:
                by_fn.setdefault(first_name(e.full_name), []).append(e)

        def resolve(nm):
            hit = by_fn.get(first_name(nm), [])
            if len(hit) != 1:
                return None
            emp = hit[0]
            parts = nm.split()
            if len(parts) > 1:
                ep = emp.full_name.replace("นาย", "").replace("นาง", "").split()
                if len(ep) > 1 and parts[1] != ep[1]:
                    return None
            return emp.id

        kept, skipped, per_emp = [], {}, {}
        for ln in lines:
            eid = resolve(ln["name"])
            if eid is None:
                skipped[ln["name"]] = skipped.get(ln["name"], 0) + 1
                continue
            ln["emp_id"] = eid
            kept.append(ln)
            per_emp[eid] = per_emp.get(eid, 0.0) + ln["amount"]

        print(f"=== {site} {cfg['tag']}: matched {len(kept)} lines / {len(per_emp)} drivers (payrun members) ===")
        for eid, tot in sorted(per_emp.items(), key=lambda x: -x[1]):
            e = s.get(Employee, eid)
            n = sum(1 for k in kept if k["emp_id"] == eid)
            print(f"  emp{eid:<4}{str(e.full_name)[:22]:<24} {tot:>9,.2f} ({n})")
        print(f"  skipped (ไม่ใช่สมาชิก payrun/ชื่อไม่ตรง): {sum(skipped.values())} lines / {len(skipped)} names")

        old = s.exec(select(PettyCashTxn).where(PettyCashTxn.source.in_(old_sources))).all()
        # only delete old rows for THIS site (don't nuke the other site's itemized)
        old = [p for p in old if (p.site_code == site)]
        print(f"\n=== ลบ petty เก่า {len(old)} ({site}) → เขียนใหม่ {len(kept)} ===")
        if dry:
            print("  (dry-run)")
            return
        for p in old:
            s.delete(p)
        s.flush()
        now = datetime.utcnow()
        for ln in kept:
            s.add(PettyCashTxn(
                txn_date=ln["date"] or pr.period_end, site_code=site, direction="out",
                amount=ln["amount"], requester_raw=ln["name"], driver_id=ln["emp_id"],
                memo=(ln["item"] or "เบิกสดย่อย")[:200], category="driver_advance",
                has_receipt=False, deduct_from_driver=True, deduct_amount=ln["amount"],
                deduction_status="pending", pay_cycle_tag=cfg["tag"], source=new_src,
                status="active", parsed_confidence=1.0, created_at=now, updated_at=now,
            ))
        s.commit()
        old_net = sum((it.net_pay or 0) for it in s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all())
        s.refresh(pr)
        items = compute_pay_run(s, pr, recompute=True)
        s.commit()
        new_net = sum((it.net_pay or 0) for it in items)
        print(f"\n=== recompute {site} payrun #{pr.id}: net {old_net:,.2f} → {new_net:,.2f} (Δ {new_net-old_net:,.2f}) ===")


if __name__ == "__main__":
    main()
