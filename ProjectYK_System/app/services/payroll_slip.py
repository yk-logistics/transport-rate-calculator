"""Shared context builder for driver pay slips (HTML + PDF export)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select

from models import DailyJob, DailyJobFee, Employee, FuelTxn, PayRunItem, PettyCashTxn
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
    """รวม seed BIGC (จากไฟล์ตัวอย่าง) เข้ากับ Employee.custom_terms — custom มี bank_account ชนะเสมอ.

    DB fields (Employee.account_no/bank_name) ชนะก่อนทุกอย่าง — เป็น source of truth ใหม่
    (กรอกผ่านหน้าแก้ไขพนักงาน) ให้ปุ่ม export PDF เก่าใช้เลขบัญชีชุดเดียวกับหน้าพิมพ์ใหม่.
    """
    db_acct = (getattr(emp, "account_no", "") or "").strip()
    if db_acct:
        return {
            "bank_account": db_acct,
            "bank_name": (getattr(emp, "bank_name", "") or "").strip(),
            "payment_note": "",
        }
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
    """ช่อง "ส่งสินค้า" ของสลิป — โครงเดลี่แต่ละไซท์ไม่เหมือนกัน สูตร route จึง
    **แยกต่อไซท์** (โอ 29มิ.ย.: "เดลี่คนละแบบในแต่ละไซท์ สูตรก็ต้องไม่เหมือนกัน").

      LCB  : origin → pickup_location → destination   (3 ช่วงครบ)
      AYU  : pickup_location → destination            (ขึ้นสินค้า → ส่งสินค้า)
      BIGC : destination                              (คอลัมน์ E=สถานะ ลง origin ผิด,
                                                       ยังไม่มี pickup → โชว์ปลายทางอย่างเดียว)
    leg ที่ว่างยุบหายไป. ไซท์อื่นที่ยังไม่กำหนด → fallback origin→pickup→dest.
    """
    site = (getattr(r, "site_code", "") or "").upper()
    origin = (r.origin or "").strip()
    pickup = (r.pickup_location or "").strip()
    dest = (r.destination or "").strip()

    if site == "LCB":
        legs = [origin, pickup, dest]
    elif site == "AYU":
        legs = [pickup, dest]
    elif site == "BIGC":
        legs = [dest]
    else:
        legs = [origin, pickup, dest]
    return " → ".join(p for p in legs if p)


def _remark_is_internal(remark: str) -> bool:
    """remark ที่ขึ้นต้นด้วย '[' = โน้ตภายในระบบ (เช่น "[งานยกเลิก-ตัดออกจากค่าจ้าง] เดิม: ...ค่าเที่ยว=1200")
    — ห้ามโชว์ให้คนขับเห็น (โอ 29มิ.ย.: เลขค่าเที่ยวที่ไม่ได้จ่าย บนสลิป = อันตราย)."""
    return (remark or "").strip().startswith("[")


def slip_route_cell(r) -> str:
    """ข้อความหลักช่อง "ส่งสินค้า" บนสลิปคนขับ.

      - มี route จริง → โชว์ route
      - ไม่มี route (วันรถจอด/งานถูกตัด) → โชว์ status_code (เช่น "รถจอด") แทนขีด —
    คืนข้อความล้วน (ไม่มี HTML); doc_no / remark เทมเพลตต่อท้ายเอง.
    """
    route = delivery_route_text(r)
    if route:
        return route
    return (getattr(r, "status_code", "") or "").strip()


def slip_route_remark(r) -> str:
    """remark ที่ "ปลอดภัยจะโชว์ให้คนขับ" — ตัดโน้ตภายใน ([...]) ออก กันเลขงานยกเลิกรั่ว
    + ตัด tel=... (เลขโทรเทาๆ ไม่เกี่ยวคนขับ ไม่มีผล — โอ 1ก.ค.)."""
    remark = (getattr(r, "remark", "") or "").strip()
    if not remark or _remark_is_internal(remark):
        return ""
    # ตัด token "tel=<อะไรก็ตามจนจบ/จนเจอ ||>" ออก แล้วเก็บกวาดตัวคั่น || ที่ค้าง
    cleaned = re.sub(r"\s*tel=\S*", "", remark, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\|\|\s*", " ", cleaned).strip(" |")
    return cleaned.strip()


# กติกาเดียวกับ services.payroll._classify_lcb_days (ratio = ค่าเที่ยว/รายได้)
_MAO_RATIO, _MAO_TOL, _TRIP_MAX = 0.60, 0.05, 0.15


def mixed_day_kind(r) -> dict:
    """ชนิดของ DailyJob แถวเดียวสำหรับ lcb_mixed (ใช้แสดงป้ายในตารางเรียงวันที่).

    คืน {kind, label, awaiting_price, abnormal}:
      kind = mao | trip | idle ; abnormal=True ถ้า rev>0 แต่ ratio อยู่กลาง (ต้องตรวจ)
    """
    rev = r.revenue_customer or 0.0
    fee = r.trip_fee_driver or 0.0
    if rev > 0:
        ratio = fee / rev
        if abs(ratio - _MAO_RATIO) <= _MAO_TOL:
            return {"kind": "mao", "label": "เหมา", "awaiting_price": False, "abnormal": False}
        return {
            "kind": "trip",
            "label": "เที่ยว",
            "awaiting_price": False,
            "abnormal": ratio >= _TRIP_MAX,
        }
    has_route = bool(
        (r.origin or "").strip()
        or (r.destination or "").strip()
        or (r.customer_name_raw or "").strip()
    )
    return {
        "kind": "idle",
        "label": "รอลงราคา" if has_route else ((r.status_code or "").strip() or "รถจอด"),
        "awaiting_price": has_route,
        "abnormal": False,
    }


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

    # --- น้ำมัน: แยกให้ชัดว่าหัก / ไม่หัก (กันคนขับเข้าใจผิดว่าหักทั้งหมด) ---
    # บิลที่ exclude_from_driver=True (ถังแรกไม่หัก / น้ำมันก่อนเริ่มวิ่ง) → ไม่หัก
    # บิล mao_tank_measure (daily_job_id=None) → "วัดถัง" หักจริง แต่ไม่โผล่ในตารางเดลี่
    fuel_excluded_amt = round(sum((f.amount or 0.0) for f in fuel_rows if f.exclude_from_driver), 2)
    fuel_deducted_amt = round(sum((f.amount or 0.0) for f in fuel_rows if not f.exclude_from_driver), 2)
    fuel_deducted_liter = round(sum((f.liter or 0.0) for f in fuel_rows if not f.exclude_from_driver), 2)
    # น้ำมัน "นอกตาราง" — บิลพิเศษที่หักจริงแต่ไม่โผล่ในคอลัมน์น้ำมันของตารางเดลี่
    # (เพราะตารางอ่าน DailyJob.fuel_amount; บิลพวกนี้เป็น FuelTxn ที่ job มี fuel_amount=0):
    #   mao_tank_measure = วัดถังตอนเริ่มเหมา ; handover_measure/handover_manual =
    #   วัดน้ำมัน/น้ำมันในถังตอนคนมาขับแทน-รับรถคืน ; manual = ยกยอด/ทำคืนน้ำมันตัดรอบ
    #   (โอลงมือในชีท — ผูก daily_job_id ของเที่ยวจริงแต่ job นั้น fuel_amount=0).
    _OFFTABLE_FUEL = ("tank_measure", "handover", "manual")
    # job ที่โชว์น้ำมันในตารางอยู่แล้ว (fuel_amount>0) → กันบิล off-table ซ้ำซ้อน
    _jobs_with_table_fuel = {r.id for r in daily_jobs if (r.fuel_amount or 0) > 0}
    tank_measure_rows = sorted(
        (
            {"txn_date": f.txn_date, "liter": f.liter or 0.0, "amount": f.amount or 0.0,
             "note": (f.note or "วัดถัง")}
            for f in fuel_rows
            if any(k in (f.source or "") for k in _OFFTABLE_FUEL)
            and (f.daily_job_id is None or f.daily_job_id not in _jobs_with_table_fuel)
        ),
        key=lambda r: r["txn_date"],  # เรียงตามวันที่ (ส่งมอบ/คืน ก่อน รับคืน/หัก ตามจริง)
    )
    # daily_job_id ที่ผูกบิล "ไม่หัก" → mark บรรทัดในตาราง
    excluded_job_ids = {f.daily_job_id for f in fuel_rows if f.exclude_from_driver and f.daily_job_id}

    fuel_grade_by_job = {
        f.daily_job_id: f.fuel_grade
        for f in fuel_rows
        if f.daily_job_id and f.fuel_grade
    }

    # --- โชว์น้ำมันตาม "วันที่เติมจริง" (FuelTxn.txn_date) บนสลิป (แสดงผลอย่างเดียว) ---
    # โอสั่ง 30มิ.ย.: คนคีย์มักผูกบิลที่เติม "เมื่อวาน" ไว้กับงานวันนี้ (เคสจริง LCB มิ.ย.
    # = 74/384 บิล txn_date = work_date − 1 วัน) → สลิปเดิมโชว์ผิดวัน. ปั๊มยังออกบิลแยก
    # B7 + B20 ในการเติมครั้งเดียว ลงคนละ DailyJob อีก. แก้ทั้งสองด้วยการ group ตาม
    # "วันเติมจริง": บิลในตาราง (มี daily_job_id) group ตาม txn_date ต่อคน → anchor =
    # แถวงานที่ work_date == txn_date (วันเติมจริง); ถ้าไม่มี ใช้แถวบนสุดของกลุ่ม.
    # anchor ถือ list บรรทัดย่อย [{liter, amount, grade, excluded}] (โชว์ซ้อนในเซลล์เดียว),
    # job อื่นในกลุ่ม → [] (เว้นช่อง). ผลรวมคอลัมน์น้ำมัน + fuel_cost_self ไม่เปลี่ยน.
    _dj_order = {r.id: i for i, r in enumerate(daily_jobs)}
    _work_date_to_job = {}   # work_date → job id (แรกสุดตามลำดับแสดงผล)
    for r in daily_jobs:
        _work_date_to_job.setdefault(r.work_date, r.id)
    _fill_groups: dict[Any, list] = {}
    for f in fuel_rows:
        if f.daily_job_id and f.daily_job_id in _dj_order:
            _fill_groups.setdefault(f.txn_date, []).append(f)
    fuel_lines_by_job: dict[int, list] = {}
    for _fill_date, _txns in _fill_groups.items():
        _job_ids = list(dict.fromkeys(t.daily_job_id for t in _txns))  # ลำดับ + ไม่ซ้ำ
        # anchor = แถวงานวันเติมจริง ถ้ามีในตาราง, ไม่งั้นแถวบนสุดของกลุ่ม
        if _fill_date in _work_date_to_job:
            anchor = _work_date_to_job[_fill_date]
        else:
            anchor = min(_job_ids, key=lambda j: _dj_order[j])
        # ต้องจัดกลุ่มเมื่อ: หลายบิล (B7+B20) หรือ บิลผูกผิดวัน (anchor ≠ job ที่บิลผูก)
        if len(_job_ids) < 2 and _job_ids[0] == anchor:
            continue  # เติมจุดเดียว ตรงวัน → โชว์ปกติ (fallback r.fuel_*)
        _txns_sorted = sorted(_txns, key=lambda t: (t.txn_date, t.id or 0))
        fuel_lines_by_job[anchor] = [
            {"liter": t.liter or 0.0, "amount": t.amount or 0.0,
             "grade": t.fuel_grade or "", "excluded": bool(t.exclude_from_driver)}
            for t in _txns_sorted
        ]
        for j in _job_ids:
            if j != anchor:
                fuel_lines_by_job[j] = []   # merged: เว้นช่อง

    plates = sorted({r.plate_no_raw for r in daily_jobs if r.plate_no_raw})
    plates_used = ", ".join(plates) if plates else ""

    miles = [r.mile_snapshot for r in daily_jobs if (r.mile_snapshot or 0) > 0]
    mile_start = min(miles) if miles else 0
    mile_end = max(miles) if miles else 0
    km_run = (mile_end - mile_start) if mile_start and mile_end and mile_end > mile_start else 0
    fuel_used_l = sum((r.liter or 0) for r in fuel_rows) or sum((r.fuel_liter or 0) for r in daily_jobs)
    avg_km_per_l = (km_run / fuel_used_l) if (km_run > 0 and fuel_used_l > 0) else 0

    # --- แถว "เติมน้ำมัน แต่ไม่มีงาน" (กันคนขับงงว่าทำไมวันไม่วิ่งมีน้ำมัน) ---
    # คนคีย์ลงการเติมน้ำมันเป็น DailyJob แยกแถว (work_date = วันไปเติม) โดยไม่มี route/ค่าเที่ยว/ค่าขนส่ง.
    # บอกคนขับว่าน้ำมันบรรทัดนี้คืออะไร โดยใช้ลำดับความเชื่อถือ:
    #   1) fuel_date (วันเติม ที่คนคีย์กรอก คอลัมน์ AC) — แม่นสุด ถ้ามี
    #   2) ไมล์ตรงกับวันที่วิ่งจริง — ใช้เดาว่า "สำหรับงานวันที่ ..." (กรณี DB เก่ายังไม่มี fuel_date)
    def _has_work(r) -> bool:
        return bool(
            (r.origin or "").strip() or (r.destination or "").strip()
            or (r.customer_name_raw or "").strip()
            or (r.trip_fee_driver or 0) or (r.revenue_customer or 0)
        )

    # จำนวน "เที่ยววิ่งจริง" สำหรับหัวสลิป — นับเฉพาะแถวที่มีงานจริง (route/ค่าเที่ยว/รายได้)
    # ตัด รถจอด / ลา / รถซ่อม / วันเติมน้ำมันล้วน ออก (โอ: หน่วยเที่ยวมีประโยชน์กว่าจำนวนบรรทัด).
    # วันเดียววิ่งหลายเที่ยว = หลาย DailyJob → นับแยกตามจริง.
    # NB: วันลาบางแถวบันทึกเป็น origin='ลา' (ไม่มี leave_status) + status "ลา / ไม่พร้อม"
    #     → _has_work=True (origin ไม่ว่าง) จะนับผิด ต้องกันด้วย status_code ของวันหยุด/ลาด้วย.
    _IDLE_STATUS = {"รถจอด", "ลา / ไม่พร้อม", "ลา", "รถซ่อม", "รถอุบัติเหตุ"}

    def _is_trip(r) -> bool:
        if (getattr(r, "leave_status", "") or "") == "leave":
            return False
        if (getattr(r, "status_code", "") or "").strip() in _IDLE_STATUS:
            return False
        return _has_work(r)

    trip_count = sum(1 for r in daily_jobs if _is_trip(r))

    # ค่าพิเศษ / OT / รับตู้คืนตู้ แตกตามแถว (job) — โชว้ในรายการวิ่งงานว่ามาจากเที่ยวไหน
    # (โอ 1ก.ค.: เดิมโชว้แค่ก้อนรวมในสรุปเงิน ไม่รู้มาจากไหน). reserve fees (ยกตู้/ผ่านลาน/
    # คลีน/ชอร์/เข้าท่า/ชั่ง) = เงินบริษัท ไม่นับ — ใช้ classify_driver_fee ตัวเดียวกับ engine.
    from services.payroll import classify_driver_fee
    driver_fees_by_job: dict[int, dict] = {}
    _job_ids_in_table = [r.id for r in daily_jobs]
    if _job_ids_in_table:
        _fee_rows = session.exec(
            select(DailyJobFee).where(DailyJobFee.daily_job_id.in_(_job_ids_in_table))
        ).all()
        for f in _fee_rows:
            bucket = classify_driver_fee(f.fee_type)
            if not bucket or not (f.amount or 0):
                continue
            d = driver_fees_by_job.setdefault(f.daily_job_id, {})
            d[bucket] = round(d.get(bucket, 0.0) + (f.amount or 0.0), 2)

    fuel_only_info: dict[int, dict] = {}
    for r in daily_jobs:
        has_fuel = (r.fuel_amount or 0) or (r.fuel_liter or 0)
        if has_fuel and not _has_work(r):
            fill_date = r.fuel_date  # วันเติมที่คนคีย์กรอกจริง (ถ้ามี)
            for_date = None
            if (r.mile_snapshot or 0) > 0:
                match = next(
                    (d for d in daily_jobs
                     if d.id != r.id and d.mile_snapshot == r.mile_snapshot and _has_work(d)),
                    None,
                )
                if match:
                    for_date = match.work_date
            fuel_only_info[r.id] = {"fill_date": fill_date, "for_date": for_date}

    # รายการ "ไม่หัก" ในรอบเดียวกัน (เบิกที่ไม่หัก / รับเข้า) — สำหรับโชว์เพิ่ม
    # (ติ๊กซ่อนได้ ไม่กระทบยอดหัก). ไม่รวมตัวที่หักอยู่แล้วใน petty_rows.
    petty_extra_rows = session.exec(
        select(PettyCashTxn).where(
            PettyCashTxn.driver_id == emp.id,
            PettyCashTxn.pay_cycle_tag == tag,
            or_(
                PettyCashTxn.deduct_from_driver == False,  # noqa: E712
                PettyCashTxn.deduction_status != "pending",
            ),
            or_(
                PettyCashTxn.site_code == pr.site_code,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            ),
        ).order_by(PettyCashTxn.txn_date)
    ).all()

    _CAT_LABEL = {"driver_advance": "เงินเบิก", "other": "อื่นๆ", "": "อื่นๆ"}

    def _mk_line(p, amt, deducted):
        cat_label = _CAT_LABEL.get(p.category or "", p.category or "เงินเบิก")
        # โอ 1ก.ค.: ยังไม่จัดหมวด → ซ่อนชื่อหมวดนำ (กัน "เงินเบิก · เงินเบิก" ซ้ำ),
        # โชว้รายละเอียด (memo) เต็มๆ ไม่ตัด …; ถ้าไม่มี memo ใช้ชื่อหมวดเป็น label.
        # (ตัด memo ระบบที่ขึ้นต้นด้วยชื่อคนขับ/"รวมหักช่อง" ออก — คนขับไม่ต้องเห็น)
        memo = (p.memo or "").strip()
        sys_memo = ("รวมหัก" in memo) or ("ช่อง O" in memo) or ("สดย่อย" in memo)
        label = memo if (memo and not sys_memo) else cat_label
        return {
            "txn_date": p.txn_date,
            "label": label,
            "amount": amt,
            "category": p.category or "other",
            "category_label": _CAT_LABEL.get(p.category or "", p.category or "อื่นๆ"),
            "direction": p.direction,
            "deducted": deducted,
        }

    petty_lines = []
    for p in petty_rows:
        amt = p.deduct_amount if (p.deduct_amount or 0) > 0 else (p.amount or 0)
        if not amt:
            continue
        petty_lines.append(_mk_line(p, amt, True))

    petty_lines_extra = []
    for p in petty_extra_rows:
        amt = p.amount or 0
        if not amt:
            continue
        petty_lines_extra.append(_mk_line(p, amt, False))

    # หมวดที่มีจริง (สำหรับ checkbox) จากทั้งสองชุด
    petty_categories = sorted({
        (ln["category"], ln["category_label"])
        for ln in (petty_lines + petty_lines_extra)
    })

    mixed = classify_mixed_days(daily_jobs) if emp.pay_mode == "lcb_mixed" else None

    # วันที่หักน้ำมัน (ใช้ logic เดียวกับ engine เพื่อให้สลิปป้าย 'หัก' ตรงกับเงินจริง):
    # วันเหมา + วันรถจอด 'ช่วงเหมา'. import แบบ lazy กันวงกลม.
    fuel_deduct_dates: set = set()
    if emp.pay_mode == "lcb_mixed":
        from services.payroll import _classify_lcb_days, _idle_dates_in_mao_phase
        split = _classify_lcb_days(session, emp.id, start, end, site_code=pr.site_code)
        fuel_deduct_dates = {d.work_date for d in split["mao_days"]} | _idle_dates_in_mao_phase(split)

    return {
        "run": pr,
        "employee": emp,
        "item": item,
        "daily_jobs": daily_jobs,
        "mixed": mixed,
        "route_text": delivery_route_text,
        "route_cell": slip_route_cell,      # ช่องส่งสินค้า: route หรือ status (ไม่มี remark)
        "route_remark": slip_route_remark,  # remark ที่ปลอดภัยจะโชว์ (ตัดโน้ตภายใน [...])
        "day_kind": mixed_day_kind,
        "fuel_deduct_dates": fuel_deduct_dates,
        "fuel_excluded_amt": fuel_excluded_amt,
        "fuel_deducted_amt": fuel_deducted_amt,
        "fuel_deducted_liter": fuel_deducted_liter,
        "tank_measure_rows": tank_measure_rows,
        "excluded_job_ids": excluded_job_ids,
        "fuel_grade_by_job": fuel_grade_by_job,
        "fuel_lines_by_job": fuel_lines_by_job,
        "trip_count": trip_count,
        "driver_fees_by_job": driver_fees_by_job,
        "fuel_only_info": fuel_only_info,
        "petty_lines": petty_lines,
        "petty_lines_extra": petty_lines_extra,
        "petty_categories": petty_categories,
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
