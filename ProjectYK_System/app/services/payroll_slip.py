"""Shared context builder for driver pay slips (HTML + PDF export)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select

from models import DailyJob, Employee, FuelTxn, PayRunItem, PettyCashTxn
from services.alias_map import canonical_person_name


_MONTH_TH = (
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)


def cycle_tag_th_label(tag: str) -> str:
    """แปลง pay_cycle_tag 'YYYY-MM' → 'มีนาคม 2569' (พ.ศ.)."""
    if not tag or len(tag) < 7 or tag[4] != "-":
        return tag
    try:
        y, m = int(tag[:4]), int(tag[5:7])
        if not (1 <= m <= 12):
            return tag
        return f"{_MONTH_TH[m]} {y + 543}"
    except ValueError:
        return tag


def salary_folder_month_tag(pr: Any) -> str:
    """โฟลเดอร์เก็บไฟล์ตาม 'เดือนจ่าย' — BIGC วิ่งมีนาคม → เก็บที่เมษายน (YYYY-MM ถัดจากงวดวิ่ง).

    ไซต์อื่นใช้ pay_cycle_tag เดิม (งวดจ่ายตามที่ระบบกำหนดไว้แล้ว).
    """
    tag = getattr(pr, "pay_cycle_tag", None) or ""
    site = (getattr(pr, "site_code", None) or "").upper()
    if site == "BIGC" and len(tag) >= 7 and tag[4] == "-":
        try:
            y, m = int(tag[:4]), int(tag[5:7])
            if m == 12:
                return f"{y + 1}-01"
            return f"{y}-{m + 1:02d}"
        except ValueError:
            pass
    return tag


def parse_bank_terms(custom_terms: str) -> dict[str, str]:
    """Extract optional bank transfer fields from Employee.custom_terms JSON."""
    out = {"bank_name": "", "bank_account": "", "payment_note": ""}
    if not (custom_terms or "").strip():
        return out
    try:
        j = json.loads(custom_terms)
        if isinstance(j, dict):
            out["bank_name"] = str(j.get("bank_name") or "").strip()
            out["bank_account"] = str(j.get("bank_account") or "").strip()
            out["payment_note"] = str(j.get("payment_note") or "").strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return out


def bank_display_line(terms: dict[str, str]) -> tuple[str, str]:
    """Return (ธนาคาร/ช่องทาง, เลขบัญชีหรือข้อความกดสด)."""
    ac = terms.get("bank_account") or ""
    bn = terms.get("bank_name") or ""
    note = terms.get("payment_note") or ""
    if ac:
        line = bn or "โอนเข้าบัญชี"
        return line, ac
    if note:
        return note, ""
    return "กดเงินสด", ""


def merged_bank_terms(emp: Employee, site_code: str) -> dict[str, str]:
    """รวม seed BIGC (จากไฟล์ตัวอย่าง) เข้ากับ Employee.custom_terms — custom มี bank_account ชนะเสมอ."""
    ct = parse_bank_terms(emp.custom_terms or "")
    ac = (ct.get("bank_account") or "").strip()
    if ac:
        return ct
    pn = (ct.get("payment_note") or "").strip()
    if pn and ("กดเงินสด" in pn or "กดสด" in pn):
        return ct
    if site_code.upper() == "BIGC":
        from services.bigc_bank_seed import lookup_bigc_bank

        seed = lookup_bigc_bank(emp.full_name)
        if seed:
            out = dict(ct)
            if not (out.get("bank_name") or "").strip():
                out["bank_name"] = seed.get("bank_name") or ""
            if not (out.get("bank_account") or "").strip():
                out["bank_account"] = seed.get("bank_account") or ""
            if not (out.get("payment_note") or "").strip():
                out["payment_note"] = seed.get("payment_note") or ""
            return out
    return ct


def employee_bank_display_name(emp: Employee, site_code: str) -> str:
    """ชื่อสำหรับ PDF สรุป/โอน/สลิป — ใช้ canonical ตามไซต์ (เช่น BIGC ชื่อไม่มีนามสกุล → ชื่อเต็มจาก alias)."""
    raw = (emp.full_name or "").strip()
    if not raw:
        return ((emp.nickname or "").strip() or getattr(emp, "code", "") or "—")
    return (canonical_person_name(raw, site_code or "") or raw).strip()


def delivery_route_text(r) -> str:
    """ต้นทาง → [โหลด] pickup → ปลายทาง — leg ที่ว่างยุบหายไป."""
    parts = []
    if (r.origin or "").strip():
        parts.append(r.origin.strip())
    if (r.pickup_location or "").strip():
        parts.append("[โหลด] " + r.pickup_location.strip())
    if (r.destination or "").strip():
        parts.append(r.destination.strip())
    return " → ".join(parts)


# กติกาเดียวกับ services.payroll._classify_lcb_days (ratio = ค่าเที่ยว/รายได้)
_MAO_RATIO, _MAO_TOL, _TRIP_MAX = 0.60, 0.05, 0.15


def classify_mixed_days(daily_jobs) -> dict:
    """แบ่งวันของ lcb_mixed เป็น mao / trip(+ambiguous) / idle(รถจอด/รอลงราคา)
    เพื่อ "แสดงผล" — ใช้ตัวเลขที่คำนวณไว้แล้ว ไม่คำนวณเงินใหม่.

    idle row ที่มี origin/destination/customer แต่ rev=0 ติดธง awaiting_price.
    """
    mao, trip, idle = [], [], []
    for r in daily_jobs:
        rev = r.revenue_customer or 0.0
        fee = r.trip_fee_driver or 0.0
        if rev > 0:
            ratio = fee / rev
            if abs(ratio - _MAO_RATIO) <= _MAO_TOL:
                mao.append(r)
            else:
                trip.append(r)  # trip + ambiguous (ambiguous ติดธงในเทมเพลต)
            continue
        has_route = bool(
            (r.origin or "").strip()
            or (r.destination or "").strip()
            or (r.customer_name_raw or "").strip()
        )
        idle.append({"row": r, "awaiting_price": has_route})
    mao_rev = sum((r.revenue_customer or 0.0) for r in mao)
    return {
        "mao_days": mao,
        "trip_days": trip,
        "idle_days": idle,
        "n_mao": len(mao),
        "n_trip": len(trip),
        "n_idle": len(idle),
        "mao_rev": mao_rev,
        "mao_share": round(mao_rev * _MAO_RATIO, 2),
        "trip_fee_sum": sum((r.trip_fee_driver or 0.0) for r in trip),
        "n_awaiting_price": sum(1 for d in idle if d["awaiting_price"]),
    }


def build_payroll_slip_context(
    session: Session,
    pr,
    emp: Employee,
    item: PayRunItem,
) -> dict[str, Any]:
    """Build dict used by payroll_slip.html and PDF export."""
    start, end, tag = pr.period_start, pr.period_end, pr.pay_cycle_tag

    daily_jobs = session.exec(
        select(DailyJob).where(
            DailyJob.driver_id == emp.id,
            DailyJob.site_code == pr.site_code,
            DailyJob.work_date >= start,
            DailyJob.work_date <= end,
        ).order_by(DailyJob.work_date, DailyJob.id)
    ).all()

    from sqlalchemy import or_

    petty_rows = session.exec(
        select(PettyCashTxn).where(
            PettyCashTxn.driver_id == emp.id,
            PettyCashTxn.pay_cycle_tag == tag,
            PettyCashTxn.deduct_from_driver == True,  # noqa: E712
            PettyCashTxn.deduction_status == "pending",
            or_(
                PettyCashTxn.site_code == pr.site_code,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            ),
        ).order_by(PettyCashTxn.txn_date)
    ).all()

    fuel_rows = session.exec(
        select(FuelTxn).where(
            FuelTxn.driver_id == emp.id,
            FuelTxn.site_code == pr.site_code,
            FuelTxn.txn_date >= start,
            FuelTxn.txn_date <= end,
        )
    ).all()

    plates = sorted({r.plate_no_raw for r in daily_jobs if r.plate_no_raw})
    plates_used = ", ".join(plates) if plates else ""

    miles = [r.mile_snapshot for r in daily_jobs if (r.mile_snapshot or 0) > 0]
    mile_start = min(miles) if miles else 0
    mile_end = max(miles) if miles else 0
    km_run = (mile_end - mile_start) if mile_start and mile_end and mile_end > mile_start else 0
    fuel_used_l = sum((r.liter or 0) for r in fuel_rows) or sum((r.fuel_liter or 0) for r in daily_jobs)
    avg_km_per_l = (km_run / fuel_used_l) if (km_run > 0 and fuel_used_l > 0) else 0

    petty_lines = []
    for p in petty_rows:
        amt = p.deduct_amount if (p.deduct_amount or 0) > 0 else (p.amount or 0)
        if not amt:
            continue
        label = (p.memo or p.category or "เงินเบิก").strip()
        if len(label) > 32:
            label = label[:30] + "…"
        petty_lines.append({"txn_date": p.txn_date, "label": label, "amount": amt})

    mixed = classify_mixed_days(daily_jobs) if emp.pay_mode == "lcb_mixed" else None

    return {
        "run": pr,
        "employee": emp,
        "item": item,
        "daily_jobs": daily_jobs,
        "mixed": mixed,
        "route_text": delivery_route_text,
        "petty_lines": petty_lines,
        "plates_used": plates_used,
        "mile_start": mile_start,
        "mile_end": mile_end,
        "km_run": km_run,
        "fuel_used_l": fuel_used_l,
        "avg_km_per_l": avg_km_per_l,
    }


def salary_export_root(project_root: Optional[Any] = None) -> Any:
    """Return Path .../data/Salary for PDF auto-save."""
    from pathlib import Path

    if project_root is None:
        # ProjectYK_System/app/services/payroll_slip.py → Project YK
        project_root = Path(__file__).resolve().parents[3]
    return Path(project_root) / "data" / "Salary"


def export_driver_folder(
    site_code: str,
    folder_month_tag: str,
    project_root: Optional[Any] = None,
) -> Any:
    """data/Salary/{SITE}/{folder_month}/Driver/ — folder_month = เดือนจ่าย (BIGC เม.ย. สำหรับงวดวิ่งมี.ค.)."""
    root = salary_export_root(project_root)
    return root / site_code.upper() / folder_month_tag / "Driver"
