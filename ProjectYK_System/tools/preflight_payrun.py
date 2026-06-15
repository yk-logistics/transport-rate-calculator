"""
Read-only payroll preflight: 4 มิติ (unlinked, cycle-date drift, cross-site indicator, source scan).

ไม่แก้ DB · ไม่ finalize · ส่งออก JSON ใต้ reports/preflight_payrun/

Run (จากราก repo):
  python ProjectYK_System/tools/preflight_payrun.py --site LCB
  python ProjectYK_System/tools/preflight_payrun.py --site LCB --run-id 9
"""
from __future__ import annotations

import io
import json
import sys
from argparse import ArgumentParser
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from _repo_paths import APP_DIR, REPO_ROOT  # noqa: E402

sys.path.insert(0, str(APP_DIR))

from sqlalchemy import func as sa_func, or_  # noqa: E402
from sqlmodel import Session, create_engine, select  # noqa: E402

from models import DailyJob, Employee, FuelTxn, PayRun, PayRunItem, PettyCashTxn  # noqa: E402
from services.alias_map import canonical_person_name, normalize_person_name, normalize_site_code, site_from_requester  # noqa: E402
from services.payroll import compute_pay_cycle_tag, compute_pay_cycle_tag_by_policy, normalize_pay_cycle_policy  # noqa: E402
from services.payroll import _count_work_days  # noqa: E402

DB_PATH = APP_DIR / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

REPORTS = REPO_ROOT / "reports"


def _site_or_blank_pred(site: str):
    return or_(
        PettyCashTxn.site_code == site,
        PettyCashTxn.site_code == "",
        PettyCashTxn.site_code.is_(None),
    )


def _petty_unlinked_preds(pr: PayRun) -> list:
    preds = [
        PettyCashTxn.pay_cycle_tag == pr.pay_cycle_tag,
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
        PettyCashTxn.driver_id.is_(None),
    ]
    site = (pr.site_code or "").strip()
    if site:
        preds.append(_site_or_blank_pred(site))
    return preds


def _cycle_drift_preds(pr: PayRun) -> list:
    preds = [
        PettyCashTxn.pay_cycle_tag == pr.pay_cycle_tag,
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
        or_(PettyCashTxn.txn_date < pr.period_start, PettyCashTxn.txn_date > pr.period_end),
    ]
    site = (pr.site_code or "").strip()
    if site:
        preds.append(_site_or_blank_pred(site))
    return preds


def _risk_level(unlinked_c: int, drift_c: int, fuel_unlinked_c: int, lcb_explicit_tag_mismatch_c: int) -> str:
    if unlinked_c > 0 or drift_c > 0:
        return "HIGH"
    if fuel_unlinked_c > 0 or lcb_explicit_tag_mismatch_c > 0:
        return "MEDIUM"
    return "LOW"


def _pct(part: float, whole: float) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 2)


def _pick_run(s: Session, site: str, run_id: int | None) -> PayRun | None:
    site_u = site.strip().upper()
    if run_id is not None:
        pr = s.get(PayRun, run_id)
        if pr is None or (pr.site_code or "").upper() != site_u:
            return None
        return pr
    pr = s.exec(
        select(PayRun).where(PayRun.site_code == site_u).order_by(PayRun.id.desc())
    ).first()
    return pr


def _build_employee_name_index(s: Session) -> dict[str, list[Employee]]:
    idx: dict[str, list[Employee]] = defaultdict(list)
    emps = s.exec(select(Employee).where(Employee.status != "deleted")).all()
    for e in emps:
        key = normalize_person_name(e.full_name or "")
        if key:
            idx[key].append(e)
        # Also index by nickname so short names like "เอ๊ะ" match "บรรเจิด คุ้มพงษ์ (เอ๊ะ)"
        if e.nickname:
            nick_key = normalize_person_name(e.nickname)
            if nick_key and nick_key != key:
                idx[nick_key].append(e)
    return idx


def _resolve_unlinked_rows(pr: PayRun, s: Session) -> dict[str, Any]:
    site = (pr.site_code or "").strip().upper()
    rows = s.exec(
        select(PettyCashTxn).where(
            *_petty_unlinked_preds(pr)
        ).order_by(PettyCashTxn.txn_date.desc(), PettyCashTxn.id.desc())
    ).all()
    emp_idx = _build_employee_name_index(s)
    unresolved: list[dict[str, Any]] = []
    quick_win: list[dict[str, Any]] = []

    for r in rows:
        req = (r.requester_raw or "").strip()
        row_site = normalize_site_code((r.site_code or "").strip())
        hint_site = site_from_requester(req)
        effective_site = hint_site or row_site or site
        cands: list[Employee] = []

        if req:
            canonical = canonical_person_name(req, effective_site)
            key = normalize_person_name(canonical)
            if key:
                cands = list(emp_idx.get(key, []))
                if hint_site:
                    hinted = [e for e in cands if normalize_site_code(e.home_site_code or "") == hint_site]
                    if hinted:
                        cands = hinted

        base_row = {
            "id": r.id,
            "txn_date": r.txn_date.isoformat() if r.txn_date else None,
            "requester_raw": req,
            "deduct_amount": float(r.deduct_amount or 0.0),
            "site_code": r.site_code,
            "pay_cycle_tag": r.pay_cycle_tag,
            "source": r.source,
            "memo": r.memo,
        }
        if not req:
            unresolved.append(
                {
                    **base_row,
                    "reason": "missing_requester_raw",
                    "next_action": "fill requester_raw or link driver manually from petty-cash screen",
                }
            )
            continue
        if len(cands) == 1:
            e = cands[0]
            quick_win.append(
                {
                    **base_row,
                    "reason": "safe_single_match",
                    "suggested_driver_id": e.id,
                    "suggested_employee_name": e.full_name,
                    "suggested_site_code": e.home_site_code,
                    "next_action": "safe to link this row to suggested employee",
                }
            )
            continue
        if len(cands) > 1:
            unresolved.append(
                {
                    **base_row,
                    "reason": "ambiguous_name_collision",
                    "candidate_employees": [
                        {"id": e.id, "full_name": e.full_name, "home_site_code": e.home_site_code}
                        for e in cands[:10]
                    ],
                    "next_action": "choose exact employee manually (skip this case in automation)",
                }
            )
            continue
        unresolved.append(
            {
                **base_row,
                "reason": "name_not_found_in_employee",
                "next_action": "add alias or create employee before linking this deduction",
            }
        )

    unresolved_amount = round(sum(float(x.get("deduct_amount") or 0.0) for x in unresolved), 2)
    quick_win_amount = round(sum(float(x.get("deduct_amount") or 0.0) for x in quick_win), 2)
    return {
        "unresolved_rows": unresolved,
        "quick_win_rows": quick_win,
        "unresolved_count": len(unresolved),
        "unresolved_amount": unresolved_amount,
        "quick_win_count": len(quick_win),
        "quick_win_amount": quick_win_amount,
    }


def _write_resolution_queue(report: dict[str, Any]) -> dict[str, str]:
    queue_dir = REPORTS / "preflight_unresolved_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    site = report.get("site_code", "")
    tag = report.get("pay_cycle_tag", "")
    run_id = report.get("pay_run_id", "")
    unresolved_json = queue_dir / f"unresolved_preflight_{site}_{tag}_run{run_id}.json"
    quick_win_json = queue_dir / f"quickwin_preflight_{site}_{tag}_run{run_id}.json"
    unresolved_csv = queue_dir / f"unresolved_preflight_{site}_{tag}_run{run_id}.csv"

    unresolved_payload = report.get("dimension_unlinked_resolution", {}).get("unresolved_rows", [])
    quick_win_payload = report.get("dimension_unlinked_resolution", {}).get("quick_win_rows", [])

    unresolved_json.write_text(json.dumps(unresolved_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    quick_win_json.write_text(json.dumps(quick_win_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_header = [
        "id", "txn_date", "requester_raw", "deduct_amount", "site_code", "pay_cycle_tag", "reason", "next_action"
    ]
    lines = [",".join(csv_header)]
    for row in unresolved_payload:
        vals = []
        for k in csv_header:
            v = str(row.get(k, "")).replace('"', '""')
            vals.append(f"\"{v}\"")
        lines.append(",".join(vals))
    unresolved_csv.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    return {
        "unresolved_json": str(unresolved_json),
        "quick_win_json": str(quick_win_json),
        "unresolved_csv": str(unresolved_csv),
    }


def _check_implicit_absent(pr: PayRun, s: Session) -> dict[str, Any]:
    """ตรวจคนขับในรอบที่ payroll engine นับเป็น 'ขาดงานเงียบ' (implicit absent) — มัก
    เกิดจากแถววันหยุด/รถจอดที่หายตอน import แล้ว engine ตีความว่าวันนั้นขาดงาน → หักเงิน.

    เกณฑ์เตือน: คนขับ pay_mode ที่ prorate ฐานเงินเดือน (lcb_monthly/lcb_trip/...) ที่มี
    days_absent >= ABSENT_FLAG วัน. ใช้ _count_work_days ตัวเดียวกับ engine จริง.
    """
    ABSENT_FLAG = 3
    PRORATE_MODES = {"lcb_monthly", "lcb_trip", "bigc_monthly", "ayu_trip"}
    start, end = pr.period_start, pr.period_end
    site = (pr.site_code or "").strip().upper()
    emp_ids = [
        int(x) for x in s.exec(
            select(PayRunItem.employee_id).where(PayRunItem.pay_run_id == pr.id)
        ).all()
    ]
    flagged: list[dict] = []
    total_absent_days = 0.0
    for eid in emp_ids:
        emp = s.get(Employee, eid)
        if emp is None:
            continue
        mode = (emp.pay_mode or "").strip()
        days = _count_work_days(s, eid, start, end, site_code=emp.home_site_code or site)
        absent = float(days.get("absent", 0.0))
        if absent >= ABSENT_FLAG and mode in PRORATE_MODES:
            base = (emp.base_salary or 0.0) + (emp.care_allowance or 0.0)
            period_days = (end - start).days + 1
            est_deduct = round((base / period_days) * absent, 2) if period_days else 0.0
            flagged.append({
                "employee_id": eid,
                "full_name": emp.full_name,
                "pay_mode": mode,
                "days_absent": absent,
                "days_worked": float(days.get("worked", 0.0)),
                "est_salary_deducted_thb": est_deduct,
            })
            total_absent_days += absent
    flagged.sort(key=lambda x: -x["days_absent"])
    return {
        "risk": "HIGH" if flagged else "LOW",
        "flagged_driver_count": len(flagged),
        "total_implicit_absent_days": total_absent_days,
        "note": (
            "คนขับที่ถูกนับขาดงานเงียบ >= 3 วัน — มักเกิดจากแถววันหยุด/รถจอดหายตอน import "
            "ทำให้ engine หักเงินเดือนผิด. ตรวจ daily ของคนนั้นว่ามีแถวครบทุกวันทำงานไหม"
        ),
        "flagged_drivers": flagged[:50],
    }


def run_preflight(pr: PayRun, s: Session) -> dict[str, Any]:
    site = (pr.site_code or "").strip().upper()
    start, end, tag = pr.period_start, pr.period_end, pr.pay_cycle_tag

    # --- 1) Unlinked ---
    u_preds = _petty_unlinked_preds(pr)
    unlinked_count = int(s.exec(select(sa_func.count(PettyCashTxn.id)).where(*u_preds)).one() or 0)
    unlinked_amount = float(
        s.exec(select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(*u_preds)).one()
        or 0.0
    )
    unlinked_resolution = _resolve_unlinked_rows(pr, s)

    # --- 1b) Pending petty (linked or not) same cycle / site visibility ---
    pend_preds = [
        PettyCashTxn.pay_cycle_tag == tag,
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
        _site_or_blank_pred(site),
    ]
    pending_petty_count = int(s.exec(select(sa_func.count(PettyCashTxn.id)).where(*pend_preds)).one() or 0)
    pending_petty_amount = float(
        s.exec(select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(*pend_preds)).one()
        or 0.0
    )

    # --- 2) Cycle-date drift (tag รอบนี้ แต่วันที่ txn นอกช่วงวิ่ง) ---
    d_preds = _cycle_drift_preds(pr)
    drift_count = int(s.exec(select(sa_func.count(PettyCashTxn.id)).where(*d_preds)).one() or 0)
    drift_amount = float(
        s.exec(select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(*d_preds)).one() or 0.0
    )

    # --- 2b) Tag vs txn_date (canonical rule per site) — flag เท่านั้น ไม่ mapping ชื่อ ---
    mis_tag_preds = [
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
        _site_or_blank_pred(site),
        PettyCashTxn.pay_cycle_tag == tag,
        PettyCashTxn.txn_date.is_not(None),
    ]
    mis_rows = s.exec(select(PettyCashTxn).where(*mis_tag_preds)).all()
    pay_cycle_mismatch_count = 0
    pay_cycle_mismatch_amount = 0.0
    samples_mismatch: list[dict] = []
    emp_ids_for_policy = sorted({int(r.driver_id) for r in mis_rows if r.driver_id})
    emp_map_for_policy = {e.id: e for e in s.exec(select(Employee).where(Employee.id.in_(emp_ids_for_policy))).all()} if emp_ids_for_policy else {}
    policy_review_count = 0
    policy_review_amount = 0.0
    policy_review_rows: list[dict] = []
    for r in mis_rows:
        td = r.txn_date
        if not isinstance(td, date):
            continue
        emp = emp_map_for_policy.get(int(r.driver_id)) if r.driver_id else None
        if emp is None:
            policy_review_count += 1
            policy_review_amount += float(r.deduct_amount or 0.0)
            if len(policy_review_rows) < 12:
                policy_review_rows.append(
                    {
                        "id": r.id,
                        "txn_date": td.isoformat(),
                        "reason": "missing_driver",
                        "deduct_amount": float(r.deduct_amount or 0.0),
                    }
                )
            expected = compute_pay_cycle_tag(site, td)
        else:
            raw_policy = (emp.pay_cycle_policy or "").strip().lower()
            norm_policy = normalize_pay_cycle_policy(raw_policy)
            expected = compute_pay_cycle_tag_by_policy(norm_policy, td, site_code=emp.home_site_code or site)
            if raw_policy and raw_policy != norm_policy:
                policy_review_count += 1
                policy_review_amount += float(r.deduct_amount or 0.0)
                if len(policy_review_rows) < 12:
                    policy_review_rows.append(
                        {
                            "id": r.id,
                            "txn_date": td.isoformat(),
                            "reason": f"unclear_policy:{raw_policy}",
                            "deduct_amount": float(r.deduct_amount or 0.0),
                        }
                    )
        if expected != (r.pay_cycle_tag or "").strip():
            pay_cycle_mismatch_count += 1
            pay_cycle_mismatch_amount += float(r.deduct_amount or 0.0)
            if len(samples_mismatch) < 12:
                samples_mismatch.append(
                    {
                        "id": r.id,
                        "txn_date": td.isoformat(),
                        "pay_cycle_tag_stored": r.pay_cycle_tag,
                        "pay_cycle_tag_expected": expected,
                        "deduct_amount": float(r.deduct_amount or 0.0),
                        "site_code": r.site_code,
                    }
                )

    # --- 3) Cross-site collision (คนในรอบ payroll มีงาน DailyJob หลาย site ในช่วงเดียวกับรอบ) ---
    emp_ids = [
        int(x)
        for x in s.exec(select(PayRunItem.employee_id).where(PayRunItem.pay_run_id == pr.id)).all()
    ]
    collision_employees: list[dict] = []
    if emp_ids:
        for eid in emp_ids:
            sites = s.exec(
                select(DailyJob.site_code)
                .where(
                    DailyJob.driver_id == eid,
                    DailyJob.work_date >= start,
                    DailyJob.work_date <= end,
                )
                .distinct()
            ).all()
            sites_u = sorted({(x or "").strip().upper() for x in sites if (x or "").strip()})
            if len(sites_u) > 1:
                emp = s.get(Employee, eid)
                collision_employees.append(
                    {
                        "employee_id": eid,
                        "full_name": (emp.full_name if emp else ""),
                        "sites_in_period": sites_u,
                    }
                )

    # --- 4) Source scan (daily / fuel / petty anomalies) ---
    daily_sources = dict(
        s.exec(
            select(DailyJob.source, sa_func.count(DailyJob.id))
            .where(
                DailyJob.site_code == site,
                DailyJob.work_date >= start,
                DailyJob.work_date <= end,
            )
            .group_by(DailyJob.source)
        ).all()
    )
    daily_bigc_source_at_site = int(daily_sources.get("bigc_fuel_rate", 0) or 0)

    fuel_rows_cnt = int(
        s.exec(
            select(sa_func.count(FuelTxn.id)).where(
                FuelTxn.site_code == site,
                FuelTxn.txn_date >= start,
                FuelTxn.txn_date <= end,
            )
        ).one()
        or 0
    )
    fuel_by_source = dict(
        s.exec(
            select(FuelTxn.source, sa_func.count(FuelTxn.id))
            .where(
                FuelTxn.site_code == site,
                FuelTxn.txn_date >= start,
                FuelTxn.txn_date <= end,
            )
            .group_by(FuelTxn.source)
        ).all()
    )
    fuel_unlinked = s.exec(
        select(sa_func.count(FuelTxn.id), sa_func.coalesce(sa_func.sum(FuelTxn.amount), 0.0)).where(
            FuelTxn.site_code == site,
            FuelTxn.txn_date >= start,
            FuelTxn.txn_date <= end,
            FuelTxn.driver_id.is_(None),
        )
    ).one()
    fuel_unlinked_count = int(fuel_unlinked[0] or 0)
    fuel_unlinked_amount = float(fuel_unlinked[1] or 0.0)

    # Petty ไซต์อื่นที่มี pay_cycle_tag สตริงเดียวกับรอบ — มักเป็นเรื่องปกติเพราะแต่ละไซต์นิยามรอบคนละแบบ
    other_site_same_tag = s.exec(
        select(sa_func.count(PettyCashTxn.id), sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(
            PettyCashTxn.pay_cycle_tag == tag,
            PettyCashTxn.deduct_from_driver == True,  # noqa: E712
            PettyCashTxn.deduction_status == "pending",
            PettyCashTxn.site_code != "",
            PettyCashTxn.site_code.is_not(None),
            PettyCashTxn.site_code != site,
        )
    ).one()
    other_site_same_tag_count = int(other_site_same_tag[0] or 0)
    other_site_same_tag_amount = float(other_site_same_tag[1] or 0.0)

    # เฉพาะแถวที่ประกาศ site ตรงกับไซต์รัน แต่ tag/วันที่ไม่สอดคล้องกฎรอบของไซต์นั้น (สัญญาณจริง ไม่ใช่ cross-site tag string)
    lcb_explicit_mismatch_count = 0
    lcb_explicit_mismatch_amount = 0.0
    samples_lcb_mismatch: list[dict] = []
    ex_rows = s.exec(
        select(PettyCashTxn).where(
            PettyCashTxn.pay_cycle_tag == tag,
            PettyCashTxn.deduct_from_driver == True,  # noqa: E712
            PettyCashTxn.deduction_status == "pending",
            PettyCashTxn.site_code == site,
            PettyCashTxn.txn_date.is_not(None),
        )
    ).all()
    for r in ex_rows:
        td = r.txn_date
        if not isinstance(td, date):
            continue
        expected = compute_pay_cycle_tag(site, td)
        st = (r.pay_cycle_tag or "").strip()
        if expected != st or td < start or td > end:
            lcb_explicit_mismatch_count += 1
            lcb_explicit_mismatch_amount += float(r.deduct_amount or 0.0)
            if len(samples_lcb_mismatch) < 12:
                samples_lcb_mismatch.append(
                    {
                        "id": r.id,
                        "txn_date": td.isoformat(),
                        "pay_cycle_tag_stored": r.pay_cycle_tag,
                        "pay_cycle_tag_expected": expected,
                        "deduct_amount": float(r.deduct_amount or 0.0),
                        "site_code": r.site_code,
                    }
                )

    implicit_absent = _check_implicit_absent(pr, s)

    summary_risk = _risk_level(
        unlinked_count, drift_count, fuel_unlinked_count, lcb_explicit_mismatch_count
    )
    if implicit_absent["flagged_driver_count"] > 0 and summary_risk == "LOW":
        summary_risk = "MEDIUM"
    total_pending_amount = round(pending_petty_amount, 2)
    unresolved_amount = float(unlinked_resolution["unresolved_amount"])
    quick_win_amount = float(unlinked_resolution["quick_win_amount"])
    drift_amount_r = round(drift_amount, 2)

    manager_summary = {
        "pending_total_count": int(pending_petty_count),
        "pending_total_amount_thb": total_pending_amount,
        "risk_breakdown": [
            {
                "key": "unresolved_unlinked",
                "label_th": "ยังไม่ผูกคนขับ (ต้องตัดสินใจ)",
                "count": int(unlinked_resolution["unresolved_count"]),
                "amount_thb": round(unresolved_amount, 2),
                "share_of_pending_amount_pct": _pct(unresolved_amount, total_pending_amount),
            },
            {
                "key": "cycle_date_drift",
                "label_th": "วันที่หลุดช่วงรอบวิ่ง",
                "count": int(drift_count),
                "amount_thb": drift_amount_r,
                "share_of_pending_amount_pct": _pct(drift_amount_r, total_pending_amount),
            },
            {
                "key": "quick_win_safe_matches",
                "label_th": "เคสแก้เร็วแบบปลอดภัย",
                "count": int(unlinked_resolution["quick_win_count"]),
                "amount_thb": round(quick_win_amount, 2),
                "share_of_pending_amount_pct": _pct(quick_win_amount, total_pending_amount),
            },
        ],
        "recommended_order": [
            "1) ทำ quick-win safe matches ก่อน",
            "2) เคลียร์ unresolved unlinked ตาม queue",
            "3) ปิด cycle-date drift แล้ว rerun preflight",
        ],
        "is_finalize_ready": bool(
            summary_risk != "HIGH"
            and int(unlinked_count) == 0
            and int(drift_count) == 0
        ),
    }

    return {
        "pay_run_id": pr.id,
        "site_code": site,
        "pay_cycle_tag": tag,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "run_status": pr.status,
        "summary_risk_level": summary_risk,
        "manager_summary": manager_summary,
        "dimension_unlinked": {
            "risk": "HIGH" if unlinked_count > 0 else "LOW",
            "count": unlinked_count,
            "amount_thb": round(unlinked_amount, 2),
            "note": "หักคนขับ pending + ยังไม่มี driver_id (รวม site ว่างจาก import)",
        },
        "dimension_unlinked_resolution": {
            "risk": "MEDIUM" if unlinked_resolution["unresolved_count"] > 0 else "LOW",
            "unresolved_count": unlinked_resolution["unresolved_count"],
            "unresolved_amount_thb": unlinked_resolution["unresolved_amount"],
            "quick_win_count": unlinked_resolution["quick_win_count"],
            "quick_win_amount_thb": unlinked_resolution["quick_win_amount"],
            "note": "skip เฉพาะเคสกำกวม/หาไม่เจอ และแยก quick-win เฉพาะ single-match ที่ปลอดภัย",
            "unresolved_rows": unlinked_resolution["unresolved_rows"][:200],
            "quick_win_rows": unlinked_resolution["quick_win_rows"][:200],
        },
        "dimension_pending_petty_cycle": {
            "risk": "INFO",
            "count": pending_petty_count,
            "amount_thb": round(pending_petty_amount, 2),
            "note": "สดย่อยหักคนขับทั้งหมดในรอบ (pending) สำหรับตั้งคำถามว่าครบหรือยัง",
        },
        "dimension_cycle_date_drift": {
            "risk": "HIGH" if drift_count > 0 else "LOW",
            "count": drift_count,
            "amount_thb": round(drift_amount, 2),
            "note": "ติด pay_cycle_tag รอบนี้แต่ txn_date นอก period_start/end",
        },
        "dimension_pay_cycle_tag_vs_txn_date": {
            "risk": "HIGH" if pay_cycle_mismatch_count > 0 else "LOW",
            "count": pay_cycle_mismatch_count,
            "amount_thb": round(pay_cycle_mismatch_amount, 2),
            "note": "stored pay_cycle_tag != compute_pay_cycle_tag(site, txn_date) — ต้องแก้ tag/วันที่ก่อนปิดความเสี่ยงเงียบ",
            "sample_rows": samples_mismatch,
        },
        "dimension_policy_review_queue": {
            "risk": "HIGH" if policy_review_count > 0 else "LOW",
            "count": int(policy_review_count),
            "amount_thb": round(policy_review_amount, 2),
            "note": "missing driver_id or unclear driver pay_cycle_policy (review required before finalize)",
            "sample_rows": policy_review_rows,
        },
        "dimension_implicit_absent": implicit_absent,
        "dimension_cross_site_collision": {
            "risk": "MEDIUM" if collision_employees else "LOW",
            "drivers_with_multi_site_jobs_in_period": len(collision_employees),
            "employees": collision_employees,
            "note": "ตัวชี้วัดเท่านั้น — ต้องดูว่างานข้ามไซต์เข้ายอดรอบนี้จริงหรือเป็นประวัติคนละไซต์",
        },
        "dimension_source_scan": {
            "daily_job_by_source": {str(k or ""): int(v) for k, v in daily_sources.items()},
            "daily_bigc_fuel_rate_rows_at_site": daily_bigc_source_at_site,
            "fuel_txn_count": fuel_rows_cnt,
            "fuel_txn_by_source": {str(k or ""): int(v) for k, v in fuel_by_source.items()},
            "fuel_unlinked_driver": {
                "risk": "MEDIUM" if fuel_unlinked_count > 0 else "LOW",
                "count": fuel_unlinked_count,
                "amount_thb": round(fuel_unlinked_amount, 2),
            },
            "petty_other_sites_same_cycle_tag_string": {
                "risk": "INFO",
                "count": other_site_same_tag_count,
                "amount_thb": round(other_site_same_tag_amount, 2),
                "note": "รายการไซต์อื่นที่ใช้ pay_cycle_tag สตริงเดียวกับรอบนี้ — ไม่ถือเป็น bug อัตโนมัติ เพราะแต่ละไซต์นิยามรอบคนละแบบ",
            },
            "petty_explicit_site_tag_date_inconsistency": {
                "risk": "MEDIUM" if lcb_explicit_mismatch_count > 0 else "LOW",
                "count": lcb_explicit_mismatch_count,
                "amount_thb": round(lcb_explicit_mismatch_amount, 2),
                "note": f"เฉพาะ site_code={site!r} ที่ pending — tag/วันที่ไม่สอดคล้องกฎรอบหรือนอกช่วง period",
                "sample_rows": samples_lcb_mismatch,
            },
        },
    }


def main() -> int:
    ap = ArgumentParser()
    ap.add_argument("--site", required=True, help="AYU | BIGC | LCB")
    ap.add_argument("--run-id", type=int, default=None)
    args = ap.parse_args()

    with Session(engine) as s:
        pr = _pick_run(s, args.site, args.run_id)
        if pr is None:
            print("ไม่พบ PayRun ที่ตรงเงื่อนไข", file=sys.stderr)
            return 2
        report = run_preflight(pr, s)

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"preflight_payrun_{report['site_code']}_{report['pay_cycle_tag']}_run{report['pay_run_id']}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    queue_paths = _write_resolution_queue(report)

    morning_md = ""
    if report.get("summary_risk_level") == "HIGH":
        qdir = REPORTS / "preflight_morning_queue"
        qdir.mkdir(parents=True, exist_ok=True)
        md_path = qdir / f"PENDING_MORNING_preflight_{report['site_code']}_{report['pay_cycle_tag']}_run{report['pay_run_id']}.md"
        u = report.get("dimension_unlinked", {})
        d = report.get("dimension_cycle_date_drift", {})
        rid = report.get("pay_run_id", "")
        mgr = report.get("manager_summary", {})
        top = mgr.get("risk_breakdown", [])
        unresolved = top[0] if len(top) > 0 else {}
        drift_top = top[1] if len(top) > 1 else {}
        quick = top[2] if len(top) > 2 else {}
        md_path.write_text(
            "\n".join(
                [
                    f"# Preflight HIGH — {report.get('site_code')} · tag {report.get('pay_cycle_tag')} · run {rid}",
                    "",
                    f"- JSON: `{out}`",
                    f"- unlinked: **{u.get('count', 0)}** รายการ · **{u.get('amount_thb', 0):,.2f}** บาท",
                    f"- cycle-date drift: **{d.get('count', 0)}** รายการ · **{d.get('amount_thb', 0):,.2f}** บาท",
                    f"- pending รวม: **{mgr.get('pending_total_count', 0)}** รายการ · **{mgr.get('pending_total_amount_thb', 0):,.2f}** บาท",
                    "",
                    "## Executive summary (manager-friendly)",
                    f"- ยังไม่ผูกคนขับ: **{unresolved.get('count', 0)}** รายการ · **{unresolved.get('amount_thb', 0):,.2f}** บาท "
                    f"({unresolved.get('share_of_pending_amount_pct', 0):,.2f}% ของ pending)",
                    f"- วันที่หลุดรอบวิ่ง: **{drift_top.get('count', 0)}** รายการ · **{drift_top.get('amount_thb', 0):,.2f}** บาท "
                    f"({drift_top.get('share_of_pending_amount_pct', 0):,.2f}% ของ pending)",
                    f"- quick-win ปลอดภัย: **{quick.get('count', 0)}** รายการ · **{quick.get('amount_thb', 0):,.2f}** บาท "
                    f"({quick.get('share_of_pending_amount_pct', 0):,.2f}% ของ pending)",
                    "",
                    "## ขั้นตอนแนะนำ",
                    f"- เปิด `/payroll/{rid}` ตรวจแบนเนอร์ unlinked + drift",
                    "- แก้สดย่อย (ลิงก์คนขับ / ย้ายรอบ / แก้วันที่) ก่อน finalize",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        morning_md = str(md_path)

    print(
        json.dumps(
            {
                "written": str(out),
                "summary_risk_level": report["summary_risk_level"],
                "morning_note_md": morning_md,
                "unresolved_queue_json": queue_paths.get("unresolved_json", ""),
                "quick_win_json": queue_paths.get("quick_win_json", ""),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
