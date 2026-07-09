"""
Project YK - One Platform (Phase 1.1)
Master Data + expanded Daily module.
Stack: FastAPI + SQLite (local) / PostgreSQL (DATABASE_URL) + HTMX + Tailwind CDN.
Run:   double-click start.bat  (or)  python main.py
URL:   http://localhost:8000
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlmodel import Session, SQLModel, select

from db_config import APP_DIR, DB_PATH, engine, resolve_database_url
from preview_auth import PreviewAuthMiddleware

import models
from models import (
    AccidentCase,
    AccidentInstallment,
    AppSetting,
    AppUser,
    BigcBranch,
    Customer,
    DailyJob,
    DailyJobFee,
    DispatchPlan,
    DispatchPlanAudit,
    DispatchPlanLine,
    DealRecord,
    DriverDeposit,
    DriverSession,
    DriverSubmission,
    AccessLink,
    Employee,
    FuelPriceIndex,
    FuelSurchargeBand,
    FuelTxn,
    ImportLog,
    InboxEmail,
    InboxSyncRun,
    AiChatLog,
    ArSettle,
    KbRule,
    KbSettle,
    LeaveRecord,
    TodoItem,
    TodoSuggest,
    Loan,
    LoanPayment,
    MaintInspection,
    MaintInspectionItem,
    MaintPart,
    MaintRecord,
    Part,
    PayCycle,
    PayRun,
    PayRunItem,
    PayAdjustment,
    PettyCashTxn,
    PlaceCache,
    PmPlan,
    Quotation,
    QuotationAudit,
    RateCard,
    SchemaInfo,
    StockTxn,
    Tire,
    TireEvent,
    Vehicle,
    VehicleSpec,
    Vendor,
    VendorPrice,
)
from services.email_oauth import (
    build_authorize_url,
    exchange_code_for_tokens,
    load_google_refresh_token,
    new_oauth_state,
    oauth_client_config,
    save_google_refresh_token,
)
from services.email_ingest import classify_email_item, get_inbox_scope, sync_inbox

SCHEMA_VERSION = 48  # v48: Tire.tire_type+removal_reason, TireEvent.reason_code (ALTER — ระบบยางหยุดเลือด: คีย์บิล+รายงานหล่อ/แท้); v47: DealRecord+PlaceCache (โต๊ะเช็คดีล /quote/deal — create_all); v46: TodoSuggest (เฟส 4 กล่องรอคัดจากไลน์ — create_all); v45: AiChatLog (เฟส 3 /ai — create_all); v44: MediaArchive (G2 — create_all); v43: DocTemplate+DocIssue (A2 — create_all); v42: Vehicle.tank_liters (ALTER); v41: JobMedia; v40: LineGroupMap+LineJobSeen; v39: PartPermission; v38: DebtAccount; v37: AuditLog
DATABASE_URL, IS_SQLITE = resolve_database_url()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


def _fmt_dmy(value, sep: str = "/") -> str:
    """Format a date/datetime/ISO-string as dd/mm/yyyy (CE).
    Used as Jinja filter `dmy` so every list/table can render Thai-friendly dates.
    """
    if value is None or value == "":
        return ""
    try:
        if isinstance(value, datetime):
            d = value.date()
        elif isinstance(value, date):
            d = value
        else:
            text = str(value).strip()
            if not text:
                return ""
            d = date.fromisoformat(text[:10])
        return f"{d.day:02d}{sep}{d.month:02d}{sep}{d.year:04d}"
    except Exception:
        return str(value)


def _to_ict(dt: datetime) -> datetime:
    """Shift a stored UTC datetime to Thai local time (ICT, UTC+7) for display.

    All timestamps in this app are stored via datetime.utcnow() (naive UTC).
    Thai users read them as local time, so convert for presentation only.
    A tz-aware value is converted properly; a naive value is assumed UTC.
    """
    ict = timezone(timedelta(hours=7))
    if dt.tzinfo is not None:
        return dt.astimezone(ict)
    return dt + timedelta(hours=7)


def _fmt_dmy_hm(value) -> str:
    """Format a datetime as dd/mm/yyyy HH:MM (Thai local time, CE)."""
    if value is None or value == "":
        return ""
    try:
        if isinstance(value, datetime):
            dt = _to_ict(value)
            return f"{dt.day:02d}/{dt.month:02d}/{dt.year:04d} {dt.strftime('%H:%M')}"
        if isinstance(value, date):
            return _fmt_dmy(value)
        text = str(value).strip()
        if not text:
            return ""
        # try ISO datetime
        try:
            dt = _to_ict(datetime.fromisoformat(text.replace("Z", "")))
            return f"{dt.day:02d}/{dt.month:02d}/{dt.year:04d} {dt.strftime('%H:%M')}"
        except Exception:
            return _fmt_dmy(text)
    except Exception:
        return str(value)


DEPOSIT_INSTALL_UNIT = 1000.0  # เงินประกันตนหักงวดละ 1,000 (มาตรฐาน ตรงกับชีต SSO)


def _dep_install_unit(emp) -> float:
    """งวดละเท่าไหร่สำหรับคนนี้ — มาตรฐาน 1,000; บางคนตกลงอื่น (เช่น ธัชชนพล 2,000)
    ตั้งผ่าน custom_terms {"deposit_install_unit": 2000}. ตรงกับ engine payroll."""
    raw = getattr(emp, "custom_terms", "") or ""
    try:
        obj = json.loads(raw) if raw else {}
        u = obj.get("deposit_install_unit") if isinstance(obj, dict) else None
        if u:
            return float(u)
    except Exception:
        pass
    return DEPOSIT_INSTALL_UNIT


def _fmt_dep_install(emp) -> str:
    """งวดเงินประกันตน 'X/Y' — X = **งวดที่กำลังหักรอบนี้** (ไม่ใช่งวดสะสม).

    deposit_balance = ยอดที่จ่ายไปแล้ว 'ก่อน' รอบนี้ = (งวดก่อน)×งวดละ.
    ถ้ายังผ่อนไม่หมด (bal<tgt) งวดที่กำลังหัก = bal//งวดละ + 1 (เช่น bal 0 → หักงวด 1/10).
    ถ้าผ่อนหมดแล้ว (bal>=tgt) โชว์ Y/Y (งวดสุดท้าย จ่ายครบ). คืน '' เมื่อไม่มีเพดาน.
    งวดละเป็นต่อคน (ธัชชนพล 2,000) ตรงกับ engine ผ่าน custom_terms."""
    if emp is None:
        return ""
    tgt = getattr(emp, "deposit_target", 0) or 0
    if tgt <= 0:
        return ""
    unit = _dep_install_unit(emp)
    bal = getattr(emp, "deposit_balance", 0) or 0
    total = int(round(tgt / unit))
    paid = int(round(bal / unit))
    # deposit_hold = พักหักรอบนี้ → โชว์งวดที่จ่ายแล้ว (ไม่ +1 เพราะรอบนี้ไม่หัก)
    held = False
    try:
        raw = getattr(emp, "custom_terms", "") or ""
        held = bool(json.loads(raw).get("deposit_hold")) if raw else False
    except Exception:
        held = False
    if held:
        current = min(paid, total)
    else:
        current = paid + 1 if paid < total else total   # งวดที่กำลังหัก (จ่ายหมดแล้ว=งวดสุดท้าย)
    return f"{current}/{total}"


templates.env.filters["dmy"] = _fmt_dmy
templates.env.filters["dmy_hm"] = _fmt_dmy_hm
templates.env.filters["dep_install"] = _fmt_dep_install


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _month_range_str(month: str) -> tuple[Optional[date], Optional[date]]:
    """'YYYY-MM' → (วันแรก, วันสุดท้าย) ของเดือนนั้น; ค่าว่าง/ผิดรูป → (None, None).
    ใช้ _month_bounds(year, month) ที่มีอยู่แล้วในไฟล์นี้."""
    try:
        y, m = (int(x) for x in month.split("-"))
        return _month_bounds(y, m)
    except (ValueError, AttributeError):
        return None, None


def _parse_float(value: str) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_int(value: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_bool(value: Optional[str]) -> bool:
    return value in ("1", "true", "on", "yes")


def _reports_root() -> Path:
    """Workspace-level reports directory (../reports from app/)."""
    return APP_DIR.parents[1] / "reports"


def _write_unresolved_case_report(
    *,
    run_id: int,
    site_code: str,
    cycle_tag: str,
    reason: str,
    payload: dict,
    next_action: str,
) -> dict:
    """Write unresolved queue entry + repeat-fail marker under reports/.

    Returns metadata for caller logging/debug:
      {"report_path": "...", "is_repeated_fail": bool, "pending_note_path": "...|''"}
    """
    out_dir = _reports_root() / "payroll_unresolved_queue"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_reason = re.sub(r"[^a-z0-9_]+", "_", (reason or "").strip().lower()).strip("_") or "unknown"
    report_path = out_dir / f"{ts}_{site_code}_{cycle_tag}_run{run_id}_{safe_reason}.json"
    report_obj = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds"),
        "run_id": run_id,
        "site_code": site_code,
        "cycle_tag": cycle_tag,
        "reason": reason,
        "payload": payload,
        "next_action": next_action,
    }
    report_path.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    history = sorted(out_dir.glob(f"*_{site_code}_{cycle_tag}_run{run_id}_{safe_reason}.json"))
    is_repeated_fail = len(history) >= 2
    pending_note_path = ""
    if is_repeated_fail:
        pending_md = out_dir / f"PENDING_MORNING_{site_code}_{cycle_tag}_run{run_id}_{safe_reason}.md"
        pending_md.write_text(
            "\n".join(
                [
                    f"# Pending (Morning) - {site_code} run {run_id}",
                    "",
                    f"- reason: {reason}",
                    f"- repeated_fail_count: {len(history)}",
                    f"- latest_report: {report_path}",
                    f"- next_action: {next_action}",
                    "",
                    "## Notes",
                    "- This case failed repeatedly in the same reason class.",
                    "- Follow policy: stop looping and continue other tasks.",
                ]
            ),
            encoding="utf-8",
        )
        pending_note_path = str(pending_md)

    return {
        "report_path": str(report_path),
        "is_repeated_fail": is_repeated_fail,
        "pending_note_path": pending_note_path,
    }


def _gen_next_code(session: Session, model, prefix: str, width: int = 4) -> str:
    """Generate next sequential code like E0001, C0001."""
    rows = session.exec(select(model)).all()
    used_numbers: list[int] = []
    for r in rows:
        code = (getattr(r, "code", "") or "")
        if code.startswith(prefix):
            tail = code[len(prefix):]
            if tail.isdigit():
                used_numbers.append(int(tail))
    next_num = (max(used_numbers) + 1) if used_numbers else 1
    return f"{prefix}{next_num:0{width}d}"


def _ensure_column(table: str, column: str, coltype: str, default: Optional[str] = None) -> None:
    """Add column if missing. SQLite ALTER TABLE ADD COLUMN is safe & non-destructive."""
    if not IS_SQLITE:
        return
    with engine.begin() as conn:
        info = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        existing = [r[1] for r in info]
        if column in existing:
            return
        default_sql = ""
        if default is not None:
            if default == "" or isinstance(default, str) and not default.replace(".", "").replace("-", "").isdigit():
                default_sql = f" DEFAULT '{default}'"
            else:
                default_sql = f" DEFAULT {default}"
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}{default_sql}")


def _drop_not_null(table: str, column: str) -> None:
    """Relax a NOT NULL constraint on an existing SQLite column.

    SQLite cannot ALTER a column to drop NOT NULL, so we rebuild the table
    (recommended 12-step pattern, simplified): recreate from the live SQLModel
    schema, copy all current columns over, swap. Idempotent — no-op if the
    column is already nullable. Runs inside one transaction so a failure leaves
    the original table intact.
    """
    if not IS_SQLITE:
        return
    with engine.begin() as conn:
        info = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        col = next((r for r in info if r[1] == column), None)
        if col is None or col[3] == 0:   # r[3] == notnull flag; 0 = already nullable
            return
        cols = [r[1] for r in info]
        collist = ", ".join(cols)
        tmp = f"{table}__rebuild"
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {tmp}")
        # Build the fresh (nullable) table from the current SQLModel metadata.
        target = SQLModel.metadata.tables[table]
        from sqlalchemy.schema import CreateTable
        create_sql = str(CreateTable(target).compile(conn)).strip().rstrip(";")
        create_sql = create_sql.replace(f"CREATE TABLE {table}", f"CREATE TABLE {tmp}", 1)
        conn.exec_driver_sql(create_sql)
        conn.exec_driver_sql(f"INSERT INTO {tmp} ({collist}) SELECT {collist} FROM {table}")
        conn.exec_driver_sql(f"DROP TABLE {table}")
        conn.exec_driver_sql(f"ALTER TABLE {tmp} RENAME TO {table}")
        # Recreate indexes (CreateTable does not emit CREATE INDEX).
        from sqlalchemy.schema import CreateIndex
        for ix in target.indexes:
            conn.exec_driver_sql(str(CreateIndex(ix).compile(conn)).strip().rstrip(";"))


def _apply_additive_migrations() -> None:
    """Non-destructive migrations run every startup. Safe to re-run."""
    # v5 → v6: Employee.role — default 'driver' keeps existing rows as drivers.
    _ensure_column("employee", "role", "TEXT", default="driver")

    # v41 → v42 (E2): ขนาดถังน้ำมันต่อคัน (0 = ใช้ default ตามชนิดรถ)
    _ensure_column("vehicle", "tank_liters", "REAL", default="0")

    # v47 → v48: ระบบยาง "หยุดเลือด" — ประเภทยาง(หล่อ/แท้)+เหตุถอด
    _ensure_column("tire",      "tire_type",      "TEXT", default="new")
    _ensure_column("tire",      "removal_reason", "TEXT", default="")
    _ensure_column("tireevent", "reason_code",    "TEXT", default="")

    # v6 → v7: PayRunItem BIGC audit columns + PayRunAdjust table (created via
    # SQLModel.metadata.create_all; nothing ALTER-wise needed for new table).
    _ensure_column("payrunitem", "fuel_budget_liter",   "REAL", default="0")
    _ensure_column("payrunitem", "fuel_consumed_liter", "REAL", default="0")
    _ensure_column("payrunitem", "fuel_residual_liter", "REAL", default="0")

    # v7 → v8: Maintenance module tables (Vendor, Part, StockTxn, MaintRecord,
    # MaintPart, Tire, TireEvent, PmPlan) — all created by SQLModel.create_all.

    # v8 → v9: RateCard table (Rate Book + auto-learn) — created by SQLModel.create_all.

    # v9 → v10: Vehicle enrichment + PmPlan active tracking + new tables (VendorPrice,
    #           VehicleSpec, MaintInspection, MaintInspectionItem — created by create_all)
    _ensure_column("vehicle", "nickname",     "TEXT",  default="")
    _ensure_column("vehicle", "old_plate_no", "TEXT",  default="")
    _ensure_column("vehicle", "brand",        "TEXT",  default="")
    _ensure_column("vehicle", "model",        "TEXT",  default="")
    _ensure_column("vehicle", "engine_no",    "TEXT",  default="")
    _ensure_column("vehicle", "chassis_no",   "TEXT",  default="")
    _ensure_column("vehicle", "current_mile", "REAL",  default="0")
    _ensure_column("pmplan",  "fluid_kind",      "TEXT", default="other")
    _ensure_column("pmplan",  "alert_km_before", "REAL", default="1000")

    # v10 → v11: FuelPriceIndex + FuelSurchargeBand (created by create_all, no ALTER needed)

    # v11 → v12: DailyJob.source — track import vs UI for safe re-import wipes
    _ensure_column("dailyjob", "source", "TEXT", default="")

    # v12 → v13: Loan + LoanPayment (CFO Dashboard). New tables created by create_all.

    # v13 → v14: Driver PWA — Employee.pin_hash + DriverSession + DriverSubmission
    _ensure_column("employee", "pin_hash", "TEXT", default="")
    _ensure_column("employee", "pin_set_at", "TEXT", default=None)
    # v14 → v15: payroll explicit income-tax field (for catch-up audit)
    _ensure_column("payrunitem", "income_tax_withholding", "REAL", default="0")

    # PayRunAdjust additional manual-override columns (v15)
    _ensure_column("payrunadjust", "days_worked_override", "REAL")
    _ensure_column("payrunadjust", "days_leave_override", "REAL")
    _ensure_column("payrunadjust", "days_absent_override", "REAL")
    _ensure_column("payrunadjust", "ss_rate_override", "REAL")
    _ensure_column("payrunadjust", "ss_base_min_override", "REAL")
    _ensure_column("payrunadjust", "ss_base_max_override", "REAL")
    # PayRun-level SS overrides (apply to whole run when set)
    _ensure_column("payrun", "ss_rate", "REAL")
    _ensure_column("payrun", "ss_base_min", "REAL")
    _ensure_column("payrun", "ss_base_max", "REAL")
    # v16: InboxEmail / InboxSyncRun tables for IMAP ingestion are create_all-only.
    # v17: Employee.pay_cycle_policy for driver-policy-first cycle resolution.
    _ensure_column("employee", "pay_cycle_policy", "TEXT", default="site_default")
    # v20: PettyCashTxn LINE-slip provenance (lcb-slip-reader phase)
    _ensure_column("pettycashtxn", "slip_line_message_id", "TEXT", default="")
    _ensure_column("pettycashtxn", "slip_media_path", "TEXT", default="")
    _ensure_column("pettycashtxn", "slip_ref_code", "TEXT", default="")

    # v20 → v21: TireEvent magic-link fields + AccessLink table (table via create_all).
    _ensure_column("tireevent", "photo_paths",    "TEXT", default="")
    _ensure_column("tireevent", "actor_name",     "TEXT", default="")
    _ensure_column("tireevent", "actor_role",     "TEXT", default="")
    _ensure_column("tireevent", "condition_flag", "TEXT", default="")
    # Magic-link weekly checks have no Employee → relax legacy NOT NULL on employee_id.
    _drop_not_null("driversubmission", "employee_id")

    # v21 → v22: short code for /c/<code> magic-link URLs.
    _ensure_column("accesslink", "short_code", "TEXT", default="")

    # v22 → v23: AppSetting key/value table (slip-reader on/off control) — created
    # by create_all(); no ALTER needed. Version bumped for the record.

    # v24 → v25: DailyJob KB (ใต้โต๊ะ) + ราคากลาง override. KbRule table via create_all.
    _ensure_column("dailyjob", "kb_amount", "REAL", default="0")
    _ensure_column("dailyjob", "price_override", "REAL")  # nullable, no default

    # v25 → v26: FuelTxn per-bill no-deduct flag (น้ำมันก่อนเริ่มวิ่ง / ถังเต็มแรก).
    _ensure_column("fueltxn", "exclude_from_driver", "BOOLEAN", default="0")

    # v26 → v27: เลขบัญชีโอนเงินเดือน + หมายเหตุหน้าโอนเงิน.
    _ensure_column("employee", "bank_name", "TEXT", default="")
    _ensure_column("employee", "account_no", "TEXT", default="")
    _ensure_column("payrunitem", "transfer_note", "TEXT", default="")

    # v28 → v29: แตกเงินคนขับ LCB (พิเศษ/OT/รับตู้แทน) เป็น field แยก เพื่อโชว์ในตาราง/สลิป.
    # ค่าเหล่านี้เป็น subset ของ other_income อยู่แล้ว (ไม่บวกซ้ำ) — recompute รอบ draft เพื่อเติมค่า.
    _ensure_column("payrunitem", "special_income", "REAL", default="0")
    _ensure_column("payrunitem", "ot_income", "REAL", default="0")
    _ensure_column("payrunitem", "pickup_return_income", "REAL", default="0")

    # v29 → v30: DailyJob ช่องอ้างอิงเพิ่มจากชีท (โชว์เป็นคอลัมน์แยกในหน้าเดลี่).
    # ทั้งหมด display/อ้างอิง ไม่กระทบสูตรเงิน. weighing(ค่าชั่งน้ำหนัก) ใช้ DailyJobFee ไม่ใช่คอลัมน์.
    _ensure_column("dailyjob", "phone", "TEXT", default="")
    _ensure_column("dailyjob", "shared_vehicle", "TEXT", default="")
    _ensure_column("dailyjob", "receive_inv_no", "TEXT", default="")
    _ensure_column("dailyjob", "bl_booking", "TEXT", default="")
    _ensure_column("dailyjob", "fuel_date", "DATE")  # nullable
    _ensure_column("dailyjob", "gps_rate", "REAL", default="0")

    # v30 → v31: FuelTxn เกรดน้ำมัน B7/B20 (ป้ายเกรดเท่านั้น ไม่กระทบสูตรเงิน).
    _ensure_column("fueltxn", "fuel_grade", "TEXT", default="")


def init_db() -> None:
    """Safe, additive init. Never drops existing data.

    - `create_all` adds any new tables that don't exist yet.
    - `_apply_additive_migrations` runs ALTER TABLE ADD COLUMN for new fields.
    - If we ever need a destructive migration, do it in an explicit tool script
      (e.g. `tools/reset_db.py`) rather than on app startup.
    """
    SQLModel.metadata.create_all(engine)
    if IS_SQLITE:
        _apply_additive_migrations()
    with Session(engine) as s:
        current = s.exec(select(SchemaInfo)).first()
        if current is None:
            s.add(SchemaInfo(version=SCHEMA_VERSION))
            s.commit()
        elif current.version != SCHEMA_VERSION:
            current.version = SCHEMA_VERSION
            current.applied_at = datetime.utcnow()
            s.commit()
        seed_initial_data(s)


def seed_kb_rules(s: Session) -> None:
    """Seed default KB rules ต่อ status_code. Idempotent — เพิ่มเฉพาะที่ยังไม่มี."""
    defaults = [
        KbRule(status_code="NHL", default_kb=110.0, required=False),
        KbRule(status_code="MOL", default_kb=100.0, required=False),
        KbRule(status_code="CY",  default_kb=0.0,   required=True),
    ]
    for rule in defaults:
        existing = s.exec(select(KbRule).where(KbRule.status_code == rule.status_code)).first()
        if not existing:
            s.add(rule)
    s.commit()


def seed_initial_data(s: Session) -> None:
    defaults = [
        PayCycle(site_code="AYU", cycle_start_day=26, cycle_end_day=25,
                 pay_rule="จ่ายสิ้นเดือน",
                 notes="รอบ 26 → 25 ของเดือนถัดไป"),
        PayCycle(site_code="BIGC", cycle_start_day=1, cycle_end_day=-1,
                 pay_rule="จ่ายวันที่ 1 ของเดือนถัดไป",
                 notes="รอบ 1 → วันสุดท้ายของเดือน (ค้าง 1 เดือน)"),
        PayCycle(site_code="LCB", cycle_start_day=16, cycle_end_day=15,
                 pay_rule="จ่ายวันที่ 1 ของเดือนถัดไป",
                 notes="รอบ 16 → 15 ของเดือนถัดไป"),
    ]
    for pc in defaults:
        existing = s.exec(select(PayCycle).where(PayCycle.site_code == pc.site_code)).first()
        if not existing:
            s.add(pc)
    s.commit()

    # v19: seed first admin account (yk1) for the RBAC trial.
    from auth import hash_password
    yk1 = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
    if not yk1:
        temp_pw = os.environ.get("YK_ADMIN_TEMP_PW", "changeme1")
        s.add(AppUser(
            username="yk1",
            password_hash=hash_password(temp_pw),
            display_name="โอ (admin)",
            role="admin",
            status="active",
            must_change_pw=True,
        ))
        s.commit()
        print("[seed] created admin user yk1 (must change password on first login)")

    seed_kb_rules(s)


# ---- Error log ลงไฟล์ (บน server แอปรันเป็น SYSTEM task — stdout หายหมด ไม่มี
# ร่องรอย 500 เลย) → logs/app.log หมุน 2MB×5 + โชว์ล่าสุดบน /admin/server-health
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "app.log"


class _DropClientDisconnect(logging.Filter):
    """asyncio โยน ConnectionResetError ทุกครั้งที่ client ตัดสายกลางคัน (uptime check /
    ปิดแท็บ) — ไม่ใช่บั๊ก แต่ท่วม log จนบัง error จริงบนหน้า 🖥️ สุขภาพเครื่อง."""

    _CLIENT_GONE = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "asyncio" or not record.exc_info:
            return True
        return not isinstance(record.exc_info[1], self._CLIENT_GONE)


def _setup_file_logging() -> None:
    try:
        LOG_DIR.mkdir(exist_ok=True)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=5,
                                      encoding="utf-8", delay=True)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%d %H:%M:%S"))
        handler.addFilter(_DropClientDisconnect())
        handler.setLevel(logging.WARNING)   # เก็บ WARNING ขึ้นไป — ไม่ spam access log
        for name in ("", "uvicorn.error", "yk.app"):
            lg = logging.getLogger(name)
            if not any(isinstance(h, RotatingFileHandler)
                       and getattr(h, "baseFilename", "") == str(LOG_FILE)
                       for h in lg.handlers):
                lg.addHandler(handler)
        logging.getLogger("yk.app").setLevel(logging.WARNING)
    except Exception:
        pass  # log ตั้งไม่ได้ต้องไม่ทำแอปพัง


_setup_file_logging()
_APP_LOG = logging.getLogger("yk.app")

from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def _lifespan(app_):
    # init_db (create_all + additive migrations) นิยามอยู่ด้านล่าง — resolve ตอนรัน
    # เดิมใช้ @app.on_event("startup") ซึ่ง deprecated ตั้งแต่ fastapi 0.109
    init_db()
    yield


app = FastAPI(title="Project YK - One Platform", lifespan=_lifespan)


@app.exception_handler(Exception)
async def _unhandled_exception_logger(request: Request, exc: Exception):
    """จับ 500 ทุกตัวลงไฟล์พร้อม traceback + หน้า error ภาษาคน (เดิมหายเงียบ)."""
    import traceback
    _APP_LOG.error("500 %s %s user=%s\n%s", request.method, request.url.path,
                   getattr(getattr(request, "state", None), "user", "") or "",
                   traceback.format_exc())
    return PlainTextResponse(
        "ระบบขัดข้องชั่วคราว — ทีมดูแลเห็นรายละเอียดแล้วใน log (🖥️ สุขภาพเครื่อง)\n"
        f"หน้า: {request.url.path}",
        status_code=500)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # เสิร์ฟ service worker จากราก เพื่อให้ scope ครอบทั้งเว็บ (/) ไม่ใช่แค่ /static/.
    return FileResponse(APP_DIR / "static" / "sw.js", media_type="application/javascript")

# Uploads folder (driver photos, etc.) — S2: ไม่เสิร์ฟ public แล้ว ต้องมี session
# ระบบ หรือ access-link token (?t= — หน้า /check/mechanic ฝังรูปพร้อม token)
_uploads_dir = APP_DIR / "uploads"
_uploads_dir.mkdir(exist_ok=True)


@app.get("/uploads/{upload_path:path}", include_in_schema=False)
def serve_upload(upload_path: str, request: Request):
    # current_user / _check_link_guard เป็น global ตอน runtime (นิยามถัดลงไปในไฟล์)
    if current_user(request) is None:
        with Session(engine) as s:
            if _check_link_guard(request, s, count_use=False) is None:
                raise HTTPException(403, "ต้องล็อกอินหรือเปิดผ่านลิงก์ที่ได้รับ")
    full = (_uploads_dir / upload_path).resolve()
    if not full.is_file() or _uploads_dir.resolve() not in full.parents:
        raise HTTPException(404)
    return FileResponse(full)

_DOCS_PRINT_DIR = APP_DIR.parent / "docs" / "print"


@app.get("/ops/lcb-fuel-dispatch")
def ops_lcb_fuel_dispatch():
    """แผนเติมน้ำมัน LCB (HTML จาก build_lcb_fuel_dispatch.bat)."""
    path = _DOCS_PRINT_DIR / "lcb_fuel_dispatch_plan.html"
    if not path.is_file():
        raise HTTPException(
            404,
            detail="ยังไม่มีไฟล์แผน — รัน ProjectYK_System/tools/build_lcb_fuel_dispatch.bat ก่อน",
        )
    return FileResponse(path, media_type="text/html; charset=utf-8")


app.add_middleware(PreviewAuthMiddleware)

# RBAC middleware: enforces login + permission matrix. Defined here, but it needs
# request.session, so it is added BEFORE SessionMiddleware (later add_middleware =
# outer wrapper). Result: Session wraps RBAC -> session is populated when RBAC runs.
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from permissions import check as perm_check  # noqa: E402

# /driver/* is the driver PWA — it has its OWN auth (DriverSession + PIN) and each
# handler calls get_current_driver(), redirecting to /driver/login when absent.
# So RBAC (AppUser-based) must NOT gate it, or drivers get bounced to the admin login.
PUBLIC_PREFIXES = ("/login", "/logout", "/static/",
                   "/uploads/",    # gated in-handler (session OR access-link token)
                   "/health", "/driver",
                   "/sw.js",       # PWA service worker — must load pre-login for installability
                   "/check",       # magic-link tire check; gated in-handler by signed token
                   "/c/",          # short-URL redirect to /check (resolves token from DB)
                   "/api/petty/")  # service-token auth (not session); checked in-handler


class RbacMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from auth import current_user  # local import: auth -> models -> db ready by now
        path = request.url.path
        if path == "/" or any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)
        user = current_user(request)
        if user is None:
            # AJAX/API → ตอบ 401 JSON ให้ fetch จับได้ (อย่า redirect HTML login เงียบ ๆ
            # ซึ่งทำให้หน้า grid เซฟไม่ติดแบบไม่มีข้อความ)
            if path.startswith("/api/"):
                return JSONResponse({"ok": False, "error": "auth_required"}, status_code=401)
            return RedirectResponse("/login", status_code=303)
        if user.must_change_pw and not path.startswith("/account/password"):
            return RedirectResponse("/account/password", status_code=303)
        if path.startswith("/account/"):
            return await call_next(request)
        if perm_check(user.role, path, request.method) == "deny":
            return PlainTextResponse("ไม่มีสิทธิ์เข้าถึงส่วนนี้", status_code=403)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defensive response headers: force HTTPS (HSTS), block clickjacking and
    MIME-sniffing, trim referrer leakage."""
    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return resp


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RbacMiddleware)
# Secure cookie ON by default (production is HTTPS). Set YK_INSECURE_COOKIES=1 only
# for local http dev / tests where TestClient speaks plain http.
_secure_cookies = os.environ.get("YK_INSECURE_COOKIES", "").lower() not in ("1", "true", "yes")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("YK_SESSION_SECRET", "dev-insecure-secret-change-me"),
    same_site="lax",
    https_only=_secure_cookies,   # Secure flag: cookie never sent over plain HTTP
    max_age=8 * 60 * 60,          # session expires after 8h (limits stolen-cookie window)
)


# ---- Auth: login / logout ----
from auth import (  # noqa: E402
    current_user,
    get_user_by_username,
    login_session,
    logout_session,
    verify_password,
)
import login_guard  # noqa: E402


def _client_ip(request: Request) -> str:
    # Behind Cloudflare: the real client IP is in CF-Connecting-IP.
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})


@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    uname = username.strip()
    ip = _client_ip(request)

    # Brute-force guards (fail closed before touching the DB).
    if login_guard.is_ip_blocked(ip) or login_guard.is_username_locked(uname):
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request,
             "error": "พยายามเข้าสู่ระบบบ่อยเกินไป — โปรดลองใหม่อีกครั้งในภายหลัง"},
            status_code=429,
        )

    u = get_user_by_username(uname)
    if u is None or u.status != "active" or not verify_password(password, u.password_hash):
        login_guard.record_failure(username=uname, ip=ip)
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request, "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"},
            status_code=401,
        )
    login_guard.record_success(username=uname, ip=ip)
    login_session(request, u)
    dest = "/account/password" if u.must_change_pw else "/daily"
    return RedirectResponse(dest, status_code=303)


@app.get("/logout")
async def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=303)


# ---- Self-service password change (any logged-in user) ----
from auth import hash_password  # noqa: E402


@app.get("/account/password", response_class=HTMLResponse)
async def password_page(request: Request):
    u = current_user(request)
    return templates.TemplateResponse(request, "account_password.html",
                                      {"request": request, "error": None, "user": u})


@app.post("/account/password")
async def password_submit(request: Request,
                          old_password: str = Form(...),
                          new_password: str = Form(...),
                          confirm: str = Form(...)):
    u = current_user(request)

    def fail(msg):
        return templates.TemplateResponse(
            request, "account_password.html",
            {"request": request, "error": msg, "user": u}, status_code=400)

    if not verify_password(old_password, u.password_hash):
        return fail("รหัสผ่านเดิมไม่ถูกต้อง")
    if new_password != confirm:
        return fail("รหัสผ่านใหม่ไม่ตรงกัน")
    if len(new_password) < 8:
        return fail("รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัวอักษร")
    with Session(engine) as s:
        db_u = s.get(AppUser, u.id)
        db_u.password_hash = hash_password(new_password)
        db_u.must_change_pw = False
        s.add(db_u)
        s.commit()
    return RedirectResponse("/daily", status_code=303)


# ---- Admin: user management (admin role only; enforced by RBAC matrix /admin) ----
from permissions import ROLES  # noqa: E402


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_list(request: Request):
    with Session(engine) as s:
        users = s.exec(select(AppUser).order_by(AppUser.username)).all()
    return templates.TemplateResponse(request, "admin_users.html",
                                      {"request": request, "users": users, "roles": ROLES})


@app.post("/admin/users/new")
async def admin_users_create(request: Request,
                             username: str = Form(...),
                             display_name: str = Form(""),
                             role: str = Form(...),
                             temp_password: str = Form(...)):
    if role not in ROLES:
        role = "viewer"
    if len(temp_password) < 8:
        return PlainTextResponse("รหัสชั่วคราวต้องยาวอย่างน้อย 8 ตัวอักษร", status_code=400)
    with Session(engine) as s:
        exists = s.exec(select(AppUser).where(AppUser.username == username.strip())).first()
        if not exists:
            s.add(AppUser(username=username.strip(),
                          password_hash=hash_password(temp_password),
                          display_name=display_name.strip(), role=role,
                          status="active", must_change_pw=True))
            s.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/disable")
async def admin_users_disable(request: Request, user_id: int):
    with Session(engine) as s:
        u = s.get(AppUser, user_id)
        if u and u.username != "yk1":   # never disable the seed admin
            u.status = "disabled"
            s.add(u)
            s.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/enable")
async def admin_users_enable(request: Request, user_id: int):
    with Session(engine) as s:
        u = s.get(AppUser, user_id)
        if u:
            u.status = "active"
            s.add(u)
            s.commit()
    return RedirectResponse("/admin/users", status_code=303)


@app.post("/admin/users/{user_id}/reset")
async def admin_users_reset(request: Request, user_id: int, temp_password: str = Form(...)):
    if len(temp_password) < 8:
        return PlainTextResponse("รหัสชั่วคราวต้องยาวอย่างน้อย 8 ตัวอักษร", status_code=400)
    with Session(engine) as s:
        u = s.get(AppUser, user_id)
        if u:
            u.password_hash = hash_password(temp_password)
            u.must_change_pw = True
            s.add(u)
            s.commit()
    return RedirectResponse("/admin/users", status_code=303)


# Template helper: nav templates call can_see(request, "/payroll") to hide links
# the current user's role may not access.
def _can_see(request, prefix: str) -> bool:
    u = current_user(request)
    if u is None:
        return False
    return perm_check(u.role, prefix, "GET") != "deny"


templates.env.globals["can_see"] = _can_see


# P1: สิทธิ์ระดับชิ้นส่วนในหน้า (part) — ดู parts.py; ใช้ใน template:
#   {% if part_visible(request, 'daily.kb_col') %} / {% if part_editable(...) %}
def _part_level_of(request, key: str) -> str:
    import parts as _parts
    u = current_user(request)
    if u is None:
        return "hide"
    with Session(engine) as s:
        return _parts.part_level(s, u.role, u.username, key)


templates.env.globals["part_visible"] = lambda request, key: _part_level_of(request, key) != "hide"
templates.env.globals["part_editable"] = lambda request, key: _part_level_of(request, key) == "edit"


# RBAC enforcement is registered as a class middleware (see RbacMiddleware below),
# added BEFORE SessionMiddleware so the session is available when it runs.


def get_setting(key: str, default: str = "") -> str:
    """Read an AppSetting value (returns default if unset)."""
    with Session(engine) as s:
        row = s.get(AppSetting, key)
        return row.value if row else default


def set_setting(key: str, value: str) -> None:
    """Upsert an AppSetting value."""
    with Session(engine) as s:
        row = s.get(AppSetting, key)
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            row = AppSetting(key=key, value=value)
        s.add(row)
        s.commit()


def base_context(request: Request) -> dict:
    return {
        "request": request,
        "today": date.today().isoformat(),
        "site_codes": models.SITE_CODES,
        "pay_modes": models.PAY_MODES,
        "pay_cycle_policies": models.PAY_CYCLE_POLICIES,
        "vehicle_kinds": models.VEHICLE_KINDS,
        "truck_types": models.TRUCK_TYPES,
        "truck_type_th": models.TRUCK_TYPE_TH,
        "vehicle_status": models.VEHICLE_STATUS,
        "employee_status": models.EMPLOYEE_STATUS,
        "leave_status_choices": models.LEAVE_STATUS_CHOICES,
        "fee_types": models.FEE_TYPES,
        "trip_types_by_site": models.TRIP_TYPE_CODES_BY_SITE,
        "petty_directions": models.PETTY_DIRECTIONS,
        "petty_categories": models.PETTY_CATEGORIES,
        "deduction_status": models.DEDUCTION_STATUS,
        "petty_txn_status": models.PETTY_TXN_STATUS,
        "employee_roles": models.EMPLOYEE_ROLES,
        "inbox_statuses": models.INBOX_EMAIL_STATUS,
        "inbox_categories": models.INBOX_EMAIL_CATEGORY,
    }


# P5.2: หน้าแรก = การ์ดงานที่ต้องทำวันนี้ (การ์ดโชว์ตามสิทธิ์ role) — ต้องเร็ว:
# query แบบ count เฉพาะช่วง + นับจาก line archive ผ่าน cache 5 นาที;
# AR จาก Drive = cache 10 นาที (พลาด/ช้า = โชว์ "—" ไม่บล็อกหน้า)
_HOME_LINE_CACHE: dict = {"at": None, "inbox": None, "pod": None, "fuel_line": None}
_HOME_AR_CACHE: dict = {"at": None, "overdue": None, "week": None}


def _home_ar_summary() -> dict:
    from datetime import datetime as _dt

    now = _dt.utcnow()
    if _HOME_AR_CACHE["at"] and (now - _HOME_AR_CACHE["at"]).total_seconds() < 600:
        return _HOME_AR_CACHE
    overdue = week = None
    try:
        from services import receivables as ar
        rows, _missing = ar.load_all()
        with Session(engine) as s:
            settled_keys = {a.inv_key for a in s.exec(select(ArSettle)).all()}
        for r in rows:
            key = f"{r['site']}:{r['inv']}" if r["inv"] else ""
            if key and key in settled_keys:
                r["received"] = True
        summ = ar.summarize(rows)
        overdue, week = summ["overdue_net"], summ["week_net"]
    except Exception:
        pass
    _HOME_AR_CACHE.update({"at": now, "overdue": overdue, "week": week})
    return _HOME_AR_CACHE


def _home_line_counts(s: Session) -> dict:
    from datetime import datetime as _dt

    now = _dt.utcnow()
    if _HOME_LINE_CACHE["at"] and (now - _HOME_LINE_CACHE["at"]).total_seconds() < 300:
        return _HOME_LINE_CACHE
    from services import line_archive as la
    from services import line_inbox as li
    from services import line_pod as lp

    inbox = pod = fuel_line = None
    if la.db_path() is not None:
        try:
            maps = {m.group_id: m for m in s.exec(
                select(models.LineGroupMap).where(
                    models.LineGroupMap.kind == "customer",
                    models.LineGroupMap.active == True)).all()}  # noqa: E712
            if maps:
                seen = {v.line_message_pk for v in s.exec(select(models.LineJobSeen)).all()}
                inbox = len(li.scan_candidates(list(maps), days=7, exclude_ids=seen))
                media_seen = {jm.line_message_pk for jm in s.exec(select(models.JobMedia)).all()}
                pod = len(lp.photo_candidates(list(maps), days=7, exclude_ids=media_seen))
        except Exception:
            pass
        # F4: แจ้งเติมในไลน์ที่ไม่เจอในระบบ (ช่วงข้อมูลครบ) 14 วันหลังสุด — โผล่เอง
        try:
            from sqlalchemy import func as sa_func

            from services import fuel_line_compare as flc
            station_groups = [m.group_id for m in s.exec(
                select(models.LineGroupMap).where(
                    models.LineGroupMap.kind == "station",
                    models.LineGroupMap.active == True)).all()]  # noqa: E712
            if station_groups:
                orders = flc.fill_orders(station_groups, days=14)
                since = date.today() - timedelta(days=15)
                txns = s.exec(select(FuelTxn)
                              .where(FuelTxn.txn_date >= since)).all()
                plate_site = {v.plate_no.strip(): v.home_site_code
                              for v in s.exec(select(Vehicle)).all()}
                site_fuel_max = {
                    k: (date.fromisoformat(v) if isinstance(v, str) else v)
                    for k, v in s.exec(
                        select(FuelTxn.site_code, sa_func.max(FuelTxn.txn_date))
                        .group_by(FuelTxn.site_code)).all()}
                fuel_line = len(flc.compare(orders, txns, plate_site=plate_site,
                                            site_fuel_max=site_fuel_max)["line_only"])
        except Exception:
            pass
    _HOME_LINE_CACHE.update({"at": now, "inbox": inbox, "pod": pod,
                             "fuel_line": fuel_line})
    return _HOME_LINE_CACHE


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    u = current_user(request)
    if u is None:
        return RedirectResponse(url="/login", status_code=303)

    today = date.today()
    m_start, m_end = _month_bounds(today.year, today.month)
    with Session(engine) as s:
        # งานวันนี้ต่อไซท์ (แยกชนิดแถวด้วย helper เดียวกับปฏิทิน/billing)
        today_rows = s.exec(select(DailyJob).where(DailyJob.work_date == today)).all()
        sites: dict[str, dict] = {}
        for j in today_rows:
            g = sites.setdefault(j.site_code or "?", {"run": 0, "idle": 0, "leave": 0, "repair": 0})
            kind = _daily_row_kind(j)
            key = {"job": "run", "idle": "idle", "leave": "leave", "repair": "repair"}.get(kind)
            if key:
                g[key] += 1
        # แถวราคาว่างเดือนนี้ (เฉพาะแถวงานจริง) ต่อไซท์
        month_rows = s.exec(select(DailyJob).where(
            DailyJob.work_date >= m_start, DailyJob.work_date <= m_end)).all()
        no_price: dict[str, int] = {}
        for j in month_rows:
            if _daily_row_kind(j) == "job" and not (j.revenue_customer or 0):
                no_price[j.site_code or "?"] = no_price.get(j.site_code or "?", 0) + 1
        # payroll รอบล่าสุดต่อไซท์
        runs = []
        for site in ("LCB", "AYU", "BIGC"):
            pr = s.exec(select(PayRun).where(PayRun.site_code == site)
                        .order_by(PayRun.id.desc())).first()  # type: ignore[union-attr]
            if pr:
                runs.append(pr)
        # ยอดตกหล่นค้างดูด (C4)
        pending_adj = len(s.exec(select(PayAdjustment).where(
            PayAdjustment.status == "pending")).all())
        line_counts = _home_line_counts(s)
        # น้ำมันผิดปกติ 7 วันหลังสุด (สแกน local เร็ว)
        try:
            from services import fuel_anomaly as fa
            fuel_flags = len(fa.scan(s, today - timedelta(days=7), today)["rows"])
        except Exception:
            fuel_flags = None
    ar_sum = _home_ar_summary() if perm_check(u.role, "/finance", "GET") != "deny" \
        else {"overdue": None, "week": None}

    # แผนงาน MVP % (อ่านไฟล์ — เร็ว)
    plan = None
    try:
        pf = APP_DIR.parent / "docs" / "PLAN_STATUS.json"
        data = json.loads(pf.read_text(encoding="utf-8"))
        tasks = [t for ph in data.get("phases", []) for t in ph.get("tasks", [])]
        done = sum(1 for t in tasks if t.get("status") == "done")
        plan = {"done": done, "total": len(tasks),
                "pct": round(done / len(tasks) * 100) if tasks else 0}
    except Exception:
        pass

    ctx = base_context(request)
    ctx.update({
        "sites": sites, "no_price": no_price, "runs": runs,
        "pending_adj": pending_adj, "plan": plan,
        "inbox_count": line_counts["inbox"], "pod_count": line_counts["pod"],
        "fuel_line_missing": line_counts.get("fuel_line"),
        "fuel_flags": fuel_flags,
        "ar_overdue": ar_sum["overdue"], "ar_week": ar_sum["week"],
        "today_d": today,
    })
    return templates.TemplateResponse(request, "home_dashboard.html", ctx)


@app.get("/health")
def health():
    db_label = f"sqlite:{DB_PATH.name}" if IS_SQLITE else "postgresql"
    return {"ok": True, "db": db_label, "schema_version": SCHEMA_VERSION}


@app.get("/employees", response_class=HTMLResponse)
def employees_list(request: Request, site: str = "", q: str = ""):
    with Session(engine) as s:
        stmt = select(Employee)
        if site:
            stmt = stmt.where(Employee.home_site_code == site)
        stmt = stmt.order_by(Employee.home_site_code, Employee.full_name)
        rows = s.exec(stmt).all()
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in (r.full_name or "").lower()
                    or ql in (r.nickname or "").lower()
                    or ql in (r.code or "").lower()]
    ctx = base_context(request)
    ctx.update({"rows": rows, "site": site, "q": q})
    return templates.TemplateResponse(request, "employees_list.html", ctx)


# ---------------------------------------------------------------------
# เงินประกันตน (driver security deposit) — overview + edit + history
# ---------------------------------------------------------------------

def _deposit_row_ctx(request: Request, e: "Employee") -> dict:
    bal = e.deposit_balance or 0.0
    tgt = e.deposit_target or 0.0
    remaining = max(0.0, tgt - bal)
    pct = min(100, round(bal / tgt * 100)) if tgt > 0 else 0
    ctx = base_context(request)
    ctx.update({"r": {"emp": e, "remaining": remaining, "pct": pct}})
    return ctx


@app.get("/deposits", response_class=HTMLResponse)
def deposits_list(request: Request, site: str = "", show: str = "active"):
    # show: "active" (default — เฉพาะคนทำงาน) | "all" (รวมคนออกแล้ว)
    with Session(engine) as s:
        base = select(Employee).where(Employee.deposit_target > 0)
        if site:
            base = base.where(Employee.home_site_code == site)
        if show != "all":
            stmt = base.where(Employee.status == "active")
        else:
            stmt = base
        stmt = stmt.order_by(Employee.home_site_code, Employee.full_name)
        emps = s.exec(stmt).all()
        # นับคนออกแล้ว (inactive) ที่ถูกซ่อน — ใช้โชว์บนปุ่มสลับ (เคารพ filter ไซต์)
        resigned_count = len(s.exec(
            base.where(Employee.status != "active")
        ).all())
    rows = []
    total_balance = 0.0
    total_remaining = 0.0
    for e in emps:
        bal = e.deposit_balance or 0.0
        tgt = e.deposit_target or 0.0
        remaining = max(0.0, tgt - bal)
        pct = min(100, round(bal / tgt * 100)) if tgt > 0 else 0
        rows.append({"emp": e, "remaining": remaining, "pct": pct})
        total_balance += bal
        total_remaining += remaining
    summary = {"count": len(rows), "total_balance": total_balance,
               "total_remaining": total_remaining}
    ctx = base_context(request)
    ctx.update({"rows": rows, "site": site, "show": show, "summary": summary,
                "resigned_count": resigned_count, "site_codes": models.SITE_CODES})
    return templates.TemplateResponse(request, "deposits_list.html", ctx)


@app.get("/deposits/{emp_id}/edit", response_class=HTMLResponse)
def deposits_edit_form(emp_id: int, request: Request):
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if not e:
            raise HTTPException(404)
    ctx = _deposit_row_ctx(request, e)
    return templates.TemplateResponse(request, "deposits_edit_row.html", ctx)


@app.post("/deposits/{emp_id}/edit", response_class=HTMLResponse)
def deposits_edit_submit(
    emp_id: int, request: Request,
    deposit_balance: str = Form("0"),
    deposit_target: str = Form("0"),
    reason: str = Form(""),
):
    new_bal = _parse_float(deposit_balance)
    new_tgt = _parse_float(deposit_target)
    if new_bal < 0 or new_tgt < 0:
        return HTMLResponse("ยอดต้องไม่ติดลบ", status_code=400)
    _u = current_user(request)
    changed_by = (_u.username if _u else "") or "?"
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if not e:
            raise HTTPException(404)
        for field_name, new_val in (("deposit_balance", new_bal),
                                    ("deposit_target", new_tgt)):
            old_val = getattr(e, field_name) or 0.0
            if old_val != new_val:
                s.add(models.DepositAudit(
                    employee_id=emp_id, changed_by=changed_by, field_name=field_name,
                    old_value=str(old_val), new_value=str(new_val), reason=reason.strip()))
                setattr(e, field_name, new_val)
        s.add(e)
        s.commit()
        s.refresh(e)
        ctx = _deposit_row_ctx(request, e)
    return templates.TemplateResponse(request, "deposits_row.html", ctx)


@app.get("/deposits/{emp_id}/history", response_class=HTMLResponse)
def deposits_history(emp_id: int, request: Request):
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if not e:
            raise HTTPException(404)
        items = s.exec(
            select(PayRunItem, PayRun)
            .join(PayRun, PayRun.id == PayRunItem.pay_run_id)
            .where(PayRunItem.employee_id == emp_id, PayRunItem.deposit_install > 0)
            .order_by(PayRun.period_start)
        ).all()
        hist = [{"site": pr.site_code, "tag": pr.pay_cycle_tag,
                 "amount": pi.deposit_install} for pi, pr in items]
        hist_total = sum(h["amount"] for h in hist)
        carried = (e.deposit_balance or 0.0) - hist_total
        edit_log = s.exec(
            select(models.DepositAudit)
            .where(models.DepositAudit.employee_id == emp_id)
            .order_by(models.DepositAudit.changed_at.desc())
        ).all()
    ctx = base_context(request)
    ctx.update({"emp": e, "hist": hist, "hist_total": hist_total,
                "carried": carried, "edit_log": edit_log})
    return templates.TemplateResponse(request, "deposits_history.html", ctx)


def _parse_custom_terms_safe(raw: str) -> dict:
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


@app.get("/employees/new", response_class=HTMLResponse)
def employees_new(request: Request):
    ctx = base_context(request)
    ctx.update({"row": None, "mode": "new", "custom_terms_obj": {}})
    return templates.TemplateResponse(request, "employee_form.html", ctx)


@app.get("/employees/{emp_id}/edit", response_class=HTMLResponse)
def employees_edit(emp_id: int, request: Request):
    with Session(engine) as s:
        row = s.get(Employee, emp_id)
        if not row:
            raise HTTPException(404)
    ctx = base_context(request)
    ctx.update({
        "row": row,
        "mode": "edit",
        "custom_terms_obj": _parse_custom_terms_safe(row.custom_terms or ""),
    })
    return templates.TemplateResponse(request, "employee_form.html", ctx)


@app.post("/employees/new")
@app.post("/employees/{emp_id}/edit")
def employees_save(
    request: Request,
    emp_id: Optional[int] = None,
    code: str = Form(""),
    full_name: str = Form(...),
    nickname: str = Form(""),
    phone: str = Form(""),
    id_card: str = Form(""),
    bank_name: str = Form(""),
    account_no: str = Form(""),
    home_site_code: str = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    status: str = Form("active"),
    pay_mode: str = Form("ayu_trip"),
    pay_cycle_policy: str = Form("site_default"),
    base_salary: str = Form("0"),
    care_allowance: str = Form("0"),
    gross_share_rate: str = Form(""),
    has_guarantee: Optional[str] = Form(None),
    guarantee_monthly_amount: str = Form("0"),
    deposit_target: str = Form("10000"),
    deposit_balance: str = Form("0"),
    social_security_base: str = Form("9000"),
    social_security_rate: str = Form("0.05"),
    custom_terms: str = Form(""),
    notes: str = Form(""),
    tax_mode: str = Form(""),
    tax_monthly_cap_rate: str = Form(""),
    tax_exempt: Optional[str] = Form(None),
    tax_extra_allowance_annual: str = Form(""),
):
    with Session(engine) as s:
        code_val = code.strip()
        if emp_id is None:
            if not code_val:
                code_val = _gen_next_code(s, Employee, prefix="E")
            row = Employee(code=code_val, full_name=full_name.strip(),
                           home_site_code=home_site_code)
        else:
            row = s.get(Employee, emp_id)
            if not row:
                raise HTTPException(404)
            row.code = code_val or row.code
            row.full_name = full_name.strip()
            row.home_site_code = home_site_code
        row.nickname = nickname.strip()
        row.phone = phone.strip()
        row.id_card = id_card.strip()
        row.bank_name = bank_name.strip()
        row.account_no = account_no.strip()
        row.start_date = _parse_date(start_date)
        row.end_date = _parse_date(end_date)
        row.status = status
        row.pay_mode = pay_mode
        policy_val = (pay_cycle_policy or "").strip().lower()
        known_policies = {p[0] for p in models.PAY_CYCLE_POLICIES}
        row.pay_cycle_policy = policy_val if policy_val in known_policies else "site_default"
        row.base_salary = _parse_float(base_salary)
        row.care_allowance = _parse_float(care_allowance)
        rate = _parse_float(gross_share_rate) if gross_share_rate else None
        row.gross_share_rate = rate if rate and rate > 0 else None
        row.has_guarantee = _parse_bool(has_guarantee)
        row.guarantee_monthly_amount = _parse_float(guarantee_monthly_amount)
        row.deposit_target = _parse_float(deposit_target)
        row.deposit_balance = _parse_float(deposit_balance)
        row.social_security_base = _parse_float(social_security_base)
        row.social_security_rate = _parse_float(social_security_rate)
        # Merge tax UI fields into custom_terms JSON (preserve other keys).
        try:
            existing_terms_obj = json.loads(custom_terms) if (custom_terms or "").strip().startswith("{") else {}
        except Exception:
            existing_terms_obj = {}
        if not isinstance(existing_terms_obj, dict):
            existing_terms_obj = {}
        if tax_mode in ("catch_up", "safe"):
            existing_terms_obj["tax_mode"] = tax_mode
        elif "tax_mode" in existing_terms_obj and tax_mode == "":
            existing_terms_obj.pop("tax_mode", None)
        if (tax_monthly_cap_rate or "").strip():
            try:
                existing_terms_obj["tax_monthly_cap_rate"] = float(tax_monthly_cap_rate)
            except Exception:
                pass
        existing_terms_obj["tax_exempt"] = bool(_parse_bool(tax_exempt))
        if (tax_extra_allowance_annual or "").strip():
            try:
                existing_terms_obj["tax_extra_allowance_annual"] = float(tax_extra_allowance_annual)
            except Exception:
                pass
        if existing_terms_obj:
            row.custom_terms = json.dumps(existing_terms_obj, ensure_ascii=False)
        else:
            row.custom_terms = custom_terms
        row.notes = notes
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url="/employees", status_code=303)


@app.post("/employees/{emp_id}/delete")
def employees_delete(emp_id: int):
    with Session(engine) as s:
        row = s.get(Employee, emp_id)
        if row:
            s.delete(row)
            s.commit()
    return RedirectResponse(url="/employees", status_code=303)


@app.post("/employees/{emp_id}/rehire")
def employees_rehire(emp_id: int, left: str = Form(""), back: str = Form("")):
    """Quick action: set start_date = back date, clear end_date, status=active,
    and append rehire history entry to custom_terms JSON.
    """
    back_d = _parse_date(back)
    left_d = _parse_date(left) if left else None
    if not back_d:
        raise HTTPException(400, "back date required")
    with Session(engine) as s:
        emp = s.get(Employee, emp_id)
        if not emp:
            raise HTTPException(404)
        try:
            ct = json.loads(emp.custom_terms or "{}")
            if not isinstance(ct, dict):
                ct = {}
        except Exception:
            ct = {}
        # preserve original hire date once
        if not ct.get("original_hire_date") and emp.start_date:
            ct["original_hire_date"] = emp.start_date.isoformat()
        rehire_log = ct.get("rehire_log") or []
        entry = {
            "left": (left_d.isoformat() if left_d else (emp.end_date.isoformat() if emp.end_date else None)),
            "back": back_d.isoformat(),
        }
        if entry not in rehire_log:
            rehire_log.append(entry)
        ct["rehire_log"] = rehire_log
        emp.custom_terms = json.dumps(ct, ensure_ascii=False)
        emp.start_date = back_d
        emp.end_date = None
        emp.status = "active"
        s.add(emp)
        s.commit()
    return JSONResponse({"ok": True, "start_date": back_d.isoformat()})


@app.get("/vehicles", response_class=HTMLResponse)
def vehicles_list(request: Request, site: str = "", q: str = ""):
    with Session(engine) as s:
        stmt = select(Vehicle)
        if site:
            stmt = stmt.where(Vehicle.home_site_code == site)
        stmt = stmt.order_by(Vehicle.home_site_code, Vehicle.plate_no)
        rows = s.exec(stmt).all()
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in (r.plate_no or "").lower()]
    ctx = base_context(request)
    ctx.update({"rows": rows, "site": site, "q": q})
    return templates.TemplateResponse(request, "vehicles_list.html", ctx)


@app.get("/vehicles/new", response_class=HTMLResponse)
def vehicles_new(request: Request):
    ctx = base_context(request)
    ctx.update({"row": None, "mode": "new"})
    return templates.TemplateResponse(request, "vehicle_form.html", ctx)


@app.get("/vehicles/{veh_id}/edit", response_class=HTMLResponse)
def vehicles_edit(veh_id: int, request: Request):
    with Session(engine) as s:
        row = s.get(Vehicle, veh_id)
        if not row:
            raise HTTPException(404)
    ctx = base_context(request)
    ctx.update({"row": row, "mode": "edit"})
    return templates.TemplateResponse(request, "vehicle_form.html", ctx)


@app.post("/vehicles/new")
@app.post("/vehicles/{veh_id}/edit")
def vehicles_save(
    request: Request,
    veh_id: Optional[int] = None,
    plate_no: str = Form(...),
    vehicle_kind: str = Form("truck"),
    truck_type: str = Form(""),
    home_site_code: str = Form(""),
    status: str = Form("active"),
    start_date: str = Form(""),
    end_date: str = Form(""),
    notes: str = Form(""),
    tank_liters: str = Form("0"),
):
    with Session(engine) as s:
        if veh_id is None:
            row = Vehicle(plate_no=plate_no.strip())
        else:
            row = s.get(Vehicle, veh_id)
            if not row:
                raise HTTPException(404)
            row.plate_no = plate_no.strip()
        row.vehicle_kind = vehicle_kind
        row.truck_type = truck_type
        row.home_site_code = home_site_code
        row.status = status
        row.start_date = _parse_date(start_date)
        row.end_date = _parse_date(end_date)
        row.notes = notes
        row.tank_liters = _parse_float(tank_liters) or 0.0
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url="/vehicles", status_code=303)


@app.post("/vehicles/{veh_id}/delete")
def vehicles_delete(veh_id: int):
    with Session(engine) as s:
        row = s.get(Vehicle, veh_id)
        if row:
            s.delete(row)
            s.commit()
    return RedirectResponse(url="/vehicles", status_code=303)


@app.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, site: str = "", q: str = ""):
    with Session(engine) as s:
        stmt = select(Customer)
        if site:
            stmt = stmt.where(Customer.home_site_code == site)
        stmt = stmt.order_by(Customer.home_site_code, Customer.name)
        rows = s.exec(stmt).all()
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in (r.name or "").lower()
                    or ql in (r.code or "").lower()]
    ctx = base_context(request)
    ctx.update({"rows": rows, "site": site, "q": q})
    return templates.TemplateResponse(request, "customers_list.html", ctx)


@app.get("/customers/new", response_class=HTMLResponse)
def customers_new(request: Request):
    ctx = base_context(request)
    ctx.update({"row": None, "mode": "new"})
    return templates.TemplateResponse(request, "customer_form.html", ctx)


@app.get("/customers/{cust_id}/edit", response_class=HTMLResponse)
def customers_edit(cust_id: int, request: Request):
    with Session(engine) as s:
        row = s.get(Customer, cust_id)
        if not row:
            raise HTTPException(404)
    ctx = base_context(request)
    ctx.update({"row": row, "mode": "edit"})
    return templates.TemplateResponse(request, "customer_form.html", ctx)


@app.post("/customers/new")
@app.post("/customers/{cust_id}/edit")
def customers_save(
    request: Request,
    cust_id: Optional[int] = None,
    code: str = Form(""),
    name: str = Form(...),
    home_site_code: str = Form(""),
    billing_profile_ref: str = Form(""),
    notes: str = Form(""),
):
    with Session(engine) as s:
        code_val = code.strip()
        if cust_id is None:
            if not code_val:
                code_val = _gen_next_code(s, Customer, prefix="C")
            row = Customer(code=code_val, name=name.strip())
        else:
            row = s.get(Customer, cust_id)
            if not row:
                raise HTTPException(404)
            row.code = code_val or row.code
            row.name = name.strip()
        row.home_site_code = home_site_code
        row.billing_profile_ref = billing_profile_ref.strip()
        row.notes = notes
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url="/customers", status_code=303)


@app.post("/customers/{cust_id}/delete")
def customers_delete(cust_id: int):
    with Session(engine) as s:
        row = s.get(Customer, cust_id)
        if row:
            s.delete(row)
            s.commit()
    return RedirectResponse(url="/customers", status_code=303)


def _load_masters(s: Session):
    employees = s.exec(select(Employee).order_by(Employee.home_site_code, Employee.full_name)).all()
    vehicles = s.exec(select(Vehicle).order_by(Vehicle.home_site_code, Vehicle.plate_no)).all()
    customers = s.exec(select(Customer).order_by(Customer.home_site_code, Customer.name)).all()
    return employees, vehicles, customers


@app.get("/daily", response_class=HTMLResponse)
def daily_list(
    request: Request,
    site: str = "",
    d_from: str = "",
    d_to: str = "",
    cycle: str = "",
    q: str = "",
    status: str = "",
    missing: str = "",
    limit: int = 0,
):
    """หน้า Daily แบบเดียว (รวม List + Grid เดิม) — แก้แบบ Excel, โหลดข้อมูลผ่าน AJAX.

    ช่วงเวลา default ผูกกับ "รอบ payroll ตามไซต์":
    - เลือกไซต์ → dropdown แสดงรอบของไซต์นั้น (LCB 16→15, AYU 26→25, BIGC 1→สิ้นเดือน);
      default = รอบล่าสุดที่มีข้อมูล. param `cycle` = tag เดือนที่รอบจบ.
    - ยังไม่เลือกไซต์ → default = ~2 เดือนปฏิทินล่าสุด (รวมทุกไซต์).
    - กรอก d_from/d_to เอง → ใช้ตามนั้น (ทับ cycle).
    """
    from sqlalchemy import func as sa_func

    today = date.today()
    with Session(engine) as s:
        max_wd = s.exec(select(sa_func.max(DailyJob.work_date))).one()
    anchor = max_wd or today          # ยึดวันล่าสุดที่มีข้อมูลเป็นจุดอ้างอิงของรอบ default

    site_cycles = _site_payroll_cycles(site, today) if site else []
    explicit_dates = bool(d_from or d_to)
    # เลือก cycle (เมื่อมีไซต์) → คุมช่วงเป็นรอบนั้น; ไม่อย่างนั้นค่อย default
    if site and not explicit_dates:
        chosen = next((c for c in site_cycles if c["tag"] == cycle), None)
        if chosen is None and cycle != "all":
            # default = รอบล่าสุดที่ครอบ "วันล่าสุดที่มีข้อมูล" (ไม่ใช่รอบอนาคตที่ยังว่าง)
            chosen = next((c for c in site_cycles if c["start"] <= anchor.isoformat() <= c["end"]), None)
            chosen = chosen or (site_cycles[0] if site_cycles else None)
        if chosen is not None:
            cycle = chosen["tag"]
            d_from, d_to = chosen["start"], chosen["end"]
    elif not site and not explicit_dates and not any([q, status, missing]):
        # เปิดหน้าครั้งแรก (ยังไม่เลือกอะไร) → ~2 เดือนปฏิทินล่าสุดรอบวันล่าสุดที่มีข้อมูล
        first_y, first_m = _shift_year_month(anchor.year, anchor.month, -1)
        d_from = date(first_y, first_m, 1).isoformat()
        d_to = _month_bounds(anchor.year, anchor.month)[1].isoformat()

    unlimited = limit <= 0          # limit=0 → โหลดครบทุกแถวตามตัวกรอง (ไม่ติด cap)
    if not unlimited:
        limit = max(1, min(800, limit))
    preset_cycles = _daily_site_preset_cycles(today)
    with Session(engine) as s:
        stmt = _daily_grid_filters(
            select(DailyJob).order_by(DailyJob.work_date.desc(), DailyJob.id.desc()),
            site, d_from, d_to, q, status, missing,
        )
        if not unlimited:
            stmt = stmt.limit(limit)
        rows = s.exec(stmt).all()
        total_rows = s.exec(
            _daily_grid_filters(select(sa_func.count(DailyJob.id)), site, d_from, d_to, q, status, missing)
        ).one()
    ctx = base_context(request)
    ctx.update(
        {
            "site": site,
            "d_from": d_from,
            "d_to": d_to,
            "cycle": cycle,
            "site_cycles": site_cycles,
            "q": q,
            "status": status,
            "missing": missing,
            "limit": (0 if unlimited else limit),
            "unlimited": unlimited,
            "today_iso": today.isoformat(),
            "total_rows": total_rows,
            "shown_rows": len(rows),
            "preset_cycles": preset_cycles,
        }
    )
    return templates.TemplateResponse(request, "daily_grid.html", ctx)


def _apply_daily_fields(row: DailyJob, f: dict) -> None:
    """Apply ค่าฟอร์ม (string ทั้งหมด) ลง DailyJob — ใช้ร่วมระหว่างฟอร์มเดี่ยวและ /daily/batch"""
    row.driver_id = _parse_int(f.get("driver_id", ""))
    row.driver_raw_name = f.get("driver_raw_name", "").strip()
    row.head_vehicle_id = _parse_int(f.get("head_vehicle_id", ""))
    row.tail_vehicle_id = _parse_int(f.get("tail_vehicle_id", ""))
    row.plate_no_raw = f.get("plate_no_raw", "").strip()
    row.tail_plate_raw = f.get("tail_plate_raw", "").strip()
    row.customer_id = _parse_int(f.get("customer_id", ""))
    row.customer_name_raw = f.get("customer_name_raw", "").strip()
    row.trip_type_code = f.get("trip_type_code", "").strip()
    row.status_code = f.get("status_code", "").strip()
    row.leave_status = f.get("leave_status", "").strip()
    row.origin = f.get("origin", "").strip()
    row.destination = f.get("destination", "").strip()
    row.doc_no = f.get("doc_no", "").strip()
    row.job_ref = f.get("job_ref", "").strip()
    row.container_no = f.get("container_no", "").strip()
    row.container_size = f.get("container_size", "").strip()
    row.revenue_customer = _parse_float(f.get("revenue_customer", "0"))
    row.trip_fee_driver = _parse_float(f.get("trip_fee_driver", "0"))
    row.fuel_liter = _parse_float(f.get("fuel_liter", "0"))
    row.fuel_amount = _parse_float(f.get("fuel_amount", "0"))
    row.fuel_station = f.get("fuel_station", "").strip()
    row.fuel_rate_km_per_l = _parse_float(f.get("fuel_rate_km_per_l", "0"))
    row.mile_snapshot = _parse_float(f.get("mile_snapshot", "0"))
    row.invoice_no = f.get("invoice_no", "").strip()
    row.invoice_date = _parse_date(f.get("invoice_date", ""))
    row.wht_53 = _parse_float(f.get("wht_53", "0"))
    row.remark = f.get("remark", "").strip()
    row.updated_at = datetime.utcnow()


@app.get("/daily/new", response_class=HTMLResponse)
def daily_new_form(request: Request):
    import json as _json
    with Session(engine) as s:
        employees, vehicles, customers = _load_masters(s)
    masters_json = _json.dumps({
        "employees": [{"id": e.id, "name": e.full_name, "site": e.home_site_code} for e in employees],
        "heads": [{"id": v.id, "plate": v.plate_no, "type": v.truck_type} for v in vehicles if v.vehicle_kind != "tail"],
        "tails": [{"id": v.id, "plate": v.plate_no} for v in vehicles if v.vehicle_kind == "tail"],
        "customers": [{"id": c.id, "name": c.name} for c in customers],
    }, ensure_ascii=False)
    trip_types_json = _json.dumps(
        {site: [list(t) for t in choices] for site, choices in models.TRIP_TYPE_CODES_BY_SITE.items()},
        ensure_ascii=False)
    ctx = base_context(request)
    ctx.update({"masters_json": masters_json, "trip_types_json": trip_types_json})
    return templates.TemplateResponse(request, "daily_batch.html", ctx)


@app.get("/daily/{job_id}/edit", response_class=HTMLResponse)
def daily_edit_form(job_id: int, request: Request):
    with Session(engine) as s:
        row = s.get(DailyJob, job_id)
        if not row:
            raise HTTPException(404)
        employees, vehicles, customers = _load_masters(s)
    ctx = base_context(request)
    ctx.update({"row": row, "mode": "edit",
                "employees": employees, "vehicles": vehicles, "customers": customers})
    return templates.TemplateResponse(request, "daily_form.html", ctx)


@app.post("/daily/new")
@app.post("/daily/{job_id}/edit")
def daily_save(
    request: Request,
    job_id: Optional[int] = None,
    work_date: str = Form(...),
    site_code: str = Form(...),
    driver_id: str = Form(""),
    driver_raw_name: str = Form(""),
    head_vehicle_id: str = Form(""),
    tail_vehicle_id: str = Form(""),
    plate_no_raw: str = Form(""),
    tail_plate_raw: str = Form(""),
    customer_id: str = Form(""),
    customer_name_raw: str = Form(""),
    trip_type_code: str = Form(""),
    status_code: str = Form(""),
    leave_status: str = Form(""),
    origin: str = Form(""),
    destination: str = Form(""),
    doc_no: str = Form(""),
    job_ref: str = Form(""),
    container_no: str = Form(""),
    container_size: str = Form(""),
    revenue_customer: str = Form("0"),
    trip_fee_driver: str = Form("0"),
    fuel_liter: str = Form("0"),
    fuel_amount: str = Form("0"),
    fuel_station: str = Form(""),
    fuel_rate_km_per_l: str = Form("0"),
    mile_snapshot: str = Form("0"),
    invoice_no: str = Form(""),
    invoice_date: str = Form(""),
    wht_53: str = Form("0"),
    remark: str = Form(""),
    inbox_mail_id: str = Form(""),
):
    wd = _parse_date(work_date)
    if not wd:
        raise HTTPException(400, "work_date invalid")
    with Session(engine) as s:
        if job_id is None:
            row = DailyJob(work_date=wd, site_code=site_code.strip().upper(), source="manual")
        else:
            row = s.get(DailyJob, job_id)
            if not row:
                raise HTTPException(404)
            row.work_date = wd
            row.site_code = site_code.strip().upper()
        _apply_daily_fields(row, {
            "driver_id": driver_id, "driver_raw_name": driver_raw_name,
            "head_vehicle_id": head_vehicle_id, "tail_vehicle_id": tail_vehicle_id,
            "plate_no_raw": plate_no_raw, "tail_plate_raw": tail_plate_raw,
            "customer_id": customer_id, "customer_name_raw": customer_name_raw,
            "trip_type_code": trip_type_code, "status_code": status_code,
            "leave_status": leave_status, "origin": origin, "destination": destination,
            "doc_no": doc_no, "job_ref": job_ref,
            "container_no": container_no, "container_size": container_size,
            "revenue_customer": revenue_customer, "trip_fee_driver": trip_fee_driver,
            "fuel_liter": fuel_liter, "fuel_amount": fuel_amount,
            "fuel_station": fuel_station, "fuel_rate_km_per_l": fuel_rate_km_per_l,
            "mile_snapshot": mile_snapshot, "invoice_no": invoice_no,
            "invoice_date": invoice_date, "wht_53": wht_53, "remark": remark,
        })
        driver_obj = s.get(Employee, row.driver_id) if row.driver_id else None
        s.add(row)
        s.commit()
        s.refresh(row)
        # Auto-learn rates from this entry (silent — just populates Rate Book)
        try:
            rate_record_from_daily(s, row)
            s.commit()
        except Exception:
            s.rollback()
        if job_id is None:
            inbox_id = _parse_int(inbox_mail_id)
            if inbox_id:
                mail = s.get(InboxEmail, inbox_id)
                if mail:
                    mail.linked_daily_job_id = row.id
                    mail.status = "linked"
                    mail.updated_at = datetime.utcnow()
                    s.add(mail)
                    s.commit()
    return RedirectResponse(url="/daily", status_code=303)


@app.post("/daily/batch")
async def daily_batch_save(request: Request):
    """รับ JSON {work_date, site_code, rows:[{...}]} จากหน้า batch entry — บันทึกทีละแถว
    แถวที่พังไม่ล้มทั้งชุด: คืนผลรายแถว {ok, id|error}"""
    payload = await request.json()
    wd = _parse_date(str(payload.get("work_date") or ""))
    site = str(payload.get("site_code") or "").strip().upper()
    if not wd:
        raise HTTPException(400, "work_date invalid")
    if site not in models.SITE_CODES:
        raise HTTPException(400, "site_code invalid")
    rows_in = payload.get("rows") or []
    if not isinstance(rows_in, list) or len(rows_in) > 200:
        raise HTTPException(400, "rows invalid")
    results = []
    with Session(engine) as s:
        for f in rows_in:
            try:
                clean = {k: ("" if v is None else str(v)) for k, v in dict(f).items()}
                row = DailyJob(work_date=wd, site_code=site, source="manual")
                _apply_daily_fields(row, clean)
                s.add(row)
                s.commit()
                s.refresh(row)
                # Auto-learn rates — เหมือน daily_save ทุกประการ
                try:
                    rate_record_from_daily(s, row)
                    s.commit()
                except Exception:
                    s.rollback()
                results.append({"ok": True, "id": row.id})
            except Exception as e:
                s.rollback()
                results.append({"ok": False, "error": str(e)[:200]})
    return {"results": results}


@app.post("/daily/{job_id}/delete")
def daily_delete(job_id: int):
    with Session(engine) as s:
        row = s.get(DailyJob, job_id)
        if row:
            s.delete(row)
            s.commit()
    return RedirectResponse(url="/daily", status_code=303)


def _daily_grid_filters(stmt, site: str, d_from: str, d_to: str, q: str, status: str = "", missing: str = ""):
    if site:
        stmt = stmt.where(DailyJob.site_code == site)
    df = _parse_date(d_from)
    dt = _parse_date(d_to)
    if df:
        stmt = stmt.where(DailyJob.work_date >= df)
    if dt:
        stmt = stmt.where(DailyJob.work_date <= dt)
    if q:
        stmt = stmt.where(
            DailyJob.driver_raw_name.contains(q)
            | DailyJob.customer_name_raw.contains(q)
            | DailyJob.plate_no_raw.contains(q)
            | DailyJob.origin.contains(q)
            | DailyJob.destination.contains(q)
        )
    if status:
        if status == "real":
            stmt = stmt.where(DailyJob.status_code.notin_(["idle", "placeholder", "leave"]))
        else:
            stmt = stmt.where(DailyJob.status_code == status)
    if missing:
        # exclude leave rows — they legitimately have 0 in both fields
        stmt = stmt.where(DailyJob.leave_status != "leave")
        ad_missing = (DailyJob.trip_fee_driver.is_(None) | (DailyJob.trip_fee_driver == 0))
        u_missing  = (DailyJob.revenue_customer.is_(None) | (DailyJob.revenue_customer == 0))
        # Smart: per-trip modes need AD; mao/lump modes need U
        trip_emp_ids = select(Employee.id).where(
            Employee.pay_mode.in_(["lcb_trip", "lcb_monthly", "ayu_trip", "ayu_trip_self_fuel", "bigc_trip"])
        )
        mao_emp_ids = select(Employee.id).where(
            Employee.pay_mode.in_(["lcb_mao", "ayu_mao", "lcb_lump"])
        )
        if missing == "ad":
            stmt = stmt.where(DailyJob.driver_id.in_(trip_emp_ids)).where(ad_missing)
        elif missing == "u":
            stmt = stmt.where(DailyJob.driver_id.in_(mao_emp_ids)).where(u_missing)
        elif missing == "any":
            stmt = stmt.where(
                (DailyJob.driver_id.in_(trip_emp_ids) & ad_missing) |
                (DailyJob.driver_id.in_(mao_emp_ids) & u_missing)
            )
    return stmt


@app.get("/daily/grid")
def daily_grid_page(request: Request):
    """หน้า Grid ถูกยุบรวมเข้า /daily แล้ว — redirect พร้อม query string เดิม (bookmark/preset เก่ายังใช้ได้)."""
    qs = request.url.query
    dest = "/daily" + (f"?{qs}" if qs else "")
    return RedirectResponse(url=dest, status_code=301)


@app.get("/api/daily/grid-data")
def daily_grid_data(
    request: Request = None,  # None = เรียกตรงจากโค้ด/เทสต์ (ข้าม filter P1)
    site: str = "",
    d_from: str = "",
    d_to: str = "",
    q: str = "",
    status: str = "",
    missing: str = "",
    limit: int = 400,
):
    from services.payroll import driver_calc_price
    # limit=0 → ไม่จำกัด (โหลดครบทุกแถวตามตัวกรอง) เพื่อให้ header-filter ในตารางกรองได้ครบ
    unlimited = limit <= 0
    stmt = _daily_grid_filters(
        select(DailyJob).order_by(DailyJob.work_date.desc(), DailyJob.id.desc()),
        site, d_from, d_to, q, status, missing,
    )
    if not unlimited:
        limit = max(1, min(800, limit))
        stmt = stmt.limit(limit)
    with Session(engine) as s:
        rows = s.exec(stmt).all()
        # Build pay_mode + linked-name maps for driver highlight / linked columns
        driver_ids = {r.driver_id for r in rows if r.driver_id}
        veh_ids = {r.head_vehicle_id for r in rows if r.head_vehicle_id} | {
            r.tail_vehicle_id for r in rows if r.tail_vehicle_id
        }
        cust_ids = {r.customer_id for r in rows if r.customer_id}
        pay_mode_map: dict[int, str] = {}
        driver_name_map: dict[int, str] = {}
        if driver_ids:
            emp_rows = s.exec(
                select(models.Employee.id, models.Employee.pay_mode, models.Employee.full_name)
                .where(models.Employee.id.in_(driver_ids))
            ).all()
            pay_mode_map = {e[0]: (e[1] or "") for e in emp_rows}
            driver_name_map = {e[0]: (e[2] or "") for e in emp_rows}
        plate_map: dict[int, str] = {}
        if veh_ids:
            veh_rows = s.exec(
                select(models.Vehicle.id, models.Vehicle.plate_no).where(models.Vehicle.id.in_(veh_ids))
            ).all()
            plate_map = {v[0]: (v[1] or "") for v in veh_rows}
        cust_name_map: dict[int, str] = {}
        if cust_ids:
            cust_rows = s.exec(
                select(models.Customer.id, models.Customer.name).where(models.Customer.id.in_(cust_ids))
            ).all()
            cust_name_map = {c[0]: (c[1] or "") for c in cust_rows}
        # ค่าต่อแถวจาก DailyJobFee — ดึงทีเดียวทั้งหน้า แล้ว bucket แยก:
        #  - เงินคนขับ (พิเศษ/OT/รับตู้คืนตู้) ผ่าน classify_driver_fee ตัวเดียวกับ engine
        #    → ตัวเลขตรงกับ payroll
        #  - ค่าบริษัท/สำรองจ่าย (ยกตู้/ผ่านลาน/คลีน/ชอร์/เข้าท่า/M-Flow) โชว์เฉย ๆ
        #    (ไม่เกี่ยวเงินคนขับ — เป็นคอลัมน์อ้างอิงให้ครบตามชีท)
        from services.payroll import classify_driver_fee
        COMPANY_FEE_TYPES = {
            "lift": "lift", "ค่ายกตู้": "lift",
            "yard": "yard", "ค่าผ่านลาน": "yard",
            "clean": "clean", "ค่าคลีน": "clean",
            "shore": "shore", "ค่าชอร์": "shore",
            "port_entry": "port_entry", "เข้าท่า": "port_entry",
            "mflow": "mflow", "m-flow": "mflow",
            "weighing": "weighing", "ค่าชั่งน้ำหนัก": "weighing",
        }
        _FEE_KEYS = ("special", "ot", "pickup_return",
                     "lift", "yard", "clean", "shore", "port_entry", "mflow", "weighing")
        job_ids = [r.id for r in rows if r.id]
        fee_map: dict[int, dict] = {}
        if job_ids:
            fee_rows = s.exec(
                select(DailyJobFee).where(DailyJobFee.daily_job_id.in_(job_ids))
            ).all()
            for f in fee_rows:
                bucket = classify_driver_fee(f.fee_type)
                if bucket is None:
                    bucket = COMPANY_FEE_TYPES.get((f.fee_type or "").strip().lower())
                if bucket is None:
                    continue
                d = fee_map.setdefault(f.daily_job_id, {k: 0.0 for k in _FEE_KEYS})
                d[bucket] += f.amount or 0.0
    data = [
        {
            "id": r.id,
            "work_date": r.work_date.isoformat() if r.work_date else "",
            "site_code": r.site_code or "",
            "driver_id": r.driver_id,
            "driver_raw_name": r.driver_raw_name or "",
            # ชื่อจริงจาก master — fallback เป็น raw เมื่อแถวยังไม่ link (กันแถวดูเหมือนว่าง)
            "driver_name": (driver_name_map.get(r.driver_id) if r.driver_id else "") or (r.driver_raw_name or ""),
            "pay_mode": pay_mode_map.get(r.driver_id, "") if r.driver_id else "",
            "head_vehicle_id": r.head_vehicle_id,
            "tail_vehicle_id": r.tail_vehicle_id,
            "plate_no_raw": r.plate_no_raw or "",
            "plate_no": (plate_map.get(r.head_vehicle_id) if r.head_vehicle_id else "") or (r.plate_no_raw or ""),
            "tail_plate_raw": r.tail_plate_raw or "",
            "tail_plate": (plate_map.get(r.tail_vehicle_id) if r.tail_vehicle_id else "") or (r.tail_plate_raw or ""),
            "customer_id": r.customer_id,
            "customer_name_raw": r.customer_name_raw or "",
            "customer_name": (cust_name_map.get(r.customer_id) if r.customer_id else "") or (r.customer_name_raw or ""),
            "trip_group_id": r.trip_group_id,
            "trip_type_code": r.trip_type_code or "",
            "origin": r.origin or "",
            "destination": r.destination or "",
            "pickup_location": r.pickup_location or "",
            "store_code": r.store_code or "",
            "truck_type_raw": r.truck_type_raw or "",
            "doc_no": r.doc_no or "",
            "job_ref": r.job_ref or "",
            "container_no": r.container_no or "",
            "container_size": r.container_size or "",
            "status_code": r.status_code or "",
            "leave_status": r.leave_status or "",
            "revenue_customer": float(r.revenue_customer or 0),
            "trip_fee_driver": float(r.trip_fee_driver or 0),
            "fee_special": round(fee_map.get(r.id, {}).get("special", 0.0), 2),
            "fee_ot": round(fee_map.get(r.id, {}).get("ot", 0.0), 2),
            "fee_pickup_return": round(fee_map.get(r.id, {}).get("pickup_return", 0.0), 2),
            "fee_lift": round(fee_map.get(r.id, {}).get("lift", 0.0), 2),
            "fee_yard": round(fee_map.get(r.id, {}).get("yard", 0.0), 2),
            "fee_clean": round(fee_map.get(r.id, {}).get("clean", 0.0), 2),
            "fee_shore": round(fee_map.get(r.id, {}).get("shore", 0.0), 2),
            "fee_port_entry": round(fee_map.get(r.id, {}).get("port_entry", 0.0), 2),
            "fee_mflow": round(fee_map.get(r.id, {}).get("mflow", 0.0), 2),
            "fee_weighing": round(fee_map.get(r.id, {}).get("weighing", 0.0), 2),
            "phone": r.phone or "",
            "shared_vehicle": r.shared_vehicle or "",
            "receive_inv_no": r.receive_inv_no or "",
            "bl_booking": r.bl_booking or "",
            "fuel_date": r.fuel_date.isoformat() if r.fuel_date else "",
            "gps_rate": float(r.gps_rate or 0),
            "kb_amount": float(r.kb_amount or 0),
            "price_override": (None if r.price_override is None else float(r.price_override)),
            "driver_calc_price": driver_calc_price(r),
            "fuel_liter": float(r.fuel_liter or 0),
            "fuel_amount": float(r.fuel_amount or 0),
            "fuel_station": r.fuel_station or "",
            "fuel_rate_km_per_l": float(r.fuel_rate_km_per_l or 0),
            "mile_snapshot": float(r.mile_snapshot or 0),
            "invoice_no": r.invoice_no or "",
            "invoice_date": r.invoice_date.isoformat() if r.invoice_date else "",
            "wht_53": float(r.wht_53 or 0),
            "remark": r.remark or "",
            "source": r.source or "",
            "created_at": r.created_at.isoformat(timespec="seconds") if r.created_at else "",
            "updated_at": r.updated_at.isoformat(timespec="seconds") if r.updated_at else "",
        }
        for r in rows
    ]
    # P1: ตัด field เงิน/KB ออกจาก payload สำหรับ role ที่ไม่มีสิทธิ์ —
    # ซ่อนแค่คอลัมน์ใน grid ไม่พอ (เปิด devtools ก็เห็น) ต้องไม่ส่งไปเลย
    if request is not None:
        if _part_level_of(request, "daily.kb_col") == "hide":
            for d in data:
                d.pop("kb_amount", None)
        if _part_level_of(request, "daily.money_cols") == "hide":
            for d in data:
                for f in ("revenue_customer", "trip_fee_driver", "price_override",
                          "driver_calc_price", "wht_53"):
                    d.pop(f, None)
    return {"items": data}


@app.post("/api/daily/grid-save")
async def daily_grid_save(request: Request):
    payload = await request.json()
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list) or not rows:
        return JSONResponse({"ok": False, "error": "no rows"}, status_code=400)

    # P1: role ที่ไม่มีสิทธิ์ edit ส่วนเงิน/KB — ห้ามเขียน field เหล่านั้น
    _blocked_fields: set = set()
    if _part_level_of(request, "daily.kb_col") != "edit":
        _blocked_fields |= {"kb_amount"}
    if _part_level_of(request, "daily.money_cols") != "edit":
        _blocked_fields |= {"revenue_customer", "trip_fee_driver",
                            "price_override", "wht_53"}

    editable = {
        "work_date",
        "site_code",
        "driver_id",
        "driver_raw_name",
        "head_vehicle_id",
        "tail_vehicle_id",
        "plate_no_raw",
        "tail_plate_raw",
        "customer_id",
        "customer_name_raw",
        "trip_group_id",
        "trip_type_code",
        "origin",
        "destination",
        "pickup_location",
        "store_code",
        "truck_type_raw",
        "doc_no",
        "job_ref",
        "container_no",
        "container_size",
        "status_code",
        "leave_status",
        "remark",
        "revenue_customer",
        "trip_fee_driver",
        "kb_amount",
        "price_override",
        "fuel_liter",
        "fuel_amount",
        "fuel_station",
        "fuel_rate_km_per_l",
        "mile_snapshot",
        "invoice_no",
        "invoice_date",
        "wht_53",
        "phone",
        "shared_vehicle",
        "receive_inv_no",
        "bl_booking",
        "fuel_date",
        "gps_rate",
    }
    allowed_leave = {k for k, _ in models.LEAVE_STATUS_CHOICES}

    _u = current_user(request)
    changed_by = (_u.username if _u else "") or "?"

    updated = 0
    saved_ids: list[int] = []
    errors: list[dict] = []
    audits: list[models.DailyJobAudit] = []
    adjustments_created = 0
    with Session(engine) as s:
        # C4: แก้ค่าเที่ยวของแถวที่อยู่ในรอบ finalize แล้ว (ห้าม recompute) →
        # ตั้งยอดตกหล่น (PayAdjustment) รอจ่ายเพิ่ม/หักคืนรอบถัดไปอัตโนมัติ
        fin_runs = s.exec(select(PayRun).where(PayRun.status == "finalized")).all()
        for item in rows:
            if not isinstance(item, dict):
                continue
            rid = _parse_int(str(item.get("id", "")))
            if not rid:
                continue
            row = s.get(DailyJob, rid)
            if not row:
                errors.append({"id": rid, "error": "not_found"})
                continue
            # snapshot ค่าเดิมของช่องที่ส่งมา → diff หลัง apply เพื่อบันทึก audit
            touched = [k for k in item.keys() if k in editable and k not in _blocked_fields]
            before_snap = {k: getattr(row, k, None) for k in touched}
            for key, val in item.items():
                if key not in editable:
                    continue
                if key in _blocked_fields:
                    errors.append({"id": rid, "error": f"no_permission:{key}"})
                    continue
                old_value = getattr(row, key, None)
                if key == "price_override":
                    # nullable: blank → None (ใช้ revenue_customer เป็นฐาน), ไม่ใช่ 0.0
                    text = (str(val) if val is not None else "").strip()
                    setattr(row, key, None if text == "" else _parse_float(text))
                    continue
                if key in (
                    "revenue_customer",
                    "trip_fee_driver",
                    "kb_amount",
                    "fuel_liter",
                    "fuel_amount",
                    "fuel_rate_km_per_l",
                    "mile_snapshot",
                    "wht_53",
                    "gps_rate",
                ):
                    setattr(row, key, _parse_float(str(val)))
                    continue
                if key in ("driver_id", "customer_id", "head_vehicle_id", "tail_vehicle_id", "trip_group_id"):
                    setattr(row, key, _parse_int(str(val)))
                    continue
                if key == "work_date":
                    parsed = _parse_date(str(val))
                    if not parsed:
                        errors.append({"id": rid, "error": "invalid work_date"})
                        continue
                    row.work_date = parsed
                    continue
                if key == "invoice_date":
                    text = (str(val) if val is not None else "").strip()
                    if not text:
                        row.invoice_date = None
                        continue
                    parsed = _parse_date(text)
                    if not parsed:
                        errors.append({"id": rid, "error": "invalid invoice_date"})
                        continue
                    row.invoice_date = parsed
                    continue
                if key == "invoice_no":
                    # กันเลขใบสกปรก (เคยเจอ 'KTIV2606-035\t19/6/2026' ทำจับกลุ่มพลาด)
                    row.invoice_no = _normalize_invoice_no(str(val or ""))
                    continue
                if key == "doc_no":
                    # กัน CSV artifact (เคยเจอ DHL doc_no ติด '\"' นำหน้าทั้งชุด)
                    row.doc_no = _normalize_doc_no(str(val or ""))
                    continue
                if key == "fuel_date":
                    text = (str(val) if val is not None else "").strip()
                    if not text:
                        row.fuel_date = None
                        continue
                    parsed = _parse_date(text)
                    if not parsed:
                        errors.append({"id": rid, "error": "invalid fuel_date"})
                        continue
                    row.fuel_date = parsed
                    continue
                text = (str(val) if val is not None else "").strip()
                if key == "leave_status" and text not in allowed_leave:
                    errors.append({"id": rid, "error": f"invalid leave_status={text}"})
                    continue
                setattr(row, key, text)
            # บันทึก audit เฉพาะช่องที่ค่าเปลี่ยนจริง
            for k in touched:
                ov, nv = before_snap.get(k), getattr(row, k, None)
                if (ov or "") != (nv or "") and ov != nv:
                    audits.append(models.DailyJobAudit(
                        daily_job_id=rid, changed_by=changed_by, action="edit",
                        field_name=k, old_value=("" if ov is None else str(ov)),
                        new_value=("" if nv is None else str(nv)),
                    ))
            # C4: engine จ่ายจาก Σ trip_fee_driver ทุก pay_mode → Δค่าเที่ยว
            # ของแถวในรอบ finalized = ยอดตกหล่นที่ต้องตามจ่าย/หักคืน
            if "trip_fee_driver" in touched and row.driver_id and row.work_date:
                old_fee = float(before_snap.get("trip_fee_driver") or 0.0)
                delta = round((row.trip_fee_driver or 0.0) - old_fee, 2)
                if abs(delta) >= 0.01:
                    fin = next((r for r in fin_runs
                                if r.site_code == row.site_code
                                and r.period_start <= row.work_date <= r.period_end),
                               None)
                    if fin:
                        s.add(PayAdjustment(
                            employee_id=row.driver_id, site_code=row.site_code,
                            source_run_id=fin.id, daily_job_id=row.id,
                            amount=delta, created_by=changed_by,
                            reason=(f"แก้ค่าเที่ยว {row.work_date:%d/%m/%Y} "
                                    f"{(row.plate_no_raw or '').strip()} หลังปิดรอบ "
                                    f"{fin.pay_cycle_tag} "
                                    f"({old_fee:,.2f}→{(row.trip_fee_driver or 0):,.2f})"),
                        ))
                        adjustments_created += 1
            row.updated_at = datetime.utcnow()
            s.add(row)
            try:
                rate_record_from_daily(s, row)
            except Exception:
                pass
            updated += 1
            saved_ids.append(rid)
        for a in audits:
            s.add(a)
        s.commit()
    return {"ok": True, "updated": updated, "saved_ids": saved_ids,
            "errors": errors, "audited": len(audits),
            "adjustments": adjustments_created}


def _normalize_invoice_no(raw: str) -> str:
    """เลขใบเข้ารูปแบบ → canonical 'PREFIXYYMM-###'; ไม่เข้ารูปแบบ = strip เฉยๆ.

    ใช้ตอนเซฟ grid + ปุ่มล้างใน /admin/data-clean — กันขยะท้ายช่อง (แท็บ/วันที่ปน).
    """
    from services.invoice_builder import parse_invoice_no

    p = parse_invoice_no(raw)
    if p:
        return f"{p[0]}{p[1]}-{p[2]:03d}"
    return (raw or "").strip()


def _normalize_doc_no(raw: str) -> str:
    """ตัด CSV artifact หัว-ท้าย doc_no (เช่น DHL '\"66144000327274/316') — เนื้อเลขไม่แตะ."""
    return (raw or "").strip().lstrip('="\'').rstrip('"\'').strip()


@app.get("/admin/data-clean", response_class=HTMLResponse)
def admin_data_clean(request: Request):
    """🧹 ความสะอาดข้อมูล: เลขใบ/เลข doc สกปรก (มีขยะหัว-ท้ายช่อง) — โชว์ก่อน ล้างเมื่อกดยืนยัน."""
    with Session(engine) as s:
        dirty = [j for j in s.exec(select(DailyJob).where(
            DailyJob.invoice_no != "")).all()
            if j.invoice_no != _normalize_invoice_no(j.invoice_no)]
        dirty_doc = [j for j in s.exec(select(DailyJob).where(
            DailyJob.doc_no != "")).all()
            if j.doc_no != _normalize_doc_no(j.doc_no)]
    ctx = base_context(request)
    ctx.update({"dirty": [{
        "id": j.id, "date": j.work_date, "site": j.site_code,
        "raw": j.invoice_no, "fixed": _normalize_invoice_no(j.invoice_no),
    } for j in dirty],
        "dirty_doc": [{
        "id": j.id, "date": j.work_date, "site": j.site_code,
        "raw": j.doc_no, "fixed": _normalize_doc_no(j.doc_no),
    } for j in dirty_doc]})
    return templates.TemplateResponse(request, "admin_data_clean.html", ctx)


@app.post("/admin/data-clean/fix-docnos")
def admin_data_clean_fix_docnos(request: Request):
    """ล้าง doc_no สกปรกทั้งหมด — audit ต่อแถว (DailyJobAudit) ย้อนดูได้."""
    u = current_user(request)
    n = 0
    with Session(engine) as s:
        for j in s.exec(select(DailyJob).where(DailyJob.doc_no != "")).all():
            fixed = _normalize_doc_no(j.doc_no)
            if fixed == j.doc_no:
                continue
            s.add(models.DailyJobAudit(
                daily_job_id=j.id, changed_by=(u.username if u else ""),
                action="data_clean", field_name="doc_no",
                old_value=j.doc_no, new_value=fixed))
            j.doc_no = fixed
            j.updated_at = datetime.utcnow()
            s.add(j)
            n += 1
        s.commit()
    return RedirectResponse(f"/admin/data-clean?fixed={n}", status_code=303)


@app.post("/admin/data-clean/fix-invoices")
def admin_data_clean_fix(request: Request):
    """ล้างเลขใบสกปรกทั้งหมด — audit ต่อแถว (DailyJobAudit) ย้อนดูได้."""
    u = current_user(request)
    n = 0
    with Session(engine) as s:
        for j in s.exec(select(DailyJob).where(DailyJob.invoice_no != "")).all():
            fixed = _normalize_invoice_no(j.invoice_no)
            if fixed == j.invoice_no:
                continue
            s.add(models.DailyJobAudit(
                daily_job_id=j.id, changed_by=(u.username if u else ""),
                action="data_clean", field_name="invoice_no",
                old_value=j.invoice_no, new_value=fixed))
            j.invoice_no = fixed
            j.updated_at = datetime.utcnow()
            s.add(j)
            n += 1
        s.commit()
    return RedirectResponse(f"/admin/data-clean?fixed={n}", status_code=303)


@app.get("/api/daily/{job_id}/media")
def daily_job_media(job_id: int):
    """รูปทั้งหมดที่ผูกกับแถวเดลี่: จากไลน์ (JobMedia/F3) + จากมือถือคนขับ (E1).

    ใช้กับเมนูคลิกขวา "ดูรูปงานนี้" ใน grid (P3).
    """
    items = []
    with Session(engine) as s:
        for jm in s.exec(select(models.JobMedia).where(
                models.JobMedia.daily_job_id == job_id,
                models.JobMedia.status == "linked")).all():
            items.append({"src": f"/line/media/{jm.line_message_pk}",
                          "kind": "ไลน์", "at": jm.at.strftime("%d/%m %H:%M"),
                          "by": jm.by_user})
        subs = s.exec(select(DriverSubmission).where(
            DriverSubmission.daily_job_id == job_id)).all()
        kind_th = dict(models.SUBMISSION_KINDS)
        for sub in subs:
            for p in (sub.photo_paths or "").split(","):
                p = p.strip()
                if p:
                    items.append({"src": f"/uploads/{p}",
                                  "kind": kind_th.get(sub.kind, sub.kind),
                                  "at": sub.submitted_at.strftime("%d/%m %H:%M"),
                                  "by": ""})
    return {"ok": True, "job_id": job_id, "items": items}


def audit_log(s: Session, request: Optional[Request], table_name: str, row_id: int,
              field: str, old, new, note: str = "") -> None:
    """P2: บันทึกจุดเขียนสำคัญที่ยังไม่มีตาราง audit เฉพาะ — INSERT-only.

    เรียกใน Session เดียวกันก่อน commit เพื่อให้ log กับข้อมูลไปด้วยกัน.
    """
    u = current_user(request) if request is not None else None
    s.add(models.AuditLog(
        user=u.username if u else "",
        table_name=table_name, row_id=int(row_id or 0), field=field,
        old_value="" if old is None else str(old),
        new_value="" if new is None else str(new),
        route=request.url.path if request is not None else "", note=note))


@app.get("/api/daily/{job_id}/audit")
def daily_job_audit(job_id: int, limit: int = 50, field: str = ""):
    """ประวัติการแก้ไขของแถวเดลี่นั้น (ล่าสุดก่อน) — field ระบุ = เฉพาะช่องนั้น (P2 คลิกขวา)."""
    with Session(engine) as s:
        stmt = select(models.DailyJobAudit).where(
            models.DailyJobAudit.daily_job_id == job_id)
        if field:
            stmt = stmt.where(models.DailyJobAudit.field_name == field)
        rows = s.exec(
            stmt.order_by(models.DailyJobAudit.changed_at.desc())
            .limit(max(1, min(200, limit)))
        ).all()
        return {
            "ok": True,
            "job_id": job_id,
            "rows": [
                {
                    "at": a.changed_at.strftime("%d/%m/%Y %H:%M"),
                    "by": a.changed_by,
                    "field": a.field_name,
                    "old": a.old_value,
                    "new": a.new_value,
                }
                for a in rows
            ],
        }


@app.get("/email/inbox", response_class=HTMLResponse)
def email_inbox(
    request: Request,
    status: str = "",
    category: str = "",
    site: str = "",
    q: str = "",
):
    scope = get_inbox_scope()
    has_refresh_token = bool(load_google_refresh_token())
    with Session(engine) as s:
        stmt = select(InboxEmail).order_by(InboxEmail.sent_at.desc(), InboxEmail.id.desc())
        if status:
            stmt = stmt.where(InboxEmail.status == status)
        if category:
            stmt = stmt.where(InboxEmail.category == category)
        if site:
            stmt = stmt.where(InboxEmail.suggested_site_code == site)
        if q:
            stmt = stmt.where(
                InboxEmail.subject.contains(q)
                | InboxEmail.from_email.contains(q)
                | InboxEmail.body_text.contains(q)
            )
        rows = s.exec(stmt.limit(300)).all()
        latest_run = s.exec(select(InboxSyncRun).order_by(InboxSyncRun.id.desc())).first()
    ctx = base_context(request)
    ctx.update(
        {
            "rows": rows,
            "status": status,
            "category": category,
            "site": site,
            "q": q,
            "latest_run": latest_run,
            "scope": scope,
            "has_refresh_token": has_refresh_token,
        }
    )
    return templates.TemplateResponse(request, "email_inbox.html", ctx)


@app.get("/email/oauth/start")
def email_oauth_start():
    state = new_oauth_state()
    url = build_authorize_url(state)
    resp = RedirectResponse(url=url, status_code=303)
    resp.set_cookie("email_oauth_state", state, max_age=600, httponly=True,
                    samesite="lax", secure=_secure_cookies)
    return resp


@app.get("/email/oauth/callback", response_class=HTMLResponse)
def email_oauth_callback(request: Request, code: str = "", state: str = ""):
    cookie_state = request.cookies.get("email_oauth_state", "")
    if not state or not cookie_state or state != cookie_state:
        raise HTTPException(400, "oauth state mismatch")
    if not code:
        raise HTTPException(400, "missing code")
    tokens = exchange_code_for_tokens(code)
    refresh_token = str(tokens.get("refresh_token") or "").strip()
    token_path = "(not updated - no refresh token in callback)"
    if refresh_token:
        token_path = str(save_google_refresh_token(refresh_token))
    _, _, redirect_uri = oauth_client_config()
    html = f"""
    <html><body style="font-family:Arial,sans-serif;padding:24px;">
      <h3>OAuth saved</h3>
      <p>Refresh token file: <code>{token_path}</code></p>
      <p>Set <code>EMAIL_IMAP_AUTH=oauth2</code> then open <a href="/email/inbox">/email/inbox</a> and Sync.</p>
      <p>Redirect URI used: <code>{redirect_uri}</code></p>
    </body></html>
    """
    resp = HTMLResponse(content=html)
    resp.delete_cookie("email_oauth_state")
    return resp


@app.get("/email/inbox/{mail_id}/draft-daily", response_class=HTMLResponse)
def email_inbox_draft_daily(mail_id: int, request: Request):
    with Session(engine) as s:
        mail = s.get(InboxEmail, mail_id)
        if not mail:
            raise HTTPException(404)
        employees, vehicles, customers = _load_masters(s)
    wd = mail.sent_at.date() if mail.sent_at else date.today()
    site = (mail.suggested_site_code or "").strip().upper() or "BIGC"
    body = (mail.body_text or "").strip()
    body_preview = body[:1200] + ("..." if len(body) > 1200 else "")
    draft_job = DailyJob(
        work_date=wd,
        site_code=site,
        customer_name_raw=(mail.suggested_customer or "").strip(),
        source="manual",
        remark=(
            f"[จากอีเมล inbox #{mail.id}]\n"
            f"หัวข้อ: {(mail.subject or '').strip()}\n"
            "---\n"
            f"{body_preview}"
        ),
    )
    preflight_warnings: list[str] = []
    preflight_warnings.append("ต้องยืนยันคนขับ/ทะเบียน/ลูกค้าก่อนบันทึกจริง (human confirm)")
    preflight_warnings.append("รายการจาก Inbox ยังไม่สร้างผลกระทบเงินอัตโนมัติจนกว่าจะกดบันทึก Daily")
    if not draft_job.driver_id:
        preflight_warnings.append("ยังไม่ได้เลือกพนักงานขับรถใน master (driver_id ว่าง)")
    if not draft_job.customer_id:
        preflight_warnings.append("ยังไม่ได้เลือกลูกค้าใน master (customer_id ว่าง)")
    if mail.has_attachment and len(body.strip()) < 30:
        preflight_warnings.append("อีเมลมีไฟล์แนบแต่ข้อความสั้นผิดปกติ ควรเปิดไฟล์แนบ/ต้นฉบับก่อนบันทึก")
    ctx = base_context(request)
    ctx.update(
        {
            "row": draft_job,
            "mode": "new",
            "employees": employees,
            "vehicles": vehicles,
            "customers": customers,
            "preflight_warnings": preflight_warnings,
            "inbox_mail_id": mail.id,
        }
    )
    return templates.TemplateResponse(request, "daily_form.html", ctx)


@app.post("/email/inbox/sync")
def email_inbox_sync():
    with Session(engine) as s:
        result = sync_inbox(s)
    suffix = "ok=1" if result.get("ok") else "ok=0"
    return RedirectResponse(url=f"/email/inbox?{suffix}", status_code=303)


@app.post("/email/inbox/{mail_id}/status")
def email_inbox_mark(mail_id: int, status: str = Form("reviewed")):
    if status not in {"new", "reviewed", "ignored", "linked"}:
        raise HTTPException(400, "invalid status")
    with Session(engine) as s:
        row = s.get(InboxEmail, mail_id)
        if not row:
            raise HTTPException(404)
        row.status = status
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url="/email/inbox", status_code=303)


@app.post("/email/inbox/{mail_id}/reclassify")
def email_inbox_reclassify(mail_id: int):
    with Session(engine) as s:
        row = s.get(InboxEmail, mail_id)
        if not row:
            raise HTTPException(404)
        classify_email_item(row)
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url="/email/inbox", status_code=303)


def _cycle_tag_for_site(site: str, d: date) -> str:
    """Backward-compatible site rule wrapper (used by legacy callers)."""
    return compute_pay_cycle_tag(site, d)


def _resolve_cycle_tag_for_driver(
    d: date,
    site_code: str,
    driver: Optional[Employee],
) -> tuple[str, str, str]:
    """Return (cycle_tag, policy_used, review_reason).

    review_reason values:
    - "" (ok)
    - "missing_driver"
    - "unclear_policy"
    """
    if driver is None:
        return compute_pay_cycle_tag(site_code, d), "site_default", "missing_driver"
    raw_policy = (driver.pay_cycle_policy or "").strip().lower()
    policy = normalize_pay_cycle_policy(raw_policy)
    tag = compute_pay_cycle_tag_by_policy(policy, d, site_code=driver.home_site_code or site_code)
    if raw_policy and raw_policy == policy:
        return tag, policy, ""
    if raw_policy in ("", "site_default"):
        return tag, "site_default", ""
    return tag, policy, "unclear_policy"


def _shift_year_month(year: int, month: int, delta: int) -> tuple[int, int]:
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return year, month


def _daily_site_preset_cycles(today: date) -> dict[str, dict[str, str]]:
    """Preset ranges for /daily and /daily/grid by payroll cycle intent.

    AYU: 26->25, LCB: 16->15, BIGC: 1->end (display intent T-1 month worked).
    """
    ayu_end_year, ayu_end_month = (today.year, today.month)
    if today.day >= 26:
        ayu_end_year, ayu_end_month = _shift_year_month(today.year, today.month, 1)
    ayu_start_year, ayu_start_month = _shift_year_month(ayu_end_year, ayu_end_month, -1)
    ayu_start = date(ayu_start_year, ayu_start_month, 26)
    ayu_end = date(ayu_end_year, ayu_end_month, 25)
    ayu_tag = f"{ayu_end_year:04d}-{ayu_end_month:02d}"

    lcb_end_year, lcb_end_month = (today.year, today.month)
    if today.day >= 16:
        lcb_end_year, lcb_end_month = _shift_year_month(today.year, today.month, 1)
    lcb_start_year, lcb_start_month = _shift_year_month(lcb_end_year, lcb_end_month, -1)
    lcb_start = date(lcb_start_year, lcb_start_month, 16)
    lcb_end = date(lcb_end_year, lcb_end_month, 15)
    lcb_tag = f"{lcb_end_year:04d}-{lcb_end_month:02d}"
    # Previous LCB cycle (T-1) — used for "missing values" button after cycle rollover
    lcb_prev_start_year, lcb_prev_start_month = _shift_year_month(lcb_start_year, lcb_start_month, -1)
    lcb_prev_start = date(lcb_prev_start_year, lcb_prev_start_month, 16)
    lcb_prev_end = lcb_start - __import__("datetime").timedelta(days=1)  # day before current cycle start

    bigc_year, bigc_month = _shift_year_month(today.year, today.month, -1)
    bigc_start, bigc_end = _month_bounds(bigc_year, bigc_month)
    bigc_tag = f"{bigc_year:04d}-{bigc_month:02d}"

    return {
        "AYU": {
            "start": ayu_start.isoformat(),
            "end": ayu_end.isoformat(),
            "tag": ayu_tag,
            "label": f"AYU รอบ {ayu_start.strftime('%d/%m')}–{ayu_end.strftime('%d/%m')}",
        },
        "BIGC": {
            "start": bigc_start.isoformat(),
            "end": bigc_end.isoformat(),
            "tag": bigc_tag,
            "label": f"BIGC เดือนวิ่ง {bigc_tag} (T-1)",
        },
        "LCB": {
            "start": lcb_start.isoformat(),
            "end": lcb_end.isoformat(),
            "tag": lcb_tag,
            "label": f"LCB รอบ {lcb_start.strftime('%d/%m')}–{lcb_end.strftime('%d/%m')}",
        },
        "LCB_prev": {
            "start": lcb_prev_start.isoformat(),
            "end": lcb_prev_end.isoformat(),
            "tag": f"{lcb_prev_end.year:04d}-{lcb_prev_end.month:02d}",
            "label": f"LCB รอบก่อน {lcb_prev_start.strftime('%d/%m')}–{lcb_prev_end.strftime('%d/%m')}",
        },
    }


def _site_payroll_cycles(site: str, today: date, n: int = 12) -> list[dict[str, str]]:
    """รายการรอบ payroll ของไซต์ที่เลือก (ใหม่→เก่า) สำหรับ dropdown ใน /daily.

    ขอบรอบต่อไซต์ (ตรงกับ CLAUDE.md): LCB 16→15, AYU 26→25, BIGC 1→สิ้นเดือน.
    `tag` = เดือนที่รอบจบ (YYYY-MM) — ใช้เป็น query param `cycle`.
    """
    site = (site or "").upper()
    cycles: list[dict[str, str]] = []
    # หาเดือนที่รอบ "ปัจจุบัน" จบ แล้วไล่ย้อนทีละเดือน
    if site == "BIGC":
        ey, em = today.year, today.month
        for _ in range(n):
            start, end = _month_bounds(ey, em)
            cycles.append({
                "tag": f"{ey:04d}-{em:02d}",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "label": f"BIGC {start.strftime('%d/%m')}–{end.strftime('%d/%m/%Y')}",
            })
            ey, em = _shift_year_month(ey, em, -1)
        return cycles
    # LCB / AYU = รอบคร่อมเดือน (start_day → end_day ของเดือนถัดไป)
    start_day, end_day, lbl = (16, 15, "LCB") if site == "LCB" else (26, 25, "AYU")
    ey, em = today.year, today.month
    if today.day >= start_day:                  # ผ่านวันเริ่มรอบแล้ว → รอบจบเดือนหน้า
        ey, em = _shift_year_month(ey, em, 1)
    for _ in range(n):
        sy, sm = _shift_year_month(ey, em, -1)
        start = date(sy, sm, start_day)
        end = date(ey, em, end_day)
        cycles.append({
            "tag": f"{ey:04d}-{em:02d}",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "label": f"{lbl} {start.strftime('%d/%m')}–{end.strftime('%d/%m/%Y')}",
        })
        ey, em = _shift_year_month(ey, em, -1)
    return cycles


def _parse_internal_path(raw: Optional[str]) -> Optional[str]:
    """Path ภายในแอปเท่านั้น — ไม่มี scheme/host."""
    s = (raw or "").strip()
    if not s.startswith("/") or s.startswith("//") or "\r" in s or "\n" in s or len(s) > 900:
        return None
    return s


def _safe_internal_path(raw: Optional[str], default: str = "/petty-cash") -> str:
    """ปลายทาง redirect ภายในเว็บเท่านั้น (กัน open redirect)."""
    return _parse_internal_path(raw) or default


@app.get("/petty-cash", response_class=HTMLResponse)
def petty_list(
    request: Request,
    site: str = "",
    d_from: str = "",
    d_to: str = "",
    driver: str = "",
    cat: str = "",
    dstatus: str = "",
    deduct: str = "",
    unlinked: str = "",
    review: str = "",
    cycle: str = "",
):
    from sqlalchemy import func as sa_func

    with Session(engine) as s:
        stmt = select(PettyCashTxn).order_by(PettyCashTxn.txn_date.desc(),
                                             PettyCashTxn.id.desc())
        count_stmt = select(sa_func.count(PettyCashTxn.id))
        sum_out_stmt = select(sa_func.coalesce(sa_func.sum(PettyCashTxn.amount), 0.0)).where(PettyCashTxn.direction == "out")
        sum_in_stmt = select(sa_func.coalesce(sa_func.sum(PettyCashTxn.amount), 0.0)).where(PettyCashTxn.direction == "in")
        ded_pending_stmt = select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(
            PettyCashTxn.deduct_from_driver == True,  # noqa: E712
            PettyCashTxn.deduction_status == "pending",
        )

        def apply_where(stmt_):
            from sqlalchemy import or_
            if site:
                stmt_ = stmt_.where(PettyCashTxn.site_code == site)
            df = _parse_date(d_from)
            dt = _parse_date(d_to)
            if df:
                stmt_ = stmt_.where(PettyCashTxn.txn_date >= df)
            if dt:
                stmt_ = stmt_.where(PettyCashTxn.txn_date <= dt)
            if cat:
                stmt_ = stmt_.where(PettyCashTxn.category == cat)
            if dstatus:
                stmt_ = stmt_.where(PettyCashTxn.deduction_status == dstatus)
            if deduct == "1":
                stmt_ = stmt_.where(PettyCashTxn.deduct_from_driver == True)  # noqa: E712
            drv_id = _parse_int(driver)
            if drv_id:
                stmt_ = stmt_.where(PettyCashTxn.driver_id == drv_id)
            if unlinked == "1":
                stmt_ = stmt_.where(PettyCashTxn.driver_id.is_(None))
            if review == "1":
                known_policies = [p[0] for p in models.PAY_CYCLE_POLICIES]
                unknown_policy_driver_ids = select(Employee.id).where(~Employee.pay_cycle_policy.in_(known_policies))
                stmt_ = stmt_.where(
                    or_(
                        PettyCashTxn.driver_id.is_(None),
                        PettyCashTxn.driver_id.in_(unknown_policy_driver_ids),
                    )
                )
            if cycle:
                stmt_ = stmt_.where(PettyCashTxn.pay_cycle_tag == cycle)
            return stmt_

        stmt = apply_where(stmt)
        count_stmt = apply_where(count_stmt)
        sum_out_stmt = apply_where(sum_out_stmt)
        sum_in_stmt = apply_where(sum_in_stmt)
        ded_pending_stmt = apply_where(ded_pending_stmt)

        total_rows = s.exec(count_stmt).one()
        total_out = float(s.exec(sum_out_stmt).one() or 0)
        total_in = float(s.exec(sum_in_stmt).one() or 0)
        total_deduct_pending = float(s.exec(ded_pending_stmt).one() or 0)

        cap = 2000
        capped = total_rows > cap
        rows = s.exec(stmt.limit(cap)).all()
        emp_map = {e.id: e for e in s.exec(select(Employee)).all()}
        employees = sorted(emp_map.values(), key=lambda e: (e.home_site_code, e.full_name))

    def disp(r: PettyCashTxn):
        drv = emp_map.get(r.driver_id) if r.driver_id else None
        auto_tag = ""
        policy_used = "site_default"
        review_reason = ""
        if r.txn_date:
            auto_tag, policy_used, review_reason = _resolve_cycle_tag_for_driver(
                r.txn_date,
                r.site_code,
                drv,
            )
        review_required = bool(review_reason or (r.pay_cycle_tag and auto_tag and r.pay_cycle_tag != auto_tag))
        reason_text = ""
        if review_reason == "missing_driver":
            reason_text = "ยังไม่ผูกคนขับ"
        elif review_reason == "unclear_policy":
            reason_text = "นโยบายรอบจ่ายไม่ชัดเจน"
        elif r.pay_cycle_tag and auto_tag and r.pay_cycle_tag != auto_tag:
            reason_text = f"แท็กรอบไม่ตรง policy ({r.pay_cycle_tag} -> {auto_tag})"
        return {
            "id": r.id,
            "txn_date": r.txn_date.isoformat() if r.txn_date else "",
            "site_code": r.site_code or "",
            "direction": r.direction or "",
            "amount": float(r.amount or 0),
            "requester": drv.full_name if drv else (r.requester_raw or ""),
            "driver_id": r.driver_id,
            "memo": r.memo or "",
            "category": r.category or "",
            "deduct_from_driver": bool(r.deduct_from_driver),
            "deduct_amount": float(r.deduct_amount or 0),
            "deduction_status": r.deduction_status or "",
            "pay_cycle_tag": r.pay_cycle_tag or "",
            "cycle_overridden": bool(r.pay_cycle_tag and auto_tag and r.pay_cycle_tag != auto_tag),
            "auto_cycle_tag": auto_tag,
            "policy_used": policy_used,
            "review_required": review_required,
            "review_reason": reason_text,
            "pending_amount": float(r.pending_amount or 0),
            "pending_cleared": r.pending_cleared_at is not None,
            "status": r.status or "",
        }

    display = [disp(r) for r in rows]
    ctx = base_context(request)
    # collect distinct pay_cycle_tag values for the dropdown
    with Session(engine) as s2:
        from sqlalchemy import func as sa_func2
        cycle_rows = s2.exec(
            select(PettyCashTxn.pay_cycle_tag, sa_func2.count(PettyCashTxn.id))
            .where(PettyCashTxn.pay_cycle_tag != "")
            .group_by(PettyCashTxn.pay_cycle_tag)
        ).all()
    cycle_options = sorted([(t, int(c or 0)) for t, c in cycle_rows if t], reverse=True)

    today = date.today()
    current_cycle_tag = f"{today.year:04d}-{today.month:02d}"

    ctx.update({
        "rows": display,
        "rows_json": json.dumps(display, ensure_ascii=False),
        "site": site, "d_from": d_from, "d_to": d_to,
        "driver": driver, "cat": cat, "dstatus": dstatus, "deduct": deduct, "unlinked": unlinked, "review": review,
        "cycle": cycle, "cycle_options": cycle_options,
        "employees": employees,
        "total_out": total_out, "total_in": total_in,
        "total_deduct_pending": total_deduct_pending,
        "total_rows": total_rows,
        "capped": capped,
        "current_cycle_tag": current_cycle_tag,
    })
    return templates.TemplateResponse(request, "petty_list.html", ctx)


@app.get("/petty-cash/new", response_class=HTMLResponse)
def petty_new(request: Request):
    with Session(engine) as s:
        employees = s.exec(select(Employee).order_by(Employee.home_site_code, Employee.full_name)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    ctx = base_context(request)
    ctx.update({"row": None, "mode": "new", "employees": employees, "vehicles": vehicles, "next_url": ""})
    return templates.TemplateResponse(request, "petty_form.html", ctx)


@app.get("/petty-cash/{txn_id}/edit", response_class=HTMLResponse)
def petty_edit(txn_id: int, request: Request):
    with Session(engine) as s:
        row = s.get(PettyCashTxn, txn_id)
        if not row:
            raise HTTPException(404)
        employees = s.exec(select(Employee).order_by(Employee.home_site_code, Employee.full_name)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    ctx = base_context(request)
    next_raw = request.query_params.get("next", "") or ""
    next_safe = _parse_internal_path(next_raw) or ""
    ctx.update(
        {
            "row": row,
            "mode": "edit",
            "employees": employees,
            "vehicles": vehicles,
            "next_url": next_safe,
        }
    )
    return templates.TemplateResponse(request, "petty_form.html", ctx)


@app.post("/petty-cash/new")
@app.post("/petty-cash/{txn_id}/edit")
def petty_save(
    request: Request,
    txn_id: Optional[int] = None,
    txn_date: str = Form(...),
    site_code: str = Form(...),
    direction: str = Form("out"),
    amount: str = Form("0"),
    requester_raw: str = Form(""),
    driver_id: str = Form(""),
    memo: str = Form(""),
    category: str = Form("other"),
    has_receipt: Optional[str] = Form(None),
    deduct_from_driver: Optional[str] = Form(None),
    deduct_amount: str = Form("0"),
    pay_cycle_tag: str = Form(""),
    linked_vehicle_plate_raw: str = Form(""),
    linked_vehicle_id: str = Form(""),
    linked_daily_job_id: str = Form(""),
    running_balance: str = Form("0"),
    note: str = Form(""),
    status: str = Form("posted"),
    pending_amount: str = Form("0"),
    pending_note: str = Form(""),
    pending_cleared_at: str = Form(""),
    deduction_status: str = Form("pending"),
    next_url: str = Form(""),
):
    td = _parse_date(txn_date)
    if not td:
        raise HTTPException(400, "txn_date invalid")
    with Session(engine) as s:
        if txn_id is None:
            row = PettyCashTxn(txn_date=td, site_code=site_code.strip().upper())
        else:
            row = s.get(PettyCashTxn, txn_id)
            if not row:
                raise HTTPException(404)
            if row.status == "locked":
                raise HTTPException(400, "ล็อครอบแล้ว แก้ไม่ได้")
            row.txn_date = td
            row.site_code = site_code.strip().upper()
        row.direction = direction
        row.amount = _parse_float(amount)
        row.requester_raw = requester_raw.strip()
        row.driver_id = _parse_int(driver_id)
        row.memo = memo.strip()
        row.category = category
        row.has_receipt = _parse_bool(has_receipt)
        row.deduct_from_driver = _parse_bool(deduct_from_driver)
        row.deduct_amount = _parse_float(deduct_amount) if row.deduct_from_driver else 0.0
        if pay_cycle_tag.strip():
            row.pay_cycle_tag = pay_cycle_tag.strip()
        else:
            resolved_tag, _, _ = _resolve_cycle_tag_for_driver(td, row.site_code, driver_obj)
            row.pay_cycle_tag = resolved_tag
        row.linked_vehicle_plate_raw = linked_vehicle_plate_raw.strip()
        row.linked_vehicle_id = _parse_int(linked_vehicle_id)
        row.linked_daily_job_id = _parse_int(linked_daily_job_id)
        row.running_balance = _parse_float(running_balance)
        row.note = note.strip()
        row.pending_amount = _parse_float(pending_amount)
        row.pending_note = pending_note.strip()
        row.pending_cleared_at = _parse_date(pending_cleared_at)
        # keep deduction_status in sync with driver-deduction flag
        if not row.deduct_from_driver:
            row.deduction_status = "pending"
        elif deduction_status in ("pending", "deducted", "settled_offline", "waived"):
            row.deduction_status = deduction_status
        row.status = status
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    nu = (next_url or "").strip()
    redir = _parse_internal_path(nu) or "/petty-cash"
    if nu and "/payroll/" in nu and "/employee/" in nu:
        sep = "&" if "?" in redir else "?"
        redir = f"{redir}{sep}petty_saved=1"
    return RedirectResponse(url=redir, status_code=303)


@app.post("/petty-cash/{txn_id}/delete")
def petty_delete(txn_id: int):
    with Session(engine) as s:
        row = s.get(PettyCashTxn, txn_id)
        if row:
            if row.status == "locked":
                raise HTTPException(400, "ล็อครอบแล้ว ลบไม่ได้")
            s.delete(row)
            s.commit()
    return RedirectResponse(url="/petty-cash", status_code=303)


def _shift_cycle_tag(cycle: str, delta: int) -> str:
    """เลื่อน pay_cycle_tag รูปแบบ 'YYYY-MM' ไปข้างหน้า/ข้างหลัง delta เดือน"""
    if not cycle or len(cycle) < 7 or "-" not in cycle:
        return cycle
    try:
        y, m = cycle[:4], cycle[5:7]
        year, month = int(y), int(m)
    except ValueError:
        return cycle
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    suffix = cycle[7:] if len(cycle) > 7 else ""
    return f"{year:04d}-{month:02d}{suffix}"


@app.post("/petty-cash/bulk-shift-cycle")
def petty_bulk_shift(
    ids: str = Form(""),
    target_cycle: str = Form(""),
    direction: str = Form(""),
    next_url: str = Form(""),
):
    """Bulk shift รอบหัก: รับ ids คั่นด้วย comma แล้วย้าย cycle.
    - target_cycle เช่น '2026-03' (set ตรงๆ)
    - direction='prev'/'next' (เลื่อน ±1 เดือนจาก cycle ปัจจุบันของแถว)
    """
    id_list: list[int] = []
    for tok in (ids or "").split(","):
        tok = tok.strip()
        if tok.isdigit():
            id_list.append(int(tok))
    if not id_list:
        return RedirectResponse(url=next_url or "/petty-cash", status_code=303)
    with Session(engine) as s:
        rows = s.exec(select(PettyCashTxn).where(PettyCashTxn.id.in_(id_list))).all()
        changed = 0
        for r in rows:
            if r.status == "locked":
                continue
            old = r.pay_cycle_tag or ""
            if target_cycle:
                r.pay_cycle_tag = target_cycle.strip()
            elif direction in ("prev", "next"):
                delta = -1 if direction == "prev" else 1
                r.pay_cycle_tag = _shift_cycle_tag(old, delta)
            else:
                continue
            r.updated_at = datetime.utcnow()
            note = (r.note or "").strip()
            tag = f"[bulk-shift {old}->{r.pay_cycle_tag}]"
            if tag not in note:
                r.note = (note + " " + tag).strip()
            s.add(r)
            changed += 1
        s.commit()
    return RedirectResponse(url=next_url or "/petty-cash", status_code=303)


@app.post("/petty-cash/{txn_id}/shift-cycle")
def petty_shift_cycle(txn_id: int, direction: str = Form("prev"), next_url: str = Form("")):
    """เลื่อนรอบหัก ±1 เดือน (ใช้ในกรณีที่หักรอบก่อน/รอบหน้าแทน)"""
    delta = -1 if direction == "prev" else 1
    with Session(engine) as s:
        row = s.get(PettyCashTxn, txn_id)
        if not row:
            raise HTTPException(404)
        if row.status == "locked":
            raise HTTPException(400, "ล็อครอบแล้ว แก้ไม่ได้")
        row.pay_cycle_tag = _shift_cycle_tag(row.pay_cycle_tag or "", delta)
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url=next_url or "/petty-cash", status_code=303)


@app.post("/petty-cash/{txn_id}/mark-settled")
def petty_mark_settled(txn_id: int, next_url: str = Form("")):
    """ทำเครื่องหมายว่าหักนอกระบบไปแล้ว (payroll จะข้าม)"""
    with Session(engine) as s:
        row = s.get(PettyCashTxn, txn_id)
        if not row:
            raise HTTPException(404)
        if row.status == "locked":
            raise HTTPException(400, "ล็อครอบแล้ว แก้ไม่ได้")
        if not row.deduct_from_driver:
            raise HTTPException(400, "รายการนี้ไม่ได้ตั้งให้หักคนขับ")
        row.deduction_status = "settled_offline"
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url=next_url or "/petty-cash", status_code=303)


@app.post("/petty-cash/{txn_id}/mark-pending")
def petty_mark_pending(txn_id: int, next_url: str = Form("")):
    """เปลี่ยนสถานะกลับเป็น 'รอหัก' (ยกเลิกการ settle/skip)"""
    with Session(engine) as s:
        row = s.get(PettyCashTxn, txn_id)
        if not row:
            raise HTTPException(404)
        if row.status == "locked":
            raise HTTPException(400, "ล็อครอบแล้ว แก้ไม่ได้")
        row.deduction_status = "pending"
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url=next_url or "/petty-cash", status_code=303)


@app.get("/petty-cash/pending", response_class=HTMLResponse)
def petty_pending(request: Request, cycle: str = "", site: str = ""):
    with Session(engine) as s:
        stmt = select(PettyCashTxn).where(
            PettyCashTxn.deduct_from_driver == True,  # noqa: E712
            PettyCashTxn.deduction_status == "pending",
        )
        if cycle:
            stmt = stmt.where(PettyCashTxn.pay_cycle_tag == cycle)
        if site:
            stmt = stmt.where(PettyCashTxn.site_code == site)
        rows = s.exec(stmt).all()
        emp_map = {e.id: e for e in s.exec(select(Employee)).all()}

    groups: dict[int, dict] = {}
    unassigned: list = []
    for r in rows:
        if not r.driver_id:
            unassigned.append(r)
            continue
        g = groups.setdefault(r.driver_id, {"driver": emp_map.get(r.driver_id), "items": [], "total": 0.0})
        g["items"].append(r)
        g["total"] += r.deduct_amount or 0.0
    summary = sorted(groups.values(),
                     key=lambda g: (g["driver"].home_site_code if g["driver"] else "",
                                    g["driver"].full_name if g["driver"] else ""))

    cycles_available = sorted({r.pay_cycle_tag for r in rows if r.pay_cycle_tag})
    ctx = base_context(request)
    ctx.update({
        "summary": summary, "unassigned": unassigned,
        "cycle": cycle, "site": site,
        "cycles_available": cycles_available,
        "grand_total": sum(g["total"] for g in summary) + sum(r.deduct_amount or 0.0 for r in unassigned),
    })
    return templates.TemplateResponse(request, "petty_pending.html", ctx)


@app.get("/petty-cash/clearance", response_class=HTMLResponse)
def petty_clearance(request: Request, site: str = ""):
    """Items with pending amount (รอใบเสร็จ/รอทอน) that are not yet cleared."""
    with Session(engine) as s:
        stmt = select(PettyCashTxn).where(
            PettyCashTxn.pending_amount > 0,
            PettyCashTxn.pending_cleared_at == None,  # noqa: E711
        )
        if site:
            stmt = stmt.where(PettyCashTxn.site_code == site)
        rows = s.exec(stmt.order_by(PettyCashTxn.txn_date.asc())).all()
        emp_map = {e.id: e for e in s.exec(select(Employee)).all()}

    display = []
    for r in rows:
        drv = emp_map.get(r.driver_id) if r.driver_id else None
        display.append({
            "id": r.id, "txn_date": r.txn_date, "site_code": r.site_code,
            "amount": r.amount, "category": r.category,
            "requester": drv.full_name if drv else r.requester_raw,
            "memo": r.memo,
            "pending_amount": r.pending_amount,
            "pending_note": r.pending_note,
            "days_old": (date.today() - r.txn_date).days if r.txn_date else 0,
        })
    total_pending = sum(d["pending_amount"] for d in display)
    ctx = base_context(request)
    ctx.update({"rows": display, "site": site, "total_pending": total_pending})
    return templates.TemplateResponse(request, "petty_clearance.html", ctx)


@app.get("/petty-cash/clearance/{txn_id}/clear")
def petty_clearance_mark(txn_id: int):
    with Session(engine) as s:
        row = s.get(PettyCashTxn, txn_id)
        if row:
            row.pending_cleared_at = date.today()
            row.updated_at = datetime.utcnow()
            s.add(row)
            s.commit()
    return RedirectResponse(url="/petty-cash/clearance", status_code=303)


@app.get("/api/cycle-tag")
def api_cycle_tag(site: str, d: str, driver_id: str = ""):
    """Helper for form UX: returns suggested pay_cycle_tag policy-first."""
    parsed = _parse_date(d)
    if not parsed:
        return {"tag": "", "policy_used": "site_default", "review_reason": "invalid_date"}
    with Session(engine) as s:
        driver = s.get(Employee, _parse_int(driver_id)) if _parse_int(driver_id) else None
    tag, policy_used, review_reason = _resolve_cycle_tag_for_driver(parsed, site, driver)
    return {"tag": tag, "policy_used": policy_used, "review_reason": review_reason}


@app.get("/api/daily-jobs/suggest")
def api_daily_jobs_suggest(
    d: str = "",
    driver_id: Optional[int] = None,
    driver_name: str = "",
    plate: str = "",
    site: str = "",
    window: int = 3,
    limit: int = 15,
):
    """Suggest likely DailyJob rows for linking a PettyCashTxn.

    Matches within ±window days of `d`. Scores candidates by:
      +3  driver_id match
      +2  driver_raw_name contains driver_name
      +2  plate matches head/tail plate (raw or master)
      +1  same site_code
      +0.5  closer date (inverse of day distance)
    Returns rows sorted by score desc, then |date diff| asc.
    """
    from datetime import timedelta

    center = _parse_date(d) if d else None
    q_driver_name = (driver_name or "").strip().lower()
    q_plate = (plate or "").strip().upper().replace(" ", "")
    q_plate = q_plate.replace("-", "")

    with Session(engine) as s:
        stmt = select(DailyJob)
        if center:
            lo = center - timedelta(days=window)
            hi = center + timedelta(days=window)
            stmt = stmt.where(DailyJob.work_date >= lo, DailyJob.work_date <= hi)
        stmt = stmt.order_by(DailyJob.work_date.desc()).limit(500)
        jobs = s.exec(stmt).all()

        veh_ids = {j.head_vehicle_id for j in jobs if j.head_vehicle_id}
        veh_ids |= {j.tail_vehicle_id for j in jobs if j.tail_vehicle_id}
        veh_map = {}
        if veh_ids:
            for v in s.exec(select(Vehicle).where(Vehicle.id.in_(veh_ids))).all():
                veh_map[v.id] = (v.plate_no or "").upper().replace("-", "").replace(" ", "")

        emp_ids = {j.driver_id for j in jobs if j.driver_id}
        emp_map = {}
        if emp_ids:
            for e in s.exec(select(Employee).where(Employee.id.in_(emp_ids))).all():
                emp_map[e.id] = e.full_name

        def plate_match(j):
            if not q_plate:
                return False
            candidates = [
                (j.plate_no_raw or "").upper().replace("-", "").replace(" ", ""),
                (j.tail_plate_raw or "").upper().replace("-", "").replace(" ", ""),
                veh_map.get(j.head_vehicle_id, ""),
                veh_map.get(j.tail_vehicle_id, ""),
            ]
            return any(c and q_plate in c for c in candidates if c)

        scored = []
        for j in jobs:
            score = 0.0
            why = []
            if driver_id and j.driver_id == driver_id:
                score += 3; why.append("driver")
            if q_driver_name:
                raw = (j.driver_raw_name or "").lower()
                master = emp_map.get(j.driver_id, "").lower()
                if q_driver_name in raw or q_driver_name in master or (raw and raw in q_driver_name):
                    score += 2; why.append("ชื่อ")
            if plate_match(j):
                score += 2; why.append("ทะเบียน")
            if site and j.site_code == site:
                score += 1; why.append("ไซท์")
            if center and j.work_date:
                diff = abs((j.work_date - center).days)
                score += max(0.0, 0.6 - diff * 0.15)
                date_diff = diff
            else:
                date_diff = 99

            if score <= 0:
                continue

            scored.append({
                "id": j.id,
                "work_date": j.work_date.isoformat() if j.work_date else "",
                "site_code": j.site_code,
                "driver": emp_map.get(j.driver_id, "") or j.driver_raw_name,
                "plate": j.plate_no_raw or veh_map.get(j.head_vehicle_id, ""),
                "route": f"{j.origin or ''}→{j.destination or ''}".strip("→"),
                "revenue": j.revenue_customer,
                "score": round(score, 2),
                "why": ",".join(why),
                "date_diff": date_diff,
            })

        scored.sort(key=lambda x: (-x["score"], x["date_diff"], -int(x["id"] or 0)))
        return {"items": scored[:limit]}


# ============================================================
#  FUEL MODULE
# ============================================================

@app.get("/fuel/anomaly", response_class=HTMLResponse)
def fuel_anomaly_page(request: Request, site: str = "", d_from: str = "", d_to: str = ""):
    """E2: รายงานน้ำมันผิดปกติ — read-only ไม่แก้เงินอัตโนมัติ (default = 30 วันหลังสุด)."""
    from services import fuel_anomaly as fa

    today = date.today()
    d2 = _parse_date(d_to) or today
    d1 = _parse_date(d_from) or (d2 - timedelta(days=30))
    with Session(engine) as s:
        data = fa.scan(s, d1, d2, site=site)
    ctx = base_context(request)
    ctx.update({"data": data, "site": site,
                "d_from": d1.isoformat(), "d_to": d2.isoformat()})
    return templates.TemplateResponse(request, "fuel_anomaly.html", ctx)


@app.get("/fuel/line-compare", response_class=HTMLResponse)
def fuel_line_compare_page(request: Request, days: int = 21):
    """F4 (ไม่ใช้ OCR): เทียบข้อความแจ้งเติมจากกลุ่มไลน์ปั๊ม ↔ FuelTxn — read-only.

    กลุ่มปั๊ม = LineGroupMap kind=station; คำสั่งเติมที่ใหม่กว่าข้อมูลน้ำมัน
    ในระบบขึ้นเป็น "รอ import" ไม่ใช่ตกหล่น (กันเตือนหลอกช่วง import ตามหลัง)."""
    from services import fuel_line_compare as flc
    from services import line_archive as la

    days = max(3, min(days, 60))
    ctx = base_context(request)
    error, data, orders = None, None, []
    with Session(engine) as s:
        station_groups = [m.group_id for m in s.exec(
            select(models.LineGroupMap)
            .where(models.LineGroupMap.kind == "station",
                   models.LineGroupMap.active == True)).all()]  # noqa: E712
        if la.db_path() is None:
            error = "ไม่พบคลังแชทบนเครื่องนี้ (line_archive.db) — ใช้ได้บนเครื่อง server"
        elif not station_groups:
            error = "ยังไม่มีกลุ่มปั๊มใน mapping — ไปตั้งชนิดกลุ่ม (ปั๊มน้ำมัน) ที่ /line/inbox ก่อน"
        else:
            try:
                orders = flc.fill_orders(station_groups, days=days)
                since = date.today() - timedelta(days=days + 1)
                txns = s.exec(select(FuelTxn)
                              .where(FuelTxn.txn_date >= since)).all()
                # ความสด import ต่างกันต่อไซท์ — ไซท์ของทะเบียนจาก Vehicle master
                plate_site = {v.plate_no.strip(): v.home_site_code
                              for v in s.exec(select(Vehicle)).all()}
                from sqlalchemy import func as sa_func
                site_fuel_max = {
                    k: (date.fromisoformat(v) if isinstance(v, str) else v)
                    for k, v in s.exec(
                        select(FuelTxn.site_code,
                               sa_func.max(FuelTxn.txn_date))
                        .group_by(FuelTxn.site_code)).all()}
                data = flc.compare(orders, txns, plate_site=plate_site,
                                   site_fuel_max=site_fuel_max)
            except Exception as e:  # noqa: BLE001 — โชว์เหตุบนหน้า
                error = f"อ่านคลังแชทไม่สำเร็จ: {e}"
    ctx.update({"days": days, "error": error, "data": data,
                "n_orders": len(orders)})
    return templates.TemplateResponse(request, "fuel_line_compare.html", ctx)


@app.get("/fuel", response_class=HTMLResponse)
def fuel_list(
    request: Request,
    site: str = "",
    d_from: str = "",
    d_to: str = "",
    plate: str = "",
    driver: str = "",
    station: str = "",
    source: str = "",
    linked: str = "",
):
    from sqlalchemy import func as sa_func

    with Session(engine) as s:
        stmt = select(FuelTxn).order_by(FuelTxn.txn_date.desc(), FuelTxn.id.desc())
        count_stmt = select(sa_func.count(FuelTxn.id))
        sum_l_stmt = select(sa_func.coalesce(sa_func.sum(FuelTxn.liter), 0.0))
        sum_b_stmt = select(sa_func.coalesce(sa_func.sum(FuelTxn.amount), 0.0))

        def apply_where(stmt_):
            if site:
                stmt_ = stmt_.where(FuelTxn.site_code == site)
            df = _parse_date(d_from)
            dt = _parse_date(d_to)
            if df:
                stmt_ = stmt_.where(FuelTxn.txn_date >= df)
            if dt:
                stmt_ = stmt_.where(FuelTxn.txn_date <= dt)
            if plate:
                stmt_ = stmt_.where(FuelTxn.plate_no_raw.contains(plate))
            if driver:
                stmt_ = stmt_.where(FuelTxn.driver_raw_name.contains(driver))
            if station:
                stmt_ = stmt_.where(FuelTxn.station.contains(station))
            if source:
                stmt_ = stmt_.where(FuelTxn.source == source)
            if linked == "yes":
                stmt_ = stmt_.where(FuelTxn.daily_job_id.isnot(None))
            elif linked == "no":
                stmt_ = stmt_.where(FuelTxn.daily_job_id.is_(None))
            return stmt_

        stmt = apply_where(stmt)
        count_stmt = apply_where(count_stmt)
        sum_l_stmt = apply_where(sum_l_stmt)
        sum_b_stmt = apply_where(sum_b_stmt)

        total_rows = s.exec(count_stmt).one()
        total_liter = float(s.exec(sum_l_stmt).one() or 0)
        total_amount = float(s.exec(sum_b_stmt).one() or 0)

        cap = 2000
        capped = total_rows > cap
        rows = s.exec(stmt.limit(cap)).all()

    avg_price = (total_amount / total_liter) if total_liter else 0
    import calendar

    def _fuel_row_json(r: FuelTxn) -> dict:
        return {
            "id": r.id,
            "txn_date": r.txn_date.isoformat() if r.txn_date else "",
            "site_code": r.site_code or "",
            "plate_no_raw": r.plate_no_raw or "",
            "driver_raw_name": r.driver_raw_name or "",
            "liter": float(r.liter or 0),
            "amount": float(r.amount or 0),
            "price_per_liter": float(r.price_per_liter or 0),
            "mile_snapshot": float(r.mile_snapshot or 0),
            "rate_km_per_l": float(r.rate_km_per_l or 0),
            "station": r.station or "",
            "fuel_grade": r.fuel_grade or "",
            "daily_job_id": r.daily_job_id,
            "source": r.source or "",
        }

    rows_json = json.dumps([_fuel_row_json(r) for r in rows], ensure_ascii=False)
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()
    current_cycle_tag = f"{today.year:04d}-{today.month:02d}"
    # E2: นับธงผิดปกติของช่วงที่ดูอยู่ → แบนเนอร์ลิงก์ไปรายงาน (ไม่กระทบเงิน)
    anomaly_n = 0
    try:
        from services import fuel_anomaly as fa
        _a_d2 = _parse_date(d_to) or today
        _a_d1 = _parse_date(d_from) or (_a_d2 - timedelta(days=30))
        with Session(engine) as s:
            anomaly_n = len(fa.scan(s, _a_d1, _a_d2, site=site)["rows"])
        anomaly_from, anomaly_to = _a_d1.isoformat(), _a_d2.isoformat()
    except Exception:
        anomaly_from = anomaly_to = ""
    ctx = base_context(request)
    ctx.update({
        "anomaly_n": anomaly_n,
        "anomaly_from": anomaly_from, "anomaly_to": anomaly_to,
        "rows": rows,
        "rows_json": rows_json,
        "site": site, "d_from": d_from, "d_to": d_to,
        "plate": plate, "driver": driver, "station": station,
        "source": source, "linked": linked,
        "total_rows": total_rows, "total_liter": total_liter,
        "total_amount": total_amount, "avg_price": avg_price,
        "capped": capped,
        "current_month_start": month_start,
        "current_month_end": month_end,
        "current_cycle_tag": current_cycle_tag,
    })
    return templates.TemplateResponse(request, "fuel_list.html", ctx)


@app.get("/fuel/new", response_class=HTMLResponse)
def fuel_new(request: Request):
    with Session(engine) as s:
        employees = s.exec(select(Employee).order_by(Employee.home_site_code, Employee.full_name)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    ctx = base_context(request)
    ctx.update({"mode": "new", "row": None, "today": date.today().isoformat(),
                "employees": employees, "vehicles": vehicles})
    return templates.TemplateResponse(request, "fuel_form.html", ctx)


@app.get("/fuel/{txn_id}/edit", response_class=HTMLResponse)
def fuel_edit(request: Request, txn_id: int):
    with Session(engine) as s:
        row = s.get(FuelTxn, txn_id)
        if not row:
            raise HTTPException(404)
        employees = s.exec(select(Employee).order_by(Employee.home_site_code, Employee.full_name)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    ctx = base_context(request)
    ctx.update({"mode": "edit", "row": row, "today": date.today().isoformat(),
                "employees": employees, "vehicles": vehicles})
    return templates.TemplateResponse(request, "fuel_form.html", ctx)


@app.post("/fuel/new")
@app.post("/fuel/{txn_id}/edit")
def fuel_save(
    request: Request,
    txn_id: Optional[int] = None,
    txn_date: str = Form(...),
    site_code: str = Form(""),
    plate_no_raw: str = Form(""),
    vehicle_id: str = Form(""),
    driver_raw_name: str = Form(""),
    driver_id: str = Form(""),
    liter: float = Form(0.0),
    amount: float = Form(0.0),
    price_per_liter: float = Form(0.0),
    rate_km_per_l: float = Form(0.0),
    mile_snapshot: float = Form(0.0),
    station: str = Form(""),
    fill_type: str = Form(""),
    fuel_grade: str = Form(""),
    daily_job_id: str = Form(""),
    note: str = Form(""),
):
    d = _parse_date(txn_date)
    if not d:
        raise HTTPException(400, "invalid txn_date")

    veh_id = _parse_int(vehicle_id)
    drv_id = _parse_int(driver_id)
    dj_id = _parse_int(daily_job_id)

    if price_per_liter == 0 and liter > 0 and amount > 0:
        price_per_liter = round(amount / liter, 4)

    with Session(engine) as s:
        if txn_id:
            row = s.get(FuelTxn, txn_id)
            if not row:
                raise HTTPException(404)
        else:
            row = FuelTxn(txn_date=d, source="manual")
            s.add(row)

        row.txn_date = d
        row.site_code = site_code
        row.plate_no_raw = plate_no_raw
        row.vehicle_id = veh_id
        row.driver_raw_name = driver_raw_name
        row.driver_id = drv_id
        row.liter = liter
        row.amount = amount
        row.price_per_liter = price_per_liter
        row.rate_km_per_l = rate_km_per_l
        row.mile_snapshot = mile_snapshot
        row.station = station
        row.fill_type = fill_type
        row.fuel_grade = fuel_grade
        row.daily_job_id = dj_id
        row.note = note

        s.commit()

    return RedirectResponse("/fuel", status_code=303)


@app.post("/fuel/{txn_id}/delete")
def fuel_delete(request: Request, txn_id: int):
    with Session(engine) as s:
        row = s.get(FuelTxn, txn_id)
        if row:
            s.delete(row)
            s.commit()
    return RedirectResponse("/fuel", status_code=303)


@app.post("/api/fuel/grid-save")
async def fuel_grid_save(request: Request):
    payload = await request.json()
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list) or not rows:
        return JSONResponse({"ok": False, "error": "no rows"}, status_code=400)
    editable = {"txn_date", "site_code", "plate_no_raw", "driver_raw_name",
                "liter", "amount", "price_per_liter", "rate_km_per_l",
                "mile_snapshot", "station", "fuel_grade"}
    updated = 0
    errors: list[dict] = []
    with Session(engine) as s:
        for item in rows:
            if not isinstance(item, dict):
                continue
            rid = _parse_int(str(item.get("id", "")))
            if not rid:
                continue
            row = s.get(FuelTxn, rid)
            if not row:
                errors.append({"id": rid, "error": "not_found"})
                continue
            for key, val in item.items():
                if key not in editable:
                    continue
                if key in ("liter", "amount", "price_per_liter", "rate_km_per_l", "mile_snapshot"):
                    try:
                        setattr(row, key, float(val) if val not in (None, "") else None)
                    except (TypeError, ValueError):
                        pass
                elif key == "txn_date":
                    parsed = _parse_date(str(val or ""))
                    if parsed:
                        row.txn_date = parsed
                else:
                    setattr(row, key, str(val or "").strip() or None)
            try:
                s.add(row)
                s.commit()
                updated += 1
            except Exception as exc:
                s.rollback()
                errors.append({"id": rid, "error": str(exc)})
    return JSONResponse({"ok": True, "updated": updated, "errors": errors})


@app.post("/api/petty/grid-save")
async def petty_grid_save(request: Request):
    payload = await request.json()
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list) or not rows:
        return JSONResponse({"ok": False, "error": "no rows"}, status_code=400)
    editable = {"txn_date", "site_code", "direction", "amount", "memo", "category",
                "pay_cycle_tag", "deduct_amount"}
    updated = 0
    errors: list[dict] = []
    with Session(engine) as s:
        for item in rows:
            if not isinstance(item, dict):
                continue
            rid = _parse_int(str(item.get("id", "")))
            if not rid:
                continue
            row = s.get(PettyCashTxn, rid)
            if not row:
                errors.append({"id": rid, "error": "not_found"})
                continue
            if row.status == "locked":
                errors.append({"id": rid, "error": "locked"})
                continue
            for key, val in item.items():
                if key not in editable:
                    continue
                if key in ("amount", "deduct_amount"):
                    try:
                        setattr(row, key, float(val) if val not in (None, "") else None)
                    except (TypeError, ValueError):
                        pass
                elif key == "txn_date":
                    parsed = _parse_date(str(val or ""))
                    if parsed:
                        row.txn_date = parsed
                else:
                    setattr(row, key, str(val or "").strip() or None)
            try:
                s.add(row)
                s.commit()
                updated += 1
            except Exception as exc:
                s.rollback()
                errors.append({"id": rid, "error": str(exc)})
    return JSONResponse({"ok": True, "updated": updated, "errors": errors})


@app.post("/api/petty/ingest")
async def petty_ingest(request: Request):
    """Service endpoint: the LINE slip-reader pushes AI-read draft entries here.

    Auth is a shared service token (X-Service-Token), NOT a session login — this
    runs from the slip-reader service, not a browser. Every row lands as
    status=pending_review for a human to approve on /petty/review. Idempotent by
    slip_line_message_id so re-running the reader never double-posts.
    """
    expected = os.environ.get("YK_SLIP_INGEST_TOKEN", "")
    if not expected or request.headers.get("X-Service-Token") != expected:
        raise HTTPException(status_code=401, detail="bad service token")
    body = await request.json()
    msg_id = str(body.get("slip_line_message_id", "")).strip()
    if not msg_id:
        return JSONResponse({"status": "error", "error": "missing slip_line_message_id"},
                            status_code=400)
    txn_date = _parse_date(str(body.get("txn_date", "")))
    if not txn_date:
        return JSONResponse({"status": "error", "error": "bad txn_date"}, status_code=400)
    with Session(engine) as s:
        existing = s.exec(select(PettyCashTxn).where(
            PettyCashTxn.slip_line_message_id == msg_id)).first()
        if existing:
            return JSONResponse({"status": "duplicate", "id": existing.id})
        t = PettyCashTxn(
            txn_date=txn_date,
            site_code=str(body.get("site_code", "")).strip(),
            direction=str(body.get("direction", "out")).strip() or "out",
            amount=float(body.get("amount") or 0.0),
            category=str(body.get("category", "other")).strip() or "other",
            requester_raw=str(body.get("requester_raw", "")).strip(),
            memo=str(body.get("memo", "")).strip(),
            status="pending_review", source="line_slip",
            slip_line_message_id=msg_id,
            slip_media_path=str(body.get("slip_media_path", "")).strip(),
            slip_ref_code=str(body.get("slip_ref_code", "")).strip(),
            parsed_confidence=float(body.get("parsed_confidence") or 0.0),
            parsed_payload_json=str(body.get("parsed_payload_json", "")),
        )
        s.add(t); s.commit(); s.refresh(t)
        return JSONResponse({"status": "created", "id": t.id})


@app.get("/petty/review", response_class=HTMLResponse)
def petty_review(request: Request):
    """Human review queue for AI-read slip drafts (admin/office, LCB only).

    Money rule: AI never posts directly. Drafts sit at pending_review until a
    person approves here. RBAC is governed by the 'petty' menu (see permissions).
    """
    with Session(engine) as s:
        rows = s.exec(select(PettyCashTxn).where(
            PettyCashTxn.status == "pending_review",
            PettyCashTxn.site_code == "LCB",
        ).order_by(PettyCashTxn.txn_date, PettyCashTxn.id)).all()
    ctx = base_context(request)
    ctx["rows"] = rows
    return templates.TemplateResponse(request, "petty_review.html", ctx)


@app.post("/petty/review/{pid}/approve")
async def petty_review_approve(pid: int, request: Request):
    form = await request.form()
    with Session(engine) as s:
        t = s.get(PettyCashTxn, pid)
        if t and t.status == "pending_review":
            if form.get("amount"):
                try:
                    t.amount = float(form["amount"])
                except (TypeError, ValueError):
                    pass
            if form.get("requester_raw"):
                t.requester_raw = str(form["requester_raw"]).strip()
            if form.get("category"):
                t.category = str(form["category"]).strip()
            if form.get("memo"):
                t.memo = str(form["memo"]).strip()
            t.status = "posted"
            s.add(t); s.commit()
    return RedirectResponse("/petty/review", status_code=303)


@app.post("/petty/review/{pid}/reject")
def petty_review_reject(pid: int):
    with Session(engine) as s:
        t = s.get(PettyCashTxn, pid)
        if t and t.status == "pending_review":
            t.status = "draft"
            s.add(t); s.commit()
    return RedirectResponse("/petty/review", status_code=303)


# ==========================================================================
# Slip-reader control — โอ turns the LCB auto-reader on/off from the MVP.
# Page routes (/petty/slip-control*) are session UI (petty menu: admin/office).
# Service routes (/api/petty/slip-config*) are service-token (the reader polls them).
# OFF = the reader makes zero Anthropic calls (the money guarantee).
# ==========================================================================

SLIP_ENABLED_KEY   = "slip_reader_enabled"     # "1"/"0", default "0" (OFF)
SLIP_SINCE_KEY     = "slip_reader_since"        # "YYYY-MM-DD" or "" (continue from rolling window)
SLIP_RUNNOW_KEY    = "slip_reader_run_now"      # "1" one-shot "check now"
SLIP_LASTRUN_KEY   = "slip_reader_last_run"     # ISO datetime of last reader poll
SLIP_LASTRESULT_KEY = "slip_reader_last_result" # short human text


def _slip_token_ok(request: Request) -> bool:
    expected = os.environ.get("YK_SLIP_INGEST_TOKEN", "")
    return bool(expected) and request.headers.get("X-Service-Token") == expected


@app.get("/api/petty/slip-config")
def slip_config_get(request: Request):
    """Service endpoint: the reader calls this BEFORE any API work to learn if it's
    enabled and from what date. Token-gated (same as ingest)."""
    if not _slip_token_ok(request):
        raise HTTPException(status_code=401, detail="bad service token")
    return {
        "enabled": get_setting(SLIP_ENABLED_KEY, "0") == "1",
        "since": get_setting(SLIP_SINCE_KEY, ""),
        "run_now": get_setting(SLIP_RUNNOW_KEY, "0") == "1",
    }


@app.post("/api/petty/slip-config/report")
async def slip_config_report(request: Request):
    """Service endpoint: the reader posts its run result back + acks the run_now flag."""
    if not _slip_token_ok(request):
        raise HTTPException(status_code=401, detail="bad service token")
    body = await request.json()
    set_setting(SLIP_LASTRUN_KEY, datetime.utcnow().isoformat(timespec="seconds"))
    set_setting(SLIP_LASTRESULT_KEY, str(body.get("result", ""))[:200])
    if body.get("ack_run_now"):
        set_setting(SLIP_RUNNOW_KEY, "0")
    return {"status": "ok"}


@app.get("/petty/slip-control", response_class=HTMLResponse)
def slip_control(request: Request):
    """Admin/office page: on/off switch, read-since, check-now, and status."""
    ctx = base_context(request)
    ctx["slip_enabled"] = get_setting(SLIP_ENABLED_KEY, "0") == "1"
    ctx["slip_since"] = get_setting(SLIP_SINCE_KEY, "")
    ctx["slip_run_now"] = get_setting(SLIP_RUNNOW_KEY, "0") == "1"
    ctx["slip_last_run"] = get_setting(SLIP_LASTRUN_KEY, "")
    ctx["slip_last_result"] = get_setting(SLIP_LASTRESULT_KEY, "")
    return templates.TemplateResponse(request, "slip_control.html", ctx)


@app.post("/petty/slip-control/toggle")
async def slip_control_toggle(request: Request):
    form = await request.form()
    set_setting(SLIP_ENABLED_KEY, "1" if form.get("enable") == "1" else "0")
    return RedirectResponse("/petty/slip-control", status_code=303)


@app.post("/petty/slip-control/since")
async def slip_control_since(request: Request):
    form = await request.form()
    raw = str(form.get("since", "")).strip()
    # Accept blank (continue from rolling window) or a valid ISO date; ignore garbage.
    set_setting(SLIP_SINCE_KEY, raw if (not raw or _parse_date(raw)) else
                get_setting(SLIP_SINCE_KEY, ""))
    return RedirectResponse("/petty/slip-control", status_code=303)


@app.post("/petty/slip-control/run-now")
def slip_control_run_now():
    set_setting(SLIP_RUNNOW_KEY, "1")
    return RedirectResponse("/petty/slip-control", status_code=303)


# ==========================================================================
# /admin/promote — Promote raw driver names / plates into Master
# ==========================================================================

from services.promote import (  # noqa: E402
    survey_unpromoted_drivers,
    survey_unpromoted_plates,
    promote_drivers,
    promote_vehicles,
)


@app.get("/admin/promote", response_class=HTMLResponse)
def admin_promote(request: Request, tab: str = "drivers"):
    from sqlalchemy import func as sa_func
    with Session(engine) as s:
        drivers = survey_unpromoted_drivers(s) if tab == "drivers" else []
        plates = survey_unpromoted_plates(s) if tab == "plates" else []

        total_drv_raw = s.exec(select(sa_func.count(DailyJob.id)).where(DailyJob.driver_id.is_(None))).one()
        total_drv_raw += s.exec(select(sa_func.count(PettyCashTxn.id)).where(PettyCashTxn.driver_id.is_(None))).one()
        total_drv_raw += s.exec(select(sa_func.count(FuelTxn.id)).where(FuelTxn.driver_id.is_(None))).one()
        total_plt_raw = s.exec(select(sa_func.count(DailyJob.id)).where(DailyJob.head_vehicle_id.is_(None))).one()
        total_plt_raw += s.exec(select(sa_func.count(FuelTxn.id)).where(FuelTxn.vehicle_id.is_(None))).one()

        emp_count = s.exec(select(sa_func.count(Employee.id))).one()
        veh_count = s.exec(select(sa_func.count(Vehicle.id))).one()

    ctx = base_context(request)
    ctx.update({
        "tab": tab,
        "drivers": drivers, "plates": plates,
        "total_drv_raw": total_drv_raw, "total_plt_raw": total_plt_raw,
        "emp_count": emp_count, "veh_count": veh_count,
        # override pay_modes with (code, label) pairs; template now expects tuples
        "pay_modes": models.PAY_MODES,
    })
    return templates.TemplateResponse(request, "admin_promote.html", ctx)


@app.post("/admin/promote/drivers")
async def admin_promote_drivers(request: Request):
    form = await request.form()
    # form fields per row: pick_<key>=on, full_<key>=..., nick_<key>=...,
    # site_<key>=..., paymode_<key>=..., variants_<key>=JSON
    selections: list[dict] = []
    import json
    picked_keys = [k[5:] for k in form.keys() if k.startswith("pick_") and form.get(k) == "on"]
    for key in picked_keys:
        try:
            variants = json.loads(form.get(f"variants_{key}", "[]"))
        except (ValueError, TypeError):
            variants = []
        selections.append({
            "variants": variants,
            "full_name": form.get(f"full_{key}", "").strip(),
            "nickname": form.get(f"nick_{key}", "").strip(),
            "home_site_code": form.get(f"site_{key}", "").strip(),
            "pay_mode": form.get(f"paymode_{key}", "").strip(),
            "role": form.get(f"role_{key}", "driver").strip() or "driver",
        })
    with Session(engine) as s:
        created, filled = promote_drivers(s, selections, _gen_next_code)
    return RedirectResponse(
        f"/admin/promote?tab=drivers&created={created}&filled={filled}",
        status_code=303,
    )


@app.post("/admin/promote/vehicles")
async def admin_promote_vehicles(request: Request):
    form = await request.form()
    selections: list[dict] = []
    picked_keys = [k[5:] for k in form.keys() if k.startswith("pick_") and form.get(k) == "on"]
    for key in picked_keys:
        selections.append({
            "plate_no": form.get(f"plate_{key}", "").strip(),
            "home_site_code": form.get(f"site_{key}", "").strip(),
            "truck_type": form.get(f"type_{key}", "").strip(),
        })
    with Session(engine) as s:
        created, filled = promote_vehicles(s, selections, _gen_next_code)
    return RedirectResponse(
        f"/admin/promote?tab=plates&created={created}&filled={filled}",
        status_code=303,
    )


# ==========================================================================
# PAYROLL
# ==========================================================================

from services.payroll import (
    get_or_create_pay_run,
    compute_pay_run,
    compute_pay_cycle_tag,
    compute_pay_cycle_tag_by_policy,
    normalize_pay_cycle_policy,
)


@app.get("/payroll", response_class=HTMLResponse)
def payroll_list(
    request: Request,
    site: str = "",
    cycle: str = "",
    status: str = "",
):
    from sqlalchemy import func as sa_func
    with Session(engine) as s:
        stmt = select(PayRun).order_by(PayRun.pay_cycle_tag.desc(), PayRun.site_code)
        if site:
            stmt = stmt.where(PayRun.site_code == site)
        if cycle:
            stmt = stmt.where(PayRun.pay_cycle_tag == cycle)
        if status:
            stmt = stmt.where(PayRun.status == status)

        runs = s.exec(stmt).all()
        summary = []
        for pr in runs:
            items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
            total_gross = sum((it.gross_total or 0) for it in items)
            total_ded = sum((it.deduction_total or 0) for it in items)
            total_net = sum((it.net_pay or 0) for it in items)
            summary.append({
                "run": pr,
                "count": len(items),
                "gross": total_gross,
                "ded": total_ded,
                "net": total_net,
            })
        cycle_rows = s.exec(
            select(PayRun.pay_cycle_tag, sa_func.count(PayRun.id))
            .group_by(PayRun.pay_cycle_tag)
            .order_by(PayRun.pay_cycle_tag.desc())
        ).all()
        cycle_options = [(t, int(c or 0)) for t, c in cycle_rows if t]
    today = date.today()
    current_cycle_tag = f"{today.year:04d}-{today.month:02d}"
    ctx = base_context(request)
    ctx.update(
        {
            "summary": summary,
            "site": site,
            "cycle": cycle,
            "status": status,
            "cycle_options": cycle_options,
            "current_cycle_tag": current_cycle_tag,
        }
    )
    return templates.TemplateResponse(request, "payroll_list.html", ctx)


@app.get("/payroll/manual-slip", response_class=HTMLResponse)
def payroll_manual_slip(request: Request, emp_id: int = 0, run_ids: str = ""):
    """สลิปเขียนเอง (โอ 7ก.ค.) — ทำสลิปย้อนหลังช่วงข้อมูลระบบยังไม่ครบ: ทุกช่อง
    พิมพ์แก้ได้ + เลือกพนักงานเติมข้อมูลที่มี (ชื่อ/รหัส/เลขบัตร/บัญชี) แล้วพิมพ์.
    run_ids=1,2 → ดึงตัวเลขจริงจาก PayRunItem ของรอบพวกนั้น หลายเดือน = หลายสลิป
    ในหน้าเดียว (แก้ต่อได้ก่อนพิมพ์). ไม่เขียนอะไรลง DB.
    NB: literal path ต้องมาก่อน /payroll/{run_id} (ไม่งั้นโดนดักเป็น run_id)."""
    # (label, field) เรียงแบบสลิปจริง — โชว์เฉพาะค่าที่ไม่เป็นศูนย์
    _INC = [("เงินเดือน", "base_salary_earned"), ("ค่าดูแลรถ", "care_allowance_earned"),
            ("ค่าเที่ยว", "trip_fee_total"), ("เหมา (60% ค่าขนส่ง)", "fuel_share_income"),
            ("ค่าเรทน้ำมัน", "fuel_rate_income"), ("ชดเชยการันตี", "guarantee_topup"),
            ("พิเศษ", "special_income"), ("OT", "ot_income"),
            ("รับตู้คืนตู้", "pickup_return_income")]
    _DED = [("ค่าน้ำมัน (หักจริง)", "fuel_cost_self"), ("ประกันสังคม", "social_security"),
            ("ภาษีหัก ณ ที่จ่าย", "income_tax_withholding"),
            ("เงินประกันตน (ผ่อน)", "deposit_install"), ("ผ่อนอุบัติเหตุ", "accident_install"),
            ("เงินเบิก / สดย่อย", "petty_cash_deduction"), ("หักอื่นๆ", "other_deduction")]

    ctx = base_context(request)
    with Session(engine) as s:
        emps = s.exec(select(Employee).where(Employee.status == "active")
                      .order_by(Employee.home_site_code, Employee.full_name)).all()
        emp = s.get(Employee, emp_id) if emp_id else None
        emp_runs, slips = [], []
        if emp:
            rows = s.exec(
                select(PayRun, PayRunItem)
                .where(PayRunItem.pay_run_id == PayRun.id,
                       PayRunItem.employee_id == emp.id)
                .order_by(PayRun.period_end.desc())).all()
            emp_runs = [pr for pr, _ in rows]
            wanted = {int(x) for x in run_ids.split(",") if x.strip().isdigit()}
            for pr, it in rows:
                if pr.id not in wanted:
                    continue
                inc = [(lb, getattr(it, f) or 0) for lb, f in _INC if (getattr(it, f) or 0)]
                rest = (it.other_income or 0) - (it.special_income or 0) \
                    - (it.ot_income or 0) - (it.pickup_return_income or 0)
                if round(rest, 2):
                    inc.append(("รายได้อื่น", rest))
                ded = [(lb, getattr(it, f) or 0) for lb, f in _DED if (getattr(it, f) or 0)]
                # วันที่จ่ายจริง (โอเคาะ 6ก.ค.): AYU = สิ้นเดือนที่รอบจบ;
                # LCB/BIGC = วันที่ 1 ของเดือนถัดจากรอบจบ
                pe = pr.period_end
                if pr.site_code == "AYU":
                    _nm = date(pe.year + (pe.month == 12), pe.month % 12 + 1, 1)
                    paydate = _nm - timedelta(days=1)
                else:
                    paydate = date(pe.year + (pe.month == 12), pe.month % 12 + 1, 1)
                slips.append({"run": pr, "inc": inc, "ded": ded, "paydate": paydate})
            slips.sort(key=lambda x: x["run"].period_start)
    ctx.update({"emps": emps, "emp": emp, "emp_runs": emp_runs, "slips": slips,
                "run_ids": run_ids})
    return templates.TemplateResponse(request, "payroll_manual_slip.html", ctx)


@app.get("/payroll/new", response_class=HTMLResponse)
def payroll_new_form(request: Request):
    from datetime import date as _d
    ctx = base_context(request)
    today = _d.today()
    default_tag = f"{today.year:04d}-{today.month:02d}"
    ctx.update({"default_tag": default_tag})
    return templates.TemplateResponse(request, "payroll_new.html", ctx)


@app.post("/payroll/new")
async def payroll_new(request: Request):
    form = await request.form()
    site_code = (form.get("site_code") or "").strip().upper()
    tag = (form.get("tag") or "").strip()
    notes = (form.get("notes") or "").strip()
    if site_code not in ("AYU", "BIGC", "LCB") or not tag:
        return RedirectResponse("/payroll/new?err=1", status_code=303)
    with Session(engine) as s:
        pr = get_or_create_pay_run(s, site_code, tag, notes=notes)
        compute_pay_run(s, pr, recompute=True)
        pr_id = pr.id
    return RedirectResponse(f"/payroll/{pr_id}", status_code=303)


def _petty_unlinked_predicates_for_payrun(pr: "PayRun"):
    """Predicates for petty rows: pending driver-deduction, no driver_id, same cycle.

    Includes rows with **missing site_code** (import gap): those never match
    `PettyCashTxn.site_code == pr.site_code` alone, so they used to hide from
    payroll banners and finalization gate while still leaking money from payroll.
    """
    from sqlalchemy import or_

    preds = [
        PettyCashTxn.pay_cycle_tag == pr.pay_cycle_tag,
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
        PettyCashTxn.driver_id.is_(None),
    ]
    site = (pr.site_code or "").strip()
    if site:
        preds.append(
            or_(
                PettyCashTxn.site_code == site,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            )
        )
    return preds


def _cycle_drift_predicates_for_payrun(pr: "PayRun"):
    """Petty หักคนขับ pending ที่ติด pay_cycle_tag รอบนี้แต่ txn_date นอกช่วงวิ่ง."""
    from sqlalchemy import or_

    preds = [
        PettyCashTxn.pay_cycle_tag == pr.pay_cycle_tag,
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
        or_(PettyCashTxn.txn_date < pr.period_start, PettyCashTxn.txn_date > pr.period_end),
    ]
    site = (pr.site_code or "").strip()
    if site:
        preds.append(
            or_(
                PettyCashTxn.site_code == site,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            )
        )
    return preds


def _collect_policy_review_for_payrun(s: Session, pr: "PayRun", limit: int = 8) -> dict:
    """Rows that require manual review to avoid silent payroll omission."""
    from sqlalchemy import or_

    site = (pr.site_code or "").strip()
    preds = [
        PettyCashTxn.pay_cycle_tag == pr.pay_cycle_tag,
        PettyCashTxn.deduct_from_driver == True,  # noqa: E712
        PettyCashTxn.deduction_status == "pending",
    ]
    if site:
        preds.append(
            or_(
                PettyCashTxn.site_code == site,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            )
        )
    rows = s.exec(
        select(PettyCashTxn).where(*preds).order_by(PettyCashTxn.txn_date.desc(), PettyCashTxn.id.desc())
    ).all()
    emp_ids = sorted({int(r.driver_id) for r in rows if r.driver_id})
    emp_map = {e.id: e for e in s.exec(select(Employee).where(Employee.id.in_(emp_ids))).all()} if emp_ids else {}

    flagged = []
    for r in rows:
        reason = ""
        expected_tag = ""
        policy_used = "site_default"
        if not r.driver_id:
            reason = "ยังไม่ผูกคนขับ"
        else:
            driver = emp_map.get(int(r.driver_id))
            if driver is None:
                reason = "ไม่พบข้อมูลคนขับ"
            elif not r.txn_date:
                reason = "ไม่พบวันที่รายการ"
            else:
                expected_tag, policy_used, review_reason = _resolve_cycle_tag_for_driver(
                    r.txn_date,
                    r.site_code or pr.site_code,
                    driver,
                )
                if review_reason == "unclear_policy":
                    reason = "นโยบายรอบจ่ายคนขับไม่ชัดเจน"
                elif expected_tag and (r.pay_cycle_tag or "").strip() != expected_tag:
                    reason = f"แท็กรอบไม่ตรง policy ({r.pay_cycle_tag} -> {expected_tag})"
        if reason:
            flagged.append(
                {
                    "id": r.id,
                    "txn_date": r.txn_date,
                    "requester_raw": r.requester_raw,
                    "deduct_amount": float(r.deduct_amount or 0.0),
                    "reason": reason,
                    "policy_used": policy_used,
                }
            )
    return {
        "count": len(flagged),
        "amount": round(sum(x["deduct_amount"] for x in flagged), 2),
        "rows": flagged[: max(1, limit)],
    }


def _detect_payrun_stale(s: Session, pr: "PayRun", items: list) -> dict:
    """ตรวจว่ามี source data (PettyCash / DailyJob / FuelTxn) ในรอบนี้ที่ถูก
    แก้ไขหลังจาก compute_pay_run ครั้งล่าสุดไหม — ถ้ามีให้เตือนผู้ใช้ recompute
    """
    from sqlalchemy import func as sa_func
    if not items:
        return {"is_stale": False, "counts": {}}
    baseline = min((it.computed_at for it in items if it.computed_at), default=None)
    if baseline is None:
        return {"is_stale": False, "counts": {}}
    start, end, tag = pr.period_start, pr.period_end, pr.pay_cycle_tag

    petty_site = (pr.site_code or "").strip()
    petty_where = [
        PettyCashTxn.pay_cycle_tag == tag,
        PettyCashTxn.updated_at > baseline,
    ]
    if petty_site:
        from sqlalchemy import or_

        petty_where.append(
            or_(
                PettyCashTxn.site_code == petty_site,
                PettyCashTxn.site_code == "",
                PettyCashTxn.site_code.is_(None),
            )
        )
    petty_cnt = s.exec(
        select(sa_func.count()).select_from(PettyCashTxn).where(*petty_where)
    ).one() or 0
    daily_cnt = s.exec(
        select(sa_func.count()).select_from(DailyJob).where(
            DailyJob.site_code == pr.site_code,
            DailyJob.work_date >= start,
            DailyJob.work_date <= end,
            DailyJob.updated_at > baseline,
        )
    ).one() or 0
    # FuelTxn has only created_at (no updated_at) — detects newly added fuel rows
    fuel_cnt = s.exec(
        select(sa_func.count()).select_from(FuelTxn).where(
            FuelTxn.site_code == pr.site_code,
            FuelTxn.txn_date >= start,
            FuelTxn.txn_date <= end,
            FuelTxn.created_at > baseline,
        )
    ).one() or 0

    total = int(petty_cnt) + int(daily_cnt) + int(fuel_cnt)
    return {
        "is_stale": total > 0,
        "baseline": baseline,
        "counts": {
            "petty": int(petty_cnt),
            "daily": int(daily_cnt),
            "fuel": int(fuel_cnt),
            "total": total,
        },
    }


@app.get("/payroll/{run_id}", response_class=HTMLResponse)
def payroll_detail(run_id: int, request: Request, err: str = ""):
    from sqlalchemy import func as sa_func
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll?err=notfound", status_code=303)
        items = s.exec(
            select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)
        ).all()
        rows = []
        for it in items:
            emp = s.get(Employee, it.employee_id)
            rows.append({"item": it, "employee": emp})
        rows.sort(key=lambda r: -(r["item"].net_pay or 0))
        totals = {
            "gross": sum((r["item"].gross_total or 0) for r in rows),
            "ded": sum((r["item"].deduction_total or 0) for r in rows),
            "net": sum((r["item"].net_pay or 0) for r in rows),
        }
        # Guardrail: show pending unlinked deductions so they don't silently miss payroll
        # (รวมแถวที่ site_code ว่างจาก import — เดิมกรองแค่ site == รอบจึงไม่เห็น)
        unlinked_q = select(sa_func.count(PettyCashTxn.id)).where(
            *_petty_unlinked_predicates_for_payrun(pr)
        )
        unlinked_count = int(s.exec(unlinked_q).one() or 0)

        unlinked_amt_q = select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(
            *_petty_unlinked_predicates_for_payrun(pr)
        )
        unlinked_amount = float(s.exec(unlinked_amt_q).one() or 0.0)

        unlinked_top = s.exec(
            select(PettyCashTxn)
            .where(*_petty_unlinked_predicates_for_payrun(pr))
            .order_by(PettyCashTxn.txn_date.desc(), PettyCashTxn.id.desc())
            .limit(8)
        ).all()
        # Guardrail: cycle-date drift (pay_cycle_tag ตรงรอบ แต่วันที่รายการอยู่นอกช่วงวิ่ง)
        cycle_drift_preds = _cycle_drift_predicates_for_payrun(pr)
        cycle_drift_count = int(
            s.exec(select(sa_func.count(PettyCashTxn.id)).where(*cycle_drift_preds)).one() or 0
        )
        cycle_drift_amount = float(
            s.exec(
                select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(*cycle_drift_preds)
            ).one() or 0.0
        )
        cycle_drift_top = s.exec(
            select(PettyCashTxn)
            .where(*cycle_drift_preds)
            .order_by(PettyCashTxn.txn_date.desc(), PettyCashTxn.id.desc())
            .limit(8)
        ).all()
        policy_review = _collect_policy_review_for_payrun(s, pr, limit=8)
        from services.payroll import find_pending_price_days
        pending_price = []
        for it in items:
            emp_pp = s.get(Employee, it.employee_id)
            days = find_pending_price_days(
                s, it.employee_id, pr.period_start, pr.period_end,
                site_code=(emp_pp.home_site_code if emp_pp else pr.site_code),
            )
            for d in days:
                pending_price.append({
                    "name": (emp_pp.nickname or emp_pp.full_name) if emp_pp else str(it.employee_id),
                    "date": d["date"], "status": d["status"],
                })
        pending_price.sort(key=lambda x: (x["date"], x["name"]))
        stale = _detect_payrun_stale(s, pr, items)
        # C4: ค่าเที่ยวตกหล่น — ที่ดูดเข้ารอบนี้แล้ว + ที่ค้างรอรอบถัดไปของไซท์นี้
        adj_applied = s.exec(
            select(PayAdjustment, Employee)
            .join(Employee, Employee.id == PayAdjustment.employee_id)
            .where(PayAdjustment.status == "applied",
                   PayAdjustment.applied_run_id == pr.id)
            .order_by(PayAdjustment.id)
        ).all()
        adj_pending = s.exec(
            select(PayAdjustment, Employee)
            .join(Employee, Employee.id == PayAdjustment.employee_id)
            .where(PayAdjustment.status == "pending",
                   PayAdjustment.site_code == pr.site_code)
            .order_by(PayAdjustment.id)
        ).all()
    ctx = base_context(request)
    from services.payroll_slip import salary_folder_month_tag

    ctx.update({
        "run": pr,
        "rows": rows,
        "totals": totals,
        "stale": stale,
        "err": err,
        "unlinked": {
            "count": unlinked_count,
            "amount": unlinked_amount,
            "rows": unlinked_top,
        },
        "cycle_drift": {
            "count": cycle_drift_count,
            "amount": cycle_drift_amount,
            "rows": cycle_drift_top,
        },
        "policy_review": policy_review,
        "pending_price": pending_price,
        "adj_applied": [{"a": a, "name": (e.nickname or e.full_name)} for a, e in adj_applied],
        "adj_pending": [{"a": a, "name": (e.nickname or e.full_name)} for a, e in adj_pending],
        "salary_export_folder_month": salary_folder_month_tag(pr),
    })
    return templates.TemplateResponse(request, "payroll_detail.html", ctx)


@app.post("/payroll/adjustments/{adj_id}/cancel")
def payroll_adjustment_cancel(adj_id: int, request: Request, run_id: str = Form("")):
    """ยกเลิกยอดตกหล่นที่ยัง pending (ก่อนถูกดูดเข้ารอบ) — applied แล้วห้ามแตะ."""
    u = current_user(request)
    with Session(engine) as s:
        a = s.get(PayAdjustment, adj_id)
        if not a:
            raise HTTPException(404)
        if a.status != "pending":
            raise HTTPException(409, "รายการถูกดูดเข้ารอบแล้ว — ยกเลิกไม่ได้")
        audit_log(s, request, "payadjustment", a.id, "status", "pending", "cancelled",
                  note=f"emp {a.employee_id} จำนวน {a.amount}")
        a.status = "cancelled"
        a.updated_at = datetime.utcnow()
        a.reason = (a.reason + f" [ยกเลิกโดย {(u.username if u else '?')}]").strip()
        s.add(a)
        s.commit()
    back = f"/payroll/{run_id}" if run_id.strip().isdigit() else "/payroll"
    return RedirectResponse(back, status_code=303)


@app.get("/payroll/{run_id}/employee/{emp_id}", response_class=HTMLResponse)
def payroll_employee_detail(run_id: int, emp_id: int, request: Request):
    """Drill-down view: exact DailyJob / PettyCash / FuelTxn rows that contributed
    to this employee's payroll number. Lets user audit vs original Excel sheets."""
    from sqlalchemy import desc
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        emp = s.get(Employee, emp_id)
        if pr is None or emp is None:
            return RedirectResponse(f"/payroll/{run_id}", status_code=303)
        item = s.exec(
            select(PayRunItem).where(
                PayRunItem.pay_run_id == run_id,
                PayRunItem.employee_id == emp_id,
            )
        ).first()
        start, end, tag = pr.period_start, pr.period_end, pr.pay_cycle_tag

        daily_jobs = s.exec(
            select(DailyJob).where(
                DailyJob.driver_id == emp_id,
                DailyJob.site_code == pr.site_code,
                DailyJob.work_date >= start,
                DailyJob.work_date <= end,
            ).order_by(DailyJob.work_date)
        ).all()

        from sqlalchemy import or_

        petty_rows = s.exec(
            select(PettyCashTxn).where(
                PettyCashTxn.driver_id == emp_id,
                PettyCashTxn.pay_cycle_tag == tag,
                or_(
                    PettyCashTxn.site_code == pr.site_code,
                    PettyCashTxn.site_code == "",
                    PettyCashTxn.site_code.is_(None),
                ),
            ).order_by(PettyCashTxn.txn_date)
        ).all()

        fuel_rows = s.exec(
            select(FuelTxn).where(
                FuelTxn.driver_id == emp_id,
                FuelTxn.site_code == pr.site_code,
                FuelTxn.txn_date >= start,
                FuelTxn.txn_date <= end,
            ).order_by(FuelTxn.txn_date)
        ).all()

        daily_totals = {
            "rows": len(daily_jobs),
            "trip_fee": sum((r.trip_fee_driver or 0) for r in daily_jobs),
            "revenue": sum((r.revenue_customer or 0) for r in daily_jobs),
        }
        petty_totals = {
            "rows": len(petty_rows),
            "out": sum((r.amount or 0) for r in petty_rows if r.direction == "out"),
            "in": sum((r.amount or 0) for r in petty_rows if r.direction == "in"),
            "deduct": sum(
                ((r.deduct_amount if (r.deduct_amount or 0) > 0 else r.amount) or 0)
                for r in petty_rows
                if r.deduct_from_driver and r.deduction_status == "pending"
            ),
        }
        excluded_amount = sum((r.amount or 0) for r in fuel_rows if r.exclude_from_driver)
        fuel_totals = {
            "rows": len(fuel_rows),
            "liter": sum((r.liter or 0) for r in fuel_rows),
            "amount": sum((r.amount or 0) for r in fuel_rows),
            "excluded_rows": sum(1 for r in fuel_rows if r.exclude_from_driver),
            "excluded_amount": excluded_amount,
            "deducted_amount": sum((r.amount or 0) for r in fuel_rows) - excluded_amount,
        }

        adjust = s.exec(
            select(models.PayRunAdjust).where(
                models.PayRunAdjust.pay_run_id == run_id,
                models.PayRunAdjust.employee_id == emp_id,
            )
        ).first()

        # staleness: which source rows were updated after this item's computed_at?
        baseline = item.computed_at if item else None
        stale_petty_ids: set[int] = set()
        stale_daily_ids: set[int] = set()
        stale_fuel_ids: set[int] = set()
        if baseline:
            stale_petty_ids = {r.id for r in petty_rows if r.updated_at and r.updated_at > baseline}
            stale_daily_ids = {r.id for r in daily_jobs if r.updated_at and r.updated_at > baseline}
            stale_fuel_ids = {r.id for r in fuel_rows if r.created_at and r.created_at > baseline}
        stale = {
            "is_stale": bool(stale_petty_ids or stale_daily_ids or stale_fuel_ids),
            "baseline": baseline,
            "petty_ids": stale_petty_ids,
            "daily_ids": stale_daily_ids,
            "fuel_ids": stale_fuel_ids,
            "counts": {
                "petty": len(stale_petty_ids),
                "daily": len(stale_daily_ids),
                "fuel": len(stale_fuel_ids),
                "total": len(stale_petty_ids) + len(stale_daily_ids) + len(stale_fuel_ids),
            },
        }

    petty_saved_hint = request.query_params.get("petty_saved") == "1"

    from services.payroll_slip import classify_mixed_days, delivery_route_text, mixed_day_kind
    mixed = classify_mixed_days(daily_jobs) if emp.pay_mode == "lcb_mixed" else None

    ctx = base_context(request)
    ctx.update({
        "run": pr,
        "employee": emp,
        "item": item,
        "adjust": adjust,
        "daily_jobs": daily_jobs,
        "mixed": mixed,
        "route_text": delivery_route_text,
        "day_kind": mixed_day_kind,
        "petty_rows": petty_rows,
        "fuel_rows": fuel_rows,
        "daily_totals": daily_totals,
        "petty_totals": petty_totals,
        "fuel_totals": fuel_totals,
        "stale": stale,
        "petty_saved_hint": petty_saved_hint,
    })
    return templates.TemplateResponse(request, "payroll_employee_detail.html", ctx)


@app.get("/payroll/{run_id}/employee/{emp_id}/slip", response_class=HTMLResponse)
def payroll_employee_slip(run_id: int, emp_id: int, request: Request):
    """Minimal printable pay slip for the driver — only what they need to see.

    Layout: header → daily trip table → 2-column summary (vehicle/fuel + earnings/deductions)
    → big net pay box. Lines with zero amount are hidden to keep it compact.
    """
    ctx = base_context(request)
    from services.payroll_slip import build_payroll_slip_context

    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        emp = s.get(Employee, emp_id)
        if pr is None or emp is None:
            return RedirectResponse(f"/payroll/{run_id}", status_code=303)
        item = s.exec(
            select(PayRunItem).where(
                PayRunItem.pay_run_id == run_id,
                PayRunItem.employee_id == emp_id,
            )
        ).first()
        if item is None:
            return RedirectResponse(f"/payroll/{run_id}/employee/{emp_id}", status_code=303)
        slip_ctx = build_payroll_slip_context(s, pr, emp, item)

    ctx.update(slip_ctx)
    resp = templates.TemplateResponse(request, "payroll_slip.html", ctx)
    # กัน browser cache สลิปเก่าไว้หลัง deploy (โอเจอ "ยังเป็นแบบเก่า" = เบราว์เซอร์ cache)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.post("/payroll/{run_id}/export-pdfs", response_class=HTMLResponse)
def payroll_export_pdfs(run_id: int, request: Request):
    """Generate PDF bundle into data/Salary/{SITE}/{cycle}/Driver/ (สรุป / โอนเงิน / สลิปรายคน / ชุดครบ)."""
    from services.payroll_export_pdf import default_project_root, export_payroll_pdf_bundle

    ctx = base_context(request)
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll", status_code=303)
        try:
            manifest = export_payroll_pdf_bundle(s, run_id, default_project_root())
        except FileNotFoundError as e:
            ctx.update({"run": pr, "run_id": run_id, "manifest": None, "export_error": str(e)})
            return templates.TemplateResponse(request, "payroll_export_done.html", ctx, status_code=500)
    ctx.update({"run": pr, "run_id": run_id, "manifest": manifest, "export_error": None})
    return templates.TemplateResponse(request, "payroll_export_done.html", ctx)


@app.post("/payroll/{run_id}/export-zip")
def payroll_export_zip(run_id: int, request: Request):
    """แยกไฟล์ต่อคน (ZIP) — render สลิปรายคนเป็น PDF ด้วย headless Chrome (ไทยคมชัด layout เดิม)
    แล้วส่ง ZIP กลับให้ดาวน์โหลดลงเครื่องผู้ใช้ (ไม่เซฟบน server).

    ?for=boss → สลิปผู้บริหาร (มี KB/ค่าขนส่งจริง). ใช้ template+context เดียวกับหน้าสลิปรายคน
    (single source) ต่างจากปุ่มเก่าที่ใช้ html2canvas ซึ่ง shaping ไทยพัง (วรรณยุกต์ลอย).
    """
    from urllib.parse import quote

    from services.payroll_zip_pdf import export_payroll_slips_zip

    is_boss = request.query_params.get("for", "driver").lower() == "boss"

    def render_slip_html(ctx: dict) -> str:
        return templates.get_template("payroll_slip.html").render(ctx)

    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll?err=notfound", status_code=303)
        try:
            zip_bytes, zip_name = export_payroll_slips_zip(
                s, run_id, render_slip_html, is_boss=is_boss
            )
        except (RuntimeError, ValueError) as e:
            return PlainTextResponse(f"สร้าง ZIP ไม่สำเร็จ: {e}", status_code=500)

    # ชื่อ ASCII fallback ก็ต้องมี timestamp — เบราว์เซอร์ที่ไม่อ่าน filename* จะได้
    # ไม่เซฟชื่อซ้ำ payroll_slips.zip แล้วโอเปิดไฟล์เก่า (เข้าใจว่าสลิปไม่อัปเดต)
    from datetime import datetime as _dt

    ascii_name = f"payroll_slips_{_dt.now().strftime('%d-%m-%y_%H.%M')}.zip"
    headers = {
        "Content-Disposition": f"attachment; filename={ascii_name}; "
        f"filename*=UTF-8''{quote(zip_name)}",
        "Cache-Control": "no-store",
    }
    return Response(content=zip_bytes, media_type="application/zip", headers=headers)


@app.post("/payroll/{run_id}/ss-settings")
def payroll_ss_settings(
    run_id: int,
    ss_rate: str = Form(""),
    ss_base_min: str = Form(""),
    ss_base_max: str = Form(""),
    clear: str = Form(""),
):
    """Set/clear PayRun-level SS overrides (apply to ALL employees in this run)."""
    def _maybe_float(s_: str) -> Optional[float]:
        s_ = (s_ or "").strip()
        if not s_:
            return None
        try:
            return float(s_)
        except ValueError:
            return None

    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            raise HTTPException(404)
        if pr.status == "finalized":
            return RedirectResponse(f"/payroll/{run_id}?err=locked", status_code=303)
        if clear == "1":
            pr.ss_rate = None
            pr.ss_base_min = None
            pr.ss_base_max = None
        else:
            pr.ss_rate = _maybe_float(ss_rate)
            pr.ss_base_min = _maybe_float(ss_base_min)
            pr.ss_base_max = _maybe_float(ss_base_max)
        s.add(pr)
        s.commit()
        from services.payroll import compute_pay_run as _compute
        _compute(s, pr, recompute=True)
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/recompute")
def payroll_recompute(run_id: int, return_to: str = Form("")):
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll", status_code=303)
        if pr.status == "finalized":
            return RedirectResponse(f"/payroll/{pr.id}?err=locked", status_code=303)
        # COPY-LOCK: payruns whose net was copied verbatim from the salary sheet
        # (BIGC/AYU onboarded by copy — engine cannot re-derive their numbers without
        # daily/petty import + missing base/route rules). Recomputing would overwrite
        # correct paid amounts with wrong engine output. Block unless explicitly forced.
        if pr.notes and "[COPY-LOCK]" in pr.notes:
            return RedirectResponse(f"/payroll/{pr.id}?err=copylock", status_code=303)
        compute_pay_run(s, pr, recompute=True)
    dest = _parse_internal_path((return_to or "").strip()) or f"/payroll/{run_id}"
    return RedirectResponse(url=dest, status_code=303)


@app.post("/payroll/{run_id}/employee/{emp_id}/override")
def payroll_employee_override(
    run_id: int,
    emp_id: int,
    days_worked_override: str = Form(""),
    days_leave_override: str = Form(""),
    days_absent_override: str = Form(""),
    ss_rate_override: str = Form(""),
    ss_base_min_override: str = Form(""),
    ss_base_max_override: str = Form(""),
    note: str = Form(""),
    clear: str = Form(""),
):
    """Save / clear PayRunAdjust manual overrides per (PayRun, Employee).
    
    Empty string = field is None (use auto). 'clear=1' = wipe all overrides.
    Always recomputes the run after saving so the user sees fresh numbers.
    """
    def _maybe_float(s_: str) -> Optional[float]:
        s_ = (s_ or "").strip()
        if not s_:
            return None
        try:
            return float(s_)
        except ValueError:
            return None

    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            raise HTTPException(404, "pay run not found")
        if pr.status == "finalized":
            return RedirectResponse(
                f"/payroll/{run_id}/employee/{emp_id}?err=locked", status_code=303
            )
        emp = s.get(Employee, emp_id)
        if emp is None:
            raise HTTPException(404, "employee not found")

        adj = s.exec(
            select(PayRunAdjust).where(
                PayRunAdjust.pay_run_id == run_id,
                PayRunAdjust.employee_id == emp_id,
            )
        ).first()
        if adj is None:
            adj = PayRunAdjust(pay_run_id=run_id, employee_id=emp_id)

        if clear == "1":
            adj.days_worked_override = None
            adj.days_leave_override = None
            adj.days_absent_override = None
            adj.ss_rate_override = None
            adj.ss_base_min_override = None
            adj.ss_base_max_override = None
            adj.note = ""
        else:
            adj.days_worked_override = _maybe_float(days_worked_override)
            adj.days_leave_override = _maybe_float(days_leave_override)
            adj.days_absent_override = _maybe_float(days_absent_override)
            adj.ss_rate_override = _maybe_float(ss_rate_override)
            adj.ss_base_min_override = _maybe_float(ss_base_min_override)
            adj.ss_base_max_override = _maybe_float(ss_base_max_override)
            adj.note = (note or "").strip()
        adj.updated_at = datetime.utcnow()
        s.add(adj)
        s.commit()

        from services.payroll import compute_pay_run as _compute  # local import
        _compute(s, pr, recompute=True)

    return RedirectResponse(
        f"/payroll/{run_id}/employee/{emp_id}", status_code=303
    )


@app.post("/payroll/{run_id}/employee/{emp_id}/fuel/{fuel_id}/toggle-exclude")
def payroll_fuel_toggle_exclude(run_id: int, emp_id: int, fuel_id: int):
    """Toggle a single FuelTxn's exclude_from_driver flag, then recompute.

    Used for น้ำมันก่อนเริ่มวิ่ง / ถังเต็มแรกตอนเริ่มเหมา = ไม่หักคนขับ.
    The flag lives on the bill itself; engine fuel-sum skips flagged bills.
    """
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            raise HTTPException(404, "pay run not found")
        if pr.status == "finalized":
            return RedirectResponse(
                f"/payroll/{run_id}/employee/{emp_id}?err=locked", status_code=303
            )
        fuel = s.get(FuelTxn, fuel_id)
        # guard: bill must belong to this driver (no cross-driver toggle)
        if fuel is None or fuel.driver_id != emp_id:
            raise HTTPException(404, "fuel txn not found for this driver")
        fuel.exclude_from_driver = not bool(fuel.exclude_from_driver)
        s.add(fuel)
        s.commit()

        from services.payroll import compute_pay_run as _compute
        _compute(s, pr, recompute=True)

    return RedirectResponse(
        f"/payroll/{run_id}/employee/{emp_id}#fuel", status_code=303
    )


def _auto_transfer_note(emp: Employee, item: PayRunItem, period_end) -> str:
    """หมายเหตุอัตโนมัติสำหรับหน้าโอนเงิน (เป็น hint; transfer_note ที่กรอกมือ override).

    ลาออก (status inactive หรือ end_date ภายในรอบ) → 'ออก'; ถ้ายังมีเงินประกันตน
    ค้าง (deposit_balance > 0) คนออกต้องได้คืน → 'คืนประกันตน {ยอด}';
    เหมา/ลูกผสม → 'เหมาน้ำมัน'.
    """
    bits = []
    resigned = (emp.status or "").lower() in ("inactive", "resigned", "ลาออก")
    if not resigned and emp.end_date and period_end and emp.end_date <= period_end:
        resigned = True
    if resigned:
        bits.append("ออก")
        # คนออกที่ยังมีเงินประกันตนสะสม → ต้องคืน
        dep = emp.deposit_balance or 0.0
        if dep > 0:
            bits.append(f"คืนประกันตน {dep:,.0f}")
    if (item.pay_mode or "") in ("lcb_mao", "lcb_mixed", "ayu_mao"):
        bits.append("เหมาน้ำมัน")
    return " ".join(bits)


def _ytd_income_tax_by_emp(s: Session, pr: PayRun) -> dict:
    """YTD (year-to-date through pr.period_end) per employee for the run's site:
    income = Σ(gross − fuel_cost_self) (= ฐานภาษีจริง, หลังหักน้ำมันคนเหมา),
    tax = Σ income_tax_withholding. Same calendar year, ≤ this cycle's period_end.
    """
    ytd_rows = s.exec(
        select(PayRunItem, PayRun)
        .join(PayRun, PayRun.id == PayRunItem.pay_run_id)
        .where(
            PayRun.site_code == pr.site_code,
            PayRun.period_end >= date(pr.period_end.year, 1, 1),
            PayRun.period_end <= pr.period_end,
        )
    ).all()
    out: dict[int, dict] = {}
    for it, _pr in ytd_rows:
        d = out.setdefault(it.employee_id, {"income": 0.0, "tax": 0.0})
        d["income"] += max((it.gross_total or 0.0) - (it.fuel_cost_self or 0.0), 0.0)
        d["tax"] += it.income_tax_withholding or 0.0
    return out


@app.get("/payroll/{run_id}/tax", response_class=HTMLResponse)
def payroll_tax_page(run_id: int, request: Request):
    """หน้าสรุปภาษี: ต่อคน — รายได้รอบนี้(หลังหักน้ำมัน), ภาษีรอบนี้,
    รายได้สะสมทั้งปี, ภาษีสะสมทั้งปี."""
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll?err=notfound", status_code=303)
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
        ytd = _ytd_income_tax_by_emp(s, pr)
        rows = []
        for it in items:
            emp = s.get(Employee, it.employee_id)
            y = ytd.get(it.employee_id, {"income": 0.0, "tax": 0.0})
            rows.append({
                "employee": emp,
                "pay_mode": it.pay_mode,
                "income_month": max((it.gross_total or 0.0) - (it.fuel_cost_self or 0.0), 0.0),
                "tax_month": it.income_tax_withholding or 0.0,
                "ytd_income": y["income"],
                "ytd_tax": y["tax"],
            })
        rows.sort(key=lambda r: -r["ytd_tax"])
        totals = {
            "tax_month": sum(r["tax_month"] for r in rows),
            "ytd_tax": sum(r["ytd_tax"] for r in rows),
        }
    ctx = base_context(request)
    ctx.update({"run": pr, "rows": rows, "totals": totals})
    return templates.TemplateResponse(request, "payroll_tax.html", ctx)


def _slip_daily_rows(s: Session, emp_id: int, pr: PayRun, pay_mode: str, is_boss: bool) -> list:
    """เดลี่เที่ยววิ่งรายวันสำหรับสลิป. กฎความลับ (KB = ใต้โต๊ะ):
      - boss: เห็น ค่าขนส่งวางบิลจริง (revenue_customer) + ราคากลาง (override??rev) + KB.
      - คนขับ เหมา: เห็นแค่ราคากลาง (override??rev) — ไม่เห็น rev จริง, ไม่เห็น KB.
      - คนขับ เที่ยว: เห็นแค่ค่าเที่ยวที่ได้ (trip_fee_driver) — ไม่เห็นราคากลาง/KB.
    """
    djs = s.exec(
        select(DailyJob).where(
            DailyJob.driver_id == emp_id,
            DailyJob.work_date >= pr.period_start,
            DailyJob.work_date <= pr.period_end,
        ).order_by(DailyJob.work_date)
    ).all()
    is_mao = (pay_mode or "") in ("lcb_mao", "lcb_mixed", "ayu_mao")
    from services.payroll_slip import delivery_route_text
    out = []
    for d in djs:
        rev = d.revenue_customer or 0.0
        central = (d.price_override if d.price_override else rev)  # ราคากลาง
        row = {
            "date": d.work_date,
            "plate": d.plate_no_raw or "",
            "status": d.status_code or "",
            "dest": d.destination or "",
            "route": delivery_route_text(d),  # ต้นทาง → โหลด → ปลายทาง
            "container": d.container_no or "",
            "trip_fee": d.trip_fee_driver or 0.0,
            "fuel": d.fuel_amount or 0.0,
            "fuel_liter": d.fuel_liter or 0.0,
            # price column shown to THIS audience:
            "show_central": False,
            "central": central,
            "rev_real": rev,
            "kb": d.kb_amount or 0.0,
        }
        if is_boss:
            row["show_central"] = True  # boss sees central + rev_real + kb columns
        elif is_mao:
            row["show_central"] = True  # mao driver sees ONLY central (template hides rev/kb)
        # trip driver (not boss): show_central stays False → only ค่าเที่ยว
        out.append(row)
    return out


@app.get("/payroll/{run_id}/print", response_class=HTMLResponse)
def payroll_print_all(run_id: int, request: Request):
    """หน้าพิมพ์สด (Ctrl+P): สรุปทุกคน → โอนเงิน → สลิปรายคน (page-break ต่อบล็อก).

    ?for=boss → สลิปผู้บริหาร (เห็นค่าขนส่งจริง + ราคากลาง + KB).
    default (คนขับ) → ซ่อน KB + ค่าขนส่งจริง (เหมาเห็นราคากลาง, เที่ยวเห็นแค่ค่าเที่ยว).
    """
    is_boss = request.query_params.get("for", "driver").lower() == "boss"
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll?err=notfound", status_code=303)
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
        ytd_by_emp = _ytd_income_tax_by_emp(s, pr)
        from services.payroll_slip import build_payroll_slip_context, slip_anomaly_rows
        _anom_rows = slip_anomaly_rows(s, pr)  # scan ธงน้ำมันครั้งเดียวทั้งรอบ ไม่วนต่อคน
        rows = []
        for it in items:
            emp = s.get(Employee, it.employee_id)
            note = (it.transfer_note or "").strip() or _auto_transfer_note(emp, it, pr.period_end)
            ytd = ytd_by_emp.get(it.employee_id, {"income": 0.0, "tax": 0.0})
            daily = _slip_daily_rows(s, it.employee_id, pr, it.pay_mode, is_boss)
            # แจกแจงรายการหักสดย่อย (วันที่/รายการ/ยอด) — reuse slip context (single source)
            slip_ctx = build_payroll_slip_context(s, pr, emp, it, anomaly_rows=_anom_rows)
            row = {"item": it, "employee": emp, "transfer_note": note,
                   "ytd": ytd, "daily": daily, "ctx": slip_ctx,
                   "petty_lines": slip_ctx.get("petty_lines", []),
                   "fuel_excluded_amt": slip_ctx.get("fuel_excluded_amt", 0.0),
                   "fuel_deducted_liter": slip_ctx.get("fuel_deducted_liter", 0.0),
                   "tank_measure_rows": slip_ctx.get("tank_measure_rows", [])}
            if is_boss:
                # หน้าสรุปผู้บริหาร: วางบิล / KB / ค่าน้ำมันรวม / รายได้คนขับ + % เทียบวางบิลหลังหัก KB
                djs = slip_ctx.get("daily_jobs") or []
                billed = sum((d.revenue_customer or 0.0) for d in djs)
                kb = sum((d.kb_amount or 0.0) for d in djs)
                base100 = billed - kb  # ฐาน 100% = วางบิลหลังหัก KB
                fuel_total = (slip_ctx.get("fuel_excluded_amt") or 0.0) + (slip_ctx.get("fuel_deducted_amt") or 0.0)
                # รายได้คนขับ: เหมา = ค่าเที่ยว−น้ำมัน, เที่ยว = เงินเดือน+ดูแลรถ+ค่าเที่ยว → ทั้งคู่ = gross−fuel_self
                drv_income = (it.gross_total or 0.0) - (it.fuel_cost_self or 0.0)
                row["boss"] = {
                    "billed": billed, "kb": kb, "base100": base100,
                    "fuel_total": fuel_total, "drv_income": drv_income,
                    "fuel_pct": (fuel_total / base100 * 100.0) if base100 else None,
                    "drv_pct": (drv_income / base100 * 100.0) if base100 else None,
                }
            rows.append(row)
        rows.sort(key=lambda r: -(r["item"].net_pay or 0))
        totals = {
            "gross": sum((r["item"].gross_total or 0) for r in rows),
            "fuel": sum((r["item"].fuel_cost_self or 0) for r in rows),
            "ded": sum((r["item"].deduction_total or 0) for r in rows),
            "net": sum((r["item"].net_pay or 0) for r in rows),
        }
        # ยอด "เตรียมเงินโอน" = นับเฉพาะคน net > 0 (คนติดลบ=เป็นหนี้บริษัท ไม่ได้โอนให้
        # ห้ามเอายอดลบไปหักยอดรวม ไม่งั้นเตรียมเงินโอนคนอื่นไม่พอ — โอ 30มิ.ย.)
        pos = [r for r in rows if (r["item"].net_pay or 0) > 0]
        totals["transfer"] = sum((r["item"].net_pay or 0) for r in pos)
        totals["transfer_count"] = len(pos)
        if is_boss:
            tb = {k: sum((r["boss"][k] or 0) for r in rows) for k in ("billed", "kb", "base100", "fuel_total", "drv_income")}
            tb["fuel_pct"] = (tb["fuel_total"] / tb["base100"] * 100.0) if tb["base100"] else None
            tb["drv_pct"] = (tb["drv_income"] / tb["base100"] * 100.0) if tb["base100"] else None
            # แตกรวมหัก: ปกส / ปกต / หักอื่น (เงินเบิก/สดย่อย + อุบัติเหตุ + อื่นๆ) — โอ 1ก.ค.
            tb["ss"] = sum((r["item"].social_security or 0) for r in rows)
            tb["deposit"] = sum((r["item"].deposit_install or 0) for r in rows)
            tb["other_ded"] = sum(
                (r["item"].petty_cash_deduction or 0) + (r["item"].accident_install or 0)
                + (r["item"].other_deduction or 0) for r in rows
            )
            totals["boss"] = tb
    ctx = base_context(request)
    ctx.update({"run": pr, "rows": rows, "totals": totals, "is_boss": is_boss})
    resp = templates.TemplateResponse(request, "payroll_print_all.html", ctx)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.get("/payroll/{run_id}/accounts", response_class=HTMLResponse)
def payroll_accounts(run_id: int, request: Request):
    """บัญชีโอนเงินของรอบ (A5 ส่วนแรก): เลขบัญชีใหญ่ ก็อปคลิกเดียว แก้ inline ได้เลย.

    ทำเป็นหน้าแยก (ไม่แตะ template /print ที่ session อื่นทำค้าง) — โอสั่ง 3ก.ค.
    "ฉันแก้เองถ้าแก้ในระบบได้"; เรียงตามธนาคารเพื่อโอนเป็นชุด, เฉพาะ net>0.
    """
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll", status_code=303)
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == run_id)).all()
        emps = {e.id: e for e in s.exec(select(Employee).where(
            Employee.id.in_([i.employee_id for i in items]))).all()}
    rows = []
    for it in items:
        if (it.net_pay or 0) <= 0:
            continue
        e = emps.get(it.employee_id)
        if e:
            rows.append({"emp": e, "net": it.net_pay})
    rows.sort(key=lambda r: ((r["emp"].bank_name or "ไม่ระบุ"), -(r["net"] or 0)))
    ctx = base_context(request)
    ctx.update({"run": pr, "rows": rows,
                "total": round(sum(r["net"] for r in rows), 2)})
    return templates.TemplateResponse(request, "payroll_accounts.html", ctx)


@app.get("/payroll/{run_id}/accounts.csv")
def payroll_accounts_csv(run_id: int):
    """CSV โอนชุด: ธนาคาร,เลขบัญชี,ชื่อ,ยอด (net>0 เรียงตามธนาคาร) — เปิดใน Excel/
    วางใน portal ธนาคารได้ (BOM ให้ไทยไม่เพี้ยน); read-only."""
    import csv
    import io as _io

    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            raise HTTPException(404)
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == run_id)).all()
        emps = {e.id: e for e in s.exec(select(Employee).where(
            Employee.id.in_([i.employee_id for i in items]))).all()}
    rows = [(emps[i.employee_id], i.net_pay) for i in items
            if (i.net_pay or 0) > 0 and i.employee_id in emps]
    rows.sort(key=lambda r: ((r[0].bank_name or "ไม่ระบุ"), -(r[1] or 0)))
    buf = _io.StringIO()
    buf.write("﻿")  # BOM ให้ Excel เปิดไทยไม่เพี้ยน
    w = csv.writer(buf)
    w.writerow(["ธนาคาร", "เลขบัญชี", "ชื่อบัญชี", "ยอดโอน"])
    for e, net in rows:
        w.writerow([e.bank_name or "", e.account_no or "", e.full_name, f"{net:.2f}"])
    w.writerow([])
    w.writerow(["รวม", "", f"{len(rows)} คน", f"{sum(n for _, n in rows):.2f}"])
    from urllib.parse import quote as _urlquote
    fname = f"โอนชุด_{pr.site_code}_{pr.pay_cycle_tag}.csv"
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             f"attachment; filename*=UTF-8''{_urlquote(fname)}"})


@app.post("/payroll/{run_id}/accounts/save")
def payroll_accounts_save(run_id: int, request: Request, emp_id: int = Form(...),
                          bank_name: str = Form(""), account_no: str = Form("")):
    """แก้ธนาคาร/เลขบัญชีของพนักงาน (แก้ที่ตัว Employee — มีผลทุกหน้า/ทุกรอบ)."""
    if _part_level_of(request, "transfer.edit_account") != "edit":
        raise HTTPException(403, "ไม่มีสิทธิ์แก้เลขบัญชี (ดู /admin/permissions)")
    with Session(engine) as s:
        e = s.get(Employee, emp_id)
        if e:
            if e.bank_name != bank_name.strip():
                audit_log(s, request, "employee", emp_id, "bank_name",
                          e.bank_name, bank_name.strip(), note=e.full_name)
            if e.account_no != account_no.strip():
                audit_log(s, request, "employee", emp_id, "account_no",
                          e.account_no, account_no.strip(), note=e.full_name)
            e.bank_name = bank_name.strip()
            e.account_no = account_no.strip()
            s.add(e)
            s.commit()
    return RedirectResponse(f"/payroll/{run_id}/accounts", status_code=303)


@app.post("/payroll/{run_id}/employee/{emp_id}/transfer-note")
def payroll_transfer_note(run_id: int, emp_id: int, note: str = Form("")):
    """บันทึกหมายเหตุหน้าโอนเงิน (แก้มือ) — ไม่ recompute (ไม่กระทบเงิน)."""
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            raise HTTPException(404, "pay run not found")
        if pr.status == "finalized":
            return RedirectResponse(f"/payroll/{run_id}/print?err=locked", status_code=303)
        it = s.exec(
            select(PayRunItem).where(
                PayRunItem.pay_run_id == run_id, PayRunItem.employee_id == emp_id
            )
        ).first()
        if it is None:
            raise HTTPException(404, "payrun item not found")
        it.transfer_note = (note or "").strip()
        s.add(it)
        s.commit()
    return RedirectResponse(f"/payroll/{run_id}/print", status_code=303)


@app.post("/payroll/{run_id}/finalize")
def payroll_finalize(run_id: int, request: Request):
    from datetime import datetime as _dt
    from sqlalchemy import func as sa_func, or_ as _or
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll", status_code=303)
        # BIGC / LCB policy lock: cycle-date drift > 0 must block first (before unlinked gate),
        # so UI/error aligns with locked policy and generates unresolved drift report immediately.
        _site_upper = (pr.site_code or "").strip().upper()
        if _site_upper in ("BIGC", "LCB"):
            _site = (pr.site_code or "").strip()
            cycle_drift_preds = _cycle_drift_predicates_for_payrun(pr)
            drift_cnt = int(s.exec(select(sa_func.count(PettyCashTxn.id)).where(*cycle_drift_preds)).one() or 0)
            if drift_cnt > 0:
                drift_amount = float(
                    s.exec(
                        select(sa_func.coalesce(sa_func.sum(PettyCashTxn.deduct_amount), 0.0)).where(*cycle_drift_preds)
                    ).one() or 0.0
                )
                drift_top = s.exec(
                    select(PettyCashTxn)
                    .where(*cycle_drift_preds)
                    .order_by(PettyCashTxn.txn_date.desc(), PettyCashTxn.id.desc())
                    .limit(20)
                ).all()
                drift_reason = (
                    "bigc_cycle_date_drift_block"
                    if _site_upper == "BIGC"
                    else "lcb_cycle_date_drift_block"
                )
                report_meta = _write_unresolved_case_report(
                    run_id=pr.id or run_id,
                    site_code=_site or _site_upper,
                    cycle_tag=pr.pay_cycle_tag or "",
                    reason=drift_reason,
                    payload={
                        "drift_count": drift_cnt,
                        "drift_amount": drift_amount,
                        "period_start": pr.period_start.isoformat(),
                        "period_end": pr.period_end.isoformat(),
                        "sample_rows": [
                            {
                                "id": r.id,
                                "txn_date": r.txn_date.isoformat() if r.txn_date else None,
                                "requester_raw": r.requester_raw,
                                "deduct_amount": float(r.deduct_amount or 0.0),
                                "site_code": r.site_code,
                            }
                            for r in drift_top
                        ],
                    },
                    next_action="review petty rows with same cycle_tag and move drifted rows to correct cycle before finalize",
                )
                if report_meta.get("is_repeated_fail"):
                    # Persist this in run note so admin immediately sees repeated blocker context.
                    pr.notes = (
                        f"[pending_morning] cycle-date drift fail repeated; "
                        f"see {report_meta.get('pending_note_path') or report_meta.get('report_path')}"
                    )
                    s.add(pr)
                    s.commit()
                return RedirectResponse(f"/payroll/{pr.id}?err=cycle_drift_block", status_code=303)
        # Finalization gate: block when there are pending driver-deductions still unlinked.
        # For BIGC/LCB this runs after drift gate by policy; for other sites behavior is unchanged.
        unlinked_cnt_q = select(sa_func.count(PettyCashTxn.id)).where(
            *_petty_unlinked_predicates_for_payrun(pr)
        )
        unlinked_cnt = int(s.exec(unlinked_cnt_q).one() or 0)
        if unlinked_cnt > 0:
            return RedirectResponse(f"/payroll/{pr.id}?err=unlinked_pending", status_code=303)
        policy_review = _collect_policy_review_for_payrun(s, pr, limit=1)
        if policy_review["count"] > 0:
            return RedirectResponse(f"/payroll/{pr.id}?err=policy_review_block", status_code=303)
        audit_log(s, request, "payrun", pr.id, "status", pr.status, "finalized",
                  note=f"{pr.site_code} {pr.pay_cycle_tag}")
        pr.status = "finalized"
        pr.finalized_at = _dt.utcnow()
        # Lock petty cash rows that were consumed — include blank/NULL site_code
        # (same OR logic as _petty_unlinked_predicates_for_payrun / _sum_petty_cash_deduction)
        _site = (pr.site_code or "").strip()
        _site_pred = _or(
            PettyCashTxn.site_code == _site,
            PettyCashTxn.site_code == "",
            PettyCashTxn.site_code.is_(None),
        ) if _site else True
        petty_rows = s.exec(
            select(PettyCashTxn).where(
                _site_pred,
                PettyCashTxn.pay_cycle_tag == pr.pay_cycle_tag,
                PettyCashTxn.deduct_from_driver == True,   # noqa: E712
                PettyCashTxn.deduction_status == "pending",
            )
        ).all()
        for r in petty_rows:
            r.deduction_status = "deducted"
            r.status = "locked"
        s.add(pr)
        s.commit()
    return RedirectResponse(f"/payroll/{run_id}", status_code=303)


@app.post("/payroll/{run_id}/delete")
def payroll_delete(run_id: int):
    with Session(engine) as s:
        pr = s.get(PayRun, run_id)
        if pr is None:
            return RedirectResponse("/payroll", status_code=303)
        if pr.status == "finalized":
            return RedirectResponse(f"/payroll/{pr.id}?err=locked", status_code=303)
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == pr.id)).all()
        for it in items:
            s.delete(it)
        s.delete(pr)
        s.commit()
    return RedirectResponse("/payroll", status_code=303)


# =========================================================================
# Maintenance / Stock / Tire / PM module (Wave 1: MaintRecord + Vendor + Part)
# =========================================================================

def _gen_code(session: Session, table, prefix: str, pad: int = 4) -> str:
    """Generate next auto-increment code like V0001, P0001, M000001."""
    rows = session.exec(select(table)).all()
    max_n = 0
    for r in rows:
        code = getattr(r, "code", None) or getattr(r, "record_no", None) or ""
        if code and code.startswith(prefix):
            tail = code[len(prefix):]
            try:
                n = int(tail)
                if n > max_n:
                    max_n = n
            except ValueError:
                pass
    return f"{prefix}{str(max_n + 1).zfill(pad)}"


def _stock_on_hand(session: Session, part_id: int) -> float:
    """Compute current stock level for a part (Σ in − Σ out, with adjust as absolute set)."""
    txns = session.exec(
        select(StockTxn).where(StockTxn.part_id == part_id).order_by(StockTxn.txn_date, StockTxn.id)
    ).all()
    bal = 0.0
    for t in txns:
        if t.direction == "in":
            bal += t.qty
        elif t.direction == "out":
            bal -= t.qty
        elif t.direction == "adjust":
            bal = t.qty  # adjust sets absolute level
    return bal


def _stock_map_for_parts(session: Session, part_ids=None) -> dict:
    q = select(StockTxn)
    if part_ids is not None:
        q = q.where(StockTxn.part_id.in_(list(part_ids)))
    txns = session.exec(q.order_by(StockTxn.txn_date, StockTxn.id)).all()
    result: dict[int, float] = {}
    for t in txns:
        cur = result.get(t.part_id, 0.0)
        if t.direction == "in":
            cur += t.qty
        elif t.direction == "out":
            cur -= t.qty
        elif t.direction == "adjust":
            cur = t.qty
        result[t.part_id] = cur
    return result


@app.get("/maint", response_class=HTMLResponse)
def maint_dashboard(request: Request):
    today = date.today()
    month_start = today.replace(day=1)
    with Session(engine) as s:
        records_total = len(s.exec(select(MaintRecord)).all())
        this_month = s.exec(
            select(MaintRecord).where(MaintRecord.work_date >= month_start)
        ).all()
        tires = s.exec(select(Tire)).all()
        pm_plans = s.exec(select(PmPlan).where(PmPlan.status == "active")).all()
        vehicles_all = s.exec(select(Vehicle)).all()
        v_map_full = {v.id: v for v in vehicles_all}
        pm_due: list[tuple[PmPlan, dict]] = []
        pm_soon: list[tuple[PmPlan, dict]] = []
        for p in pm_plans:
            v = v_map_full.get(p.vehicle_id) if p.vehicle_id else None
            st = _pm_status(p, v)
            if st["status"] == "overdue":
                pm_due.append((p, st))
            elif st["status"] == "due_soon":
                pm_soon.append((p, st))
        parts = s.exec(select(Part).where(Part.status == "active")).all()
        stock_map = _stock_map_for_parts(s, [p.id for p in parts])
        parts_low = [p for p in parts if stock_map.get(p.id, 0) < (p.min_stock_qty or 0) and (p.min_stock_qty or 0) > 0]

        # Low tread depth alert: in_use tires with tread < 3mm (and tread recorded)
        low_tread_tires = [
            t for t in tires
            if t.status == "in_use" and t.tread_depth_mm and 0 < t.tread_depth_mm < 3.0
        ]
        low_tread_rows = [
            {
                "id": t.id,
                "code": t.code,
                "plate": (v_map_full.get(t.current_vehicle_id).plate_no if t.current_vehicle_id and v_map_full.get(t.current_vehicle_id) else "-"),
                "position": t.current_position or "-",
                "brand_model": f"{t.brand} {t.model}".strip() or "-",
                "tread": t.tread_depth_mm,
            }
            for t in sorted(low_tread_tires, key=lambda x: x.tread_depth_mm)
        ]

        by_vehicle: dict[str, dict] = {}
        for r in this_month:
            key = r.plate_raw or "-"
            row = by_vehicle.setdefault(key, {"plate": key, "total_cost": 0.0, "count": 0})
            row["total_cost"] += r.total_cost or 0.0
            row["count"] += 1
        by_vehicle_list = sorted(by_vehicle.values(), key=lambda x: -x["total_cost"])

        recent = s.exec(
            select(MaintRecord).order_by(MaintRecord.work_date.desc(), MaintRecord.id.desc()).limit(10)
        ).all()
        vendors = s.exec(select(Vendor)).all()
        recent_stock = s.exec(
            select(StockTxn).order_by(StockTxn.txn_date.desc(), StockTxn.id.desc()).limit(8)
        ).all()
        part_name_map = {p.id: p.name for p in parts}

    # Sort PM by urgency: most-overdue first, then least days-to-due
    def _pm_sort_key(entry):
        p, st = entry
        if st.get("days_to_due") is not None:
            return st["days_to_due"]
        if st.get("km_to_due") is not None:
            return st["km_to_due"] / 100.0
        return 9_999_999
    pm_due_sorted = sorted(pm_due, key=_pm_sort_key)[:8]
    pm_soon_sorted = sorted(pm_soon, key=_pm_sort_key)[:8]
    pm_items = [
        {
            "id": p.id,
            "name": p.name,
            "kind": p.kind,
            "fluid_kind": p.fluid_kind,
            "plate": (v_map_full.get(p.vehicle_id).plate_no if p.vehicle_id and v_map_full.get(p.vehicle_id) else "-"),
            "status": st["status"],
            "days_to_due": st.get("days_to_due"),
            "km_to_due": st.get("km_to_due"),
            "next_due_date": p.next_due_date,
            "next_due_mile": p.next_due_mile,
        }
        for (p, st) in pm_due_sorted + pm_soon_sorted
    ]

    vendor_map = {v.id: v.name for v in vendors}
    kind_map = dict(models.MAINT_KINDS)

    stats = {
        "records_total": records_total,
        "records_this_month": len(this_month),
        "cost_this_month": sum(r.total_cost or 0.0 for r in this_month),
        "tires_total": len(tires),
        "tires_in_use": sum(1 for t in tires if t.status == "in_use"),
        "pm_plans": len(pm_plans),
        "pm_due": len(pm_due),
        "pm_soon": len(pm_soon),
        "parts_total": len(parts),
        "parts_low_stock": len(parts_low),
    }
    return templates.TemplateResponse(
        request, "maint_dashboard.html",
        {
            "request": request,
            "stats": stats,
            "by_vehicle": by_vehicle_list[:10],
            "recent": recent,
            "vendor_map": vendor_map,
            "kind_map": kind_map,
            "pm_items": pm_items,
            "recent_stock": recent_stock,
            "part_name_map": part_name_map,
            "low_tread_rows": low_tread_rows,
        },
    )


# ---- Vendors ----
@app.get("/maint/vendors", response_class=HTMLResponse)
def maint_vendor_list(request: Request):
    with Session(engine) as s:
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
        records = s.exec(select(MaintRecord)).all()
        usage: dict[int, int] = {}
        for r in records:
            if r.vendor_id:
                usage[r.vendor_id] = usage.get(r.vendor_id, 0) + 1
    return templates.TemplateResponse(
        request, "maint_vendor_list.html",
        {
            "request": request,
            "vendors": vendors,
            "usage": usage,
            "kinds": models.VENDOR_KINDS,
            "kind_map": dict(models.VENDOR_KINDS),
        },
    )


@app.post("/maint/vendors")
async def maint_vendor_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        v = Vendor(
            code=_gen_code(s, Vendor, "V", 4),
            name=(form.get("name") or "").strip(),
            kind=(form.get("kind") or "parts").strip(),
            phone=(form.get("phone") or "").strip(),
            address=(form.get("address") or "").strip(),
        )
        if v.name:
            s.add(v)
            s.commit()
    return RedirectResponse("/maint/vendors", status_code=303)


# ---- Parts ----
@app.get("/maint/parts", response_class=HTMLResponse)
def maint_part_list(request: Request, q: Optional[str] = None, category: Optional[str] = None):
    with Session(engine) as s:
        query = select(Part)
        if category:
            query = query.where(Part.category == category)
        if q:
            like = f"%{q.strip()}%"
            query = query.where(Part.name.like(like))
        parts = s.exec(query.order_by(Part.category, Part.name)).all()
        part_ids = [p.id for p in parts]
        stock_map = _stock_map_for_parts(s, part_ids)

        # Vendor prices summary per part
        vp_map: dict[int, list[VendorPrice]] = {}
        if part_ids:
            all_vp = s.exec(
                select(VendorPrice).where(VendorPrice.part_id.in_(part_ids)).order_by(
                    VendorPrice.is_preferred.desc(), VendorPrice.unit_price
                )
            ).all()
            for vp in all_vp:
                vp_map.setdefault(vp.part_id, []).append(vp)
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
        vendor_map = {v.id: v for v in vendors}

    return templates.TemplateResponse(
        request, "maint_part_list.html",
        {
            "request": request,
            "parts": parts,
            "stock_map": stock_map,
            "vp_map": vp_map,
            "vendor_map": vendor_map,
            "categories": models.PART_CATEGORIES,
            "cat_map": dict(models.PART_CATEGORIES),
            "units": models.PART_UNITS,
            "q": q or "",
            "category": category or "",
        },
    )


# ---- Part detail + VendorPrice management ----
@app.get("/maint/parts/{part_id}", response_class=HTMLResponse)
def maint_part_detail(request: Request, part_id: int):
    with Session(engine) as s:
        p = s.get(Part, part_id)
        if not p:
            raise HTTPException(404, "Part not found")
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
        prices = s.exec(
            select(VendorPrice).where(VendorPrice.part_id == part_id).order_by(
                VendorPrice.is_preferred.desc(), VendorPrice.unit_price
            )
        ).all()
        recent_txns = s.exec(
            select(StockTxn).where(StockTxn.part_id == part_id).order_by(
                StockTxn.txn_date.desc(), StockTxn.id.desc()
            ).limit(30)
        ).all()
        stock_map = _stock_map_for_parts(s, [part_id])
        vendor_map = {v.id: v for v in vendors}
        # Mark which vendor_ids already have price entries
        vp_vendor_ids = {vp.vendor_id for vp in prices}

    return templates.TemplateResponse(
        request, "maint_part_detail.html",
        {
            "request": request,
            "part": p,
            "vendors": vendors,
            "prices": prices,
            "recent_txns": recent_txns,
            "stock": stock_map.get(part_id, 0.0),
            "vendor_map": vendor_map,
            "vp_vendor_ids": vp_vendor_ids,
            "cat_map": dict(models.PART_CATEGORIES),
            "today": date.today().isoformat(),
            "categories": models.PART_CATEGORIES,
            "units": models.PART_UNITS,
        },
    )


@app.post("/maint/parts/{part_id}")
async def maint_part_update(part_id: int, request: Request):
    form = await request.form()
    with Session(engine) as s:
        p = s.get(Part, part_id)
        if not p:
            raise HTTPException(404, "Part not found")
        name = (form.get("name") or "").strip()
        if name:
            p.name = name
        p.category = (form.get("category") or p.category).strip()
        p.unit = (form.get("unit") or p.unit).strip()
        try:
            p.min_stock_qty = float(form.get("min_stock_qty") or 0)
        except ValueError:
            pass
        try:
            dp = form.get("default_price")
            if dp is not None and dp != "":
                p.default_price = float(dp)
        except ValueError:
            pass
        p.is_tire = (p.category == "tire")
        p.status = (form.get("status") or "active").strip()
        p.updated_at = datetime.utcnow()
        s.add(p)
        s.commit()
    return RedirectResponse(f"/maint/parts/{part_id}", status_code=303)


@app.post("/maint/parts/{part_id}/vendor-price")
async def vendor_price_create(part_id: int, request: Request):
    form = await request.form()
    vendor_raw = form.get("vendor_id") or ""
    if not vendor_raw.strip():
        return RedirectResponse(f"/maint/parts/{part_id}", status_code=303)
    vendor_id = int(vendor_raw)
    try:
        unit_price = float(form.get("unit_price") or 0)
    except ValueError:
        unit_price = 0.0
    try:
        min_qty = float(form.get("min_order_qty") or 0)
    except ValueError:
        min_qty = 0.0
    try:
        lead_days = int(form.get("lead_time_days") or 0)
    except ValueError:
        lead_days = 0
    quoted_on = _parse_date(form.get("quoted_on") or "") or date.today()

    with Session(engine) as s:
        # Upsert: one active row per (part, vendor)
        existing = s.exec(
            select(VendorPrice).where(
                VendorPrice.part_id == part_id,
                VendorPrice.vendor_id == vendor_id,
            )
        ).first()
        if existing:
            existing.unit_price = unit_price
            existing.vat_included = (form.get("vat_included") == "on")
            existing.min_order_qty = min_qty
            existing.lead_time_days = lead_days
            existing.quoted_on = quoted_on
            existing.notes = (form.get("notes") or "").strip()
            existing.updated_at = datetime.utcnow()
            s.add(existing)
        else:
            vp = VendorPrice(
                part_id=part_id,
                vendor_id=vendor_id,
                unit_price=unit_price,
                vat_included=(form.get("vat_included") == "on"),
                min_order_qty=min_qty,
                lead_time_days=lead_days,
                quoted_on=quoted_on,
                is_preferred=(form.get("is_preferred") == "on"),
                notes=(form.get("notes") or "").strip(),
            )
            s.add(vp)
        s.commit()
    return RedirectResponse(f"/maint/parts/{part_id}", status_code=303)


@app.post("/maint/vendor-price/{vp_id}/delete")
def vendor_price_delete(vp_id: int):
    with Session(engine) as s:
        vp = s.get(VendorPrice, vp_id)
        if vp:
            part_id = vp.part_id
            s.delete(vp)
            s.commit()
            return RedirectResponse(f"/maint/parts/{part_id}", status_code=303)
    return RedirectResponse("/maint/parts", status_code=303)


@app.post("/maint/vendor-price/{vp_id}/prefer")
def vendor_price_prefer(vp_id: int):
    """Mark this vendor as preferred for the part (unsets others) and sync Part.default_price."""
    with Session(engine) as s:
        vp = s.get(VendorPrice, vp_id)
        if not vp:
            raise HTTPException(404, "VendorPrice not found")
        # Clear previous preferred
        others = s.exec(
            select(VendorPrice).where(
                VendorPrice.part_id == vp.part_id,
                VendorPrice.id != vp.id,
            )
        ).all()
        for o in others:
            if o.is_preferred:
                o.is_preferred = False
                o.updated_at = datetime.utcnow()
                s.add(o)
        vp.is_preferred = True
        vp.updated_at = datetime.utcnow()
        s.add(vp)
        # Sync Part.default_price with preferred vendor's unit_price
        p = s.get(Part, vp.part_id)
        if p and vp.unit_price > 0:
            p.default_price = vp.unit_price
            p.updated_at = datetime.utcnow()
            s.add(p)
        s.commit()
        return RedirectResponse(f"/maint/parts/{vp.part_id}", status_code=303)


# ---- Global vendor-price comparison view ----
@app.get("/maint/vendor-prices", response_class=HTMLResponse)
def vendor_price_compare(request: Request, q: Optional[str] = None):
    """Comparison view: all parts × vendors, grouped by Part, showing cheapest first."""
    with Session(engine) as s:
        part_q = select(Part).where(Part.status == "active")
        if q:
            like = f"%{q.strip()}%"
            part_q = part_q.where(Part.name.like(like))
        parts = s.exec(part_q.order_by(Part.category, Part.name)).all()
        part_ids = [p.id for p in parts]
        vp_by_part: dict[int, list[VendorPrice]] = {}
        if part_ids:
            all_vp = s.exec(
                select(VendorPrice).where(VendorPrice.part_id.in_(part_ids)).order_by(
                    VendorPrice.unit_price
                )
            ).all()
            for vp in all_vp:
                vp_by_part.setdefault(vp.part_id, []).append(vp)
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()

    return templates.TemplateResponse(
        request, "vendor_price_compare.html",
        {
            "request": request,
            "parts": parts,
            "vp_by_part": vp_by_part,
            "vendor_map": {v.id: v for v in vendors},
            "cat_map": dict(models.PART_CATEGORIES),
            "q": q or "",
        },
    )


# ============================================================
# MaintInspection — monthly vehicle checklist (v10)
# ============================================================
DEFAULT_INSPECT_ITEMS = [
    "ไฟหน้า / ไฟสูง / ไฟต่ำ",
    "ไฟเลี้ยว / ไฟฉุกเฉิน",
    "ไฟท้าย / ไฟเบรก",
    "ไฟถอย / ไฟส่องป้าย",
    "ระบบเบรก (ลม/ผ้า/ดิสก์)",
    "น้ำมันเครื่อง (ระดับ/สภาพ)",
    "น้ำหล่อเย็น (ระดับ)",
    "น้ำมันเกียร์ / เฟืองท้าย",
    "สายพาน / แบตเตอรี่",
    "ยาง (ดอก/ลม/รอยสึก)",
    "ยางอะไหล่",
    "พวงมาลัย / Power",
    "ที่ปัดน้ำฝน / น้ำฉีด",
    "กระจก / กระจกมองข้าง",
    "แตร",
    "เข็มขัดนิรภัย",
    "ถังดับเพลิง",
    "กล่องปฐมพยาบาล",
    "สามเหลี่ยมฉุกเฉิน",
    "ประตู / ล็อค / กลอน",
    "ระบบลม (tank/valve)",
    "อื่น ๆ (เขียนใน remark)",
]


@app.get("/maint/inspections", response_class=HTMLResponse)
def inspection_list(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    vehicle_id: Optional[int] = None,
    overall_status: Optional[str] = None,
):
    df = _parse_date(date_from or "")
    dt = _parse_date(date_to or "")
    with Session(engine) as s:
        q = select(MaintInspection)
        if df:
            q = q.where(MaintInspection.inspection_date >= df)
        if dt:
            q = q.where(MaintInspection.inspection_date <= dt)
        if vehicle_id:
            q = q.where(MaintInspection.vehicle_id == vehicle_id)
        if overall_status:
            q = q.where(MaintInspection.overall_status == overall_status)
        inspections = s.exec(q.order_by(MaintInspection.inspection_date.desc(), MaintInspection.id.desc())).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        v_map = {v.id: v for v in vehicles}
        # Fail/warning counts per inspection (for list view)
        insp_ids = [i.id for i in inspections]
        item_stats: dict[int, dict] = {}
        if insp_ids:
            items = s.exec(
                select(MaintInspectionItem).where(MaintInspectionItem.inspection_id.in_(insp_ids))
            ).all()
            for it in items:
                d = item_stats.setdefault(it.inspection_id, {"ok": 0, "fail": 0, "warning": 0, "na": 0, "total": 0})
                d[it.status] = d.get(it.status, 0) + 1
                d["total"] += 1
    return templates.TemplateResponse(
        request, "inspection_list.html",
        {
            "request": request,
            "inspections": inspections,
            "vehicles": vehicles,
            "v_map": v_map,
            "item_stats": item_stats,
            "date_from": date_from or "",
            "date_to": date_to or "",
            "vehicle_id": vehicle_id,
            "overall_status": overall_status or "",
            "status_options": [
                ("pass", "ผ่าน"),
                ("partial", "ผ่านบางส่วน"),
                ("fail", "ไม่ผ่าน"),
            ],
        },
    )


@app.get("/maint/inspections/new", response_class=HTMLResponse)
def inspection_new(request: Request, vehicle_id: Optional[int] = None):
    with Session(engine) as s:
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    return templates.TemplateResponse(
        request, "inspection_form.html",
        {
            "request": request,
            "inspection": None,
            "items": [],
            "default_items": DEFAULT_INSPECT_ITEMS,
            "vehicles": vehicles,
            "selected_vehicle_id": vehicle_id,
            "today": date.today().isoformat(),
            "status_options": [
                ("pass", "ผ่าน"),
                ("partial", "ผ่านบางส่วน"),
                ("fail", "ไม่ผ่าน"),
            ],
            "item_status_options": [
                ("ok", "✓ ok"),
                ("warning", "⚠ เฝ้าระวัง"),
                ("fail", "✗ ไม่ผ่าน"),
                ("na", "— ไม่มี"),
            ],
        },
    )


def _parse_inspection_form(s: Session, form, insp: MaintInspection) -> MaintInspection:
    insp.inspection_date = _parse_date(form.get("inspection_date") or "") or date.today()
    vid_raw = form.get("vehicle_id") or ""
    insp.vehicle_id = int(vid_raw) if vid_raw.strip() else None
    insp.plate_raw = (form.get("plate_raw") or "").strip()
    if insp.vehicle_id and not insp.plate_raw:
        v = s.get(Vehicle, insp.vehicle_id)
        if v:
            insp.plate_raw = v.plate_no
    insp.inspector_name = (form.get("inspector_name") or "").strip()
    insp.overall_status = (form.get("overall_status") or "pass").strip()
    insp.notes = (form.get("notes") or "").strip()
    insp.updated_at = datetime.utcnow()
    return insp


def _apply_inspection_items(s: Session, inspection_id: int, form):
    """Expect repeated fields: item_name[], item_status[], item_remark[]"""
    # Clear existing items
    existing = s.exec(
        select(MaintInspectionItem).where(MaintInspectionItem.inspection_id == inspection_id)
    ).all()
    for e in existing:
        s.delete(e)

    names = form.getlist("item_name") if hasattr(form, "getlist") else form.get("item_name") or []
    statuses = form.getlist("item_status") if hasattr(form, "getlist") else form.get("item_status") or []
    remarks = form.getlist("item_remark") if hasattr(form, "getlist") else form.get("item_remark") or []
    if isinstance(names, str):
        names = [names]
    if isinstance(statuses, str):
        statuses = [statuses]
    if isinstance(remarks, str):
        remarks = [remarks]

    for i, name in enumerate(names):
        n = (name or "").strip()
        if not n:
            continue
        st = (statuses[i] if i < len(statuses) else "ok") or "ok"
        rm = (remarks[i] if i < len(remarks) else "") or ""
        s.add(MaintInspectionItem(
            inspection_id=inspection_id,
            item_name=n,
            status=st,
            remark=rm,
        ))


def _auto_overall_status(s: Session, inspection_id: int) -> str:
    items = s.exec(
        select(MaintInspectionItem).where(MaintInspectionItem.inspection_id == inspection_id)
    ).all()
    if not items:
        return "pass"
    has_fail = any(it.status == "fail" for it in items)
    has_warn = any(it.status == "warning" for it in items)
    if has_fail:
        return "fail"
    if has_warn:
        return "partial"
    return "pass"


@app.post("/maint/inspections/new")
async def inspection_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        insp = MaintInspection(inspection_date=date.today())
        _parse_inspection_form(s, form, insp)
        s.add(insp)
        s.commit()
        s.refresh(insp)
        _apply_inspection_items(s, insp.id, form)
        s.commit()
        # Auto-status override if user left default but items say otherwise
        if (form.get("auto_status") or "on") == "on":
            insp.overall_status = _auto_overall_status(s, insp.id)
            s.add(insp)
            s.commit()
        return RedirectResponse(f"/maint/inspections/{insp.id}", status_code=303)


@app.get("/maint/inspections/{insp_id}", response_class=HTMLResponse)
def inspection_edit(request: Request, insp_id: int):
    with Session(engine) as s:
        insp = s.get(MaintInspection, insp_id)
        if not insp:
            raise HTTPException(404, "Inspection not found")
        items = s.exec(
            select(MaintInspectionItem).where(MaintInspectionItem.inspection_id == insp_id).order_by(MaintInspectionItem.id)
        ).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    return templates.TemplateResponse(
        request, "inspection_form.html",
        {
            "request": request,
            "inspection": insp,
            "items": items,
            "default_items": DEFAULT_INSPECT_ITEMS,
            "vehicles": vehicles,
            "selected_vehicle_id": insp.vehicle_id,
            "today": date.today().isoformat(),
            "status_options": [
                ("pass", "ผ่าน"),
                ("partial", "ผ่านบางส่วน"),
                ("fail", "ไม่ผ่าน"),
            ],
            "item_status_options": [
                ("ok", "✓ ok"),
                ("warning", "⚠ เฝ้าระวัง"),
                ("fail", "✗ ไม่ผ่าน"),
                ("na", "— ไม่มี"),
            ],
        },
    )


@app.post("/maint/inspections/{insp_id}")
async def inspection_update(insp_id: int, request: Request):
    form = await request.form()
    with Session(engine) as s:
        insp = s.get(MaintInspection, insp_id)
        if not insp:
            raise HTTPException(404, "Inspection not found")
        _parse_inspection_form(s, form, insp)
        s.add(insp)
        _apply_inspection_items(s, insp_id, form)
        s.commit()
        if (form.get("auto_status") or "on") == "on":
            insp.overall_status = _auto_overall_status(s, insp.id)
            s.add(insp)
            s.commit()
    return RedirectResponse(f"/maint/inspections/{insp_id}", status_code=303)


@app.post("/maint/inspections/{insp_id}/delete")
def inspection_delete(insp_id: int):
    with Session(engine) as s:
        insp = s.get(MaintInspection, insp_id)
        if not insp:
            return RedirectResponse("/maint/inspections", status_code=303)
        items = s.exec(
            select(MaintInspectionItem).where(MaintInspectionItem.inspection_id == insp_id)
        ).all()
        for it in items:
            s.delete(it)
        s.delete(insp)
        s.commit()
    return RedirectResponse("/maint/inspections", status_code=303)


@app.post("/maint/parts")
async def maint_part_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        try:
            min_stock = float(form.get("min_stock_qty") or 0)
        except ValueError:
            min_stock = 0.0
        category = (form.get("category") or "other").strip()
        p = Part(
            code=_gen_code(s, Part, "P", 4),
            name=(form.get("name") or "").strip(),
            category=category,
            unit=(form.get("unit") or "ชิ้น").strip(),
            min_stock_qty=min_stock,
            is_tire=(category == "tire"),
        )
        if p.name:
            s.add(p)
            s.commit()
    return RedirectResponse("/maint/parts", status_code=303)


# ---- Stock movements ----
@app.get("/maint/stock", response_class=HTMLResponse)
def maint_stock_view(request: Request):
    with Session(engine) as s:
        parts = s.exec(select(Part).where(Part.status == "active").order_by(Part.name)).all()
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
        txns = s.exec(select(StockTxn).order_by(StockTxn.txn_date.desc(), StockTxn.id.desc()).limit(100)).all()
        stock_map = _stock_map_for_parts(s, [p.id for p in parts])
    return templates.TemplateResponse(
        request, "maint_stock.html",
        {
            "request": request,
            "today": date.today().isoformat(),
            "parts": parts,
            "vendors": vendors,
            "txns": txns,
            "part_map": {p.id: p.name for p in parts},
            "vendor_map": {v.id: v.name for v in vendors},
            "stock_map": stock_map,
        },
    )


@app.post("/maint/stock")
async def maint_stock_create(request: Request):
    form = await request.form()
    try:
        qty = float(form.get("qty") or 0)
    except ValueError:
        qty = 0.0
    try:
        unit_price = float(form.get("unit_price") or 0)
    except ValueError:
        unit_price = 0.0
    part_id = int(form.get("part_id") or 0)
    if not part_id or qty == 0.0:
        return RedirectResponse("/maint/stock", status_code=303)

    txn_date = _parse_date(form.get("txn_date") or "") or date.today()
    vendor_raw = form.get("vendor_id") or ""
    vendor_id = int(vendor_raw) if vendor_raw.strip() else None
    direction = (form.get("direction") or "in").strip()

    with Session(engine) as s:
        t = StockTxn(
            txn_date=txn_date,
            part_id=part_id,
            direction=direction,
            qty=qty,
            unit_price=unit_price,
            total_amount=qty * unit_price,
            vendor_id=vendor_id,
            note=(form.get("note") or "").strip(),
        )
        s.add(t)
        # Update part.default_price on "in" with a valid unit_price
        if direction == "in" and unit_price > 0:
            p = s.get(Part, part_id)
            if p:
                p.default_price = unit_price
                p.updated_at = datetime.utcnow()
                s.add(p)

        # Auto-learn VendorPrice: upsert price for (part, vendor) when buying in
        if direction == "in" and vendor_id and unit_price > 0:
            vp = s.exec(
                select(VendorPrice).where(
                    VendorPrice.part_id == part_id,
                    VendorPrice.vendor_id == vendor_id,
                )
            ).first()
            now = datetime.utcnow()
            if vp:
                vp.unit_price = unit_price
                vp.quoted_on = txn_date
                vp.use_count = (vp.use_count or 0) + 1
                vp.last_used_at = now
                vp.updated_at = now
                s.add(vp)
            else:
                s.add(VendorPrice(
                    part_id=part_id,
                    vendor_id=vendor_id,
                    unit_price=unit_price,
                    quoted_on=txn_date,
                    use_count=1,
                    last_used_at=now,
                    notes="auto-learned from stock-in",
                ))
        s.commit()
    return RedirectResponse("/maint/stock", status_code=303)


# ---- MaintRecord list / form / CRUD ----
@app.get("/maint/records", response_class=HTMLResponse)
def maint_record_list(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    vehicle_id: Optional[int] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
):
    df = _parse_date(date_from or "")
    dt = _parse_date(date_to or "")
    with Session(engine) as s:
        q = select(MaintRecord)
        if df:
            q = q.where(MaintRecord.work_date >= df)
        if dt:
            q = q.where(MaintRecord.work_date <= dt)
        if vehicle_id:
            q = q.where(MaintRecord.vehicle_id == vehicle_id)
        if kind:
            q = q.where(MaintRecord.kind == kind)
        if status:
            q = q.where(MaintRecord.status == status)
        records = s.exec(q.order_by(MaintRecord.work_date.desc(), MaintRecord.id.desc())).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()

    total_cost = sum(r.total_cost or 0 for r in records)
    sum_parts = sum(r.parts_cost or 0 for r in records)
    sum_labor = sum(r.labor_cost or 0 for r in records)

    return templates.TemplateResponse(
        request, "maint_record_list.html",
        {
            "request": request,
            "records": records,
            "vehicles": vehicles,
            "vendor_map": {v.id: v.name for v in vendors},
            "kind_map": dict(models.MAINT_KINDS),
            "paid_map": dict(models.MAINT_PAID_BY),
            "kinds": models.MAINT_KINDS,
            "date_from": date_from,
            "date_to": date_to,
            "vehicle_id": vehicle_id,
            "kind": kind,
            "status": status,
            "total_count": len(records),
            "total_cost": total_cost,
            "sum_parts": sum_parts,
            "sum_labor": sum_labor,
        },
    )


def _maint_form_context(s: Session, record=None):
    vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
    employees = s.exec(select(Employee).where(Employee.status == "active").order_by(Employee.full_name)).all()
    parts = s.exec(select(Part).where(Part.status == "active").order_by(Part.name)).all()
    maint_parts = []
    parts_sum = 0.0
    if record and record.id:
        maint_parts = s.exec(
            select(MaintPart).where(MaintPart.maint_record_id == record.id)
        ).all()
        parts_sum = sum(mp.total or 0 for mp in maint_parts)
    return {
        "vehicles": vehicles,
        "vendors": vendors,
        "employees": employees,
        "parts": parts,
        "maint_parts": maint_parts,
        "parts_sum": parts_sum,
        "part_map": {p.id: p.name for p in parts},
        "part_unit_map": {p.id: p.unit for p in parts},
        "kinds": models.MAINT_KINDS,
        "paid_by": models.MAINT_PAID_BY,
        "today": date.today().isoformat(),
    }


@app.get("/maint/records/new", response_class=HTMLResponse)
def maint_record_new(request: Request):
    with Session(engine) as s:
        ctx = _maint_form_context(s)
    ctx["request"] = request
    ctx["record"] = None
    return templates.TemplateResponse(request, "maint_record_form.html", ctx)


@app.get("/maint/records/{rec_id}", response_class=HTMLResponse)
def maint_record_edit(request: Request, rec_id: int):
    with Session(engine) as s:
        rec = s.get(MaintRecord, rec_id)
        if rec is None:
            return RedirectResponse("/maint/records", status_code=303)
        ctx = _maint_form_context(s, rec)
    ctx["request"] = request
    ctx["record"] = rec
    return templates.TemplateResponse(request, "maint_record_form.html", ctx)


def _apply_maint_form(rec: MaintRecord, form, s: Session) -> None:
    rec.work_date = _parse_date(form.get("work_date") or "") or date.today()
    rec.kind = (form.get("kind") or "repair").strip()
    rec.status = (form.get("status") or "done").strip()
    rec.plate_raw = (form.get("plate_raw") or "").strip()
    # resolve vehicle_id by plate
    if rec.plate_raw:
        v = s.exec(select(Vehicle).where(Vehicle.plate_no == rec.plate_raw)).first()
        rec.vehicle_id = v.id if v else None
    else:
        rec.vehicle_id = None
    try:
        rec.mile_snapshot = float(form.get("mile_snapshot") or 0)
    except ValueError:
        rec.mile_snapshot = 0.0
    drv_raw = form.get("driver_id") or ""
    rec.driver_id = int(drv_raw) if drv_raw.strip() else None
    rec.symptom = (form.get("symptom") or "").strip()
    rec.work_done = (form.get("work_done") or "").strip()
    vendor_raw = form.get("vendor_id") or ""
    rec.vendor_id = int(vendor_raw) if vendor_raw.strip() else None
    rec.receipt_ref = (form.get("invoice_no") or "").strip()
    rec.paid_by = (form.get("paid_by") or "cash").strip()
    try:
        rec.parts_cost = float(form.get("parts_cost") or 0)
    except ValueError:
        rec.parts_cost = 0.0
    try:
        rec.labor_cost = float(form.get("labor_cost") or 0)
    except ValueError:
        rec.labor_cost = 0.0
    try:
        rec.other_cost = float(form.get("other_cost") or 0)
    except ValueError:
        rec.other_cost = 0.0
    rec.total_cost = (rec.parts_cost or 0) + (rec.labor_cost or 0) + (rec.other_cost or 0)
    rec.notes = (form.get("notes") or "").strip()
    rec.updated_at = datetime.utcnow()


@app.post("/maint/records/new")
async def maint_record_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        rec = MaintRecord(
            record_no=_gen_code(s, MaintRecord, "M", 6),
            work_date=date.today(),
        )
        _apply_maint_form(rec, form, s)
        s.add(rec)
        s.commit()
        s.refresh(rec)
        new_id = rec.id
    return RedirectResponse(f"/maint/records/{new_id}", status_code=303)


@app.post("/maint/records/{rec_id}")
async def maint_record_update(request: Request, rec_id: int):
    form = await request.form()
    with Session(engine) as s:
        rec = s.get(MaintRecord, rec_id)
        if rec is None:
            return RedirectResponse("/maint/records", status_code=303)
        _apply_maint_form(rec, form, s)
        s.add(rec)
        s.commit()
    return RedirectResponse(f"/maint/records/{rec_id}", status_code=303)


@app.post("/maint/records/{rec_id}/delete")
def maint_record_delete(rec_id: int):
    with Session(engine) as s:
        rec = s.get(MaintRecord, rec_id)
        if rec is None:
            return RedirectResponse("/maint/records", status_code=303)
        mps = s.exec(select(MaintPart).where(MaintPart.maint_record_id == rec_id)).all()
        for mp in mps:
            s.delete(mp)
        s.delete(rec)
        s.commit()
    return RedirectResponse("/maint/records", status_code=303)


# ---- MaintPart (line items) ----
@app.post("/maint/records/{rec_id}/parts/add")
async def maint_part_add(request: Request, rec_id: int):
    form = await request.form()
    with Session(engine) as s:
        rec = s.get(MaintRecord, rec_id)
        if rec is None:
            return RedirectResponse("/maint/records", status_code=303)
        pid_raw = form.get("part_id") or ""
        part_id = int(pid_raw) if pid_raw.strip() else None
        try:
            qty = float(form.get("qty") or 0)
        except ValueError:
            qty = 0.0
        try:
            unit_price = float(form.get("unit_price") or 0)
        except ValueError:
            unit_price = 0.0
        name_raw = (form.get("part_name_raw") or "").strip()

        # If no unit_price provided, try Part.default_price
        if unit_price == 0 and part_id:
            p = s.get(Part, part_id)
            if p and p.default_price:
                unit_price = p.default_price

        mp = MaintPart(
            maint_record_id=rec_id,
            part_id=part_id,
            part_name_raw=name_raw,
            qty=qty,
            unit_price=unit_price,
            total=qty * unit_price,
        )
        s.add(mp)

        # Auto stock-out if linked to a master Part
        if part_id and qty > 0:
            t = StockTxn(
                txn_date=rec.work_date,
                part_id=part_id,
                direction="out",
                qty=qty,
                unit_price=unit_price,
                total_amount=qty * unit_price,
                maint_record_id=rec_id,
                note=f"เบิกใช้ในงานซ่อม {rec.record_no}",
            )
            s.add(t)

        # Recompute parts_cost
        s.flush()
        all_lines = s.exec(select(MaintPart).where(MaintPart.maint_record_id == rec_id)).all()
        rec.parts_cost = sum(l.total or 0 for l in all_lines)
        rec.total_cost = (rec.parts_cost or 0) + (rec.labor_cost or 0) + (rec.other_cost or 0)
        rec.updated_at = datetime.utcnow()
        s.add(rec)
        s.commit()
    return RedirectResponse(f"/maint/records/{rec_id}", status_code=303)


@app.post("/maint/records/{rec_id}/parts/{line_id}/delete")
def maint_part_delete(rec_id: int, line_id: int):
    with Session(engine) as s:
        mp = s.get(MaintPart, line_id)
        if mp is None or mp.maint_record_id != rec_id:
            return RedirectResponse(f"/maint/records/{rec_id}", status_code=303)
        # Also remove auto-generated stock-out, if any (match by maint_record_id + part_id + qty)
        if mp.part_id:
            dup = s.exec(
                select(StockTxn).where(
                    StockTxn.maint_record_id == rec_id,
                    StockTxn.part_id == mp.part_id,
                    StockTxn.direction == "out",
                    StockTxn.qty == mp.qty,
                )
            ).first()
            if dup:
                s.delete(dup)
        s.delete(mp)
        s.flush()
        rec = s.get(MaintRecord, rec_id)
        if rec:
            all_lines = s.exec(select(MaintPart).where(MaintPart.maint_record_id == rec_id)).all()
            rec.parts_cost = sum(l.total or 0 for l in all_lines)
            rec.total_cost = (rec.parts_cost or 0) + (rec.labor_cost or 0) + (rec.other_cost or 0)
            rec.updated_at = datetime.utcnow()
            s.add(rec)
        s.commit()
    return RedirectResponse(f"/maint/records/{rec_id}", status_code=303)


# =========================================================================
# Rate Book (price-master + auto-learn from DailyJob history)
# =========================================================================

RATE_DIM_FIELDS = (
    "site_code",
    "customer_id",
    "vehicle_kind",
    "trip_type_code",
    "origin",
    "destination",
    "pickup_location",
)


def _rate_dim_is_wild(card: RateCard, field: str) -> bool:
    v = getattr(card, field, None)
    if field == "customer_id":
        return v is None
    return v in (None, "", "*")


def _rate_dim_match(card: RateCard, field: str, ctx_value) -> bool:
    cv = getattr(card, field, None)
    if field == "customer_id":
        return cv == ctx_value
    a = (cv or "").strip().lower()
    b = (ctx_value or "").strip().lower() if isinstance(ctx_value, str) else str(ctx_value or "").lower()
    return a == b


def _resolve_vehicle_kind(session: Session, ctx: dict) -> str:
    """Normalise vehicle_kind from context.
    Prefer resolved Vehicle.truck_type when FK head_vehicle_id is given.
    """
    kind = (ctx.get("vehicle_kind") or "").strip()
    if kind:
        return kind
    veh_id = ctx.get("head_vehicle_id")
    if veh_id:
        v = session.get(Vehicle, int(veh_id)) if isinstance(veh_id, (int, str)) else None
        if v and v.truck_type:
            return v.truck_type.strip()
    # last resort: DailyJob.truck_type_raw
    raw = (ctx.get("truck_type_raw") or "").strip()
    return raw or ""


def rate_find(session: Session, kind: str, ctx: dict) -> Optional[RateCard]:
    """Return best-matching active RateCard for the given context, or None.

    Scoring: +10 for exact match on a dim, +1 for wildcard. Reject if dim
    is specific in card but mismatches context. Tie-break: priority desc,
    then updated_at desc.
    """
    work_date = ctx.get("work_date")
    cards = session.exec(
        select(RateCard).where(RateCard.kind == kind, RateCard.status == "active")
    ).all()

    best = None
    best_key: tuple = (-1, -1, datetime.min)

    for c in cards:
        if work_date:
            if c.effective_from and work_date < c.effective_from:
                continue
            if c.effective_to and work_date > c.effective_to:
                continue

        score = 0
        ok = True
        for field in RATE_DIM_FIELDS:
            if _rate_dim_is_wild(c, field):
                score += 1
            elif _rate_dim_match(c, field, ctx.get(field)):
                score += 10
            else:
                ok = False
                break
        if not ok:
            continue

        key = (score, c.priority, c.updated_at or datetime.min)
        if key > best_key:
            best = c
            best_key = key
    return best


def rate_record(
    session: Session,
    kind: str,
    ctx: dict,
    value: float,
    job_id: Optional[int] = None,
    source: str = "auto",
) -> Optional[RateCard]:
    """Upsert an exact-dim RateCard from an observed DailyJob entry.

    On duplicate: bump use_count / last_used_at; if source=auto and value
    drifted, overwrite rate_value (latest wins) and annotate notes.
    """
    if value is None or value <= 0:
        return None

    site = (ctx.get("site_code") or "*").strip() or "*"
    customer_id = ctx.get("customer_id") or None
    vehicle_kind = (ctx.get("vehicle_kind") or "*").strip() or "*"
    trip_type = (ctx.get("trip_type_code") or "*").strip() or "*"
    origin = (ctx.get("origin") or "*").strip() or "*"
    destination = (ctx.get("destination") or "*").strip() or "*"
    pickup = (ctx.get("pickup_location") or "*").strip() or "*"

    q = select(RateCard).where(
        RateCard.kind == kind,
        RateCard.site_code == site,
        RateCard.vehicle_kind == vehicle_kind,
        RateCard.trip_type_code == trip_type,
        RateCard.origin == origin,
        RateCard.destination == destination,
        RateCard.pickup_location == pickup,
    )
    if customer_id is None:
        q = q.where(RateCard.customer_id.is_(None))
    else:
        q = q.where(RateCard.customer_id == int(customer_id))

    existing = session.exec(q).first()
    now = datetime.utcnow()
    if existing:
        existing.use_count = (existing.use_count or 0) + 1
        existing.last_used_at = now
        if job_id:
            existing.last_seen_job_id = job_id
        if existing.source != "manual" and abs((existing.rate_value or 0) - value) > 0.01:
            existing.rate_value = value
            existing.notes = ((existing.notes or "") + f" [auto-updated from job#{job_id} on {now.date()}]").strip()
        existing.updated_at = now
        session.add(existing)
        return existing

    card = RateCard(
        kind=kind,
        site_code=site,
        customer_id=int(customer_id) if customer_id else None,
        vehicle_kind=vehicle_kind,
        trip_type_code=trip_type,
        origin=origin,
        destination=destination,
        pickup_location=pickup,
        rate_value=value,
        rate_unit=models.RATE_UNIT_BY_KIND.get(kind, "THB"),
        priority=0,
        source=source,
        use_count=1,
        last_used_at=now,
        last_seen_job_id=job_id,
    )
    session.add(card)
    return card


def rate_record_from_daily(session: Session, dj: DailyJob) -> None:
    """Record all applicable rates from a DailyJob entry (auto-learn)."""
    # Resolve vehicle_kind
    vk = ""
    if dj.head_vehicle_id:
        v = session.get(Vehicle, dj.head_vehicle_id)
        if v:
            vk = (v.truck_type or "").strip()
    if not vk:
        vk = (dj.truck_type_raw or "").strip()

    ctx = {
        "site_code":       dj.site_code or "*",
        "customer_id":     dj.customer_id,
        "vehicle_kind":    vk or "*",
        "trip_type_code":  dj.trip_type_code or "*",
        "origin":          dj.origin or "*",
        "destination":     dj.destination or "*",
        "pickup_location": dj.pickup_location or "*",
    }
    if dj.fuel_liter and dj.fuel_liter > 0:
        rate_record(session, "fuel_budget_liter", ctx, dj.fuel_liter, dj.id)
    if dj.revenue_customer and dj.revenue_customer > 0:
        rate_record(session, "revenue_customer", ctx, dj.revenue_customer, dj.id)
    if dj.trip_fee_driver and dj.trip_fee_driver > 0:
        rate_record(session, "trip_fee_driver", ctx, dj.trip_fee_driver, dj.id)


# ---- Rate Book Routes ----
@app.get("/rates", response_class=HTMLResponse)
def rate_list(
    request: Request,
    kind: Optional[str] = None,
    site: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = None,
):
    with Session(engine) as s:
        stmt = select(RateCard).where(RateCard.status == "active")
        if kind:
            stmt = stmt.where(RateCard.kind == kind)
        if site:
            stmt = stmt.where(RateCard.site_code == site)
        if source:
            stmt = stmt.where(RateCard.source == source)
        stmt = stmt.order_by(RateCard.kind, RateCard.site_code, RateCard.use_count.desc(), RateCard.updated_at.desc())
        cards = s.exec(stmt).all()
        if q:
            ql = q.strip().lower()
            cards = [
                c for c in cards
                if ql in (c.origin or "").lower()
                or ql in (c.destination or "").lower()
                or ql in (c.pickup_location or "").lower()
                or ql in (c.notes or "").lower()
            ]
        customers = s.exec(select(Customer).order_by(Customer.name)).all()
    # aggregate stats
    by_kind: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for c in cards:
        by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
        by_source[c.source] = by_source.get(c.source, 0) + 1
    return templates.TemplateResponse(
        request, "rate_list.html",
        {
            "request": request,
            "cards": cards,
            "kinds": models.RATE_KINDS,
            "kind_map": dict(models.RATE_KINDS),
            "sites": models.SITE_CODES,
            "customer_map": {c.id: c.name for c in customers},
            "kind": kind, "site": site, "source": source, "q": q,
            "by_kind": by_kind, "by_source": by_source,
            "total": len(cards),
        },
    )


def _rate_form_ctx(session: Session, card: Optional[RateCard] = None) -> dict:
    customers = session.exec(select(Customer).order_by(Customer.name)).all()
    return {
        "customers": customers,
        "kinds": models.RATE_KINDS,
        "sites": models.SITE_CODES,
        "sources": [("manual", "Manual"), ("auto", "Auto"), ("import", "Import")],
        "card": card,
    }


@app.get("/rates/new", response_class=HTMLResponse)
def rate_new(request: Request):
    with Session(engine) as s:
        ctx = _rate_form_ctx(s)
    ctx["request"] = request
    return templates.TemplateResponse(request, "rate_form.html", ctx)


@app.get("/rates/{card_id}", response_class=HTMLResponse)
def rate_edit(request: Request, card_id: int):
    with Session(engine) as s:
        card = s.get(RateCard, card_id)
        if card is None:
            return RedirectResponse("/rates", status_code=303)
        ctx = _rate_form_ctx(s, card)
    ctx["request"] = request
    return templates.TemplateResponse(request, "rate_form.html", ctx)


def _apply_rate_form(card: RateCard, form) -> None:
    card.kind = (form.get("kind") or "other").strip()
    card.site_code = (form.get("site_code") or "*").strip() or "*"
    cust_raw = form.get("customer_id") or ""
    card.customer_id = int(cust_raw) if cust_raw.strip() else None
    card.vehicle_kind = (form.get("vehicle_kind") or "*").strip() or "*"
    card.trip_type_code = (form.get("trip_type_code") or "*").strip() or "*"
    card.origin = (form.get("origin") or "*").strip() or "*"
    card.destination = (form.get("destination") or "*").strip() or "*"
    card.pickup_location = (form.get("pickup_location") or "*").strip() or "*"
    card.except_pattern = (form.get("except_pattern") or "").strip()
    try:
        card.rate_value = float(form.get("rate_value") or 0)
    except ValueError:
        card.rate_value = 0.0
    card.rate_unit = models.RATE_UNIT_BY_KIND.get(card.kind, "THB")
    try:
        card.priority = int(form.get("priority") or 0)
    except ValueError:
        card.priority = 0
    card.effective_from = _parse_date(form.get("effective_from") or "")
    card.effective_to = _parse_date(form.get("effective_to") or "")
    card.notes = (form.get("notes") or "").strip()
    card.updated_at = datetime.utcnow()


@app.post("/rates/backfill")
def rate_backfill():
    """One-shot: scan all DailyJob rows and auto-record RateCards.
    Safe to run multiple times — existing exact-match cards just bump use_count.
    MUST be declared before /rates/{card_id} POST to avoid path-param collision.
    """
    with Session(engine) as s:
        jobs = s.exec(select(DailyJob)).all()
        for dj in jobs:
            rate_record_from_daily(s, dj)
        s.commit()
    return RedirectResponse("/rates?backfilled=1", status_code=303)


@app.post("/rates/new")
async def rate_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        card = RateCard(kind="other", source="manual")
        _apply_rate_form(card, form)
        card.source = "manual"
        s.add(card)
        audit_log(s, request, "ratecard", 0, "create", "",
                  f"{card.kind} {card.site_code}/{card.destination} = {card.rate_value}")
        s.commit()
    return RedirectResponse("/rates", status_code=303)


@app.post("/rates/{card_id}/delete")
def rate_delete(card_id: int, request: Request):
    with Session(engine) as s:
        card = s.get(RateCard, card_id)
        if card is not None:
            audit_log(s, request, "ratecard", card_id, "delete",
                      f"{card.kind} {card.site_code}/{card.destination} = {card.rate_value}", "")
            s.delete(card)
            s.commit()
    return RedirectResponse("/rates", status_code=303)


@app.post("/rates/{card_id}")
async def rate_update(request: Request, card_id: int):
    form = await request.form()
    with Session(engine) as s:
        card = s.get(RateCard, card_id)
        if card is None:
            return RedirectResponse("/rates", status_code=303)
        old_value = card.rate_value
        _apply_rate_form(card, form)
        if card.source == "auto" and (form.get("promote_to_manual") or "") == "on":
            card.source = "manual"
            card.priority = max(card.priority, 1)
        if card.rate_value != old_value:
            audit_log(s, request, "ratecard", card_id, "rate_value", old_value,
                      card.rate_value, note=f"{card.kind} {card.site_code}/{card.destination}")
        s.add(card)
        s.commit()
    return RedirectResponse("/rates", status_code=303)


@app.get("/api/rates/suggest")
def api_rate_suggest(
    kind: str,
    site_code: Optional[str] = None,
    customer_id: Optional[int] = None,
    vehicle_kind: Optional[str] = None,
    trip_type_code: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    pickup_location: Optional[str] = None,
    work_date: Optional[str] = None,
):
    """Return best-matching rate for a given DailyJob context.
    Shape: {"rate_value": float, "unit": "THB"|"L", "source": "...", "card_id": int, "score_hint": str} or {"rate_value": null}
    """
    ctx = {
        "site_code": site_code or "*",
        "customer_id": customer_id,
        "vehicle_kind": vehicle_kind or "*",
        "trip_type_code": trip_type_code or "*",
        "origin": origin or "*",
        "destination": destination or "*",
        "pickup_location": pickup_location or "*",
        "work_date": _parse_date(work_date or "") if work_date else None,
    }
    with Session(engine) as s:
        card = rate_find(s, kind, ctx)
    if card is None:
        return {"rate_value": None}
    # Summarise which dims matched exactly (admin transparency)
    matched = []
    for f in RATE_DIM_FIELDS:
        if not _rate_dim_is_wild(card, f) and _rate_dim_match(card, f, ctx.get(f)):
            matched.append(f)
    return {
        "rate_value": card.rate_value,
        "unit": card.rate_unit,
        "source": card.source,
        "card_id": card.id,
        "use_count": card.use_count,
        "matched_dims": matched,
    }


# =====================================================================
# Fuel-adjusted Pricing helpers (schema v11)
# =====================================================================

def _month_tag(d: Optional[date]) -> str:
    """Return 'YYYY-MM' for given date; empty if None."""
    if not d:
        return ""
    return f"{d.year:04d}-{d.month:02d}"


def _shift_month(tag: str, n: int) -> str:
    """Shift 'YYYY-MM' by n months (negative = earlier)."""
    if not tag or "-" not in tag:
        return tag
    try:
        y, m = tag.split("-")
        y, m = int(y), int(m)
    except ValueError:
        return tag
    idx = y * 12 + (m - 1) + n
    ny, nm = divmod(idx, 12)
    return f"{ny:04d}-{nm + 1:02d}"


def get_fuel_price(session: Session, month_tag: str, region: str = "BKK") -> Optional[float]:
    """Look up diesel price for YYYY-MM + region. Fall back to any region if not found."""
    if not month_tag:
        return None
    row = session.exec(
        select(FuelPriceIndex).where(
            FuelPriceIndex.month == month_tag,
            FuelPriceIndex.region == region,
        )
    ).first()
    if row:
        return row.diesel_price
    # Fallback: any region for that month
    row = session.exec(
        select(FuelPriceIndex).where(FuelPriceIndex.month == month_tag)
    ).first()
    return row.diesel_price if row else None


def match_surcharge_band(
    session: Session,
    *,
    customer_id: Optional[int],
    trip_type_code: str,
    vehicle_kind: str,
    on_date: Optional[date],
    diesel_price: float,
) -> Optional[FuelSurchargeBand]:
    """Pick the best-matching active band.

    Priority: specific customer > wildcard customer; specific trip_type > *;
    specific vehicle_kind > *; higher priority > lower; then latest effective_from.
    """
    stmt = select(FuelSurchargeBand).where(FuelSurchargeBand.status == "active")
    bands = session.exec(stmt).all()
    candidates: list[tuple[int, FuelSurchargeBand]] = []
    for b in bands:
        # Customer
        if b.customer_id is not None and b.customer_id != customer_id:
            continue
        # Trip / vehicle dimensions (support wildcard)
        if b.trip_type_code != "*" and b.trip_type_code != (trip_type_code or ""):
            continue
        if b.vehicle_kind != "*" and b.vehicle_kind != (vehicle_kind or ""):
            continue
        # Date range
        if on_date:
            if b.effective_from and on_date < b.effective_from:
                continue
            if b.effective_to and on_date > b.effective_to:
                continue
        # Fuel range: fuel_min <= price < fuel_max
        if diesel_price < b.fuel_min or diesel_price >= b.fuel_max:
            continue
        # Specificity score (higher = more specific)
        score = b.priority * 1000
        if b.customer_id is not None:
            score += 100
        if b.trip_type_code != "*":
            score += 10
        if b.vehicle_kind != "*":
            score += 1
        candidates.append((score, b))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], -(x[1].effective_from.toordinal() if x[1].effective_from else 0)))
    return candidates[0][1]


def compute_effective_rate(
    session: Session,
    *,
    base_rate: float,
    customer_id: Optional[int],
    trip_type_code: str = "*",
    vehicle_kind: str = "*",
    work_date: Optional[date] = None,
    region: str = "BKK",
) -> dict:
    """Apply fuel surcharge on top of base rate.

    Returns:
      {
        "base": base_rate,
        "diesel_price": 32.50 | None,
        "fuel_month": "2026-03" | "",
        "band_id": int | None,
        "pct": 2.0,
        "flat": 0.0,
        "effective": 1020.0,
        "explain": "base 1000 × (1 + 2%) = 1020",
      }
    """
    result = {
        "base": base_rate,
        "diesel_price": None,
        "fuel_month": "",
        "band_id": None,
        "pct": 0.0,
        "flat": 0.0,
        "effective": base_rate,
        "explain": f"base {base_rate:,.2f} (ไม่มี fuel surcharge)",
    }
    if base_rate <= 0 or not customer_id:
        return result

    # Pick a band to know fuel_ref_mode + region
    # Probe first with a dummy price high enough to include all bands, so we
    # can read which fuel_ref_mode to apply. Simpler approach: just try each
    # ref mode in order of specificity. For MVP: if any band configured for
    # this customer uses prev1/prev2, we try them and pick the first match.
    month_current = _month_tag(work_date) if work_date else ""
    bands_any = session.exec(
        select(FuelSurchargeBand).where(
            FuelSurchargeBand.status == "active",
            (FuelSurchargeBand.customer_id == customer_id) | (FuelSurchargeBand.customer_id == None),  # noqa: E711
        )
    ).all()
    if not bands_any:
        return result

    # Try ref modes referenced by this customer's bands
    ref_modes = {(b.fuel_ref_mode or "current") for b in bands_any}
    for mode in ("current", "prev1", "prev2"):
        if mode not in ref_modes:
            continue
        offset = {"current": 0, "prev1": -1, "prev2": -2}[mode]
        m_tag = _shift_month(month_current, offset) if month_current else ""
        price = get_fuel_price(session, m_tag, region=region)
        if price is None or price <= 0:
            continue
        band = match_surcharge_band(
            session,
            customer_id=customer_id,
            trip_type_code=trip_type_code,
            vehicle_kind=vehicle_kind,
            on_date=work_date,
            diesel_price=price,
        )
        if band and (band.fuel_ref_mode or "current") == mode:
            eff = base_rate * (1 + band.surcharge_pct / 100.0) + band.surcharge_flat
            result.update({
                "diesel_price": price,
                "fuel_month": m_tag,
                "band_id": band.id,
                "pct": band.surcharge_pct,
                "flat": band.surcharge_flat,
                "effective": eff,
                "explain": (
                    f"base {base_rate:,.2f} × (1 + {band.surcharge_pct}%) "
                    f"+ {band.surcharge_flat:,.2f} = {eff:,.2f}  "
                    f"(น้ำมัน {m_tag}={price:.2f} ฿/L, {mode})"
                ),
            })
            return result
    return result


# =====================================================================
# Fuel Price Index routes (/fuel-index)
# =====================================================================

@app.get("/fuel-index", response_class=HTMLResponse)
def fuel_index_list(request: Request, region: Optional[str] = None):
    with Session(engine) as s:
        stmt = select(FuelPriceIndex)
        if region:
            stmt = stmt.where(FuelPriceIndex.region == region)
        rows = s.exec(stmt.order_by(FuelPriceIndex.month.desc(), FuelPriceIndex.region)).all()
    return templates.TemplateResponse(
        request, "fuel_index_list.html",
        {
            "request": request,
            "rows": rows,
            "regions": models.FUEL_REGIONS,
            "filter_region": region,
        },
    )


@app.post("/fuel-index/new")
async def fuel_index_create(request: Request):
    form = await request.form()
    month = (form.get("month") or "").strip()
    region = (form.get("region") or "BKK").strip()
    if not month:
        return RedirectResponse("/fuel-index", status_code=303)
    with Session(engine) as s:
        row = s.exec(
            select(FuelPriceIndex).where(
                FuelPriceIndex.month == month,
                FuelPriceIndex.region == region,
            )
        ).first()
        if row is None:
            row = FuelPriceIndex(month=month, region=region)
        row.diesel_price = _parse_float(form.get("diesel_price") or "0")
        row.source = (form.get("source") or "").strip()
        row.notes = (form.get("notes") or "").strip()
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse("/fuel-index", status_code=303)


@app.post("/fuel-index/{row_id}/delete")
def fuel_index_delete(row_id: int):
    with Session(engine) as s:
        row = s.get(FuelPriceIndex, row_id)
        if row is not None:
            s.delete(row)
            s.commit()
    return RedirectResponse("/fuel-index", status_code=303)


# =====================================================================
# Fuel Surcharge Band routes (/fuel-surcharge)
# =====================================================================

@app.get("/fuel-surcharge", response_class=HTMLResponse)
def fuel_surcharge_list(request: Request, customer_id: Optional[int] = None):
    with Session(engine) as s:
        stmt = select(FuelSurchargeBand)
        if customer_id:
            stmt = stmt.where(FuelSurchargeBand.customer_id == customer_id)
        rows = s.exec(
            stmt.order_by(
                FuelSurchargeBand.customer_id.asc(),
                FuelSurchargeBand.priority.desc(),
                FuelSurchargeBand.fuel_min.asc(),
            )
        ).all()
        customers = s.exec(select(Customer).order_by(Customer.name)).all()
    customer_map = {c.id: c.name for c in customers}
    return templates.TemplateResponse(
        request, "fuel_surcharge_list.html",
        {
            "request": request,
            "rows": rows,
            "customers": customers,
            "customer_map": customer_map,
            "ref_modes": models.FUEL_REF_MODES,
            "filter_customer_id": customer_id,
        },
    )


def _apply_surcharge_form(band: FuelSurchargeBand, form) -> None:
    cust_raw = form.get("customer_id") or ""
    band.customer_id = int(cust_raw) if cust_raw.strip() else None
    band.trip_type_code = (form.get("trip_type_code") or "*").strip() or "*"
    band.vehicle_kind = (form.get("vehicle_kind") or "*").strip() or "*"
    band.fuel_min = _parse_float(form.get("fuel_min") or "0")
    band.fuel_max = _parse_float(form.get("fuel_max") or "999")
    band.surcharge_pct = _parse_float(form.get("surcharge_pct") or "0")
    band.surcharge_flat = _parse_float(form.get("surcharge_flat") or "0")
    band.fuel_ref_mode = (form.get("fuel_ref_mode") or "current").strip()
    band.region = (form.get("region") or "BKK").strip()
    band.effective_from = _parse_date(form.get("effective_from") or "")
    band.effective_to = _parse_date(form.get("effective_to") or "")
    try:
        band.priority = int(form.get("priority") or 0)
    except ValueError:
        band.priority = 0
    band.status = (form.get("status") or "active").strip()
    band.notes = (form.get("notes") or "").strip()
    band.updated_at = datetime.utcnow()


@app.post("/fuel-surcharge/new")
async def fuel_surcharge_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        band = FuelSurchargeBand()
        _apply_surcharge_form(band, form)
        s.add(band)
        s.commit()
    return RedirectResponse("/fuel-surcharge", status_code=303)


@app.post("/fuel-surcharge/{band_id}")
async def fuel_surcharge_update(request: Request, band_id: int):
    form = await request.form()
    with Session(engine) as s:
        band = s.get(FuelSurchargeBand, band_id)
        if band is None:
            return RedirectResponse("/fuel-surcharge", status_code=303)
        _apply_surcharge_form(band, form)
        s.add(band)
        s.commit()
    return RedirectResponse("/fuel-surcharge", status_code=303)


@app.post("/fuel-surcharge/{band_id}/delete")
def fuel_surcharge_delete(band_id: int):
    with Session(engine) as s:
        band = s.get(FuelSurchargeBand, band_id)
        if band is not None:
            s.delete(band)
            s.commit()
    return RedirectResponse("/fuel-surcharge", status_code=303)


@app.get("/api/rates/effective")
def api_rate_effective(
    base_rate: float,
    customer_id: Optional[int] = None,
    trip_type_code: Optional[str] = None,
    vehicle_kind: Optional[str] = None,
    work_date: Optional[str] = None,
    region: str = "BKK",
):
    """Return base + fuel surcharge = effective rate for UI preview."""
    wd = _parse_date(work_date or "") if work_date else None
    with Session(engine) as s:
        out = compute_effective_rate(
            s,
            base_rate=base_rate,
            customer_id=customer_id,
            trip_type_code=trip_type_code or "*",
            vehicle_kind=vehicle_kind or "*",
            work_date=wd,
            region=region,
        )
    return out


# =====================================================================
# Maintenance — PM / RM (Wave 3)
# =====================================================================

def _pm_compute_next_due(p: PmPlan, vehicle: Optional[Vehicle] = None) -> tuple[Optional[date], float]:
    """Compute (next_due_date, next_due_mile) from last_done + intervals."""
    nd_date = None
    nd_mile = 0.0
    if p.last_done_date and (p.interval_days or 0) > 0:
        nd_date = p.last_done_date + timedelta(days=int(p.interval_days))
    if (p.last_done_mile or 0) > 0 and (p.interval_km or 0) > 0:
        nd_mile = float(p.last_done_mile) + float(p.interval_km)
    return nd_date, nd_mile


def _pm_status(p: PmPlan, vehicle: Optional[Vehicle]) -> dict:
    """Return {'status': overdue|due_soon|ok|unknown, 'remaining_km', 'remaining_days', 'reasons': [..]}"""
    today = date.today()
    current_mile = float(vehicle.current_mile) if vehicle and vehicle.current_mile else 0.0
    reasons = []
    overdue = False
    due_soon = False
    remaining_km = None
    remaining_days = None

    if p.next_due_mile and current_mile:
        remaining_km = float(p.next_due_mile) - current_mile
        if remaining_km <= 0:
            overdue = True
            reasons.append(f"เลยกำหนด {-remaining_km:,.0f} km")
        elif remaining_km <= (p.alert_km_before or 0):
            due_soon = True
            reasons.append(f"เหลือ {remaining_km:,.0f} km")

    if p.next_due_date:
        remaining_days = (p.next_due_date - today).days
        if remaining_days < 0:
            overdue = True
            reasons.append(f"เลยกำหนด {-remaining_days} วัน")
        elif remaining_days <= 7:
            due_soon = True
            reasons.append(f"เหลือ {remaining_days} วัน")

    if overdue:
        status = "overdue"
    elif due_soon:
        status = "due_soon"
    elif p.next_due_date or p.next_due_mile:
        status = "ok"
    else:
        status = "unknown"
    return {
        "status": status,
        "remaining_km": remaining_km,
        "remaining_days": remaining_days,
        "reasons": reasons,
    }


@app.get("/maint/pm", response_class=HTMLResponse)
def maint_pm_list(request: Request, status_filter: str = "", fluid_filter: str = "", vehicle_filter: str = ""):
    with Session(engine) as s:
        plans = s.exec(select(PmPlan).where(PmPlan.status == "active")).all()
        vehicles = s.exec(select(Vehicle)).all()
        v_map = {v.id: v for v in vehicles}

        rows = []
        for p in plans:
            v = v_map.get(p.vehicle_id) if p.vehicle_id else None
            st = _pm_status(p, v)
            rows.append({"plan": p, "vehicle": v, "st": st})

        if fluid_filter:
            rows = [r for r in rows if r["plan"].fluid_kind == fluid_filter]
        if vehicle_filter:
            rows = [r for r in rows if r["vehicle"] and vehicle_filter.lower() in (r["vehicle"].plate_no or "").lower()]
        if status_filter:
            rows = [r for r in rows if r["st"]["status"] == status_filter]

        rows.sort(key=lambda r: (
            {"overdue": 0, "due_soon": 1, "ok": 2, "unknown": 3}[r["st"]["status"]],
            r["st"]["remaining_km"] if r["st"]["remaining_km"] is not None else 1e12,
        ))

        counts = {"overdue": 0, "due_soon": 0, "ok": 0, "unknown": 0}
        for r in rows:
            counts[r["st"]["status"]] += 1

    return templates.TemplateResponse(
        request, "pm_list.html",
        {
            "request": request,
            "rows": rows,
            "vehicles": vehicles,
            "fluid_kinds": models.FLUID_KINDS,
            "fluid_map": dict(models.FLUID_KINDS),
            "status_filter": status_filter,
            "fluid_filter": fluid_filter,
            "vehicle_filter": vehicle_filter,
            "counts": counts,
            "total": len(rows),
        },
    )


@app.get("/maint/pm/new", response_class=HTMLResponse)
def maint_pm_new_form(request: Request, vehicle_id: Optional[int] = None):
    with Session(engine) as s:
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    return templates.TemplateResponse(
        request, "pm_form.html",
        {
            "request": request,
            "plan": None,
            "vehicles": vehicles,
            "fluid_kinds": models.FLUID_KINDS,
            "preselect_vehicle_id": vehicle_id,
        },
    )


@app.get("/maint/pm/{plan_id}", response_class=HTMLResponse)
def maint_pm_edit_form(request: Request, plan_id: int):
    with Session(engine) as s:
        plan = s.get(PmPlan, plan_id)
        if not plan:
            raise HTTPException(404, "PmPlan not found")
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        vehicle = s.get(Vehicle, plan.vehicle_id) if plan.vehicle_id else None
        st = _pm_status(plan, vehicle)
        # history: MaintRecords referencing this plan? we use last_maint_record_id
        last_rec = s.get(MaintRecord, plan.last_maint_record_id) if plan.last_maint_record_id else None
    return templates.TemplateResponse(
        request, "pm_form.html",
        {
            "request": request,
            "plan": plan,
            "vehicles": vehicles,
            "fluid_kinds": models.FLUID_KINDS,
            "vehicle": vehicle,
            "status_info": st,
            "last_record": last_rec,
        },
    )


def _apply_pm_form(plan: PmPlan, form) -> None:
    plan.name = (form.get("name") or "").strip() or plan.name
    plan.kind = (form.get("kind") or "PM").strip()
    plan.fluid_kind = (form.get("fluid_kind") or "other").strip()
    vid = form.get("vehicle_id") or ""
    plan.vehicle_id = int(vid) if vid.isdigit() else None
    plan.interval_km = _parse_float(form.get("interval_km") or "0")
    plan.interval_days = int(_parse_float(form.get("interval_days") or "0"))
    plan.alert_km_before = _parse_float(form.get("alert_km_before") or "1000")
    plan.last_done_date = _parse_date(form.get("last_done_date") or "")
    plan.last_done_mile = _parse_float(form.get("last_done_mile") or "0")
    plan.description = (form.get("description") or "").strip()
    plan.notes = (form.get("notes") or "").strip()
    plan.status = (form.get("status") or "active").strip()
    # recompute next_due
    nd_date, nd_mile = _pm_compute_next_due(plan)
    plan.next_due_date = nd_date
    plan.next_due_mile = nd_mile
    plan.updated_at = datetime.utcnow()


@app.post("/maint/pm/new")
async def maint_pm_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        p = PmPlan(code=_gen_code(s, PmPlan, "PM", 4), name="")
        _apply_pm_form(p, form)
        if not p.name:
            raise HTTPException(400, "name required")
        s.add(p)
        s.commit()
        pid = p.id
    return RedirectResponse(f"/maint/pm/{pid}", status_code=303)


@app.post("/maint/pm/{plan_id}")
async def maint_pm_update(plan_id: int, request: Request):
    form = await request.form()
    with Session(engine) as s:
        p = s.get(PmPlan, plan_id)
        if not p:
            raise HTTPException(404, "PmPlan not found")
        _apply_pm_form(p, form)
        s.add(p)
        s.commit()
    return RedirectResponse(f"/maint/pm/{plan_id}", status_code=303)


@app.post("/maint/pm/{plan_id}/delete")
def maint_pm_delete(plan_id: int):
    with Session(engine) as s:
        p = s.get(PmPlan, plan_id)
        if p:
            s.delete(p)
            s.commit()
    return RedirectResponse("/maint/pm", status_code=303)


@app.post("/maint/pm/{plan_id}/mark_done")
async def maint_pm_mark_done(plan_id: int, request: Request):
    """เมื่อเปลี่ยนแล้ว — บันทึก last_done + สร้าง MaintRecord อัตโนมัติ (optional)"""
    form = await request.form()
    done_date = _parse_date(form.get("done_date") or "") or date.today()
    done_mile = _parse_float(form.get("done_mile") or "0")
    create_record = (form.get("create_record") or "") == "1"
    with Session(engine) as s:
        p = s.get(PmPlan, plan_id)
        if not p:
            raise HTTPException(404, "PmPlan not found")
        p.last_done_date = done_date
        p.last_done_mile = done_mile
        # recompute next
        nd_date, nd_mile = _pm_compute_next_due(p)
        p.next_due_date = nd_date
        p.next_due_mile = nd_mile
        # also bump vehicle.current_mile
        if p.vehicle_id:
            v = s.get(Vehicle, p.vehicle_id)
            if v and done_mile and done_mile > (v.current_mile or 0):
                v.current_mile = done_mile
                v.updated_at = datetime.utcnow()
                s.add(v)

        if create_record:
            v = s.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
            rec = MaintRecord(
                record_no=_gen_code(s, MaintRecord, "M", 6),
                work_date=done_date,
                vehicle_id=p.vehicle_id,
                plate_raw=v.plate_no if v else "",
                mile_snapshot=done_mile,
                kind="service",
                status="done",
                work_done=f"PM: {p.name}",
                notes=(form.get("record_note") or "").strip(),
            )
            s.add(rec)
            s.commit()
            s.refresh(rec)
            p.last_maint_record_id = rec.id

        p.updated_at = datetime.utcnow()
        s.add(p)
        s.commit()
    return RedirectResponse(f"/maint/pm/{plan_id}", status_code=303)


# =====================================================================
# Tire Check — magic-link (login-less) data entry for drivers & mechanics
# =====================================================================
import services.access_link as access_link
import services.tire_view as tire_view

LINK_MAX_AGE_DEFAULT = 3600   # seconds; UI lets admin pick ttl in hours
LINK_HARD_CAP_SECONDS = 7 * 24 * 3600   # signature never honored beyond 7 days


def _check_link_guard(request: Request, session: Session, count_use: bool = True):
    """Return the live AccessLink for a request's ?t= token, or None.

    count_use=False สำหรับ subresource (รูปใน /uploads) — ไม่บวก use_count
    ให้ตัวนับใน /admin/check-links ยังแปลว่า "เปิดลิงก์กี่ครั้ง" ไม่ใช่จำนวนรูป.
    """
    tok = request.query_params.get("t") or ""
    if not tok:
        return None
    payload = access_link.read_token(tok, max_age_seconds=LINK_HARD_CAP_SECONDS)
    if not payload:
        return None
    link = session.exec(select(AccessLink).where(AccessLink.token == tok)).first()
    if not link or link.revoked or link.expires_at < datetime.utcnow():
        return None
    if count_use:
        link.use_count += 1
        link.last_used_at = datetime.utcnow()
        session.add(link); session.commit()
    return link


@app.get("/check", response_class=HTMLResponse)
def check_landing(request: Request):
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link:
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        role_th = dict(models.ACCESS_LINK_ROLES).get(link.role, link.role)
    return templates.TemplateResponse(request, "check_landing.html", {
        "request": request, "token": request.query_params.get("t"),
        "role": link.role, "role_th": role_th,
    })


@app.get("/c/{code}")
def check_short_redirect(code: str):
    """Resolve a short code to its full magic-link token and redirect to /check."""
    with Session(engine) as s:
        link = s.exec(select(AccessLink).where(AccessLink.short_code == code)).first()
        if not link:
            raise HTTPException(404, "ลิงก์ไม่ถูกต้องหรือหมดอายุ")
        tok = link.token
    return RedirectResponse(f"/check?t={tok}", status_code=303)


@app.get("/admin/check-links", response_class=HTMLResponse)
def admin_check_links(request: Request):
    u = current_user(request)
    with Session(engine) as s:
        links = s.exec(select(AccessLink).order_by(AccessLink.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse(request, "check_links_admin.html", {
        "request": request, "links": links, "roles": models.ACCESS_LINK_ROLES, "user": u,
    })


def _gen_short_code(s: Session, n: int = 6) -> str:
    """Random URL-safe code unique within accesslink.short_code."""
    import secrets
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"  # no 0/O/1/I/l
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(n))
        if not s.exec(select(AccessLink).where(AccessLink.short_code == code)).first():
            return code
    return secrets.token_urlsafe(8)[:n]   # fallback


@app.post("/admin/check-links")
async def admin_check_links_create(request: Request):
    u = current_user(request)
    form = await request.form()
    role = (form.get("role") or "driver").strip()
    ttl_hours = _parse_int(form.get("ttl_hours") or "1") or 1
    tok = access_link.make_token(role, ttl_hours * 3600)
    with Session(engine) as s:
        s.add(AccessLink(
            token=tok, role=role, short_code=_gen_short_code(s),
            created_by=(u.username if u else ""),
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
        ))
        s.commit()
    return RedirectResponse("/admin/check-links", status_code=303)


@app.post("/admin/check-links/{link_id}/revoke")
def admin_check_link_revoke(link_id: int):
    """Disable a link immediately. Row is kept (audit) but the link stops working."""
    with Session(engine) as s:
        link = s.get(AccessLink, link_id)
        if link:
            link.revoked = True
            s.add(link); s.commit()
    return RedirectResponse("/admin/check-links", status_code=303)


def _last_inspect_mile(session: Session, vehicle_id: int) -> float:
    row = session.exec(select(TireEvent).where(
        TireEvent.event_type == "inspect", TireEvent.to_vehicle_id == vehicle_id,
        TireEvent.mile > 0).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())).first()
    return row.mile if row else 0.0


@app.get("/check/driver", response_class=HTMLResponse)
def check_driver_form(request: Request):
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "driver":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        vehicles = s.exec(select(Vehicle).where(Vehicle.status == "active").order_by(Vehicle.plate_no)).all()
        vid = _parse_int(request.query_params.get("vehicle_id") or "") or 0
        v = s.get(Vehicle, vid) if vid else None
        positions = _tire_positions_for_vehicle(v) if v else ()
        axles = tire_view.axle_layout(positions) if positions else []
        # After a head submit (?done=n) offer to inspect a trailer next (optional).
        done = _parse_int(request.query_params.get("done") or "") or 0
        trailers = []
        if done:
            trailers = s.exec(select(Vehicle).where(
                Vehicle.vehicle_kind == "tail",
                Vehicle.status == "active").order_by(Vehicle.plate_no)).all()
    return templates.TemplateResponse(request, "check_driver.html", {
        "request": request, "token": request.query_params.get("t"),
        "actor_name": request.query_params.get("actor_name", ""),
        "vehicles": vehicles, "vehicle": v, "axles": axles,
        "conditions": models.TIRE_CONDITION_FLAGS,
        "weekly_items": models.VEHICLE_CHECK_ITEMS,
        "weekly_status": models.VEHICLE_CHECK_STATUS,
        "type_options": [("6W", "6 ล้อ"), ("10W", "10 ล้อ"),
                         ("TRL8", "หาง 8 ล้อ"), ("10WL", "หัว+หาง 10 ล้อ"),
                         ("18W", "18 ล้อ")],
        "done": done, "trailers": trailers,
    })


@app.post("/check/driver")
async def check_driver_submit(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "driver":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)

        actor_name = (form.get("actor_name") or "").strip()
        vehicle_id = _parse_int(form.get("vehicle_id") or "") or 0
        mile = _parse_float(form.get("mile") or "0")
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise HTTPException(400, "เลือกทะเบียนรถก่อน")

        last = _last_inspect_mile(s, vehicle_id)
        warn_mile = bool(last and mile and mile < last)

        positions = _tire_positions_for_vehicle(v)
        today = date.today()

        # Pass 1: read photos for every touched tyre and ENFORCE the required count
        # (outer = 2, inner = 1). Validate everything before writing anything, so a
        # single short tyre rejects the whole submit without saving a partial record.
        pending = []   # (pos, cond, [photo bytes])
        for pos in positions:
            cond = (form.get(f"cond_{pos}") or "").strip()
            if not cond:
                continue   # untouched position
            need = tire_view.photo_count(pos)
            shots = []
            files = form.getlist(f"photo_{pos}") if hasattr(form, "getlist") else []
            for f in files:
                if hasattr(f, "read"):
                    data = await f.read()
                    if data and len(data) > 100:
                        shots.append(data)
            if len(shots) < need:
                label = tire_view.th_label(pos)
                raise HTTPException(
                    400, f"ต้องถ่ายรูปให้ครบทุกเส้น — “{label}” ต้องมี {need} รูป "
                         f"(ได้ {len(shots)})")
            pending.append((pos, cond, shots))

        created = 0
        for pos, cond, shots in pending:
            paths = [drv.save_photo(0, "check", data, ext="jpg") for data in shots]
            tire = s.exec(select(Tire).where(
                Tire.current_vehicle_id == vehicle_id, Tire.current_position == pos)).first()
            ev = TireEvent(
                tire_id=(tire.id if tire else 0),
                event_date=today, event_type="inspect",
                to_vehicle_id=vehicle_id, to_position=pos, mile=mile,
                tread_before_mm=(tire.tread_depth_mm if tire else 0.0),
                tread_after_mm=0.0,
                actor_name=actor_name, actor_role="driver",
                condition_flag=cond, photo_paths=",".join(paths),
            )
            s.add(ev); created += 1

        # Weekly fluid/equipment check -> reuse DriverSubmission (no Employee for link entry).
        if form.get("weekly"):
            answers = {}
            any_fail = False
            for key, _ in models.VEHICLE_CHECK_ITEMS:
                val = (form.get(f"item_{key}") or "").strip()
                if not val:
                    continue
                answers[key] = val
                if val == "fail":
                    any_fail = True
            if answers:
                s.add(DriverSubmission(
                    employee_id=None, kind="vehicle_check",
                    vehicle_id=vehicle_id, plate_raw=(v.plate_no if v else ""),
                    data_json=_json.dumps(
                        {"items": answers, "actor_name": actor_name, "source": "check_link"},
                        ensure_ascii=False),
                    review_status="flagged" if any_fail else "pending",
                    device_info=request.headers.get("user-agent", "")[:200],
                ))
        s.commit()
    return RedirectResponse(
        f"/check/driver?t={form.get('t')}&done={created}&warn_mile={int(warn_mile)}",
        status_code=303)


@app.get("/check/mechanic", response_class=HTMLResponse)
def check_mechanic_form(request: Request):
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        queue = tire_view.awaiting_mechanic(s)
        rows = [{"ev": e, "label": tire_view.th_label(e.to_position or "")} for e in queue]
        tires = s.exec(select(Tire)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        vid = _parse_int(request.query_params.get("vehicle_id") or "") or 0
        insp_v = s.get(Vehicle, vid) if vid else None
        positions = _tire_positions_for_vehicle(insp_v) if insp_v else ()
        axles = tire_view.axle_layout(positions) if positions else []
    return templates.TemplateResponse(request, "check_mechanic.html", {
        "request": request, "token": request.query_params.get("t"),
        "queue": rows, "tires": tires, "vehicles": vehicles,
        "event_types": models.TIRE_EVENT_TYPES,
        "insp_vehicle": insp_v, "axles": axles,
        "conditions": models.TIRE_CONDITION_FLAGS,
        "truck_types": models.TRUCK_TYPES,
        "truck_type_th": models.TRUCK_TYPE_TH,
    })


@app.post("/check/mechanic/measure")
async def check_mechanic_measure(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        ev = s.get(TireEvent, _parse_int(form.get("event_id") or "") or 0)
        if not ev:
            raise HTTPException(404, "ไม่พบรายการ")
        ev.tread_after_mm = _parse_float(form.get("tread_mm") or "0")
        ev.actor_role = "mechanic"
        ev.actor_name = (form.get("actor_name") or "").strip() or ev.actor_name
        t = s.get(Tire, ev.tire_id) if ev.tire_id else None
        if t and ev.tread_after_mm:
            t.tread_depth_mm = ev.tread_after_mm
            s.add(t)
        s.add(ev); s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}", status_code=303)


@app.post("/check/mechanic/job")
async def check_mechanic_job(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        t = s.get(Tire, _parse_int(form.get("tire_id") or "") or 0)
        if not t:
            raise HTTPException(404, "ไม่พบยาง")
        _apply_tire_event(
            s, t,
            event_type=(form.get("event_type") or "").strip(),
            event_date=_parse_date(form.get("event_date") or "") or date.today(),
            mile=_parse_float(form.get("mile") or "0"),
            to_vehicle_id=_parse_int(form.get("to_vehicle_id") or "") or None,
            to_position=(form.get("to_position") or "").strip().upper(),
            note=(form.get("note") or "").strip(),
            actor_name=(form.get("actor_name") or "").strip(),
            actor_role="mechanic",
        )
        s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}", status_code=303)


@app.post("/check/mechanic/inspect")
async def check_mechanic_inspect(request: Request):
    """Mechanic inspects a whole vehicle via the top-view: condition + measured mm
    + photos per tyre. Like the driver flow but tread is filled now (not awaiting)."""
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        actor_name = (form.get("actor_name") or "").strip()
        vehicle_id = _parse_int(form.get("vehicle_id") or "") or 0
        mile = _parse_float(form.get("mile") or "0")
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise HTTPException(400, "เลือกทะเบียนรถก่อน")
        positions = _tire_positions_for_vehicle(v)
        today = date.today()
        created = 0
        for pos in positions:
            cond = (form.get(f"cond_{pos}") or "").strip()
            mm = _parse_float(form.get(f"mm_{pos}") or "0")
            if not cond and not mm:
                continue   # untouched tyre
            paths = []
            files = form.getlist(f"photo_{pos}") if hasattr(form, "getlist") else []
            for f in files:
                if hasattr(f, "read"):
                    data = await f.read()
                    if data and len(data) > 100:
                        paths.append(drv.save_photo(0, "check", data, ext="jpg"))
            tire = s.exec(select(Tire).where(
                Tire.current_vehicle_id == vehicle_id, Tire.current_position == pos)).first()
            ev = TireEvent(
                tire_id=(tire.id if tire else 0),
                event_date=today, event_type="inspect",
                to_vehicle_id=vehicle_id, to_position=pos, mile=mile,
                tread_before_mm=(tire.tread_depth_mm if tire else 0.0),
                tread_after_mm=mm,
                actor_name=actor_name, actor_role="mechanic",
                condition_flag=cond, photo_paths=",".join(paths),
            )
            s.add(ev)
            if tire and mm:
                tire.tread_depth_mm = mm
                s.add(tire)
            created += 1
        s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}&done={created}", status_code=303)


@app.post("/check/add-vehicle")
async def check_add_vehicle(request: Request):
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link:
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        role = (form.get("role") or link.role or "driver").strip()
        plate = (form.get("plate_no") or "").strip()
        truck_type = (form.get("truck_type") or "").strip().upper()
        nickname = (form.get("nickname") or "").strip()
        if not plate:
            raise HTTPException(400, "กรอกทะเบียนก่อน")

        existing = s.exec(select(Vehicle).where(Vehicle.plate_no == plate)).first()
        if existing:
            vid = existing.id   # reuse, never overwrite truck_type
        else:
            kind = "tail" if truck_type.startswith("TRL") else "head"
            v = Vehicle(plate_no=plate, truck_type=truck_type or "10W",
                        vehicle_kind=kind, nickname=nickname,
                        status="active", notes="added via check-link")
            s.add(v); s.commit(); s.refresh(v)
            vid = v.id
    dest = "/check/mechanic" if role == "mechanic" else "/check/driver"
    return RedirectResponse(f"{dest}?t={form.get('t')}&vehicle_id={vid}", status_code=303)


@app.post("/check/mechanic/edit-vehicle")
async def check_mechanic_edit_vehicle(request: Request):
    """Mechanic fixes a vehicle's truck_type (6W/10W/หาง) permanently.
    Driver cannot — they report a wrong type to the mechanic instead."""
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        v = s.get(Vehicle, _parse_int(form.get("vehicle_id") or "") or 0)
        if not v:
            raise HTTPException(400, "เลือกทะเบียนรถก่อน")
        new_type = (form.get("truck_type") or "").strip().upper()
        if new_type:
            v.truck_type = new_type
            if new_type.startswith("TRL"):
                v.vehicle_kind = "tail"
            s.add(v); s.commit()
        vid = v.id
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}&vehicle_id={vid}", status_code=303)


@app.post("/check/mechanic/edit-vehicles")
async def check_mechanic_edit_vehicles(request: Request):
    """Bulk: mechanic fixes truck_type for many vehicles at once.
    Form has one `type_<vehicle_id>` field per row; only changed rows are saved."""
    form = await request.form()
    with Session(engine) as s:
        link = _check_link_guard(request, s)
        if not link or link.role != "mechanic":
            return HTMLResponse("ลิงก์ไม่ถูกต้องหรือหมดอายุ", status_code=403)
        changed = 0
        for key in form.keys():
            if not key.startswith("type_"):
                continue
            new_type = (form.get(key) or "").strip().upper()
            if not new_type:
                continue
            v = s.get(Vehicle, _parse_int(key[len("type_"):]) or 0)
            if not v or v.truck_type == new_type:
                continue
            v.truck_type = new_type
            if new_type.startswith("TRL"):
                v.vehicle_kind = "tail"
            s.add(v); changed += 1
        s.commit()
    return RedirectResponse(f"/check/mechanic?t={form.get('t')}&saved={changed}", status_code=303)


# =====================================================================
# Maintenance — Tires (Wave 2)
# =====================================================================


@app.get("/maint/tires/setup", response_class=HTMLResponse)
def maint_tire_setup_form(request: Request):
    with Session(engine) as s:
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    return templates.TemplateResponse(request, "tire_setup.html", {
        "request": request,
        "vehicles": vehicles,
        "today": date.today().isoformat(),
    })


@app.get("/maint/tires/setup/grid", response_class=HTMLResponse)
def maint_tire_setup_grid(request: Request, vehicle_id: int = 0):
    with Session(engine) as s:
        v = s.get(Vehicle, vehicle_id) if vehicle_id else None
    positions = _tire_positions_for_vehicle(v) if v else ()
    return templates.TemplateResponse(request, "tire_setup_grid.html", {
        "request": request,
        "vehicle": v,
        "positions": positions,
    })


@app.post("/maint/tires/setup")
async def maint_tire_setup_save(request: Request):
    """Bulk-create tires + mount events for all checked positions."""
    form = await request.form()
    vehicle_id = int(form.get("vehicle_id") or 0)
    mount_date = _parse_date(form.get("mount_date") or "") or date.today()
    mount_mile = _parse_float(form.get("mount_mile") or "0")
    default_brand = (form.get("default_brand") or "").strip()
    default_model = (form.get("default_model") or "").strip()
    default_spec = (form.get("default_spec") or "").strip()
    default_purchase_date = _parse_date(form.get("default_purchase_date") or "")
    default_purchase_price = _parse_float(form.get("default_purchase_price") or "0")

    with Session(engine) as s:
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise HTTPException(404, "Vehicle not found")
        positions = _tire_positions_for_vehicle(v)

        created = 0
        for pos in positions:
            if not form.get(f"include_{pos}"):
                continue
            brand = (form.get(f"brand_{pos}") or "").strip() or default_brand
            model = (form.get(f"model_{pos}") or "").strip() or default_model
            spec = (form.get(f"spec_{pos}") or "").strip() or default_spec
            serial_no = (form.get(f"serial_{pos}") or "").strip()
            tread = _parse_float(form.get(f"tread_{pos}") or "0")
            note = (form.get(f"note_{pos}") or "").strip()

            t = Tire(
                code=_gen_code(s, Tire, "T", 4),
                brand=brand,
                model=model,
                spec=spec,
                serial_no=serial_no,
                purchase_date=default_purchase_date,
                purchase_price=default_purchase_price,
                status="in_use",
                current_vehicle_id=vehicle_id,
                current_position=pos,
                mounted_at=mount_date,
                mounted_mile=mount_mile,
                tread_depth_mm=tread,
                notes=note,
            )
            s.add(t)
            s.flush()

            ev = TireEvent(
                tire_id=t.id,
                event_date=mount_date,
                event_type="mount",
                to_vehicle_id=vehicle_id,
                to_position=pos,
                mile=mount_mile,
                tread_before_mm=tread,
                tread_after_mm=tread,
                note=f"Quick Setup{' — ' + note if note else ''}",
            )
            s.add(ev)
            created += 1

        s.commit()

    return RedirectResponse(f"/maint/tires/by-vehicle/{vehicle_id}", status_code=303)

def _tire_positions_for_vehicle(v: Optional[Vehicle]) -> tuple:
    """Return list of position codes for a vehicle based on its truck_type."""
    if v is None:
        return ()
    key = (v.truck_type or "").upper().replace(" ", "")
    if "TRL8" in key or (("TRL" in key or "TAIL" in key) and "8" in key):
        return models.TIRE_POSITIONS_BY_KIND["TRL8"]
    if "18" in key:
        return models.TIRE_POSITIONS_BY_KIND["18W"]
    if "10W" in key and ("L" in key or "TRL" in key or "LAK" in key.upper()):
        return models.TIRE_POSITIONS_BY_KIND["10WL"]
    if "10" in key:
        return models.TIRE_POSITIONS_BY_KIND["10W"]
    if "6" in key:
        return models.TIRE_POSITIONS_BY_KIND["6W"]
    # default: 10W
    return models.TIRE_POSITIONS_BY_KIND["10W"]


@app.get("/maint/tires", response_class=HTMLResponse)
def maint_tire_list(request: Request, status_filter: str = "", vehicle_filter: str = "", q: str = ""):
    with Session(engine) as s:
        tires = s.exec(select(Tire)).all()
        vehicles = s.exec(select(Vehicle)).all()
        v_map = {v.id: v for v in vehicles}

        rows = list(tires)
        if status_filter:
            rows = [t for t in rows if t.status == status_filter]
        if vehicle_filter:
            rows = [t for t in rows if t.current_vehicle_id and vehicle_filter.lower() in (v_map.get(t.current_vehicle_id, Vehicle(plate_no="")).plate_no or "").lower()]
        if q:
            ql = q.lower()
            rows = [t for t in rows if ql in (t.brand or "").lower() or ql in (t.model or "").lower() or ql in (t.serial_no or "").lower() or ql in (t.spec or "").lower()]

        rows.sort(key=lambda t: ((t.current_vehicle_id or 0), t.current_position or "", t.code))
        counts = {k[0]: 0 for k in models.TIRE_STATUS}
        for t in tires:
            counts[t.status] = counts.get(t.status, 0) + 1

    return templates.TemplateResponse(
        request, "tire_list.html",
        {
            "request": request,
            "tires": rows,
            "v_map": v_map,
            "vehicles": vehicles,
            "status_options": models.TIRE_STATUS,
            "status_filter": status_filter,
            "vehicle_filter": vehicle_filter,
            "q": q,
            "counts": counts,
            "total": len(tires),
        },
    )


# --- Tire "หยุดเลือด": bill entry (office) + cost/longevity report -----------
# NOTE: these literal paths MUST be declared before /maint/tires/{tire_id}
# below, otherwise Starlette matches "bill"/"report" as a tire_id.

@app.get("/maint/tires/bill", response_class=HTMLResponse)
def maint_tire_bill_form(request: Request, vehicle_id: int = 0):
    with Session(engine) as s:
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        vendors = s.exec(
            select(Vendor).where(Vendor.kind == "tire").order_by(Vendor.name)
        ).all()
        sel = s.get(Vehicle, vehicle_id) if vehicle_id else None
    positions = _tire_positions_for_vehicle(sel) if sel else ()
    return templates.TemplateResponse(request, "tire_bill.html", {
        "request": request,
        "vehicles": vehicles,
        "vendors": vendors,
        "selected": sel,
        "positions": positions,
        "tire_types": models.TIRE_TYPES,
        "removal_reasons": models.TIRE_REMOVAL_REASONS,
        "paid_by_options": models.MAINT_PAID_BY,
        "today": date.today().isoformat(),
    })


@app.get("/maint/tires/bill/positions", response_class=HTMLResponse)
def maint_tire_bill_positions(request: Request, vehicle_id: int = 0):
    """HTMX partial: position <option>s for the chosen vehicle."""
    with Session(engine) as s:
        v = s.get(Vehicle, vehicle_id) if vehicle_id else None
    positions = _tire_positions_for_vehicle(v) if v else ()
    opts = "".join(
        f'<option value="{p}">{models.TIRE_POSITION_TH.get(p, p)} ({p})</option>'
        for p in positions
    )
    return HTMLResponse(opts)


@app.post("/maint/tires/bill")
async def maint_tire_bill_save(request: Request):
    """One tire bill -> MaintRecord(kind=tire_change) + per-tyre Tire/mount/MaintPart.

    Any tyre currently at a target position is auto-unmounted (carrying the
    replacement's removal reason) by _apply_tire_event's mount branch, and we
    also stamp removal_reason on it explicitly for the office flow.
    """
    form = await request.form()
    vehicle_id = int(form.get("vehicle_id") or 0)
    work_date = _parse_date(form.get("work_date") or "") or date.today()
    mile = _parse_float(form.get("mile") or "0")
    vendor_raw = form.get("vendor_id") or ""
    vendor_id = int(vendor_raw) if vendor_raw.strip().isdigit() else None
    paid_by = (form.get("paid_by") or "cash").strip()
    receipt_ref = (form.get("receipt_ref") or "").strip()
    mechanic_name = (form.get("mechanic_name") or "").strip()
    row_count = int(form.get("row_count") or 0)

    with Session(engine) as s:
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise HTTPException(404, "Vehicle not found")

        rec = MaintRecord(
            record_no=_gen_code(s, MaintRecord, "M", 6),
            work_date=work_date,
            vehicle_id=vehicle_id,
            plate_raw=v.plate_no or "",
            mile_snapshot=mile,
            kind="tire_change",
            status="done",
            vendor_id=vendor_id,
            paid_by=paid_by,
            receipt_ref=receipt_ref,
            mechanic_name=mechanic_name,
        )
        s.add(rec)
        s.flush()  # get rec.id

        parts_total = 0.0
        changed = 0
        for i in range(row_count):
            pos = (form.get(f"pos_{i}") or "").strip().upper()
            if not pos:
                continue
            ttype = (form.get(f"type_{i}") or "new").strip()
            brand = (form.get(f"brand_{i}") or "").strip()
            model = (form.get(f"model_{i}") or "").strip()
            spec = (form.get(f"spec_{i}") or "").strip()
            serial = (form.get(f"serial_{i}") or "").strip()
            price = _parse_float(form.get(f"price_{i}") or "0")
            tread = _parse_float(form.get(f"tread_{i}") or "0")
            reason = (form.get(f"reason_{i}") or "").strip()

            # displaced old tyre at this position -> unmount it explicitly with
            # the reason, so the event trail (not just the Tire) records why.
            # (mount below would auto-unmount too, but that event has no reason.)
            for old in s.exec(select(Tire).where(
                Tire.current_vehicle_id == vehicle_id,
                Tire.current_position == pos,
            )).all():
                _apply_tire_event(
                    s, old, event_type="unmount", event_date=work_date,
                    mile=mile, reason_code=reason,
                    note=f"ถอดออก (คีย์บิล {rec.record_no})",
                )

            new_tire = Tire(
                code=_gen_code(s, Tire, "T", 4),
                brand=brand, model=model, spec=spec, serial_no=serial,
                purchase_date=work_date, purchase_price=price,
                purchase_vendor_id=vendor_id,
                tire_type=ttype, status="new",
                tread_depth_mm=tread,
            )
            s.add(new_tire)
            s.flush()

            _apply_tire_event(
                s, new_tire, event_type="mount", event_date=work_date,
                mile=mile, to_vehicle_id=vehicle_id, to_position=pos,
                tread_before=tread, tread_after=tread,
                reason_code=reason,
                note=f"คีย์บิล {rec.record_no}",
            )
            # link mount event to the record
            ev = s.exec(select(TireEvent).where(
                TireEvent.tire_id == new_tire.id
            ).order_by(TireEvent.id.desc())).first()
            if ev:
                ev.maint_record_id = rec.id
                s.add(ev)

            s.add(MaintPart(
                maint_record_id=rec.id, part_id=None,
                part_name_raw=f"ยาง {brand} {model} {spec}".strip(),
                qty=1, unit_price=price, total=price,
                tire_id=new_tire.id,
                note=dict(models.TIRE_REMOVAL_REASONS).get(reason, reason),
            ))
            parts_total += price
            changed += 1

        labor = _parse_float(form.get("labor_cost") or "0")
        other = _parse_float(form.get("other_cost") or "0")
        rec.parts_cost = parts_total
        rec.labor_cost = labor
        rec.other_cost = other
        rec.total_cost = parts_total + labor + other

        # keep vehicle odometer fresh when a reading was supplied
        if mile > 0 and mile > (v.current_mile or 0):
            v.current_mile = mile
            s.add(v)

        s.commit()

    return RedirectResponse(f"/maint/tires/by-vehicle/{vehicle_id}", status_code=303)


@app.get("/maint/tires/report", response_class=HTMLResponse)
def maint_tire_report(request: Request, month: str = ""):
    import services.tire_view as tv
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = [int(x) for x in month.split("-")]
        period_start, period_end = _month_bounds(y, m)
    except Exception:
        y, m = today.year, today.month
        period_start, period_end = _month_bounds(y, m)
    # previous month bounds for the delta card
    if m == 1:
        prev_start, prev_end = _month_bounds(y - 1, 12)
    else:
        prev_start, prev_end = _month_bounds(y, m - 1)

    with Session(engine) as s:
        recs = s.exec(
            select(MaintRecord).where(MaintRecord.kind == "tire_change")
        ).all()
        veh_map = {v.id: v for v in s.exec(select(Vehicle)).all()}

        def _in(rec, a, b):
            return a <= rec.work_date <= b

        month_recs = [r for r in recs if _in(r, period_start, period_end)]
        prev_recs = [r for r in recs if _in(r, prev_start, prev_end)]

        month_cost = sum(r.total_cost or 0 for r in month_recs)
        prev_cost = sum(r.total_cost or 0 for r in prev_recs)

        # tyres changed this month = MaintPart rows with tire_id on month records
        month_rec_ids = {r.id for r in month_recs}
        all_parts = s.exec(select(MaintPart).where(MaintPart.tire_id.isnot(None))).all()
        month_parts = [p for p in all_parts if p.maint_record_id in month_rec_ids]
        tyres_changed = len(month_parts)

        # per-vehicle spend this month
        per_vehicle: dict[int, dict] = {}
        for r in month_recs:
            pv = per_vehicle.setdefault(r.vehicle_id or 0, {
                "plate": (veh_map.get(r.vehicle_id).plate_no if veh_map.get(r.vehicle_id) else (r.plate_raw or "—")),
                "count": 0, "cost": 0.0,
            })
            pv["count"] += 1
            pv["cost"] += r.total_cost or 0
        per_vehicle_rows = sorted(per_vehicle.values(), key=lambda x: -x["cost"])

        # lifecycle + reason breakdown (all-time; the comparison needs history)
        life = tv.tire_lifecycle_report(s)

    delta = None
    if prev_cost > 0:
        delta = round((month_cost - prev_cost) / prev_cost * 100.0, 1)

    return templates.TemplateResponse(request, "tire_report.html", {
        "request": request,
        "month": month,
        "period_start": period_start,
        "period_end": period_end,
        "month_cost": month_cost,
        "prev_cost": prev_cost,
        "delta_pct": delta,
        "tyres_changed": tyres_changed,
        "avg_per_tyre": (month_cost / tyres_changed if tyres_changed else 0.0),
        "per_vehicle_rows": per_vehicle_rows,
        "by_type": life["by_type"],
        "by_reason": life["by_reason"],
        "retired_count": life["retired_count"],
    })


@app.get("/maint/tires/new", response_class=HTMLResponse)
def maint_tire_new_form(request: Request):
    with Session(engine) as s:
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
    return templates.TemplateResponse(request, "tire_form.html", {
        "request": request,
        "tire": None,
        "vendors": vendors,
        "status_options": models.TIRE_STATUS,
    })


@app.get("/maint/tires/by-vehicle/{vehicle_id}", response_class=HTMLResponse)
def maint_tire_by_vehicle(request: Request, vehicle_id: int):
    with Session(engine) as s:
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise HTTPException(404, "Vehicle not found")
        positions = _tire_positions_for_vehicle(v)
        tires = s.exec(select(Tire).where(Tire.current_vehicle_id == vehicle_id)).all()
        by_pos = {t.current_position: t for t in tires if t.current_position}
        other_tires = [t for t in tires if not t.current_position]

        # fetch events for these tires
        tire_ids = [t.id for t in tires] if tires else []
        events = []
        if tire_ids:
            events = s.exec(
                select(TireEvent).where(TireEvent.tire_id.in_(tire_ids)).order_by(TireEvent.event_date.desc(), TireEvent.id.desc()).limit(30)
            ).all()

        # list of spare tires (status=stored, new) for mount action
        spare_tires = s.exec(select(Tire).where(Tire.status.in_(["new", "stored"]))).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()

    return templates.TemplateResponse(request, "tire_by_vehicle.html", {
        "request": request,
        "vehicle": v,
        "positions": positions,
        "by_pos": by_pos,
        "other_tires": other_tires,
        "events": events,
        "spare_tires": spare_tires,
        "vehicles": vehicles,
        "today": date.today().isoformat(),
    })


@app.get("/maint/tires/{tire_id}", response_class=HTMLResponse)
def maint_tire_edit_form(request: Request, tire_id: int):
    with Session(engine) as s:
        tire = s.get(Tire, tire_id)
        if not tire:
            raise HTTPException(404, "Tire not found")
        vendors = s.exec(select(Vendor).order_by(Vendor.name)).all()
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        current_vehicle = s.get(Vehicle, tire.current_vehicle_id) if tire.current_vehicle_id else None
        events = s.exec(
            select(TireEvent).where(TireEvent.tire_id == tire_id).order_by(TireEvent.event_date.desc(), TireEvent.id.desc())
        ).all()
    return templates.TemplateResponse(request, "tire_form.html", {
        "request": request,
        "tire": tire,
        "vendors": vendors,
        "vehicles": vehicles,
        "current_vehicle": current_vehicle,
        "events": events,
        "status_options": models.TIRE_STATUS,
    })


def _apply_tire_form(t: Tire, form) -> None:
    t.brand       = (form.get("brand") or "").strip()
    t.model       = (form.get("model") or "").strip()
    t.spec        = (form.get("spec") or "").strip()
    t.serial_no   = (form.get("serial_no") or "").strip()
    t.purchase_date  = _parse_date(form.get("purchase_date") or "")
    t.purchase_price = _parse_float(form.get("purchase_price") or "0")
    vid = form.get("purchase_vendor_id") or ""
    t.purchase_vendor_id = int(vid) if vid.isdigit() else None
    t.status      = (form.get("status") or "new").strip()
    t.tread_depth_mm = _parse_float(form.get("tread_depth_mm") or "0")
    t.notes       = (form.get("notes") or "").strip()


@app.post("/maint/tires/new")
async def maint_tire_create(request: Request):
    form = await request.form()
    with Session(engine) as s:
        t = Tire(code=_gen_code(s, Tire, "T", 4))
        _apply_tire_form(t, form)
        s.add(t)
        s.commit()
        tid = t.id
    return RedirectResponse(f"/maint/tires/{tid}", status_code=303)


@app.post("/maint/tires/{tire_id}")
async def maint_tire_update(tire_id: int, request: Request):
    form = await request.form()
    with Session(engine) as s:
        t = s.get(Tire, tire_id)
        if not t:
            raise HTTPException(404, "Tire not found")
        _apply_tire_form(t, form)
        s.add(t)
        s.commit()
    return RedirectResponse(f"/maint/tires/{tire_id}", status_code=303)


@app.post("/maint/tires/{tire_id}/delete")
def maint_tire_delete(tire_id: int):
    with Session(engine) as s:
        t = s.get(Tire, tire_id)
        if t:
            # also delete events referencing this tire
            evs = s.exec(select(TireEvent).where(TireEvent.tire_id == tire_id)).all()
            for e in evs:
                s.delete(e)
            s.delete(t)
            s.commit()
    return RedirectResponse("/maint/tires", status_code=303)


def _apply_tire_event(s: Session, t: Tire, *, event_type: str, event_date: date,
                      mile: float, to_vehicle_id: Optional[int] = None,
                      to_position: str = "", tread_before: float = 0.0,
                      tread_after: float = 0.0, note: str = "",
                      actor_name: str = "", actor_role: str = "",
                      photo_paths: str = "", reason_code: str = "") -> TireEvent:
    """Create a TireEvent + mutate Tire state atomically (caller commits).

    Shared by the office route (/maint/tires/{id}/event) and the mechanic
    magic-link route (/check/mechanic/job). Behavior must stay identical.
    """
    ev = TireEvent(
        tire_id=t.id,
        event_date=event_date,
        event_type=event_type,
        from_vehicle_id=t.current_vehicle_id,
        from_position=t.current_position,
        mile=mile,
        tread_before_mm=tread_before or t.tread_depth_mm or 0.0,
        tread_after_mm=tread_after,
        note=note,
        actor_name=actor_name, actor_role=actor_role, photo_paths=photo_paths,
        reason_code=reason_code,
    )

    if event_type == "mount":
        if not to_vehicle_id or not to_position:
            raise HTTPException(400, "mount requires to_vehicle_id and to_position")
        # If another tire occupies this position on the target vehicle, auto-unmount it
        existing = s.exec(
            select(Tire).where(
                Tire.current_vehicle_id == to_vehicle_id,
                Tire.current_position == to_position,
            )
        ).all()
        for other in existing:
            if other.id != t.id:
                other.current_vehicle_id = None
                other.current_position = ""
                other.status = "stored"
                s.add(other)
                s.add(TireEvent(
                    tire_id=other.id,
                    event_date=event_date,
                    event_type="unmount",
                    from_vehicle_id=to_vehicle_id,
                    from_position=to_position,
                    mile=mile,
                    note=f"auto-unmount (displaced by T{t.id})",
                ))
        ev.to_vehicle_id = to_vehicle_id
        ev.to_position = to_position
        t.current_vehicle_id = to_vehicle_id
        t.current_position = to_position
        t.status = "in_use"
        t.mounted_at = event_date
        t.mounted_mile = mile

    elif event_type == "unmount":
        t.current_vehicle_id = None
        t.current_position = ""
        t.status = "stored"
        if reason_code:
            t.removal_reason = reason_code

    elif event_type == "rotate":
        # rotate = same vehicle, different position
        if not to_position:
            raise HTTPException(400, "rotate requires to_position")
        ev.to_vehicle_id = t.current_vehicle_id
        ev.to_position = to_position
        t.current_position = to_position

    elif event_type == "retread":
        t.retread_count = (t.retread_count or 0) + 1
        t.status = "retreaded"
        t.tread_depth_mm = tread_after or 16.0   # assume 16mm after retread if not given

    elif event_type == "scrap":
        t.current_vehicle_id = None
        t.current_position = ""
        t.status = "scrapped"
        if reason_code:
            t.removal_reason = reason_code

    elif event_type == "inspect":
        if tread_after:
            t.tread_depth_mm = tread_after

    if tread_after:
        t.tread_depth_mm = tread_after

    s.add(ev)
    s.add(t)
    return ev


@app.post("/maint/tires/{tire_id}/event")
async def maint_tire_event(tire_id: int, request: Request):
    """Mount / unmount / rotate / inspect / retread / scrap + update Tire state atomically."""
    form = await request.form()
    to_vid_s = form.get("to_vehicle_id") or ""
    with Session(engine) as s:
        t = s.get(Tire, tire_id)
        if not t:
            raise HTTPException(404, "Tire not found")
        _apply_tire_event(
            s, t,
            event_type=(form.get("event_type") or "").strip(),
            event_date=_parse_date(form.get("event_date") or "") or date.today(),
            mile=_parse_float(form.get("mile") or "0"),
            to_vehicle_id=(int(to_vid_s) if to_vid_s.isdigit() else None),
            to_position=(form.get("to_position") or "").strip().upper(),
            tread_before=_parse_float(form.get("tread_before_mm") or "0"),
            tread_after=_parse_float(form.get("tread_after_mm") or "0"),
            note=(form.get("note") or "").strip(),
        )
        s.commit()

    return RedirectResponse(f"/maint/tires/{tire_id}", status_code=303)


# ==========================================================================
# BILLING EXPORT  (Phase 2, P0-3)  —  minimal per site+month+customer export
# Detailed per-customer invoice templates come later (user deferred).
# ==========================================================================

def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


@app.get("/billing", response_class=HTMLResponse)
def billing_page(
    request: Request,
    site: str = "",
    month: str = "",    # YYYY-MM
    customer_id: str = "",
):
    from sqlalchemy import func as sa_func
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = [int(x) for x in month.split("-")]
        period_start, period_end = _month_bounds(y, m)
    except Exception:
        period_start, period_end = _month_bounds(today.year, today.month)

    cust_id_int = _parse_int(customer_id)

    with Session(engine) as s:
        stmt = (
            select(DailyJob)
            .where(
                DailyJob.work_date >= period_start,
                DailyJob.work_date <= period_end,
                DailyJob.revenue_customer > 0,
            )
            .order_by(DailyJob.work_date, DailyJob.id)
        )
        if site:
            stmt = stmt.where(DailyJob.site_code == site)
        if cust_id_int:
            stmt = stmt.where(DailyJob.customer_id == cust_id_int)

        jobs = s.exec(stmt).all()
        cust_map = {c.id: c for c in s.exec(select(Customer)).all()}
        emp_map = {e.id: e for e in s.exec(select(Employee)).all()}
        veh_map = {v.id: v for v in s.exec(select(Vehicle)).all()}

        # Sum LCB fees per job in one query
        fee_rows = s.exec(select(DailyJobFee)).all()
        fee_by_job: dict[int, float] = {}
        for f in fee_rows:
            fee_by_job[f.daily_job_id] = fee_by_job.get(f.daily_job_id, 0.0) + (f.amount or 0.0)

        # Group rows for UI summary: by customer (name or raw)
        groups: dict[str, dict] = {}
        for j in jobs:
            c = cust_map.get(j.customer_id) if j.customer_id else None
            cname = (c.name if c else (j.customer_name_raw or j.status_code or "(ไม่ระบุ)")).strip() or "(ไม่ระบุ)"
            g = groups.setdefault(cname, {
                "name": cname, "customer_id": (c.id if c else None),
                "count": 0, "revenue": 0.0, "fees": 0.0, "wht": 0.0,
                "rows": [],
            })
            extra = fee_by_job.get(j.id, 0.0)
            g["count"] += 1
            g["revenue"] += (j.revenue_customer or 0.0)
            g["fees"] += extra
            g["wht"] += (j.wht_53 or 0.0)

            if len(g["rows"]) < 40:  # keep UI light
                drv = emp_map.get(j.driver_id)
                head = veh_map.get(j.head_vehicle_id)
                g["rows"].append({
                    "id": j.id,
                    "work_date": j.work_date,
                    "doc_no": j.doc_no or j.invoice_no or "",
                    "plate": head.plate_no if head else j.plate_no_raw,
                    "driver": drv.full_name if drv else j.driver_raw_name,
                    "origin": j.origin, "destination": j.destination,
                    "container_no": j.container_no,
                    "trip_type": j.trip_type_code,
                    "revenue": j.revenue_customer, "extra_fee": extra,
                    "wht": j.wht_53,
                    "net": (j.revenue_customer or 0) + extra - (j.wht_53 or 0),
                })

        customers = sorted(cust_map.values(), key=lambda c: c.name or "")
        summary = {
            "count": sum(g["count"] for g in groups.values()),
            "revenue": sum(g["revenue"] for g in groups.values()),
            "fees": sum(g["fees"] for g in groups.values()),
            "wht": sum(g["wht"] for g in groups.values()),
        }

        # ---- C1: แถบ "พร้อมวางบิล?" — ตรวจจากแถวทั้งหมดในช่วง (ไม่ใช่แค่ revenue>0)
        # ต่อลูกค้า: ราคาว่าง / ไม่มีเลขใบงาน / ซ้ำ วัน+ทะเบียน+ตู้ (ตู้ไม่ว่างเท่านั้น
        # — รถเดิมวิ่งหลายเที่ยว/วันเป็นเรื่องปกติ); แถวรถจอด/ลา/ซ่อม ไม่ใช่งานวางบิล
        all_stmt = select(DailyJob).where(
            DailyJob.work_date >= period_start,
            DailyJob.work_date <= period_end,
        ).order_by(DailyJob.work_date, DailyJob.id)
        if site:
            all_stmt = all_stmt.where(DailyJob.site_code == site)
        if cust_id_int:
            all_stmt = all_stmt.where(DailyJob.customer_id == cust_id_int)
        ready_by_cust: dict[str, dict] = {}
        _dup_key_rows: dict[tuple, list] = {}
        # B3: เทียบราคาแถวที่ลงแล้วกับใบเสนอ agreed (ลูกค้า+ปลายทางตรง)
        agreed_quotes = _agreed_quotes(s)
        cust_names = {cid: c.name for cid, c in cust_map.items()}

        def _sample(j) -> dict:
            return {"work_date": j.work_date, "site": j.site_code,
                    "plate": (j.plate_no_raw or "").strip(),
                    "driver": j.driver_raw_name or "",
                    "dest": j.destination or "", "container": j.container_no or ""}

        for j in s.exec(all_stmt).all():
            if _daily_row_kind(j) != "job":
                continue
            has_cust = bool(j.customer_id or (j.customer_name_raw or "").strip()
                            or (j.status_code or "").strip())
            if not has_cust and not (j.destination or "").strip():
                continue  # แถวไม่มีทั้งลูกค้า/ปลายทาง (เช่น เติมน้ำมันอย่างเดียว)
            c = cust_map.get(j.customer_id) if j.customer_id else None
            cname = (c.name if c else (j.customer_name_raw or j.status_code or "(ไม่ระบุ)")).strip() or "(ไม่ระบุ)"
            rg = ready_by_cust.setdefault(cname, {
                "name": cname, "no_price": [], "no_doc": [], "dup": [],
                "price_diff": []})
            if (j.revenue_customer or 0) <= 0:
                rg["no_price"].append(_sample(j))
            elif agreed_quotes:
                mq = _quote_price_match(agreed_quotes, j, cust_names)
                if mq and abs((j.revenue_customer or 0) - mq.price_agreed) > 0.005:
                    rg["price_diff"].append(dict(
                        _sample(j), current=j.revenue_customer,
                        expected=mq.price_agreed, quote_id=mq.id))
            if not ((j.doc_no or "").strip() or (j.invoice_no or "").strip()
                    or (j.job_ref or "").strip() or (j.receive_inv_no or "").strip()):
                rg["no_doc"].append(_sample(j))
            if (j.container_no or "").strip():
                k = (j.work_date, (j.plate_no_raw or "").strip(), j.container_no.strip())
                _dup_key_rows.setdefault(k, []).append((cname, _sample(j)))
        for k, lst in _dup_key_rows.items():
            if len(lst) > 1:
                for cname, smp in lst:
                    ready_by_cust[cname]["dup"].append(smp)
        ready_issues = sorted(
            (g for g in ready_by_cust.values()
             if g["no_price"] or g["no_doc"] or g["dup"] or g["price_diff"]),
            key=lambda g: -(len(g["no_price"]) + len(g["no_doc"])
                            + len(g["dup"]) + len(g["price_diff"])))

    current_billing_month = f"{today.year:04d}-{today.month:02d}"
    ctx = base_context(request)
    ctx.update({
        "site": site, "month": month, "customer_id": customer_id,
        "period_start": period_start, "period_end": period_end,
        "groups": sorted(groups.values(), key=lambda g: -g["revenue"]),
        "customers": customers,
        "summary": summary,
        "current_billing_month": current_billing_month,
        "ready_issues": ready_issues,
    })
    return templates.TemplateResponse(request, "billing_page.html", ctx)


@app.get("/billing/export.csv")
def billing_export_csv(
    site: str = "",
    month: str = "",
    customer_id: str = "",
):
    """Download CSV. Includes: date, site, customer, doc_no, driver, plate,
    origin, destination, container, revenue, extra fees, WHT, net."""
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = [int(x) for x in month.split("-")]
        period_start, period_end = _month_bounds(y, m)
    except Exception:
        period_start, period_end = _month_bounds(today.year, today.month)

    cust_id_int = _parse_int(customer_id)

    with Session(engine) as s:
        stmt = (
            select(DailyJob)
            .where(
                DailyJob.work_date >= period_start,
                DailyJob.work_date <= period_end,
                DailyJob.revenue_customer > 0,
            )
            .order_by(DailyJob.site_code, DailyJob.work_date, DailyJob.id)
        )
        if site:
            stmt = stmt.where(DailyJob.site_code == site)
        if cust_id_int:
            stmt = stmt.where(DailyJob.customer_id == cust_id_int)
        jobs = s.exec(stmt).all()

        cust_map = {c.id: c for c in s.exec(select(Customer)).all()}
        emp_map = {e.id: e for e in s.exec(select(Employee)).all()}
        veh_map = {v.id: v for v in s.exec(select(Vehicle)).all()}
        fee_by_job: dict[int, float] = {}
        for f in s.exec(select(DailyJobFee)).all():
            fee_by_job[f.daily_job_id] = fee_by_job.get(f.daily_job_id, 0.0) + (f.amount or 0.0)

    import csv
    import io as _io
    buf = _io.StringIO()
    buf.write("\ufeff")  # BOM for Excel Thai
    w = csv.writer(buf)
    w.writerow([
        "วันที่", "ไซท์", "ลูกค้า", "เลขที่เอกสาร", "invoice_no",
        "คนขับ", "ทะเบียนหัว", "ทะเบียนหาง",
        "ต้นทาง", "ปลายทาง", "Loading/รับของ", "ตู้", "ขนาดตู้", "ประเภทเที่ยว",
        "ค่าขนส่ง", "ค่าใช้จ่ายอื่น (lift/yard/…)", "รวมก่อนหัก", "ภงด.53", "สุทธิ",
        "หมายเหตุ",
    ])
    for j in jobs:
        c = cust_map.get(j.customer_id) if j.customer_id else None
        drv = emp_map.get(j.driver_id) if j.driver_id else None
        head = veh_map.get(j.head_vehicle_id) if j.head_vehicle_id else None
        tail = veh_map.get(j.tail_vehicle_id) if j.tail_vehicle_id else None
        extra = fee_by_job.get(j.id, 0.0)
        rev = j.revenue_customer or 0.0
        wht = j.wht_53 or 0.0
        w.writerow([
            j.work_date.isoformat(), j.site_code,
            (c.name if c else j.customer_name_raw),
            j.doc_no, j.invoice_no,
            (drv.full_name if drv else j.driver_raw_name),
            (head.plate_no if head else j.plate_no_raw),
            (tail.plate_no if tail else j.tail_plate_raw),
            j.origin, j.destination, j.pickup_location,
            j.container_no, j.container_size, j.trip_type_code,
            f"{rev:.2f}", f"{extra:.2f}", f"{rev + extra:.2f}",
            f"{wht:.2f}", f"{rev + extra - wht:.2f}",
            (j.remark or "")[:200],
        ])
    filename = f"billing_{site or 'ALL'}_{month}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==========================================================================
# FINANCE / CFO DASHBOARD  (Phase 3)
# Debt schedule, P&L, Cost per Vehicle, Cash Flow, Break-even.
# ==========================================================================
from services import finance as finance_svc  # noqa: E402


def _cycle_period_for_tag(site: str, tag: str) -> Optional[tuple[date, date, str]]:
    """หา (start, end, tag) ของรอบจ่าย site ที่ tag ตรง (มองย้อน 24 รอบให้พอครอบ)."""
    for c in _site_payroll_cycles(site, date.today(), n=24):
        if c["tag"] == tag:
            return date.fromisoformat(c["start"]), date.fromisoformat(c["end"]), c["tag"]
    return None


@app.get("/finance", response_class=HTMLResponse)
def finance_dashboard(
    request: Request, month: str = "", site: str = "",
    include_other: str = "", mode: str = "calendar", view: str = "single",
):
    from sqlalchemy import func as sa_func
    today = date.today()
    # โหมดรอบจ่ายต้องมีไซต์ (รอบเป็นของแต่ละไซต์) — ไม่มีไซต์ → ถอยเป็นเดือนปฏิทิน
    cycle_mode = (mode == "cycle") and bool(site)

    # รายการรอบจ่ายของไซต์ (สำหรับ dropdown ในโหมดรอบจ่าย) + default = รอบล่าสุดที่มีข้อมูล
    site_cycles = _site_payroll_cycles(site, today, n=12) if site else []
    if cycle_mode:
        with Session(engine) as s:
            max_wd = s.exec(select(sa_func.max(DailyJob.work_date))).one()
        anchor = (max_wd or today).isoformat()
        if not any(c["tag"] == month for c in site_cycles):  # ยังไม่เลือกรอบ → default
            chosen = next((c for c in site_cycles if c["start"] <= anchor <= c["end"]), None)
            month = (chosen or (site_cycles[0] if site_cycles else None) or {"tag": ""}).get("tag", "")

    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = finance_svc.parse_month(month)
    except Exception:
        y, m = today.year, today.month
        month = f"{y:04d}-{m:02d}"

    include_other_flag = include_other in ("1", "true", "on")

    # --- มุมมองเทียบทุกไซท์ (compare) ---------------------------------------
    # anchor = เดือน (month). โหมด cycle: แต่ละไซท์ map รอบจ่ายของตัวที่จบในเดือนนั้น;
    # ถ้า map ไม่ได้ → ถอยเป็นเดือนปฏิทินสำหรับไซท์นั้น. โหมด calendar: ทุกไซท์ใช้เดือนเดียวกัน.
    if view == "compare":
        compare_cycle = (mode == "cycle")
        if not month:
            month = f"{today.year:04d}-{today.month:02d}"
        try:
            cy, cm = finance_svc.parse_month(month)
        except Exception:
            cy, cm = today.year, today.month
            month = f"{cy:04d}-{cm:02d}"

        SUM_FIELDS = ["trip_count", "revenue_transport", "revenue_fees", "kb_return",
                      "revenue_total",
                      "wht", "cost_fuel", "cost_fuel_liters", "cost_petty_net",
                      "cost_payroll", "cost_maint", "cost_interest", "cost_total"]
        rows = []
        with Session(engine) as s:
            for sc in ["AYU", "BIGC", "LCB"]:
                per = _cycle_period_for_tag(sc, month) if compare_cycle else None
                rows.append(finance_svc.monthly_pnl(
                    s, cy, cm, sc, include_other_petty=include_other_flag, period=per))
        totals = {f: sum((r.get(f) or 0.0) for r in rows) for f in SUM_FIELDS}
        totals["net_profit"] = totals["revenue_total"] - totals["cost_total"]
        totals["net_margin_pct"] = (
            totals["net_profit"] / totals["revenue_total"] * 100 if totals["revenue_total"] else 0)

        ctx = base_context(request)
        ctx.update({
            "view": "compare", "month": month, "mode": mode,
            "compare_cycle": compare_cycle,
            "include_other": include_other_flag,
            "rows": rows, "totals": totals,
        })
        return templates.TemplateResponse(request, "finance_dashboard.html", ctx)

    def _period_for(tag: str) -> Optional[tuple[date, date, str]]:
        return _cycle_period_for_tag(site, tag) if cycle_mode else None

    with Session(engine) as s:
        pnl = finance_svc.monthly_pnl(s, y, m, site, include_other_petty=include_other_flag,
                                      period=_period_for(month))
        loans_info = finance_svc.loan_summary(s)
        health = finance_svc.break_even_and_runway(s)
        # Top 15 ตามรายรับ (cost_per_vehicle เรียงกำไรแย่สุดก่อนตาม D3 — หน้านี้คงเดิม)
        veh_costs = sorted(finance_svc.cost_per_vehicle(s, y, m, site),
                           key=lambda r: -r["revenue"])[:15]

        prev_y, prev_m = (y, m - 1) if m > 1 else (y - 1, 12)
        prev_tag = f"{prev_y:04d}-{prev_m:02d}"
        prev_pnl = finance_svc.monthly_pnl(s, prev_y, prev_m, site, include_other_petty=include_other_flag,
                                           period=_period_for(prev_tag))

        trend = []
        cur_y, cur_m = y, m
        for _ in range(6):
            cur_tag = f"{cur_y:04d}-{cur_m:02d}"
            trend.append(finance_svc.monthly_pnl(s, cur_y, cur_m, site, include_other_petty=include_other_flag,
                                                 period=_period_for(cur_tag)))
            cur_m -= 1
            if cur_m == 0:
                cur_m = 12
                cur_y -= 1
        trend.reverse()

    ctx = base_context(request)
    ctx.update({
        "view": "single",
        "month": month, "site": site,
        "include_other": include_other_flag,
        "mode": "cycle" if cycle_mode else "calendar",
        "cycle_mode": cycle_mode,
        "site_cycles": site_cycles,
        "pnl": pnl, "prev_pnl": prev_pnl, "trend": trend,
        "loans_info": loans_info, "health": health,
        "vehicle_costs": veh_costs,
    })
    return templates.TemplateResponse(request, "finance_dashboard.html", ctx)


@app.get("/finance/loans", response_class=HTMLResponse)
def loans_list(request: Request, show: str = "active"):
    with Session(engine) as s:
        stmt = select(Loan).order_by(Loan.status, Loan.lender)
        if show == "active":
            stmt = stmt.where(Loan.status == "active")
        loans = s.exec(stmt).all()

        rows = []
        total_bal = 0.0
        total_monthly = 0.0
        for loan in loans:
            mp = loan.monthly_payment or finance_svc.compute_monthly_payment(
                loan.principal or 0.0, loan.annual_rate_pct or 0.0, loan.term_months or 0
            )
            if loan.loan_kind == "revolving" and loan.current_balance:
                mp = loan.monthly_payment or (loan.current_balance * (loan.annual_rate_pct / 100.0) / 12.0)
            rows.append({"loan": loan, "monthly": mp})
            if loan.status == "active":
                total_bal += loan.current_balance or 0.0
                total_monthly += mp

    ctx = base_context(request)
    ctx.update({
        "rows": rows, "show": show,
        "total_balance": total_bal, "total_monthly": total_monthly,
        "loan_kinds": models.LOAN_KINDS,
    })
    return templates.TemplateResponse(request, "loans_list.html", ctx)


@app.get("/finance/loans/new", response_class=HTMLResponse)
def loan_new(request: Request):
    ctx = base_context(request)
    with Session(engine) as s:
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
    ctx.update({
        "loan": None, "vehicles": vehicles,
        "loan_kinds": models.LOAN_KINDS, "loan_status_opts": models.LOAN_STATUS,
    })
    return templates.TemplateResponse(request, "loan_form.html", ctx)


@app.get("/finance/loans/{loan_id:int}", response_class=HTMLResponse)
def loan_edit(loan_id: int, request: Request):
    with Session(engine) as s:
        loan = s.get(Loan, loan_id)
        if not loan:
            raise HTTPException(404, "Loan not found")
        vehicles = s.exec(select(Vehicle).order_by(Vehicle.plate_no)).all()
        schedule = finance_svc.amortization_schedule(loan)
        payments = s.exec(
            select(LoanPayment).where(LoanPayment.loan_id == loan_id).order_by(LoanPayment.pay_date.desc())
        ).all()

    ctx = base_context(request)
    ctx.update({
        "loan": loan, "vehicles": vehicles, "schedule": schedule, "payments": payments,
        "loan_kinds": models.LOAN_KINDS, "loan_status_opts": models.LOAN_STATUS,
    })
    return templates.TemplateResponse(request, "loan_form.html", ctx)


@app.post("/finance/loans/new")
def loan_save_new(
    request: Request,
    lender: str = Form(""),
    loan_kind: str = Form("term"),
    purpose: str = Form(""),
    principal: str = Form("0"),
    annual_rate_pct: str = Form("0"),
    term_months: str = Form("0"),
    start_date: str = Form(""),
    first_payment_date: str = Form(""),
    pay_day_of_month: str = Form("5"),
    monthly_payment: str = Form("0"),
    current_balance: str = Form("0"),
    collateral: str = Form(""),
    linked_vehicle_id: str = Form(""),
    status: str = Form("active"),
    notes: str = Form(""),
):
    return _loan_save_impl(
        None, lender, loan_kind, purpose, principal, annual_rate_pct,
        term_months, start_date, first_payment_date, pay_day_of_month,
        monthly_payment, current_balance, collateral, linked_vehicle_id,
        status, notes,
    )


@app.post("/finance/loans/{loan_id:int}")
def loan_save_existing(
    loan_id: int,
    request: Request,
    lender: str = Form(""),
    loan_kind: str = Form("term"),
    purpose: str = Form(""),
    principal: str = Form("0"),
    annual_rate_pct: str = Form("0"),
    term_months: str = Form("0"),
    start_date: str = Form(""),
    first_payment_date: str = Form(""),
    pay_day_of_month: str = Form("5"),
    monthly_payment: str = Form("0"),
    current_balance: str = Form("0"),
    collateral: str = Form(""),
    linked_vehicle_id: str = Form(""),
    status: str = Form("active"),
    notes: str = Form(""),
):
    return _loan_save_impl(
        loan_id, lender, loan_kind, purpose, principal, annual_rate_pct,
        term_months, start_date, first_payment_date, pay_day_of_month,
        monthly_payment, current_balance, collateral, linked_vehicle_id,
        status, notes,
    )


def _loan_save_impl(
    loan_id: Optional[int],
    lender: str, loan_kind: str, purpose: str,
    principal: str, annual_rate_pct: str, term_months: str,
    start_date: str, first_payment_date: str, pay_day_of_month: str,
    monthly_payment: str, current_balance: str, collateral: str,
    linked_vehicle_id: str, status: str, notes: str,
):
    if not lender.strip():
        raise HTTPException(400, "ต้องกรอกชื่อเจ้าหนี้")

    with Session(engine) as s:
        if loan_id is None:
            loan = Loan(code=_gen_code(s, Loan, "L", 4), lender=lender.strip())
        else:
            loan = s.get(Loan, loan_id)
            if not loan:
                raise HTTPException(404, "Loan not found")

        loan.lender = lender.strip()
        loan.loan_kind = loan_kind
        loan.purpose = purpose.strip()
        loan.principal = _parse_float(principal)
        loan.annual_rate_pct = _parse_float(annual_rate_pct)
        loan.term_months = int(_parse_float(term_months))
        loan.start_date = _parse_date(start_date)
        loan.first_payment_date = _parse_date(first_payment_date) or loan.start_date
        loan.pay_day_of_month = max(1, min(28, int(_parse_float(pay_day_of_month) or 5)))
        loan.monthly_payment = _parse_float(monthly_payment)
        loan.current_balance = _parse_float(current_balance) or loan.principal
        loan.collateral = collateral.strip()
        loan.linked_vehicle_id = _parse_int(linked_vehicle_id)
        loan.status = status
        loan.notes = notes.strip()
        loan.updated_at = datetime.utcnow()

        if loan.start_date and loan.term_months > 0:
            loan.end_date = finance_svc.add_months(loan.start_date, loan.term_months)

        s.add(loan)
        s.commit()
        new_id = loan.id

    return RedirectResponse(f"/finance/loans/{new_id}", status_code=303)


@app.post("/finance/loans/{loan_id:int}/delete")
def loan_delete(loan_id: int):
    with Session(engine) as s:
        loan = s.get(Loan, loan_id)
        if loan:
            s.exec(select(LoanPayment).where(LoanPayment.loan_id == loan_id)).all()
            for lp in s.exec(select(LoanPayment).where(LoanPayment.loan_id == loan_id)).all():
                s.delete(lp)
            s.delete(loan)
            s.commit()
    return RedirectResponse("/finance/loans", status_code=303)


@app.post("/finance/loans/{loan_id:int}/payment")
def loan_payment_add(
    loan_id: int,
    pay_date: str = Form(""),
    amount: str = Form("0"),
    interest_portion: str = Form("0"),
    notes: str = Form(""),
):
    with Session(engine) as s:
        loan = s.get(Loan, loan_id)
        if not loan:
            raise HTTPException(404, "Loan not found")
        pay_amount = _parse_float(amount)
        interest = _parse_float(interest_portion)
        principal_paid = max(0.0, pay_amount - interest)
        lp = LoanPayment(
            loan_id=loan_id,
            pay_date=_parse_date(pay_date) or date.today(),
            amount=pay_amount,
            principal_portion=principal_paid,
            interest_portion=interest,
            notes=notes.strip(),
        )
        s.add(lp)
        # Reduce current_balance
        loan.current_balance = max(0.0, (loan.current_balance or 0.0) - principal_paid)
        if loan.current_balance < 0.01:
            loan.status = "paid_off"
        loan.updated_at = datetime.utcnow()
        s.add(loan)
        s.commit()
    return RedirectResponse(f"/finance/loans/{loan_id}", status_code=303)


@app.post("/finance/loans/{loan_id:int}/payment/{payment_id:int}/delete")
def loan_payment_delete(loan_id: int, payment_id: int):
    with Session(engine) as s:
        lp = s.get(LoanPayment, payment_id)
        if lp and lp.loan_id == loan_id:
            # Restore balance
            loan = s.get(Loan, loan_id)
            if loan:
                loan.current_balance = (loan.current_balance or 0.0) + (lp.principal_portion or 0.0)
                loan.updated_at = datetime.utcnow()
                s.add(loan)
            s.delete(lp)
            s.commit()
    return RedirectResponse(f"/finance/loans/{loan_id}", status_code=303)


@app.get("/finance/pnl", response_class=HTMLResponse)
def finance_pnl_detail(request: Request, year: int = 0, site: str = ""):
    if year <= 0:
        year = date.today().year
    with Session(engine) as s:
        months = finance_svc.yearly_rollup(s, year, site)
    totals = {
        "kb_return": sum(m.get("kb_return", 0.0) for m in months),
        "revenue_total": sum(m["revenue_total"] for m in months),
        "cost_fuel": sum(m["cost_fuel"] for m in months),
        "cost_petty_net": sum(m["cost_petty_net"] for m in months),
        "cost_payroll": sum(m["cost_payroll"] for m in months),
        "cost_maint": sum(m["cost_maint"] for m in months),
        "cost_interest": sum(m["cost_interest"] for m in months),
        "cost_total": sum(m["cost_total"] for m in months),
        "net_profit": sum(m["net_profit"] for m in months),
        "trip_count": sum(m["trip_count"] for m in months),
    }
    ctx = base_context(request)
    ctx.update({"year": year, "site": site, "months": months, "totals": totals})
    return templates.TemplateResponse(request, "finance_pnl.html", ctx)


@app.get("/finance/receivables", response_class=HTMLResponse)
def finance_receivables(request: Request):
    """รอรับเงินลูกค้า (AR) — อ่านทะเบียน "รายการรับเช็ค AYU/LCB" จาก Drive.

    ทีมบัญชียังกรอก Excel แบบเดิม; ระบบอ่านสีไฮไลท์ (มีสี=รับแล้ว) → ค้างรับ/
    เลยกำหนด/ครบใน 7 วัน. read-only. สิทธิ์ตามเมนู finance (admin/accountant).
    """
    from services import receivables as ar

    ctx = base_context(request)
    error = None
    rows: list = []
    missing: list = []
    try:
        rows, missing = ar.load_all()
    except Exception as e:
        error = f"อ่านไฟล์จาก Google Drive ไม่สำเร็จ: {e}"
    # ติ๊กรับเงิน "ในระบบ" (ArSettle — โอ 3ก.ค.: ไม่แตะ Excel): received = สีในชีท OR ติ๊ก
    with Session(engine) as s:
        settled = {a.inv_key: a for a in s.exec(select(ArSettle)).all()}
    sys_settled = []
    for r in rows:
        key = f"{r['site']}:{r['inv']}" if r["inv"] else ""
        r["inv_key"] = key
        if key and key in settled and not r["received"]:
            r["received"] = True
            r["fill"] = "system"
            r["settle_info"] = settled[key]
            sys_settled.append(r)
    sys_settled.sort(key=lambda r: r["settle_info"].settled_on, reverse=True)
    ctx.update({
        "summary": ar.summarize(rows) if rows else None,
        "missing": missing, "error": error,
        "sa_email": ar.service_account_email(),
        "sys_settled": sys_settled[:40],
        "today": date.today(),
    })
    return templates.TemplateResponse(request, "finance_receivables.html", ctx)


@app.post("/finance/receivables/settle")
def finance_receivables_settle(request: Request, inv_key: str = Form(...), undo: str = Form("")):
    """ติ๊ก/ยกเลิกติ๊ก รับเงินแล้ว — เก็บในระบบเท่านั้น ไม่เขียนกลับชีท."""
    from auth import current_user

    if _part_level_of(request, "ar.settle") != "edit":
        raise HTTPException(403, "ไม่มีสิทธิ์ติ๊กรับเงิน (ดู /admin/permissions)")
    user = current_user(request)
    key = inv_key.strip()
    if not key or ":" not in key:
        return RedirectResponse("/finance/receivables", status_code=303)
    with Session(engine) as s:
        existing = s.exec(select(ArSettle).where(ArSettle.inv_key == key)).first()
        if undo == "1":
            if existing:
                audit_log(s, request, "arsettle", existing.id or 0, "received",
                          "1", "0", note=key)
                s.delete(existing)
        elif not existing:
            audit_log(s, request, "arsettle", 0, "received", "0", "1", note=key)
            s.add(ArSettle(inv_key=key, by_user=user.username if user else ""))
        s.commit()
    return RedirectResponse("/finance/receivables", status_code=303)


# 🔍 ค้นหากลาง — พิมพ์ตู้/ทะเบียน/คนขับ/เลขใบ ที่ช่องเดียว เจอทุกแหล่งที่มีสิทธิ์เห็น
# =========================================================================


@app.get("/search", response_class=HTMLResponse)
def global_search(request: Request, q: str = ""):
    needle = q.strip()
    u = current_user(request)
    role = u.role if u else ""

    def allowed(path: str) -> bool:
        return perm_check(role, path, "GET") != "deny"

    sections: list[dict] = []
    if len(needle) >= 2:
        like = f"%{needle}%"
        with Session(engine) as s:
            # เดลี่ — สนามที่คนตามหาบ่อยสุด (ตู้/ทะเบียน/เลขใบ/BL/คนขับ)
            if allowed("/daily"):
                jobs = s.exec(select(DailyJob).where(or_(
                    DailyJob.container_no.like(like),      # type: ignore[attr-defined]
                    DailyJob.plate_no_raw.like(like),      # type: ignore[attr-defined]
                    DailyJob.doc_no.like(like),            # type: ignore[attr-defined]
                    DailyJob.job_ref.like(like),           # type: ignore[attr-defined]
                    DailyJob.invoice_no.like(like),        # type: ignore[attr-defined]
                    DailyJob.bl_booking.like(like),        # type: ignore[attr-defined]
                    DailyJob.driver_raw_name.like(like),   # type: ignore[attr-defined]
                    DailyJob.status_code.like(like),       # type: ignore[attr-defined]
                )).order_by(DailyJob.work_date.desc()).limit(40)).all()  # type: ignore[union-attr,arg-type]
                if jobs:
                    sections.append({"title": "🚚 เดลี่ (งานรายวัน)", "items": [{
                        "label": f"{j.work_date:%d/%m/%y} · {j.site_code} · {j.status_code or j.customer_name_raw}"
                                 f" · {j.plate_no_raw} · ตู้ {j.container_no or '—'}"
                                 f"{' · ใบ ' + j.invoice_no if j.invoice_no else ''}",
                        "href": f"/daily?site={j.site_code}&d_from={j.work_date.isoformat()}"
                                f"&d_to={j.work_date.isoformat()}&q={needle}",
                    } for j in jobs]})
            if allowed("/employees"):
                emps = [e for e in s.exec(select(Employee)).all()
                        if needle.lower() in f"{e.full_name} {e.nickname or ''} {e.code} {e.phone or ''}".lower()][:15]
                if emps:
                    sections.append({"title": "👤 พนักงาน", "items": [{
                        "label": f"{e.full_name} ({e.nickname or e.code}) · {e.home_site_code}"
                                 f" · {e.status}",
                        "href": f"/employees?q={e.full_name}"} for e in emps]})
                vehs = [v for v in s.exec(select(Vehicle)).all()
                        if needle.lower() in f"{v.plate_no} {v.nickname or ''} {v.old_plate_no or ''}".lower()][:15]
                if vehs:
                    sections.append({"title": "🚛 รถ", "items": [{
                        "label": f"{v.plate_no} ({v.nickname or v.truck_type}) · {v.home_site_code} · {v.status}",
                        "href": "/vehicles"} for v in vehs]})
            if allowed("/customers"):
                custs = [c for c in s.exec(select(Customer)).all()
                         if needle.lower() in f"{c.name} {c.code}".lower()][:10]
                if custs:
                    sections.append({"title": "🏢 ลูกค้า", "items": [{
                        "label": f"{c.name} ({c.code})", "href": "/customers"} for c in custs]})
            if allowed("/fuel"):
                fuels = s.exec(select(FuelTxn).where(or_(
                    FuelTxn.plate_no_raw.like(like),       # type: ignore[attr-defined]
                    FuelTxn.driver_raw_name.like(like),    # type: ignore[attr-defined]
                    FuelTxn.station.like(like),            # type: ignore[attr-defined]
                )).order_by(FuelTxn.txn_date.desc()).limit(15)).all()  # type: ignore[union-attr,arg-type]
                if fuels:
                    sections.append({"title": "⛽ น้ำมัน", "items": [{
                        "label": f"{f.txn_date:%d/%m/%y} · {f.plate_no_raw} · {f.liter:,.0f} ลิตร"
                                 f" · {f.amount:,.0f} บาท · {f.station}",
                        "href": f"/fuel?plate={f.plate_no_raw}"} for f in fuels]})
            if allowed("/quote"):
                quotes = [x for x in s.exec(select(Quotation)).all()
                          if needle.lower() in f"{x.customer_name} {x.factory_name} {x.tags} {x.note}".lower()][:10]
                if quotes:
                    sections.append({"title": "📄 ใบเสนอราคา", "items": [{
                        "label": f"{x.customer_name} · {x.factory_name} · {x.price_offered:,.0f}"
                                 f" · {_QUOTE_STATUS_TH.get(x.status, x.status)}",
                        "href": f"/quote/{x.id}"} for x in quotes]})
        # คลังแชทไลน์ (นอก session DB หลัก — read-only + กันพังถ้าเครื่องไม่มีไฟล์)
        if allowed("/line"):
            try:
                from services import line_archive as la
                if la.db_path() is not None:
                    hits = la.search(needle, limit=8)
                    if hits:
                        sections.append({"title": "💬 แชทไลน์", "items": [{
                            "label": f"{h['group_name']} · {h['who'] or ''} · "
                                     f"{str(h['sent_at'])[:16]} · {(h['text'] or '['+h['msg_type']+']')[:80]}",
                            "href": f"/line?q={needle}"} for h in hits]})
            except Exception:
                pass

    ctx = base_context(request)
    ctx.update({"q": needle, "sections": sections,
                "n_total": sum(len(x["items"]) for x in sections)})
    return templates.TemplateResponse(request, "search_results.html", ctx)


# =========================================================================
# D1: เติมราคาเร็ว — แถวงานราคาว่าง + เรทที่ระบบจำ (RateCard) → คนกดรับต่อแถว
# pattern เดียว B3 apply-quote: server ตรวจซ้ำเอง, เฉพาะแถวราคาว่าง, audit ทุกครั้ง
# =========================================================================


def _rate_ctx_from_daily(s: Session, j: DailyJob) -> dict:
    vk = ""
    if j.head_vehicle_id:
        v = s.get(Vehicle, j.head_vehicle_id)
        if v:
            vk = (v.truck_type or "").strip()
    return {
        "site_code": j.site_code or "*",
        "customer_id": j.customer_id,
        "vehicle_kind": vk or (j.truck_type_raw or "").strip() or "*",
        "trip_type_code": j.trip_type_code or "*",
        "origin": j.origin or "*",
        "destination": j.destination or "*",
        "pickup_location": j.pickup_location or "*",
        "work_date": j.work_date,
    }


@app.get("/billing/fill-prices", response_class=HTMLResponse)
def billing_fill_prices(request: Request, site: str = "", month: str = ""):
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = [int(x) for x in month.split("-")]
        d1, d2 = _month_bounds(y, m)
    except ValueError:
        y, m = today.year, today.month
        d1, d2 = _month_bounds(y, m)
        month = f"{y:04d}-{m:02d}"
    with Session(engine) as s:
        stmt = select(DailyJob).where(
            DailyJob.work_date >= d1, DailyJob.work_date <= d2)
        if site:
            stmt = stmt.where(DailyJob.site_code == site)
        jobs = [j for j in s.exec(stmt.order_by(DailyJob.work_date, DailyJob.id)).all()
                if _daily_row_kind(j) == "job" and not (j.revenue_customer or 0)]
        rows = []
        for j in jobs:
            card = rate_find(s, "revenue_customer", _rate_ctx_from_daily(s, j))
            rows.append({"j": j, "card": card})
    n_suggest = sum(1 for r in rows if r["card"])
    ctx = base_context(request)
    ctx.update({"rows": rows, "site": site, "month": month, "n_suggest": n_suggest})
    return templates.TemplateResponse(request, "billing_fill_prices.html", ctx)


@app.post("/api/billing/fill-price")
async def api_billing_fill_price(request: Request):
    """กดรับเรทที่ระบบจำ 1 แถว — server หาเรทซ้ำเอง ไม่เชื่อค่าจากหน้าเว็บ."""
    body = await request.json()
    try:
        job_id = int(body.get("job_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "job_id ไม่ถูกต้อง")
    u = current_user(request)
    with Session(engine) as s:
        j = s.get(DailyJob, job_id)
        if not j:
            raise HTTPException(404)
        if (j.revenue_customer or 0) > 0:
            raise HTTPException(409, "แถวนี้มีราคาแล้ว — ระบบไม่ทับราคาเดิม")
        card = rate_find(s, "revenue_customer", _rate_ctx_from_daily(s, j))
        if card is None:
            raise HTTPException(409, "ไม่มีเรทที่ระบบจำสำหรับแถวนี้แล้ว")
        j.revenue_customer = float(card.rate_value)
        j.updated_at = datetime.utcnow()
        card.use_count += 1
        card.last_used_at = datetime.utcnow()
        card.last_seen_job_id = j.id
        s.add(models.DailyJobAudit(
            daily_job_id=j.id, changed_by=(u.username if u else ""),
            action="rate_apply", field_name="revenue_customer",
            old_value="0", new_value=str(j.revenue_customer)))
        s.add(j)
        s.add(card)
        s.commit()
        return {"ok": True, "value": j.revenue_customer}


@app.post("/api/billing/fill-price-bulk")
async def api_billing_fill_price_bulk(request: Request):
    """รับเรทที่ระบบจำ "ทั้งชุดตามหน้าที่เห็น" (site+month) — ตัด 700 คลิกเหลือคลิกเดียว.

    server ไล่หาแถวเอง (ไม่เชื่อ list จากหน้าเว็บ): เฉพาะแถวงานราคาว่าง + มีเรทจำ ณ ตอนกด;
    ไม่ทับราคาเดิม; audit ต่อแถว (action=rate_apply_bulk) ย้อนดู/ย้อนแก้ได้เหมือนกดทีละแถว.
    """
    body = await request.json()
    site = (body.get("site") or "").strip()
    month = (body.get("month") or "").strip()
    try:
        y, m = [int(x) for x in month.split("-")]
        d1, d2 = _month_bounds(y, m)
    except (ValueError, AttributeError):
        raise HTTPException(400, "month ไม่ถูกต้อง (YYYY-MM)")
    u = current_user(request)
    applied, skipped = 0, 0
    with Session(engine) as s:
        stmt = select(DailyJob).where(
            DailyJob.work_date >= d1, DailyJob.work_date <= d2)
        if site:
            stmt = stmt.where(DailyJob.site_code == site)
        jobs = [j for j in s.exec(stmt.order_by(DailyJob.work_date, DailyJob.id)).all()
                if _daily_row_kind(j) == "job" and not (j.revenue_customer or 0)]
        for j in jobs:
            card = rate_find(s, "revenue_customer", _rate_ctx_from_daily(s, j))
            if card is None:
                skipped += 1
                continue
            j.revenue_customer = float(card.rate_value)
            j.updated_at = datetime.utcnow()
            card.use_count += 1
            card.last_used_at = datetime.utcnow()
            card.last_seen_job_id = j.id
            s.add(models.DailyJobAudit(
                daily_job_id=j.id, changed_by=(u.username if u else ""),
                action="rate_apply_bulk", field_name="revenue_customer",
                old_value="0", new_value=str(j.revenue_customer)))
            s.add(j)
            s.add(card)
            applied += 1
        s.commit()
    return {"ok": True, "applied": applied, "no_rate": skipped}


# =========================================================================
# C2: ออกใบวางบิลจากระบบ /billing/invoice — เติมฟอร์ม xlsx จาก template ไฟล์จริง
# (สำเนาใบจริงใน app/invoice_templates/) แถวตู้จากเดลี่; ช่องที่ DB ไม่มี
# (ค่าทดรองจ่าย/ป้ายลูกค้า) แก้ในฟอร์มก่อนสร้าง; **ไม่เขียน DB** — คีย์เลขใบ
# ในกริดเหมือนเดิม; ตรวจย้อนกลับ: tools/verify_invoice_builder.py
# =========================================================================


@app.get("/billing/invoice", response_class=HTMLResponse)
def invoice_builder_page(request: Request, series: str = "", month: str = ""):
    from services import invoice_builder as ib

    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = [int(x) for x in month.split("-")]
        d1, d2 = _month_bounds(y, m)
    except ValueError:
        y, m = today.year, today.month
        d1, d2 = _month_bounds(y, m)
        month = f"{y:04d}-{m:02d}"

    billed_groups, unbilled, next_no, cfg = [], [], "", None
    if series in ib.REGISTRY:
        cfg = ib.REGISTRY[series]
        with Session(engine) as s:
            billed, unbilled_jobs = ib.daily_rows_for_series(s, cfg, d1, d2)
            next_no = ib.next_invoice_no(s, cfg, f"{y % 100:02d}{m:02d}")
        billed_groups = [
            {"inv": inv, "n": len(js),
             "total": sum(j.revenue_customer for j in js),
             "d1": min(j.work_date for j in js).strftime("%d/%m"),
             "d2": max(j.work_date for j in js).strftime("%d/%m"),
             "rows": [ib.job_to_row(j, cfg) for j in js]}
            for inv, js in sorted(billed.items())
        ]
        unbilled = [ib.job_to_row(j, cfg) for j in unbilled_jobs]
    ctx = base_context(request)
    ctx.update({
        "series": series, "month": month, "cfg": cfg,
        "registry": ib.REGISTRY, "next_no": next_no,
        "billed_groups": billed_groups, "unbilled": unbilled,
        "ui_charges": cfg.ui_charges() if cfg else [],
        "has_plate": bool(cfg and "plate" in cfg.cols),
        "has_cust": bool(cfg and "cust" in cfg.cols),
        "billed_json": json.dumps(billed_groups, ensure_ascii=False, default=str),
        "unbilled_json": json.dumps(unbilled, ensure_ascii=False, default=str),
    })
    return templates.TemplateResponse(request, "invoice_builder.html", ctx)


@app.post("/billing/invoice/build")
def invoice_builder_build(request: Request,
                          series: str = Form(...), inv_no: str = Form(...),
                          inv_date: str = Form(...), rows_json: str = Form(...)):
    from services import invoice_builder as ib

    cfg = ib.REGISTRY.get(series)
    if cfg is None:
        raise HTTPException(400, "ไม่รู้จักชุดใบวางบิลนี้")
    inv_no = inv_no.strip()
    if not ib.parse_invoice_no(inv_no):
        raise HTTPException(400, f"เลขใบไม่เข้ารูปแบบ {cfg.prefix}YYMM-###")
    try:
        d = datetime.strptime(inv_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "วันที่ใบไม่ถูกต้อง")
    try:
        raw_rows = json.loads(rows_json)
        assert isinstance(raw_rows, list)
    except (ValueError, AssertionError):
        raise HTTPException(400, "rows_json ไม่ใช่ JSON list")
    money_keys = ["price", "advance"] + [c["key"] for c in cfg.charges]
    rows = []
    for r in raw_rows:
        rd = None
        try:
            rd = datetime.strptime(str(r.get("date") or "")[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
        row = {k: str(r.get(k) or "") for k in
               ("route", "cntr", "size", "plate", "cust", "job")}
        row["date"] = rd
        for k in money_keys:
            row[k] = float(r.get(k) or 0)
        rows.append(row)
    try:
        data = ib.build_invoice(cfg, inv_no, d, rows)
    except ValueError as e:
        raise HTTPException(400, str(e))
    cust = (rows[0].get("cust") or "").strip() if rows else ""
    fname = f"{inv_no}{(' ' + cust) if cust else ''}.xlsx"
    from urllib.parse import quote as _urlquote
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":
                 f"attachment; filename*=UTF-8''{_urlquote(fname)}"})


# P3: เมนูคลิกขวาทั้งระบบ — registry ฝั่ง server (กรองสิทธิ์ต่อ item ด้วย perm path)
# client: static/ctxmenu.js (data-ctx บน element หรือ YKCtx.open จากโค้ด เช่น Tabulator)
# กติกา: ห้ามใส่ action เงินตรงในเมนู — เมนูเปิดหน้า/ฟอร์มที่มีของเดิมเท่านั้น
# =========================================================================

CTX_MENUS: dict = {
    "daily-cell": [
        {"label": "📜 ประวัติช่องนี้", "kind": "call", "fn": "ykCtxDailyAuditField"},
        {"label": "📜 ประวัติทั้งแถว", "kind": "call", "fn": "ykCtxDailyAudit"},
        {"label": "📷 ดูรูปงานนี้", "kind": "call", "fn": "ykCtxJobMedia"},
        {"label": "📋 คัดลอกค่าในช่อง", "kind": "copy", "key": "value"},
        {"label": "📋 คัดลอกเบอร์ตู้", "kind": "copy", "key": "container"},
        {"label": "💬 หาตู้นี้ในแชทไลน์", "kind": "link",
         "href": "/line?q={container}", "perm": "/line"},
        {"label": "💡 ใบเสนอราคาลูกค้านี้", "kind": "link",
         "href": "/quote/list?q={customer}", "perm": "/quote"},
    ],
    "transfer-row": [
        {"label": "📋 คัดลอกเลขบัญชี", "kind": "copy", "key": "account"},
        {"label": "📋 คัดลอกชื่อ", "kind": "copy", "key": "name"},
        {"label": "👤 เปิดหน้าพนักงาน", "kind": "link",
         "href": "/employees?q={name}", "perm": "/employees"},
        {"label": "📜 ประวัติแก้บัญชีคนนี้", "kind": "link",
         "href": "/admin/audit?table=employee&q={name}&days=90", "perm": "/admin/users"},
    ],
    "ar-row": [
        {"label": "📋 คัดลอกเลข INV", "kind": "copy", "key": "inv"},
        {"label": "📋 คัดลอกยอดสุทธิ", "kind": "copy", "key": "net"},
        {"label": "💬 หาลูกค้านี้ในแชทไลน์", "kind": "link",
         "href": "/line?q={customer}", "perm": "/line"},
    ],
}


@app.get("/api/ctxmenu/{menu_type}")
def ctxmenu_items(menu_type: str, request: Request):
    items = CTX_MENUS.get(menu_type)
    if items is None:
        raise HTTPException(404, "ไม่รู้จักชนิดเมนูนี้")
    u = current_user(request)
    role = u.role if u else ""
    out = [{k: v for k, v in it.items() if k != "perm"} for it in items
           if not it.get("perm") or perm_check(role, it["perm"], "GET") != "deny"]
    return {"items": out}


# P1: หน้า /admin/permissions — โอปรับสิทธิ์รายชิ้นส่วน (role × part) สด
# =========================================================================


@app.get("/admin/permissions", response_class=HTMLResponse)
def admin_permissions(request: Request):
    import parts as _parts
    from permissions import ROLES

    with Session(engine) as s:
        db_rows = s.exec(select(models.PartPermission)).all()
        users = s.exec(select(AppUser).order_by(AppUser.username)).all()  # type: ignore[arg-type]
    role_over = {(r.part_key, r.role): r.level for r in db_rows if not r.username}
    user_over = [r for r in db_rows if r.username]
    matrix = []
    for key, spec in _parts.PART_DEFAULTS.items():
        row = {"key": key, "label": spec["label"], "cells": []}
        for role in ROLES:
            default = spec["roles"].get(role, "hide")
            row["cells"].append({
                "role": role,
                "level": role_over.get((key, role), default),
                "default": default,
                "overridden": (key, role) in role_over,
            })
        matrix.append(row)
    ctx = base_context(request)
    ctx.update({"matrix": matrix, "roles": ROLES, "user_over": user_over,
                "usernames": [u.username for u in users],
                "part_keys": list(_parts.PART_DEFAULTS)})
    return templates.TemplateResponse(request, "admin_permissions.html", ctx)


@app.post("/admin/permissions/save")
def admin_permissions_save(request: Request, part_key: str = Form(...),
                           role: str = Form(""), username: str = Form(""),
                           level: str = Form(...)):
    """ตั้งสิทธิ์ 1 ช่อง (role หรือ override รายคน); level='default' = ลบแถวกลับ default."""
    import parts as _parts
    from permissions import ROLES

    if part_key not in _parts.PART_DEFAULTS:
        raise HTTPException(400, "ไม่รู้จัก part นี้")
    if level not in _parts.LEVELS + ("default",):
        raise HTTPException(400, "ระดับไม่ถูกต้อง")
    if not username and role not in ROLES:
        raise HTTPException(400, "ต้องระบุ role หรือ username")
    with Session(engine) as s:
        q = select(models.PartPermission).where(
            models.PartPermission.part_key == part_key,
            models.PartPermission.role == (("" if username else role)),
            models.PartPermission.username == username.strip())
        row = s.exec(q).first()
        old = row.level if row else "(default)"
        if level == "default":
            if row:
                s.delete(row)
        elif row:
            row.level = level
            row.updated_at = datetime.utcnow()
            s.add(row)
        else:
            s.add(models.PartPermission(
                part_key=part_key, role="" if username else role,
                username=username.strip(), level=level))
        audit_log(s, request, "partpermission", 0, part_key, old, level,
                  note=username.strip() or role)
        s.commit()
    _parts.invalidate_cache()
    return RedirectResponse("/admin/permissions", status_code=303)


# =========================================================================
# P2: หน้า /admin/audit — รวมประวัติจากทุกตาราง audit (AuditLog กลาง + ตารางเฉพาะ)
# =========================================================================

_AUDIT_TABLE_TH = {
    "daily": "เดลี่", "deposit": "เงินประกันตน", "dispatch": "แผนจัดรถ",
    "quotation": "ใบเสนอราคา", "employee": "พนักงาน (บัญชี/ธนาคาร)",
    "payrun": "รอบเงินเดือน", "arsettle": "ติ๊กรับเงิน AR", "kbsettle": "ติ๊กรับ KB",
}


def _collect_audit_rows(s: Session, since: datetime, limit: int = 500) -> list[dict]:
    """รวม audit ทุกแหล่งเป็นรูปเดียว {at,user,table,row_id,field,old,new,note,route}."""
    out: list[dict] = []
    for a in s.exec(select(models.AuditLog).where(models.AuditLog.at >= since)).all():
        out.append({"at": a.at, "user": a.user, "table": a.table_name,
                    "row_id": a.row_id, "field": a.field, "old": a.old_value,
                    "new": a.new_value, "note": a.note, "route": a.route})
    for a in s.exec(select(models.DailyJobAudit)
                    .where(models.DailyJobAudit.changed_at >= since)).all():
        out.append({"at": a.changed_at, "user": a.changed_by, "table": "daily",
                    "row_id": a.daily_job_id, "field": a.field_name,
                    "old": a.old_value, "new": a.new_value, "note": a.action,
                    "route": "/daily"})
    for a in s.exec(select(models.DepositAudit)
                    .where(models.DepositAudit.changed_at >= since)).all():
        out.append({"at": a.changed_at, "user": a.changed_by, "table": "deposit",
                    "row_id": a.employee_id, "field": a.field_name,
                    "old": a.old_value, "new": a.new_value, "note": a.reason,
                    "route": "/deposits"})
    for a in s.exec(select(models.DispatchPlanAudit)
                    .where(models.DispatchPlanAudit.changed_at >= since)).all():
        out.append({"at": a.changed_at, "user": a.changed_by, "table": "dispatch",
                    "row_id": a.plan_id, "field": a.field_name,
                    "old": a.old_value, "new": a.new_value,
                    "note": f"{a.action} {a.note}".strip(), "route": "/dispatch/planner"})
    for a in s.exec(select(QuotationAudit)
                    .where(QuotationAudit.changed_at >= since)).all():
        out.append({"at": a.changed_at, "user": a.changed_by, "table": "quotation",
                    "row_id": a.quotation_id, "field": a.field_name,
                    "old": a.old_value, "new": a.new_value, "note": a.action,
                    "route": "/quote/list"})
    out.sort(key=lambda r: r["at"], reverse=True)
    return out[:limit]


@app.get("/admin/audit", response_class=HTMLResponse)
def admin_audit(request: Request, user: str = "", table: str = "",
                days: int = 7, q: str = ""):
    days = max(1, min(days, 90))
    since = datetime.utcnow() - timedelta(days=days)
    with Session(engine) as s:
        rows = _collect_audit_rows(s, since)
    if user.strip():
        rows = [r for r in rows if user.strip().lower() in r["user"].lower()]
    if table:
        rows = [r for r in rows if r["table"] == table]
    if q.strip():
        needle = q.strip().lower()
        rows = [r for r in rows if needle in
                f"{r['field']} {r['old']} {r['new']} {r['note']}".lower()]
    users = sorted({r["user"] for r in rows if r["user"]})
    ctx = base_context(request)
    ctx.update({"rows": rows, "user_q": user, "table_q": table, "days": days,
                "q": q, "table_th": _AUDIT_TABLE_TH, "users": users})
    return templates.TemplateResponse(request, "admin_audit.html", ctx)


# =========================================================================
# เครื่องคิดราคาขนส่ง (/quote) + รายงาน Oatside (/oatside/report) — โอสั่ง 3ก.ค. 03:00
# "ย้ายเข้าระบบเลย" — เสิร์ฟไฟล์เดิมตรงๆ (ไม่ผ่าน Jinja) = เลขตรง GitHub Pages 100%
# ที่มา: TransportRateCalculator/transport_rate_calculator.html +
#        transport-rate-calculator-repo/reports/oatside-pg-2026/ (สำเนา vendored ใน app)
# =========================================================================

_APP_DIR_SELF = Path(__file__).resolve().parent


def _first_existing(*paths: Path) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None


# B2: bootstrap ต่อท้ายไฟล์เครื่องคิด (ไม่แก้เนื้อไฟล์ — เลขเป๊ะ 100% ตามหลัก B1):
# ชี้ระบบ "Sync to Drive" เดิมของไฟล์เข้า /quote/sync ของ MVP ครั้งแรกอัตโนมัติ
# → ปุ่ม "บันทึกงาน" เดิม = เซฟเข้าระบบ (Quotation) + เปิดหน้าใหม่โหลดรายการกลับเอง
_QUOTE_SYNC_BOOTSTRAP = """
<script id="yk-quote-sync-bootstrap">
(function () {
  try {
    var K = 'yk_drive_sync_settings_v1';
    if (!localStorage.getItem(K)) {
      localStorage.setItem(K, JSON.stringify({
        url: '/quote/sync', secret: '',
        autoSyncAfterSave: true, autoLoadOnOpen: true, autoNameOnSave: true
      }));
      if (typeof loadDriveSettings === 'function') loadDriveSettings();
      if (typeof loadFromDrive === 'function') loadFromDrive(true);
    }
  } catch (e) {}
})();
</script>
"""


# B1.1: แถบเมนู YK บนหัวเครื่องคิด — inject ตอนเสิร์ฟแบบเดียวกับ sync bootstrap
# (ไม่แตะเนื้อไฟล์/สูตร — เลขเป๊ะ 100% ตามหลัก B1); inline style ล้วน
# เพราะไฟล์เครื่องคิดไม่มี Tailwind ของ base.html
_QUOTE_NAV_BAR = """
<div id="yk-quote-nav" style="background:#0f172a;color:#fff;padding:10px 16px;
display:flex;align-items:center;gap:18px;flex-wrap:wrap;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;font-size:14px;">
  <a href="/daily" style="color:#fff;text-decoration:none;font-weight:700;">&larr; Project YK</a>
  <a href="/quote" style="color:#cbd5e1;text-decoration:none;font-weight:600;">📋 เครื่องคิดราคา</a>
  <a href="/quote/deal" style="color:#cbd5e1;text-decoration:none;">🧮 โต๊ะเช็คดีล</a>
  <a href="/quote/list" style="color:#cbd5e1;text-decoration:none;">📄 ใบเสนอที่เซฟไว้</a>
  <a href="/quote/wonder" style="color:#cbd5e1;text-decoration:none;">🚚 ต้นทุน Wonder</a>
</div>
"""


@app.get("/quote", response_class=HTMLResponse)
def quote_calculator():
    """เครื่องคิดค่าขนส่งตามราคาน้ำมัน — ไฟล์เดี่ยวตัวเดียวกับ GitHub Pages."""
    p = _first_existing(
        _APP_DIR_SELF / "quote_calc.html",  # server (vendored)
        _APP_DIR_SELF.parent / "TransportRateCalculator" / "transport_rate_calculator.html",  # dev
    )
    if p is None:
        raise HTTPException(404, "ยังไม่ได้วางไฟล์เครื่องคิดราคาบนเครื่องนี้")
    html = p.read_text(encoding="utf-8")
    if "</body>" in html:
        html = html.replace("</body>", _QUOTE_SYNC_BOOTSTRAP + "\n</body>", 1)
    # แทรกแถบเมนูถัดจาก <body ...> แรก (ไฟล์เดิมไม่ถูกแก้)
    m = re.search(r"<body[^>]*>", html)
    if m:
        html = html[:m.end()] + _QUOTE_NAV_BAR + html[m.end():]
    return HTMLResponse(html)


def _quote_fields_from_record(rec: dict) -> dict:
    """ถอดฟิลด์ค้นหา/รายงานจาก record ของเครื่องคิด (snapshot ทั้งก้อนอยู่ raw_json)."""
    snap = rec.get("snapshot") or {}
    fv = snap.get("fieldValues") or {}
    summ = snap.get("summary") or {}

    def _f(x) -> float:
        try:
            return float(x)
        except (TypeError, ValueError):
            return 0.0

    preset = str(fv.get("mapsOriginPreset") or "")
    cust_price = _f(fv.get("customerPrice"))
    saved_at = None
    try:
        saved_at = datetime.fromisoformat(str(rec.get("savedAt") or "").replace("Z", "+00:00"))
        saved_at = saved_at.replace(tzinfo=None)
    except ValueError:
        pass
    return {
        "customer_name": str(rec.get("customerName") or "").strip(),
        "factory_name": str(rec.get("jobName") or "").strip(),
        "location_url": str(fv.get("mapsDestinationLink") or "").strip(),
        # preset ทั้งสองตัวในไฟล์ = ต้นทางโซนแหลมฉบัง; "custom" = กำหนดเอง
        "origin_site": "LCB" if preset.startswith("13.0") else "",
        "km_round": _f(summ.get("totalDistance")),
        "toll_cost": _f(fv.get("tollCost")),
        "price_offered": cust_price if cust_price > 0 else _f(summ.get("suggested15AfterFinance")),
        "tags": str(rec.get("tags") or "").strip(),
        "note": str(rec.get("note") or "").strip(),
        "saved_at": saved_at,
    }


@app.post("/quote/sync")
async def quote_sync_save(request: Request):
    """รับ payload จากปุ่ม Sync ของเครื่องคิด (Content-Type text/plain ตามไฟล์เดิม).
    upsert ตาม record id; record ที่หายจากเครื่องคิด → archived (ไม่ลบ — เก็บประวัติ)."""
    try:
        data = json.loads((await request.body()).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "payload ไม่ใช่ JSON")
    if data.get("action") != "save":
        raise HTTPException(400, "action ต้องเป็น save")
    records = (data.get("payload") or {}).get("records") or []
    u = current_user(request)
    by = u.username if u else ""
    with Session(engine) as s:
        existing = {q.record_id: q for q in s.exec(select(Quotation)).all()}
        seen: set[str] = set()
        for rec in records:
            rid = str(rec.get("id") or "").strip()
            if not rid:
                continue
            seen.add(rid)
            fields = _quote_fields_from_record(rec)
            raw = json.dumps(rec, ensure_ascii=False)
            q = existing.get(rid)
            if q is None:
                s.add(Quotation(record_id=rid, raw_json=raw, **fields))
                continue
            if q.raw_json == raw:
                continue
            for k, v in fields.items():
                setattr(q, k, v)
            q.raw_json = raw
            q.updated_at = datetime.utcnow()
            if q.status == "archived":
                q.status = "draft"  # กลับมาโผล่ในเครื่องคิดอีกครั้ง
            s.add(q)
            s.add(QuotationAudit(quotation_id=q.id, changed_by=by,
                                 action="sync_update", field_name="raw_json"))
        for rid, q in existing.items():
            if rid not in seen and q.status != "archived":
                s.add(QuotationAudit(quotation_id=q.id, changed_by=by,
                                     action="sync_archive", field_name="status",
                                     old_value=q.status, new_value="archived"))
                q.status = "archived"
                q.updated_at = datetime.utcnow()
                s.add(q)
        s.commit()
    return JSONResponse({"ok": True, "count": len(seen)})


@app.get("/quote/sync")
def quote_sync_load(action: str = "load"):
    """เครื่องคิดโหลดรายการกลับ (?action=load) — คืนเฉพาะที่ยังไม่ archived."""
    if action != "load":
        raise HTTPException(400, "action ต้องเป็น load")
    with Session(engine) as s:
        rows = s.exec(
            select(Quotation)
            .where(Quotation.status != "archived")
            .order_by(Quotation.saved_at.desc())  # type: ignore[union-attr]
        ).all()
    records = []
    for q in rows:
        try:
            records.append(json.loads(q.raw_json))
        except ValueError:
            continue
    return JSONResponse({"records": records})


_QUOTE_STATUS_TH = {
    "draft": "ร่าง", "negotiating": "ต่อรองอยู่", "agreed": "ตกลงแล้ว",
    "rejected": "ไม่ผ่าน", "archived": "ลบจากเครื่องคิด",
}


@app.get("/quote/list", response_class=HTMLResponse)
def quote_list(request: Request, q: str = "", status: str = ""):
    with Session(engine) as s:
        rows = s.exec(select(Quotation).order_by(
            Quotation.saved_at.desc())).all()  # type: ignore[union-attr]
    if status:
        rows = [r for r in rows if r.status == status]
    else:
        rows = [r for r in rows if r.status != "archived"]
    if q.strip():
        needle = q.strip().lower()
        rows = [r for r in rows if needle in
                f"{r.customer_name} {r.factory_name} {r.tags} {r.note}".lower()]
    ctx = base_context(request)
    ctx.update({"rows": rows, "q": q, "status": status,
                "status_th": _QUOTE_STATUS_TH})
    return templates.TemplateResponse(request, "quote_list.html", ctx)


# ---------------------------------------------------------------------------
# โต๊ะเช็คดีล /quote/deal (v47) — spec: docs/superpowers/specs/2026-07-06-deal-checker-design.md
# หมายเหตุ route ordering: ทุก path literal ใต้ /quote ต้องอยู่ "ก่อน" /quote/{qid}
# ---------------------------------------------------------------------------

# พิกัดกลางตัวเมือง 77 จังหวัด (ใช้เป็นปลายทางระดับจังหวัด — OSRM snap ถนนเอง)
_TH_PROVINCE_COORDS: dict[str, tuple[float, float]] = {
    "กรุงเทพมหานคร": (13.7563, 100.5018), "สมุทรปราการ": (13.5991, 100.5967),
    "นนทบุรี": (13.8622, 100.5140), "ปทุมธานี": (14.0208, 100.5250),
    "พระนครศรีอยุธยา": (14.3532, 100.5689), "อ่างทอง": (14.5896, 100.4550),
    "ลพบุรี": (14.7995, 100.6534), "สิงห์บุรี": (14.8879, 100.4049),
    "ชัยนาท": (15.1852, 100.1251), "สระบุรี": (14.5289, 100.9109),
    "ชลบุรี": (13.3611, 100.9847), "ระยอง": (12.6814, 101.2776),
    "จันทบุรี": (12.6113, 102.1039), "ตราด": (12.2428, 102.5177),
    "ฉะเชิงเทรา": (13.6904, 101.0780), "ปราจีนบุรี": (14.0509, 101.3717),
    "นครนายก": (14.2069, 101.2130), "สระแก้ว": (13.8240, 102.0645),
    "ราชบุรี": (13.5282, 99.8134), "กาญจนบุรี": (14.0228, 99.5328),
    "สุพรรณบุรี": (14.4745, 100.1177), "นครปฐม": (13.8199, 100.0622),
    "สมุทรสาคร": (13.5475, 100.2744), "สมุทรสงคราม": (13.4098, 100.0023),
    "เพชรบุรี": (13.1119, 99.9399), "ประจวบคีรีขันธ์": (11.8126, 99.7957),
    "เชียงราย": (19.9105, 99.8406), "เชียงใหม่": (18.7883, 98.9853),
    "น่าน": (18.7756, 100.7730), "พะเยา": (19.1664, 99.9017),
    "แพร่": (18.1445, 100.1405), "แม่ฮ่องสอน": (19.2990, 97.9682),
    "ลำปาง": (18.2888, 99.4909), "ลำพูน": (18.5741, 99.0087),
    "ตาก": (16.8840, 99.1258), "เพชรบูรณ์": (16.4189, 101.1591),
    "สุโขทัย": (17.0078, 99.8237), "อุตรดิตถ์": (17.6200, 100.0993),
    "พิษณุโลก": (16.8211, 100.2659), "กำแพงเพชร": (16.4828, 99.5226),
    "พิจิตร": (16.4429, 100.3487), "อุทัยธานี": (15.3835, 100.0245),
    "นครสวรรค์": (15.7047, 100.1372), "ชุมพร": (10.4930, 99.1800),
    "ระนอง": (9.9529, 98.6085), "สุราษฎร์ธานี": (9.1382, 99.3215),
    "นครศรีธรรมราช": (8.4304, 99.9631), "กระบี่": (8.0863, 98.9063),
    "พังงา": (8.4510, 98.5297), "ภูเก็ต": (7.8804, 98.3923),
    "พัทลุง": (7.6167, 100.0742), "ตรัง": (7.5563, 99.6114),
    "สตูล": (6.6238, 100.0673), "สงขลา": (7.1897, 100.5954),
    "ปัตตานี": (6.8692, 101.2500), "ยะลา": (6.5413, 101.2803),
    "นราธิวาส": (6.4254, 101.8253), "หนองคาย": (17.8783, 102.7420),
    "บึงกาฬ": (18.3609, 103.6465), "หนองบัวลำภู": (17.2046, 102.4260),
    "อุดรธานี": (17.4139, 102.7872), "นครพนม": (17.4108, 104.7787),
    "มุกดาหาร": (16.5453, 104.7208), "สกลนคร": (17.1545, 104.1348),
    "มหาสารคาม": (16.1850, 103.3020), "เลย": (17.4860, 101.7223),
    "ขอนแก่น": (16.4419, 102.8360), "กาฬสินธุ์": (16.4315, 103.5059),
    "ร้อยเอ็ด": (16.0538, 103.6520), "ชัยภูมิ": (15.8069, 102.0311),
    "สุรินทร์": (14.8818, 103.4936), "บุรีรัมย์": (14.9930, 103.1029),
    "นครราชสีมา": (14.9799, 102.0977), "ยโสธร": (15.7921, 104.1452),
    "ศรีสะเกษ": (15.1186, 104.3229), "อำนาจเจริญ": (15.8657, 104.6265),
    "อุบลราชธานี": (15.2448, 104.8473),
}
_TH_PROVINCE_ALIAS = {
    "กทม": "กรุงเทพมหานคร", "กรุงเทพ": "กรุงเทพมหานคร", "กรุงเทพฯ": "กรุงเทพมหานคร",
    "อยุธยา": "พระนครศรีอยุธยา", "โคราช": "นครราชสีมา", "แปดริ้ว": "ฉะเชิงเทรา",
    "อุบล": "อุบลราชธานี", "นครศรีฯ": "นครศรีธรรมราช", "ประจวบ": "ประจวบคีรีขันธ์",
}
_DEAL_YK_HOME = (14.15969179682617, 100.60157104661114)  # ฐาน YK วังน้อย


def _deal_parse_latlng(text: str):
    """แกะ 'lat,lng' จากข้อความ — คืน (lat,lng) หรือ None."""
    m = re.search(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text or "")
    if not m:
        return None
    lat, lng = float(m.group(1)), float(m.group(2))
    if 4.0 <= lat <= 21.5 and 96.0 <= lng <= 106.5:  # กรอบประเทศไทย
        return (lat, lng)
    return None


def _deal_parse_gmaps_link(url: str):
    """แกะพิกัดจากลิงก์ Google Maps — ตามลิงก์สั้นให้ด้วย; คืน (lat,lng) หรือ None."""
    import urllib.request
    u = (url or "").strip()
    if not u.startswith("http"):
        return None
    # ลิงก์สั้น (maps.app.goo.gl / goo.gl) → ตาม redirect หา URL เต็ม
    if "goo.gl" in u:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (yk-deal)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                u = r.geturl()
        except Exception:
            return None
    # ลอง !3dLAT!4dLNG (พิกัดหมุด) ก่อน แล้วค่อย @LAT,LNG (จุดกลางแผนที่)
    m = re.search(r"!3d(-?\d{1,2}\.\d+)!4d(-?\d{1,3}\.\d+)", u)
    if not m:
        m = re.search(r"@(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)", u)
    if not m:
        return _deal_parse_latlng(u)
    lat, lng = float(m.group(1)), float(m.group(2))
    return (lat, lng) if (4.0 <= lat <= 21.5 and 96.0 <= lng <= 106.5) else None


def _deal_norm_name(name: str) -> str:
    n = (name or "").strip()
    for pre in ("จังหวัด", "จ.", "อ.เมือง", "ตัวเมือง"):
        if n.startswith(pre):
            n = n[len(pre):].strip()
    return n


def _deal_resolve_point(s, spec: dict):
    """resolve จุดหนึ่งเป็นพิกัด — ลำดับ: latlng ตรง → ลิงก์ gmaps → คลังสถานที่ → จังหวัด
    คืน {lat, lon, how} หรือ None; ถ้า resolve จากลิงก์/พิกัดและมีชื่อ → จำเข้า PlaceCache"""
    if not spec:
        return None
    name = _deal_norm_name(str(spec.get("name") or ""))
    # 1) พิกัดตรง
    ll = _deal_parse_latlng(str(spec.get("latlng") or ""))
    how = "latlng"
    # 2) ลิงก์ Google Maps
    if not ll and spec.get("link"):
        ll = _deal_parse_gmaps_link(str(spec.get("link")))
        how = "link"
    if ll:
        if name:  # จำไว้ใช้ครั้งหน้า
            row = s.exec(select(PlaceCache).where(PlaceCache.name == name)).first()
            if row is None:
                s.add(PlaceCache(name=name, lat=ll[0], lon=ll[1], source=how, use_count=1))
            else:
                row.lat, row.lon, row.source = ll[0], ll[1], how
                row.use_count += 1
                row.updated_at = datetime.utcnow()
                s.add(row)
            s.commit()
        return {"lat": ll[0], "lon": ll[1], "how": how}
    if not name:
        return None
    # 3) คลังสถานที่
    row = s.exec(select(PlaceCache).where(PlaceCache.name == name)).first()
    if row is not None:
        row.use_count += 1
        s.add(row); s.commit()
        return {"lat": row.lat, "lon": row.lon, "how": "place"}
    # 4) จังหวัด (ชื่อตรง / alias / ชื่อจังหวัดอยู่ในข้อความ)
    prov = _TH_PROVINCE_ALIAS.get(name, name)
    if prov in _TH_PROVINCE_COORDS:
        lat, lon = _TH_PROVINCE_COORDS[prov]
        return {"lat": lat, "lon": lon, "how": "province", "province": prov}
    for p, (lat, lon) in _TH_PROVINCE_COORDS.items():
        if p in name:
            return {"lat": lat, "lon": lon, "how": "province", "province": p}
    return None


def _deal_osrm(points: list) -> tuple[float, float]:
    """เรียก OSRM public — points = [(lat,lon),...] คืน (กม., ชม.ขับ); โยน RuntimeError ถ้าพลาด"""
    import urllib.request
    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=false"
    last_err: Exception | None = None
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "yk-deal/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("code") == "Ok" and d.get("routes"):
                rt = d["routes"][0]
                return rt["distance"] / 1000.0, rt["duration"] / 3600.0
            last_err = RuntimeError(str(d.get("code")))
        except Exception as e:  # noqa: BLE001 — retry ครั้งเดียวพอ
            last_err = e
    raise RuntimeError(f"OSRM: {last_err}")


@app.post("/quote/deal/distance")
async def deal_distance(request: Request):
    """คิดระยะ 1 รูทตามโครงเที่ยวของดีล — client วนยิงทีละรูท (เห็น progress)
    รองรับหลายจุดส่งต่อรูท: ส่ง stops=[spec,...] (ไปตามลำดับ) หรือ dest=spec จุดเดียว"""
    import math
    try:
        body = json.loads((await request.body()).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "payload ไม่ใช่ JSON")
    trip_mode = body.get("trip_mode") or "circuit"     # circuit | direct
    roundtrip = bool(body.get("roundtrip", True))
    stop_specs = body.get("stops") or ([body.get("dest")] if body.get("dest") else [])
    if not stop_specs:
        return JSONResponse({"ok": False, "reason": "no_stops"})
    with Session(engine) as s:
        origin = _deal_resolve_point(s, body.get("origin") or {}) or \
            {"lat": _DEAL_YK_HOME[0], "lon": _DEAL_YK_HOME[1], "how": "default_yk"}
        pickup = _deal_resolve_point(s, body.get("pickup") or {}) if body.get("pickup") else None
        stops = [_deal_resolve_point(s, sp) for sp in stop_specs]
    for idx, st in enumerate(stops):
        if st is None:
            return JSONResponse({"ok": False, "reason": "dest_unresolved", "stop_index": idx,
                                 "stop_name": str((stop_specs[idx] or {}).get("name") or "")})
    o = (origin["lat"], origin["lon"])
    stop_pts = [(st["lat"], st["lon"]) for st in stops]
    if trip_mode == "circuit":
        pts = [o] + ([(pickup["lat"], pickup["lon"])] if pickup else []) + stop_pts + [o]
    else:  # direct: ไล่ทุกจุดตามลำดับ; ไป-กลับ = บวกขากลับเส้นจริง (แม่นกว่า ×2)
        pts = [o] + stop_pts + ([o] if roundtrip else [])
    try:
        km, hr = _deal_osrm(pts)
    except RuntimeError as e:
        return JSONResponse({"ok": False, "reason": "osrm_error", "detail": str(e)})
    days = max(1, math.ceil(hr / 9.0))  # ~9 ชม.ขับ/วัน รวมพัก/โหลด (ท่าเดียวกับหน้า Wonder)
    return JSONResponse({"ok": True, "km": round(km, 1), "hours": round(hr, 1), "days": days,
                         "stops": stops, "dest": stops[-1], "origin": origin, "pickup": pickup})


@app.post("/quote/deal/save")
async def deal_save(request: Request):
    try:
        body = json.loads((await request.body()).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "payload ไม่ใช่ JSON")
    snapshot = body.get("snapshot") or {}
    routes = snapshot.get("routes") or []
    u = current_user(request)
    with Session(engine) as s:
        did = body.get("id")
        row = s.get(DealRecord, int(did)) if did else None
        if row is None:
            row = DealRecord(created_by=(u.username if u else ""))
        row.customer_name = str(body.get("customer_name") or "").strip()
        row.deal_name = str(body.get("deal_name") or "").strip()
        if body.get("status") in ("draft", "agreed", "rejected", "archived"):
            row.status = body["status"]
        row.snapshot_json = json.dumps(snapshot, ensure_ascii=False)
        row.route_count = len(routes)
        row.updated_at = datetime.utcnow()
        s.add(row); s.commit(); s.refresh(row)
        return JSONResponse({"ok": True, "id": row.id})


@app.get("/quote/deal/list")
def deal_list(q: str = ""):
    with Session(engine) as s:
        rows = s.exec(select(DealRecord).order_by(
            DealRecord.updated_at.desc()).limit(200)).all()  # type: ignore[union-attr]
    needle = q.strip().lower()
    out = []
    for r in rows:
        if r.status == "archived":
            continue
        if needle and needle not in f"{r.customer_name} {r.deal_name}".lower():
            continue
        out.append({"id": r.id, "customer_name": r.customer_name, "deal_name": r.deal_name,
                    "status": r.status, "route_count": r.route_count,
                    "updated_at": r.updated_at.isoformat(timespec="minutes")})
    return JSONResponse({"deals": out})


@app.get("/quote/deal/load/{did}")
def deal_load(did: int):
    with Session(engine) as s:
        row = s.get(DealRecord, did)
    if row is None:
        raise HTTPException(404)
    try:
        snapshot = json.loads(row.snapshot_json or "{}")
    except ValueError:
        snapshot = {}
    return JSONResponse({"ok": True, "id": row.id, "customer_name": row.customer_name,
                         "deal_name": row.deal_name, "status": row.status, "snapshot": snapshot})


def _serve_tool_page(*candidates) -> HTMLResponse:
    """เสิร์ฟไฟล์เครื่องมือเดี่ยว + แทรกแถบเมนู YK (ท่าเดียวกับ /quote)

    GOTCHA: ห้ามใช้ re.search หา <body> ทั้งไฟล์แบบเหมารวม — ไฟล์ fragment
    (เช่น wonder_sub_cost_2026.html) มีคำว่า '<body>' อยู่ใน "string ของ JS"
    (โค้ดปุ่มพิมพ์) การฉีดเมนูเข้ากลาง string ทำ script ทั้งหน้าพังเงียบ
    → ตัดสินจากต้นไฟล์: เอกสารเต็ม (<!doctype/<html) ค่อยฉีดหลังแท็กจริง,
    fragment ห่อใหม่โดยวางเมนูหน้าสุด ไม่แตะเนื้อไฟล์เลย"""
    p = _first_existing(*candidates)
    if p is None:
        raise HTTPException(404, "ยังไม่ได้วางไฟล์เครื่องมือบนเครื่องนี้")
    html = p.read_text(encoding="utf-8")
    head = html.lstrip()[:100].lower()
    if head.startswith("<!doctype") or head.startswith("<html"):
        m = re.search(r"<body[^>]*>", html)
        if m:
            html = html[:m.end()] + _QUOTE_NAV_BAR + html[m.end():]
    else:  # fragment — ครอบให้ครบเอกสาร เมนูอยู่หน้าสุด
        html = ("<!doctype html><html lang='th'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'></head>"
                "<body>" + _QUOTE_NAV_BAR + html + "</body></html>")
    return HTMLResponse(html)


@app.get("/quote/deal", response_class=HTMLResponse)
def deal_page():
    """โต๊ะเช็คดีล — ตารางหลายรูท เช็คราคาลูกค้า/ตั้งราคาเอง (v47)"""
    return _serve_tool_page(_APP_DIR_SELF / "deal_check.html")


@app.get("/quote/wonder", response_class=HTMLResponse)
def wonder_page():
    """เครื่องต้นทุน Wonder Sub 2026 — เข้าแอปเพื่อให้พิมพ์ได้ (พ้น sandbox artifact)"""
    return _serve_tool_page(
        _APP_DIR_SELF / "wonder_sub_cost_2026.html",
        _APP_DIR_SELF.parent / "TransportRateCalculator" / "wonder_sub_cost_2026.html",
    )


@app.get("/quote/{qid}", response_class=HTMLResponse)
def quote_detail(qid: int, request: Request):
    with Session(engine) as s:
        row = s.get(Quotation, qid)
        if not row:
            raise HTTPException(404)
        audits = s.exec(
            select(QuotationAudit)
            .where(QuotationAudit.quotation_id == qid)
            .order_by(QuotationAudit.changed_at.desc())  # type: ignore[union-attr]
        ).all()
    ctx = base_context(request)
    ctx.update({"row": row, "audits": audits, "status_th": _QUOTE_STATUS_TH})
    return templates.TemplateResponse(request, "quote_detail.html", ctx)


@app.post("/quote/{qid}/status")
def quote_set_status(qid: int, request: Request,
                     status: str = Form(...), price_agreed: str = Form("")):
    if status not in _QUOTE_STATUS_TH:
        raise HTTPException(400, "สถานะไม่ถูกต้อง")
    u = current_user(request)
    by = u.username if u else ""
    with Session(engine) as s:
        row = s.get(Quotation, qid)
        if not row:
            raise HTTPException(404)
        if status != row.status:
            s.add(QuotationAudit(quotation_id=qid, changed_by=by, action="status",
                                 field_name="status", old_value=row.status,
                                 new_value=status))
            row.status = status
        new_price: Optional[float] = None
        if price_agreed.strip():
            try:
                new_price = float(price_agreed.replace(",", ""))
            except ValueError:
                raise HTTPException(400, "ราคาตกลงไม่ใช่ตัวเลข")
        if new_price is not None and new_price != row.price_agreed:
            s.add(QuotationAudit(quotation_id=qid, changed_by=by, action="price_agreed",
                                 field_name="price_agreed",
                                 old_value="" if row.price_agreed is None else str(row.price_agreed),
                                 new_value=str(new_price)))
            row.price_agreed = new_price
        row.updated_at = datetime.utcnow()
        s.add(row)
        s.commit()
    return RedirectResponse(url=f"/quote/{qid}", status_code=303)


# ---------------------------------------------------------------------------
# B3: ราคาไหลเข้าเดลี่/บิล — ใบเสนอ status=agreed เสนอราคาให้แถวเดลี่ที่
# ลูกค้า+ปลายทางตรง; ไม่ auto-ทับ (คนคีย์กดรับต่อแถว → เขียน + DailyJobAudit)
# ห้ามแตะ engine เงินเดือน — เขียนเฉพาะ revenue_customer ของแถวที่ราคาว่าง
# ---------------------------------------------------------------------------

def _qnorm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _agreed_quotes(s: Session) -> list:
    return s.exec(select(Quotation).where(
        Quotation.status == "agreed",
        Quotation.price_agreed.is_not(None),  # type: ignore[union-attr]
    )).all()


def _quote_price_match(quotes: list, job, cust_name_by_id: dict) -> Optional[Quotation]:
    """หาใบเสนอที่ตรง "ทั้งลูกค้าและปลายทาง" (เข้มไว้ก่อน — เรื่องเงินห้ามเดา):
    ลูกค้า = ชื่อในใบเสนอเท่ากับ customer_name_raw / status_code / ชื่อลูกค้า master;
    ปลายทาง = ชื่องาน/โรงงานในใบเสนอเป็นส่วนหนึ่งของปลายทางเดลี่ (หรือกลับกัน)."""
    jcust = {_qnorm(job.customer_name_raw), _qnorm(job.status_code),
             _qnorm(cust_name_by_id.get(job.customer_id, ""))} - {""}
    jdest = _qnorm(job.destination)
    if not jcust or not jdest:
        return None
    for q in quotes:
        qc, qf = _qnorm(q.customer_name), _qnorm(q.factory_name)
        if qc and qf and qc in jcust and (qf in jdest or jdest in qf):
            return q
    return None


@app.get("/api/daily-jobs/quote-suggest")
def api_daily_quote_suggest(site: str = "", d_from: str = "", d_to: str = ""):
    """แถวเดลี่ราคาว่างที่มีใบเสนอ agreed ตรง — ให้ปุ่มในหน้า grid โชว์ให้คนคีย์กดรับ."""
    lo, hi = _parse_date(d_from), _parse_date(d_to)
    with Session(engine) as s:
        quotes = _agreed_quotes(s)
        if not quotes:
            return {"items": []}
        stmt = select(DailyJob)
        if lo:
            stmt = stmt.where(DailyJob.work_date >= lo)
        if hi:
            stmt = stmt.where(DailyJob.work_date <= hi)
        if site:
            stmt = stmt.where(DailyJob.site_code == site.strip().upper())
        cust = {c.id: c.name for c in s.exec(select(Customer)).all()}
        items = []
        for j in s.exec(stmt.order_by(DailyJob.work_date).limit(3000)).all():  # type: ignore[arg-type]
            if (j.revenue_customer or 0) > 0 or _daily_row_kind(j) != "job":
                continue
            q = _quote_price_match(quotes, j, cust)
            if not q:
                continue
            items.append({
                "job_id": j.id, "quote_id": q.id,
                "work_date": j.work_date.isoformat(),
                "site": j.site_code,
                "plate": (j.plate_no_raw or "").strip(),
                "driver": j.driver_raw_name or "",
                "customer": (j.customer_name_raw or j.status_code or "").strip(),
                "destination": j.destination or "",
                "price": q.price_agreed,
                "quote_label": f"{q.customer_name} — {q.factory_name}",
            })
    return {"items": items[:200]}


@app.post("/api/daily-jobs/apply-quote")
async def api_daily_apply_quote(request: Request):
    """คนคีย์กดรับ → เขียนราคาใบเสนอลง revenue_customer (เฉพาะแถวราคาว่าง) + audit.
    ตรวจ match ซ้ำฝั่ง server — ไม่เชื่อ payload จากหน้าเว็บ."""
    body = await request.json()
    try:
        job_id, quote_id = int(body.get("job_id")), int(body.get("quote_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "job_id/quote_id ไม่ถูกต้อง")
    u = current_user(request)
    with Session(engine) as s:
        j = s.get(DailyJob, job_id)
        q = s.get(Quotation, quote_id)
        if not j or not q:
            raise HTTPException(404)
        if q.status != "agreed" or q.price_agreed is None:
            raise HTTPException(409, "ใบเสนอไม่อยู่สถานะตกลงราคา")
        if (j.revenue_customer or 0) > 0:
            raise HTTPException(409, "แถวนี้มีราคาแล้ว — ระบบไม่ทับราคาเดิม")
        cust = {c.id: c.name for c in s.exec(select(Customer)).all()}
        if _quote_price_match([q], j, cust) is not q:
            raise HTTPException(409, "ลูกค้า/ปลายทางของแถวไม่ตรงใบเสนอ")
        old = j.revenue_customer or 0.0
        j.revenue_customer = float(q.price_agreed)
        j.updated_at = datetime.utcnow()
        s.add(models.DailyJobAudit(
            daily_job_id=j.id, changed_by=(u.username if u else ""),
            action="quote_apply", field_name="revenue_customer",
            old_value=str(old), new_value=str(j.revenue_customer)))
        s.add(j)
        s.commit()
        return {"ok": True, "value": j.revenue_customer}


_OATSIDE_REPORT_DIRS = (
    _APP_DIR_SELF / "oatside" / "TransportRateCalculator" / "reports" / "oatside-apr2026",  # build ล่าสุดจากระบบ (C3)
    _APP_DIR_SELF / "oatside_report",  # สำเนารายงานเดิม (ก่อนมี C3)
    _APP_DIR_SELF.parents[1] / "transport-rate-calculator-repo" / "reports" / "oatside-pg-2026",  # dev (ราก repo)
)


@app.get("/oatside", response_class=HTMLResponse)
def oatside_page(request: Request):
    """ศูนย์ Oatside (C3): อัปโหลดไฟล์ GPS 2 ไฟล์ → คำนวณใหม่ → ดูรายงาน/โหลด Excel."""
    from services import oatside_runner as orun

    ctx = base_context(request)
    ctx.update({
        "lb": orun.last_build(),
        "has_report": _first_existing(*_OATSIDE_REPORT_DIRS) is not None,
        "has_xlsx": orun.XLSX_OUT.exists(),
    })
    return templates.TemplateResponse(request, "oatside.html", ctx)


@app.post("/oatside/run")
async def oatside_run(request: Request):
    """รับไฟล์ GPS ต้นทาง (Oatside) + ปลายทาง (P&G) → รัน engine (นาที-สองนาที)."""
    from datetime import datetime as _dt

    from services import oatside_runner as orun

    form = await request.form()
    fo, fd = form.get("origin_file"), form.get("dest_file")
    if not (getattr(fo, "filename", "") and getattr(fd, "filename", "")):
        return RedirectResponse("/oatside?err=ต้องเลือกไฟล์ครบทั้ง 2 ไฟล์", status_code=303)
    updir = orun.UPLOADS / _dt.now().strftime("%Y%m%d-%H%M%S")
    updir.mkdir(parents=True, exist_ok=True)
    po = updir / Path(fo.filename).name
    pd_ = updir / Path(fd.filename).name
    po.write_bytes(await fo.read())
    pd_.write_bytes(await fd.read())
    orun.run_build(po, pd_)
    return RedirectResponse("/oatside", status_code=303)


@app.get("/oatside/xlsx")
def oatside_xlsx():
    from services import oatside_runner as orun

    if not orun.XLSX_OUT.exists():
        raise HTTPException(404, "ยังไม่เคยคำนวณ")
    return FileResponse(orun.XLSX_OUT, filename=orun.XLSX_OUT.name)


@app.get("/oatside/settings", response_class=HTMLResponse)
def oatside_settings(request: Request, err: str = "", ok: str = ""):
    """C5: โอแก้เงื่อนไขทุกอย่างเอง — เขียนกลับ JSON เดิม (สำรองก่อนทุกครั้ง)."""
    from services import oatside_runner as orun

    cfg = orun.load_json(orun.CONFIG)
    ovr = orun.load_json(orun.OVERRIDES)
    sections = []
    for name, spec in orun.SECTIONS.items():
        data = (ovr if spec["file"] == "overrides" else cfg).get(spec["key"], [])
        sections.append({"name": name, "title": spec["title"], "fields": spec["fields"],
                         "labels": spec["labels"], "rows": data})
    ctx = base_context(request)
    ctx.update({
        "sections": sections, "general_fields": orun.GENERAL_FIELDS, "cfg": cfg,
        "raw_config": json.dumps(cfg, ensure_ascii=False, indent=2),
        "raw_overrides": json.dumps(ovr, ensure_ascii=False, indent=2),
        "err": err, "ok": ok,
    })
    return templates.TemplateResponse(request, "oatside_settings.html", ctx)


@app.post("/oatside/settings/{section}")
async def oatside_settings_save(section: str, request: Request):
    from urllib.parse import quote as _q

    from services import oatside_runner as orun

    form = await request.form()
    try:
        if section == "general":
            cfg = orun.load_json(orun.CONFIG)
            for f, kind, _lab in orun.GENERAL_FIELDS:
                v = (form.get(f) or "").strip()
                if kind == "bool":
                    cfg[f] = form.get(f) == "on"
                elif v == "":
                    continue
                elif kind == "num":
                    cfg[f] = int(float(v)) if float(v) == int(float(v)) else float(v)
                else:
                    if not orun._DATE_RE.match(v):
                        raise ValueError(f"{f}: ต้องเป็น ปปปป-ดด-วว")
                    cfg[f] = v
            bak = orun.save_json(orun.CONFIG, cfg)
        elif section == "raw":
            which = form.get("which")
            data = json.loads(form.get("json_text") or "")  # validate ก่อนเขียน
            target = orun.OVERRIDES if which == "overrides" else orun.CONFIG
            bak = orun.save_json(target, data)
        elif section in orun.SECTIONS:
            rows, perr = orun.parse_section_rows(form, section)
            if perr:
                raise ValueError(perr)
            spec = orun.SECTIONS[section]
            target = orun.OVERRIDES if spec["file"] == "overrides" else orun.CONFIG
            data = orun.load_json(target)
            data[spec["key"]] = rows
            bak = orun.save_json(target, data)
        else:
            raise HTTPException(404)
        return RedirectResponse(f"/oatside/settings?ok={_q('บันทึกแล้ว (สำรองเดิมไว้ที่ ' + bak + ') — กด คำนวณใหม่ เพื่อให้มีผล')}", status_code=303)
    except (ValueError, json.JSONDecodeError) as e:
        return RedirectResponse(f"/oatside/settings?err={_q(str(e))}", status_code=303)


@app.get("/oatside/report")
def oatside_report_index():
    return RedirectResponse("/oatside/report/index.html", status_code=303)


@app.get("/oatside/report/{rel:path}")
def oatside_report_file(rel: str):
    """เสิร์ฟรายงาน Oatside ที่ generate แล้ว (index.html / trips.html / plates/... / exports)."""
    base = _first_existing(*_OATSIDE_REPORT_DIRS)
    if base is None:
        raise HTTPException(404, "ยังไม่มีรายงาน Oatside บนเครื่องนี้")
    p = (base / rel).resolve()
    if not str(p).startswith(str(base.resolve())) or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


# =========================================================================
# คลังแชทไลน์ (/line) — F1: ค้นทุกกลุ่ม + เปิดรูปเก่า + กลุ่มเงียบลอยขึ้น
# อ่าน line_archive.db ของ service 8020 แบบ read-only เท่านั้น (ห้ามเขียน)
# =========================================================================


@app.get("/line", response_class=HTMLResponse)
def line_search_page(request: Request, q: str = "", group: str = "", page: int = 0,
                     saved: int = 0):
    from services import line_archive as la

    ctx = base_context(request)
    error = None
    groups: list = []
    results: list = []
    if la.db_path() is None:
        error = "ไม่พบคลังแชทบนเครื่องนี้ (line_archive.db) — ใช้ได้บนเครื่อง server"
    else:
        try:
            groups = la.groups_by_activity()
            if q.strip() or group:
                results = la.search(q, group_id=group, limit=100, offset=max(page, 0) * 100)
        except Exception as e:
            error = f"อ่านคลังแชทไม่สำเร็จ: {e}"
    ctx.update({"groups": groups, "results": results, "q": q, "group": group,
                "page": max(page, 0), "error": error, "saved": saved})
    return templates.TemplateResponse(request, "line_search.html", ctx)


@app.get("/line/digest", response_class=HTMLResponse)
def line_digest(request: Request, d: str = ""):
    """F5: สรุปเช้ารายกลุ่ม — จำนวนข้อความ/รูปของวัน (default เมื่อวาน) + กลุ่มเงียบ >3 วัน."""
    from services import line_archive as la

    today = date.today()
    try:
        day = date.fromisoformat(d) if d.strip() else today - timedelta(days=1)
    except ValueError:
        day = today - timedelta(days=1)
    ctx = base_context(request)
    error, data = None, None
    if la.db_path() is None:
        error = "ไม่พบคลังแชทบนเครื่องนี้ (line_archive.db) — ใช้ได้บนเครื่อง server"
    else:
        try:
            data = la.daily_digest(day.isoformat(), today.isoformat())
        except Exception as e:
            error = f"อ่านคลังแชทไม่สำเร็จ: {e}"
    ctx.update({"day": day, "data": data, "error": error})
    return templates.TemplateResponse(request, "line_digest.html", ctx)


@app.get("/line/inbox", response_class=HTMLResponse)
def line_inbox(request: Request, days: int = 7):
    """F2: กล่องงานเข้าจากกลุ่มลูกค้า — candidate จาก pattern, คนกดรับ/ปัดเสมอ."""
    from services import line_archive as la
    from services import line_inbox as li

    days = max(1, min(days, 30))
    ctx = base_context(request)
    error, candidates = None, []
    with Session(engine) as s:
        maps = {m.group_id: m for m in s.exec(select(models.LineGroupMap)).all()}
        seen = {v.line_message_pk: v.status
                for v in s.exec(select(models.LineJobSeen)).all()}
    groups: list = []
    if la.db_path() is None:
        error = "ไม่พบคลังแชทบนเครื่องนี้ (line_archive.db) — ใช้ได้บนเครื่อง server"
    else:
        try:
            groups = la.groups_by_activity()
            cust_ids = [g["group_id"] for g in groups
                        if maps.get(g["group_id"])
                        and maps[g["group_id"]].kind == "customer"
                        and maps[g["group_id"]].active]
            candidates = li.scan_candidates(cust_ids, days=days,
                                            exclude_ids=set(seen))
            for c in candidates:
                mp = maps.get(c["group_id"])
                c["customer_name"] = mp.customer_name if mp else ""
                c["site_code"] = (mp.site_code if mp else "") or "LCB"
        except Exception as e:
            error = f"อ่านคลังแชทไม่สำเร็จ: {e}"
    from services.line_inbox import guess_group_map
    for g in groups:
        mp = maps.get(g["group_id"])
        if mp:
            g["kind"] = mp.kind
            g["customer_name"] = mp.customer_name
            g["site_code"] = mp.site_code
            g["guessed"] = False
        else:
            # ยังไม่ mark — เดาจากชื่อกลุ่มให้ก่อน (prefill) โอแค่กดบันทึกยืนยัน
            g["kind"], g["customer_name"], g["site_code"] = guess_group_map(g["name"])
            g["guessed"] = g["kind"] != "other"
    ctx.update({"groups": groups, "candidates": candidates, "days": days,
                "error": error, "n_seen": len(seen)})
    return templates.TemplateResponse(request, "line_inbox.html", ctx)


@app.post("/line/inbox/map")
def line_inbox_map(request: Request, group_id: str = Form(...), label: str = Form(""),
                   kind: str = Form("other"), customer_name: str = Form(""),
                   site_code: str = Form("")):
    """ตั้งชนิดกลุ่ม (ลูกค้า/ปั๊ม/ภายใน) — เก็บฝั่ง app.db ไม่แตะ DB archiver."""
    if kind not in ("customer", "station", "internal", "other"):
        raise HTTPException(400, "ชนิดกลุ่มไม่ถูกต้อง")
    with Session(engine) as s:
        m = s.exec(select(models.LineGroupMap)
                   .where(models.LineGroupMap.group_id == group_id.strip())).first()
        if m is None:
            m = models.LineGroupMap(group_id=group_id.strip())
        m.label = label.strip() or m.label
        m.kind = kind
        m.customer_name = customer_name.strip()
        m.site_code = site_code.strip().upper()
        m.updated_at = datetime.utcnow()
        s.add(m)
        s.commit()
    return RedirectResponse("/line/inbox", status_code=303)


@app.post("/line/inbox/mark")
def line_inbox_mark(request: Request, msg_id: int = Form(...),
                    action: str = Form(...), site: str = Form("LCB"),
                    work_date: str = Form("")):
    """รับเป็นงาน (accepted → เปิด planner prefill) หรือ ไม่ใช่งาน (dismissed) — กันเด้งซ้ำ."""
    if action not in ("accept", "dismiss"):
        raise HTTPException(400, "action ไม่ถูกต้อง")
    u = current_user(request)
    with Session(engine) as s:
        existing = s.exec(select(models.LineJobSeen)
                          .where(models.LineJobSeen.line_message_pk == msg_id)).first()
        if existing is None:
            s.add(models.LineJobSeen(
                line_message_pk=msg_id,
                status="accepted" if action == "accept" else "dismissed",
                by_user=u.username if u else ""))
            s.commit()
    if action == "accept":
        q = f"site={site.strip().upper() or 'LCB'}"
        if work_date.strip():
            q += f"&plan_date={work_date.strip()}"
        return RedirectResponse(f"/dispatch/planner/new?{q}", status_code=303)
    return RedirectResponse("/line/inbox", status_code=303)


@app.get("/line/pod", response_class=HTMLResponse)
def line_pod(request: Request, days: int = 7):
    """F3: รีวิวผูกรูปจากกลุ่มลูกค้าเข้ากับแถวเดลี่ (POD) — คนยืนยันเสมอ."""
    from services import line_archive as la
    from services import line_pod as lp

    days = max(1, min(days, 30))
    ctx = base_context(request)
    error, cards = None, []
    with Session(engine) as s:
        maps = {m.group_id: m for m in s.exec(
            select(models.LineGroupMap)
            .where(models.LineGroupMap.kind == "customer",
                   models.LineGroupMap.active == True)).all()}  # noqa: E712
        seen = {jm.line_message_pk for jm in s.exec(select(models.JobMedia)).all()}
        if la.db_path() is None:
            error = "ไม่พบคลังแชทบนเครื่องนี้ (line_archive.db) — ใช้ได้บนเครื่อง server"
        else:
            try:
                cands = lp.photo_candidates(list(maps), days=days, exclude_ids=seen)
                for c in cands:
                    mp = maps.get(c["group_id"])
                    codes = tuple(x.strip() for x in
                                  (mp.customer_name or "").split(",") if x.strip()) if mp else ()
                    c["matches"] = lp.match_daily_jobs(s, c, codes)
                    cards.append(c)
            except Exception as e:
                error = f"อ่านคลังแชทไม่สำเร็จ: {e}"
    n_linked = 0
    with Session(engine) as s:
        n_linked = len(s.exec(select(models.JobMedia)
                              .where(models.JobMedia.status == "linked")).all())
    ctx.update({"cards": cards, "days": days, "error": error, "n_linked": n_linked})
    return templates.TemplateResponse(request, "line_pod.html", ctx)


@app.post("/line/pod/mark")
def line_pod_mark(request: Request, msg_id: int = Form(...), action: str = Form(...),
                  job_id: str = Form("")):
    """ผูกรูปกับแถวเดลี่ (link) หรือข้าม (skip) — unique ต่อรูป กันซ้ำ."""
    if action not in ("link", "skip"):
        raise HTTPException(400, "action ไม่ถูกต้อง")
    u = current_user(request)
    with Session(engine) as s:
        existing = s.exec(select(models.JobMedia)
                          .where(models.JobMedia.line_message_pk == msg_id)).first()
        if existing is None:
            jid = _parse_int(job_id) if action == "link" else None
            if action == "link" and not jid:
                raise HTTPException(400, "เลือกแถวงานก่อน")
            if jid and s.get(DailyJob, jid) is None:
                raise HTTPException(404, "ไม่พบแถวเดลี่")
            s.add(models.JobMedia(
                line_message_pk=msg_id, daily_job_id=jid,
                status="linked" if action == "link" else "skipped",
                by_user=u.username if u else ""))
            s.commit()
    return RedirectResponse("/line/pod", status_code=303)


@app.get("/billing/evidence")
def billing_evidence(request: Request, series: str = "", month: str = "",
                     download: str = ""):
    """F3: ชุดหลักฐานต่อลูกค้า+เดือน — แถวเดลี่ + รูปที่ผูกแล้ว; download=zip ได้."""
    from services import invoice_builder as ib
    from services import line_archive as la

    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = [int(x) for x in month.split("-")]
        d1, d2 = _month_bounds(y, m)
    except ValueError:
        y, m = today.year, today.month
        d1, d2 = _month_bounds(y, m)
        month = f"{y:04d}-{m:02d}"

    rows, media_by_job = [], {}
    cfg = ib.REGISTRY.get(series)
    if cfg:
        with Session(engine) as s:
            billed, unbilled = ib.daily_rows_for_series(s, cfg, d1, d2)
            jobs = [j for js in billed.values() for j in js] + unbilled
            job_ids = [j.id for j in jobs]
            if job_ids:
                for jm in s.exec(select(models.JobMedia).where(
                        models.JobMedia.status == "linked",
                        models.JobMedia.daily_job_id.in_(job_ids))).all():  # type: ignore[union-attr]
                    media_by_job.setdefault(jm.daily_job_id, []).append(jm.line_message_pk)
            rows = [{"job": j, "media_ids": media_by_job.get(j.id, [])} for j in jobs]

    if download == "zip" and cfg:
        import io as _io
        import zipfile
        buf = _io.BytesIO()
        n_files = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in rows:
                j = r["job"]
                for msg_id in r["media_ids"]:
                    p = la.media_file(msg_id)
                    if p is None:  # อาจถูกย้ายลงแผ่น External แล้ว (G2)
                        with Session(engine) as s:
                            p, _ = _archived_media_path(s, msg_id)
                    if p is None:
                        continue
                    label = j.invoice_no or f"job{j.id}"
                    zf.writestr(f"{label}/{j.work_date}_{j.container_no or j.id}_{msg_id}{p.suffix}",
                                p.read_bytes())
                    n_files += 1
        if n_files == 0:
            raise HTTPException(404, "ยังไม่มีรูปที่ผูกไว้ในช่วงนี้ — ไปผูกที่ /line/pod ก่อน")
        from urllib.parse import quote as _urlquote
        fname = f"หลักฐาน_{series}_{month}.zip"
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition":
                                 f"attachment; filename*=UTF-8''{_urlquote(fname)}"})

    ctx = base_context(request)
    ctx.update({"series": series, "month": month, "cfg": cfg,
                "registry": ib.REGISTRY, "rows": rows,
                "n_media": sum(len(r["media_ids"]) for r in rows)})
    return templates.TemplateResponse(request, "billing_evidence.html", ctx)


def _archived_media_path(s: Session, msg_id: int) -> tuple[Path | None, str]:
    """(path บนแผ่นถ้าเสียบอยู่, disk_label) ของรูปที่ถูกย้ายแล้ว — ไม่เคยย้าย = (None, '')."""
    from services import media_archive as ma

    row = s.exec(select(models.MediaArchive)
                 .where(models.MediaArchive.line_message_pk == msg_id)).first()
    if row is None:
        return None, ""
    p = Path(row.archive_path)
    if p.exists():
        return p, row.disk_label
    # แผ่นอาจโผล่คนละอักษรไดรฟ์ — ตามหาแผ่นจาก label แล้วประกอบ path ใหม่
    disk = ma.find_disk(row.disk_label, _ext_backup_targets())
    if disk is not None:
        parts = Path(row.archive_path).parts
        if "YK_MEDIA" in parts:
            alt = disk.joinpath(*parts[parts.index("YK_MEDIA"):])
            if alt.exists():
                return alt, row.disk_label
    return None, row.disk_label


@app.get("/line/media/{msg_id}")
def line_media_serve(msg_id: int):
    from services import line_archive as la

    p = la.media_file(msg_id)
    if p is not None:
        return FileResponse(p)
    with Session(engine) as s:
        ap, label = _archived_media_path(s, msg_id)
    if ap is not None:
        return FileResponse(ap)
    if label:
        # รูปถูกย้ายลงแผ่นแล้วและแผ่นไม่ได้เสียบ — โชว์ป้ายแทน (ระบบไม่พัง)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="200">'
               f'<rect width="100%" height="100%" fill="#f3f4f6"/>'
               f'<text x="50%" y="45%" text-anchor="middle" font-size="18" fill="#374151">'
               f'📦 รูปอยู่แผ่น {label}</text>'
               f'<text x="50%" y="62%" text-anchor="middle" font-size="13" fill="#6b7280">'
               f'เสียบแผ่นที่เครื่อง server แล้วรีเฟรช</text></svg>')
        return Response(svg, media_type="image/svg+xml")
    raise HTTPException(404)


# =========================================================================
# สมุดโน้ต / สิ่งที่ต้องทำ (/todo) — โอสั่ง 3ก.ค.: แทนสมุดจด+ห้องโยนมาก่อน
# จดเร็วแบบพิมพ์แชท (มือถือใช้ไมค์คีย์บอร์ดพูดแทนพิมพ์ได้) ค้นได้ แนบรูปได้
# ของใครของมัน (แยกตาม username) — รายละเอียด (หมวด/ด่วน/กำหนด) ค่อยเติมทีหลังได้
# =========================================================================

_TODO_MEDIA = Path(__file__).resolve().parent / "_todo_media"


def _todo_groups(items: list, today_d) -> list:
    """จัดกลุ่มตามความเร่ง: ด่วน → เลยกำหนด → วันนี้ → มีกำหนดถัดไป → ไม่มีกำหนด."""
    urgent, overdue, todays, upcoming, someday = [], [], [], [], []
    for t in items:
        if t.priority > 0:
            urgent.append(t)
        elif t.due_date and t.due_date < today_d:
            overdue.append(t)
        elif t.due_date and t.due_date == today_d:
            todays.append(t)
        elif t.due_date:
            upcoming.append(t)
        else:
            someday.append(t)
    upcoming.sort(key=lambda t: t.due_date)
    urgent.sort(key=lambda t: (-t.priority, t.due_date or date.max))
    return [
        ("🔥 ด่วน", urgent), ("⏰ เลยกำหนด", overdue), ("📌 วันนี้", todays),
        ("📅 มีกำหนด", upcoming), ("🗒️ ยังไม่กำหนด", someday),
    ]


@app.get("/todo", response_class=HTMLResponse)
def todo_page(request: Request, q: str = "", cat: str = ""):
    from auth import current_user

    user = current_user(request)
    uname = user.username if user else ""
    with Session(engine) as s:
        rows = s.exec(select(TodoItem).where(TodoItem.username == uname)).all()
    if q.strip():
        qq = q.strip().lower()
        rows = [t for t in rows if qq in (t.text or "").lower() or qq in (t.category or "").lower()]
    cats = sorted({(t.category or "").strip() for t in rows if (t.category or "").strip()})
    if cat:
        rows = [t for t in rows if (t.category or "").strip() == cat]
    open_items = [t for t in rows if t.status == "open"]
    done_items = sorted([t for t in rows if t.status == "done"],
                        key=lambda t: t.done_at or t.created_at, reverse=True)[:50]
    # เฟส 4: กล่องรอคัดจากไลน์ — เห็น/สแกนเฉพาะ admin (ข้อมูลไลน์รวมทุกไซท์)
    is_admin = bool(user and user.role == "admin")
    suggests = []
    if is_admin:
        _todo_scan_maybe_auto()
        with Session(engine) as s:
            suggests = s.exec(select(TodoSuggest).where(TodoSuggest.status == "pending")
                              .order_by(TodoSuggest.sent_at.desc()).limit(30)).all()
    ctx = base_context(request)
    ctx.update({
        "groups": _todo_groups(open_items, date.today()),
        "done_items": done_items, "cats": cats, "q": q, "cat": cat,
        "n_open": len(open_items),
        "media_of": lambda t: [m for m in (t.media_json or "").split(",") if m],
        "suggests": suggests, "can_scan": is_admin,
        "scanned": request.query_params.get("scanned", ""),
        "scan_err": (request.query_params.get("scan_err", "")
                     or (get_setting("todo_scan_err", "") if is_admin else "")),
    })
    return templates.TemplateResponse(request, "todo.html", ctx)


@app.post("/todo/add")
async def todo_add(request: Request):
    from auth import current_user

    user = current_user(request)
    form = await request.form()
    text = (form.get("text") or "").strip()
    if not text:
        return RedirectResponse("/todo", status_code=303)
    due_raw = (form.get("due_date") or "").strip()
    item = TodoItem(
        username=user.username if user else "",
        text=text,
        category=(form.get("category") or "").strip(),
        priority=int(form.get("priority") or 0),
        due_date=date.fromisoformat(due_raw) if due_raw else None,
    )
    with Session(engine) as s:
        s.add(item)
        s.commit()
        s.refresh(item)
        names = []
        for f in form.getlist("photos"):
            if not getattr(f, "filename", ""):
                continue
            ext = Path(f.filename).suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
                continue
            d = _TODO_MEDIA / str(item.id)
            d.mkdir(parents=True, exist_ok=True)
            name = f"{len(names) + 1}{ext}"
            (d / name).write_bytes(await f.read())
            names.append(name)
        if names:
            item.media_json = ",".join(names)
            s.add(item)
            s.commit()
    return RedirectResponse("/todo", status_code=303)


@app.post("/todo/{item_id}/update")
def todo_update(item_id: int, request: Request, text: str = Form(""), category: str = Form(""),
                priority: str = Form("0"), due_date: str = Form("")):
    from auth import current_user

    user = current_user(request)
    with Session(engine) as s:
        t = s.get(TodoItem, item_id)
        if t and user and t.username == user.username:
            if text.strip():
                t.text = text.strip()
            t.category = category.strip()
            t.priority = int(priority or 0)
            t.due_date = date.fromisoformat(due_date) if due_date.strip() else None
            s.add(t)
            s.commit()
    return RedirectResponse("/todo", status_code=303)


@app.post("/todo/{item_id}/toggle")
def todo_toggle(item_id: int, request: Request):
    from auth import current_user
    from datetime import datetime as _dt

    user = current_user(request)
    with Session(engine) as s:
        t = s.get(TodoItem, item_id)
        if t and user and t.username == user.username:
            t.status = "open" if t.status == "done" else "done"
            t.done_at = _dt.utcnow() if t.status == "done" else None
            s.add(t)
            s.commit()
    return RedirectResponse("/todo", status_code=303)


@app.post("/todo/{item_id}/delete")
def todo_delete(item_id: int, request: Request):
    from auth import current_user

    user = current_user(request)
    with Session(engine) as s:
        t = s.get(TodoItem, item_id)
        if t and user and t.username == user.username:
            s.delete(t)
            s.commit()
    return RedirectResponse("/todo", status_code=303)


@app.get("/todo/media/{item_id}/{fname}")
def todo_media(item_id: int, fname: str, request: Request):
    from auth import current_user

    user = current_user(request)
    with Session(engine) as s:
        t = s.get(TodoItem, item_id)
    if not (t and user and t.username == user.username):
        raise HTTPException(404)
    p = (_TODO_MEDIA / str(item_id) / fname).resolve()
    if not str(p).startswith(str(_TODO_MEDIA.resolve())) or not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.post("/todo/{item_id}/ai-draft", response_class=HTMLResponse)
def todo_ai_draft(item_id: int, request: Request):
    """ปุ่ม ✨ บนหน้า /todo (เฟส 2 LINE→todo) — ให้ Qwen ฟรี (9arm) แก้คำผิด+จัดหมวด
    เป็น draft เท่านั้น: คืน fragment ให้โอแก้ต่อ/กดรับผ่าน /todo/{id}/update ตัวเดิม
    — AI ไม่เขียน DB เอง."""
    from auth import current_user
    from services import ai_assist

    user = current_user(request)
    with Session(engine) as s:
        t = s.get(TodoItem, item_id)
        if not (t and user and t.username == user.username):
            raise HTTPException(404)
        cats = sorted({x.strip() for x in
                       s.exec(select(TodoItem.category)
                              .where(TodoItem.username == user.username)).all()
                       if (x or "").strip()})
    ctx = {"t": t, "error": "", "draft_text": "", "draft_category": "", "engine": ""}
    try:
        d = ai_assist.rewrite_todo(t.text, cats,
                                   provider=get_setting("ai_draft_provider", "auto"))
        ctx.update({"draft_text": d["text"], "draft_category": d["category"] or t.category,
                    "engine": d["engine"]})
    except Exception as e:
        ctx["error"] = str(e)
    return templates.TemplateResponse(request, "todo_ai_draft.html", ctx)


def _todo_from_line_bundle(username: str, msg_id: int, category: str = "ไลน์") -> int | None:
    """สร้าง TodoItem จากข้อความไลน์ + รูปชุดเดียวกัน (±20 นาที คนส่งเดียวกัน) —
    ก็อปรูปเข้า _todo_media เอง ไม่แตะ DB archiver. คืน todo_id (None = ไม่พบข้อความ).
    ใช้ร่วมปุ่ม ➕ บนหน้า /line (เฟส 1) และปุ่มรับจากกล่องรอคัด (เฟส 4)."""
    import shutil

    from services import line_archive as la

    b = la.bundle_for_todo(msg_id)
    if b is None:
        return None
    header = f"📱 ไลน์ {b['group_name']} — {b['who']} {str(b['sent_at'])[:16]}"
    text = (b["text"].strip() + "\n\n" + header) if b["text"].strip() else header
    item = TodoItem(username=username, text=text, category=category)
    with Session(engine) as s:
        s.add(item)
        s.commit()
        s.refresh(item)
        todo_id = item.id
        names, missing = [], 0
        for mid in b["media_ids"]:
            src = la.media_file(mid)
            if src is None:
                missing += 1  # รูปย้ายลงแผ่น External แล้ว (G2) — ก็อปไม่ได้ตอนนี้
                continue
            d = _TODO_MEDIA / str(todo_id)
            d.mkdir(parents=True, exist_ok=True)
            name = f"{len(names) + 1}{src.suffix.lower() or '.jpg'}"
            shutil.copyfile(src, d / name)
            names.append(name)
        if missing:
            item.text += f"\n(⚠️ อีก {missing} รูปอยู่แผ่น External — เปิดดูได้ในคลังไลน์)"
        if names:
            item.media_json = ",".join(names)
        s.add(item)
        s.commit()
    return todo_id


@app.post("/line/{msg_id}/to-todo")
def line_to_todo(msg_id: int, request: Request, q: str = Form(""), group: str = Form(""),
                 page: str = Form("0")):
    """ปุ่ม ➕ บนหน้า /line — ส่งข้อความ+รูปทั้งชุดเข้า /todo ของคนที่กด (เฟส 1)."""
    from urllib.parse import quote

    from auth import current_user

    user = current_user(request)
    todo_id = _todo_from_line_bundle(user.username if user else "", msg_id)
    if todo_id is None:
        raise HTTPException(404, "ไม่พบข้อความในคลังแชท")
    return RedirectResponse(
        f"/line?q={quote(q)}&group={quote(group)}&page={page or 0}&saved={todo_id}",
        status_code=303)


# ---- เฟส 4: กล่องรอคัดจากไลน์ (TodoSuggest) — AI เสนอ โอคัด --------------------

import threading  # noqa: E402

_TODO_SCAN_LOCK = threading.Lock()   # กันสแกนซ้อน (ปุ่ม + auto-trigger พร้อมกัน)


def _todo_scan_run() -> dict:
    """รันสแกน + จดเวลา/ผลไว้ใน AppSetting (ใช้ทั้งปุ่มและ auto-trigger).

    todo_scan_err = ข้อความพังของรอบล่าสุด ("" = รอบล่าสุดสำเร็จ) — โชว์บน /todo
    และเป็นตัวบอก _todo_scan_maybe_auto ว่าให้ลองใหม่เร็วขึ้น."""
    from services import todo_scan

    if not _TODO_SCAN_LOCK.acquire(blocking=False):
        return {"skipped": "กำลังสแกนอยู่แล้ว"}
    try:
        set_setting("todo_scan_last", datetime.utcnow().isoformat())
        try:
            res = todo_scan.scan()
        except Exception as e:
            set_setting("todo_scan_err", str(e)[:300])
            raise
        set_setting("todo_scan_err",
                    f"AI ล่มบางส่วน — คัดไม่ครบ {res['failed']} ก้อน จะลองใหม่ให้เอง"
                    if res.get("failed") else "")
        return res
    finally:
        _TODO_SCAN_LOCK.release()


def _todo_scan_maybe_auto() -> None:
    """auto-scan รายวัน: ถ้ารอบล่าสุดเกิน 20 ชม. เด้ง thread สแกนเบื้องหลัง
    (เรียกตอน admin เปิด /todo — ไม่หน่วงหน้า; พังเงียบได้ รอบหน้า/ปุ่มลองใหม่).
    มาร์กเวลาแบบ sync ก่อนเด้ง thread — โปรเซสหนึ่งเด้งอย่างมากวันละครั้ง.
    รอบล่าสุดพัง (AI ล่ม) → ลองใหม่ใน 1 ชม. ไม่ใช่เงียบไปทั้งวัน."""
    from services import line_archive

    if line_archive.db_path() is None:
        return  # เครื่องนี้ไม่มีคลังไลน์ (dev/test) — ไม่มีอะไรให้สแกน
    last = get_setting("todo_scan_last", "")
    gap = timedelta(hours=1) if get_setting("todo_scan_err", "") else timedelta(hours=20)
    try:
        if last and datetime.utcnow() - datetime.fromisoformat(last) < gap:
            return
    except ValueError:
        pass
    set_setting("todo_scan_last", datetime.utcnow().isoformat())

    def _bg():
        try:
            _todo_scan_run()
        except Exception as e:   # อย่าให้ thread ตายแบบมีเสียง — log พอ
            logging.getLogger("yk.todo_scan").warning("auto-scan ล้มเหลว: %s", e)
    threading.Thread(target=_bg, daemon=True).start()


@app.post("/todo/scan-line")
def todo_scan_now(request: Request):
    """ปุ่ม 🔍 สแกนไลน์ตอนนี้ — เฉพาะ admin (ข้อมูลไลน์รวมทุกไซท์)."""
    from auth import current_user

    user = current_user(request)
    if not (user and user.role == "admin"):
        raise HTTPException(403)
    try:
        r = _todo_scan_run()
    except Exception as e:
        return RedirectResponse(f"/todo?scan_err={e}", status_code=303)
    return RedirectResponse(f"/todo?scanned={r.get('added', 0)}", status_code=303)


@app.post("/todo/suggest/{sid}/accept")
def todo_suggest_accept(sid: int, request: Request):
    """รับข้อเสนอ → TodoItem จริงของคนที่กด (ดึงรูปชุดเดียวกันจากไลน์มาด้วย)."""
    from auth import current_user

    user = current_user(request)
    if not (user and user.role == "admin"):
        raise HTTPException(403)
    with Session(engine) as s:
        sg = s.get(TodoSuggest, sid)
        if not sg or sg.status != "pending":
            raise HTTPException(404)
        todo_id = _todo_from_line_bundle(user.username, sg.line_msg_id,
                                         category=sg.category or "งาน")
        if todo_id is None:
            # ข้อความหายจาก archive (เช่น เทสต์/ลบ) — สร้างจากสรุป AI แทน ไม่มีรูป
            item = TodoItem(username=user.username, category=sg.category or "งาน",
                            text=f"{sg.summary}\n\n📱 ไลน์ {sg.group_name} — {sg.who} {sg.sent_at}")
            s.add(item)
            s.commit()
            s.refresh(item)
            todo_id = item.id
        sg.status = "accepted"
        sg.todo_id = todo_id
        s.add(sg)
        s.commit()
    return RedirectResponse("/todo", status_code=303)


@app.post("/todo/suggest/{sid}/dismiss")
def todo_suggest_dismiss(sid: int, request: Request):
    from auth import current_user

    user = current_user(request)
    if not (user and user.role == "admin"):
        raise HTTPException(403)
    with Session(engine) as s:
        sg = s.get(TodoSuggest, sid)
        if sg and sg.status == "pending":
            sg.status = "dismissed"
            s.add(sg)
            s.commit()
    return RedirectResponse("/todo", status_code=303)


# =========================================================================
# /ai — ผู้ช่วย AI ถามระบบ (เฟส 3) — เฉพาะ admin (RBAC เมนู "ai")
# กฎยืน: AI อ่านอย่างเดียว — ตอบคำถามเท่านั้น ไม่มีทางเขียน DB
# (Qwen = REST ไม่มี tool; Claude = claude -p จำกัด Read,Grep,Glob)
# =========================================================================

def _ai_system_prompt() -> str:
    """บริบทระบบ + ตัวเลขคร่าวๆ สดจาก DB (นับอย่างเดียว — ถูกและพอให้ AI ตอบแม่น)."""
    from sqlalchemy import func

    with Session(engine) as s:
        n_daily = s.exec(select(func.count()).select_from(DailyJob)).one()
        n_emp = s.exec(select(func.count()).select_from(Employee)).one()
        n_veh = s.exec(select(func.count()).select_from(Vehicle)).one()
        cycles = s.exec(select(PayRun.site_code, PayRun.pay_cycle_tag, PayRun.status)
                        .order_by(PayRun.id.desc()).limit(6)).all()
    cyc = "; ".join(f"{c[0]} {c[1]} ({c[2]})" for c in cycles) or "-"
    return (
        "คุณคือผู้ช่วย AI ของระบบ Project YK (ระบบบริหารงานขนส่งหัวลาก 3 ไซท์: "
        "LCB แหลมฉบัง, AYU อยุธยา, BIGC) ผู้ถามคือโอ ผู้จัดการบริษัท ตอบภาษาไทย กระชับ ตรงคำถาม\n"
        "ขอบเขต: ตอบจากข้อมูลที่มี ถ้าไม่รู้ให้บอกตรงๆ ว่าไม่รู้ ห้ามเดาตัวเลขเงิน "
        "และห้ามแนะนำให้แก้ไขฐานข้อมูลตรงๆ (ระบบมีหน้าจอสำหรับแก้อยู่แล้ว)\n"
        f"สถานะระบบวันนี้ {date.today().isoformat()}: งานเดลี่ {n_daily} แถว, "
        f"พนักงาน {n_emp}, รถ {n_veh}; รอบจ่ายล่าสุด: {cyc}\n"
        "รอบจ่าย: BIGC 1→สิ้นเดือน, LCB 16→15, AYU 26→25 (cycle_tag = เดือนที่รอบจบ)")


@app.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request):
    from services import ai_assist

    with Session(engine) as s:
        logs = s.exec(select(AiChatLog).order_by(AiChatLog.id.desc()).limit(20)).all()
    ctx = base_context(request)
    ctx.update({"claude_ok": ai_assist.claude_available(), "logs": logs,
                "draft_provider": get_setting("ai_draft_provider", "auto")})
    return templates.TemplateResponse(request, "ai.html", ctx)


@app.post("/ai/settings")
def ai_settings(request: Request, draft_provider: str = Form("auto")):
    """ตั้งค่าปุ่ม ✨ เรียบเรียง (หน้า /todo) — auto = Qwen ก่อน ล่มค่อยสลับ Claude."""
    if draft_provider in ("auto", "qwen", "claude"):
        set_setting("ai_draft_provider", draft_provider)
    return RedirectResponse("/ai", status_code=303)


@app.post("/ai/ask")
async def ai_ask(request: Request):
    """แชทถามระบบ — body JSON {q, model, history:[{role,content}...]} → {ok, answer}.
    ทุกครั้งลง AiChatLog (สำเร็จหรือพัง) — log การใช้ตามที่โอเคาะ."""
    import time as _time

    from auth import current_user
    from services import ai_assist

    user = current_user(request)
    data = await request.json()
    q = (data.get("q") or "").strip()
    model = data.get("model") or "qwen"
    if not q:
        return JSONResponse({"ok": False, "answer": "พิมพ์คำถามก่อนครับ"})
    history = [m for m in (data.get("history") or [])[-10:]
               if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()]
    t0 = _time.monotonic()
    ok = True
    try:
        if model.startswith("claude"):
            # "claude" = รุ่น default ของ CLI; "claude:haiku|sonnet|opus" = เลือกรุ่นเอง
            sub = {"claude:haiku": "haiku", "claude:sonnet": "sonnet",
                   "claude:opus": "opus"}.get(model)
            if sub is None:
                model = "claude"
            # claude -p ไม่รับ messages array — แบนประวัติเป็นข้อความเดียว
            lines = [_ai_system_prompt(), ""]
            for m in history:
                lines.append(("โอ: " if m["role"] == "user" else "ผู้ช่วย: ") + m["content"])
            lines.append("โอ: " + q)
            answer = ai_assist.chat_claude("\n".join(lines), cwd=str(APP_DIR), model=sub)
        else:
            model = "qwen"
            msgs = ([{"role": "system", "content": _ai_system_prompt()}]
                    + history + [{"role": "user", "content": q}])
            answer = ai_assist.chat_qwen(msgs, max_tokens=2000, temperature=0.3)
    except Exception as e:
        ok, answer = False, str(e)
    ms = int((_time.monotonic() - t0) * 1000)
    with Session(engine) as s:
        s.add(AiChatLog(username=user.username if user else "", model=model,
                        question=q, answer=answer, ok=ok, ms=ms))
        s.commit()
    return JSONResponse({"ok": ok, "answer": answer})


_HEALTH_CACHE: dict = {"at": None, "data": None}

# ---- S1 ชั้น 2: Backup ลงแผ่น External (ปุ่มบนหน้า server-health) --------------
_EXT_BACKUP: dict = {"running": False, "ok": None, "log": "", "ts": None}


def _ext_backup_targets() -> list[str]:
    """ไดรฟ์ที่เสียบเพิ่ม (E:-Z:) + เป้าทดสอบจาก env — ตัวเลือกของปุ่ม Backup ลงแผ่น."""
    out = []
    test = os.getenv("YK_EXT_TEST_TARGET", "").strip()
    if test:
        out.append(test)
    for letter in "EFGHIJKLMNOPQRSTUVWXYZ":
        try:
            if Path(f"{letter}:/").exists():
                out.append(f"{letter}:/")
        except OSError:
            continue
    return out


def _ext_backup_worker(target: str) -> None:
    """robocopy ของเย็น (line_media) + ชุด zip ชั้น 1 ลงแผ่น — incremental
    (ครั้งแรก ~4GB, ครั้งถัดไปเฉพาะไฟล์ใหม่). รันใน thread — ดูผลบนหน้าเดิม."""
    import subprocess
    from datetime import datetime as _dt

    line_dir = Path(os.getenv("YK_LINE_DIR", r"C:\Users\yklog\YK_LINE_ARCHIVER"))
    hot_dir = Path(os.getenv("YK_BACKUP_ROOT", r"D:\YK_BACKUPS"))
    dest = Path(target) / "YK_BACKUP"
    logs: list[str] = []
    ok = True
    try:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "YK_ARCHIVE.txt").write_text(
            f"YK backup drive - do not delete\nlast: {_dt.now():%Y-%m-%d %H:%M}\n",
            encoding="utf-8")
        for src, name in ((line_dir / "line_media", "line_media"),
                          (hot_dir, "hot_zips")):
            if not src.exists():
                logs.append(f"(ข้าม {name} — ไม่พบ {src})")
                continue
            r = subprocess.run(
                ["robocopy", str(src), str(dest / name),
                 "/E", "/NFL", "/NDL", "/NP", "/R:1", "/W:1"],
                capture_output=True, text=True)
            tail = (r.stdout or "").strip().splitlines()[-8:]
            logs.append(f"{name}: exit {r.returncode}\n" + "\n".join(tail))
            if r.returncode >= 8:   # robocopy: 0-7 = สำเร็จ, >=8 = มีไฟล์พลาด
                ok = False
        if ok:
            set_setting("external_backup_last",
                        _dt.now().isoformat(timespec="seconds") + "|" + str(target))
    except Exception as e:  # noqa: BLE001 — โชว์เหตุบนหน้า ไม่ให้ thread ตายเงียบ
        ok = False
        logs.append(f"{type(e).__name__}: {e}")
    _EXT_BACKUP.update({"running": False, "ok": ok, "log": "\n\n".join(logs),
                        "ts": _dt.now().strftime("%d/%m/%Y %H:%M")})


@app.post("/admin/server-health/backup-external")
def admin_backup_external(target: str = Form(...)):
    import threading

    if _EXT_BACKUP["running"]:
        return RedirectResponse("/admin/server-health", status_code=303)
    if target not in _ext_backup_targets():
        raise HTTPException(400, "ไม่พบไดรฟ์ที่เลือก — เสียบ External แล้วรีเฟรชหน้า")
    _EXT_BACKUP.update({"running": True, "ok": None, "log": "", "ts": None})
    threading.Thread(target=_ext_backup_worker, args=(target,), daemon=True).start()
    return RedirectResponse("/admin/server-health", status_code=303)


# ---- G2: ย้ายรูปเก่าลงแผ่น External (copy → hash → ลบ → จด MediaArchive) ----
_MEDIA_ARCH: dict = {"running": False, "ok": None, "log": "", "ts": None}


def _media_archive_worker(target: str, mode: str, username: str) -> None:
    from datetime import date as _d, datetime as _dt, timedelta as _td

    from services import media_archive as ma

    logs: list[str] = []
    ok = True
    try:
        with Session(engine) as s:
            archived = {r.line_message_pk
                        for r in s.exec(select(models.MediaArchive)).all()}
            label = ma.read_label(target)
            if label is None:
                seq = int(get_setting("media_archive_disk_seq") or "0") + 1
                set_setting("media_archive_disk_seq", str(seq))
                label = ma.ensure_label(target, seq)
                logs.append(f"แผ่นใหม่ — ตั้งชื่อ {label} (สร้าง {ma.MARKER} ที่รากแผ่น)")
            if mode == "oldest-month":
                allp = ma.scan_photos(archived, limit=200000)
                if not allp:
                    raise ValueError("ไม่มีรูปให้ย้าย")
                month = allp[0]["sent"][:7]
                photos = [p for p in allp if p["sent"][:7] == month]
                logs.append(f"โหมดเดือนเก่าสุด: {month} — {len(photos)} ไฟล์")
            else:
                before = _d.today() - _td(days=ma.RETENTION_DAYS)
                photos = ma.scan_photos(archived, before=before, limit=200000)
                logs.append(f"ครบกำหนด (เก่ากว่า {before}): {len(photos)} ไฟล์")
            res = ma.move_files(s, target, label, photos, by_user=username)
        import shutil as _sh
        du = _sh.disk_usage(str(Path(target)))
        logs.append(f"ย้ายสำเร็จ {res['ok']} ไฟล์ ({res['gb']} GB) · พลาด {res['fail']}")
        logs += res["errors"]
        logs.append(f"แผ่น {label} เหลือที่ว่าง {round(du.free / 1e9, 1)} GB")
        ok = res["fail"] == 0
        _HEALTH_CACHE["at"] = None   # ตัวเลขดิสก์/รูปบนหน้า health อัปเดตทันที
    except Exception as e:  # noqa: BLE001 — โชว์เหตุบนหน้า ไม่ให้ thread ตายเงียบ
        ok = False
        logs.append(f"{type(e).__name__}: {e}")
    _MEDIA_ARCH.update({"running": False, "ok": ok, "log": "\n".join(logs),
                        "ts": _dt.now().strftime("%d/%m/%Y %H:%M")})


@app.post("/admin/media-archive/move")
def admin_media_archive_move(request: Request, target: str = Form(...),
                             mode: str = Form("due")):
    import threading

    if _MEDIA_ARCH["running"]:
        return RedirectResponse("/admin/server-health", status_code=303)
    if target not in _ext_backup_targets():
        raise HTTPException(400, "ไม่พบไดรฟ์ที่เลือก — เสียบ External แล้วรีเฟรชหน้า")
    if mode not in ("due", "oldest-month"):
        raise HTTPException(400, "mode ไม่ถูกต้อง")
    u = current_user(request)
    _MEDIA_ARCH.update({"running": True, "ok": None, "log": "", "ts": None})
    threading.Thread(target=_media_archive_worker,
                     args=(target, mode, u.username if u else ""),
                     daemon=True).start()
    return RedirectResponse("/admin/server-health", status_code=303)


@app.get("/admin/server-health", response_class=HTMLResponse)
def admin_server_health(request: Request):
    """สุขภาพเครื่อง (G1): ดิสก์/ขนาดข้อมูล/backup ล่าสุด/พอร์ต — เตือนเหลือ <20%=เหลือง <10%=แดง.

    เดินนับขนาดโฟลเดอร์ใหญ่ (รูปไลน์ 2 หมื่นไฟล์) ช้าเป็นวินาที → cache 10 นาที.
    ส่วนแจ้งเข้า Discord อัตโนมัติ = ทำพร้อม S1 (ใช้ webhook เดียวกับ backup).
    """
    import shutil as _sh
    import socket
    from datetime import datetime as _dt, timedelta as _td

    if _HEALTH_CACHE["at"] and _dt.now() - _HEALTH_CACHE["at"] < _td(minutes=10):
        data = _HEALTH_CACHE["data"]
    else:
        def _dir_size(p: Path):
            if not p.exists():
                return None
            return round(sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e9, 2)

        def _port_up(port: int) -> bool:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return True
            except OSError:
                return False

        app_dir = Path(__file__).resolve().parent
        du = _sh.disk_usage(str(Path(app_dir.anchor)))
        line_dir = Path(r"C:\Users\yklog\YK_LINE_ARCHIVER")
        backups = app_dir.parent / "backups"
        latest_bak = max(backups.glob("*.db"), key=lambda f: f.stat().st_mtime, default=None) \
            if backups.exists() else None
        data = {
            "total_gb": round(du.total / 1e9, 1), "free_gb": round(du.free / 1e9, 1),
            "used_gb": round(du.used / 1e9, 1),
            "free_pct": round(du.free / du.total * 100, 1),
            "line_media_gb": _dir_size(line_dir / "line_media"),
            "backups_gb": _dir_size(backups),
            "todo_media_gb": _dir_size(app_dir / "_todo_media"),
            "db_mb": round((app_dir / "app.db").stat().st_size / 1e6, 1) if (app_dir / "app.db").exists() else None,
            "latest_backup": _dt.fromtimestamp(latest_bak.stat().st_mtime).strftime("%d/%m/%Y %H:%M") if latest_bak else None,
            "latest_backup_name": latest_bak.name if latest_bak else None,
            "line_bot_up": _port_up(8020),
            "checked_at": _dt.now().strftime("%d/%m/%Y %H:%M"),
        }
        # G2: รูปเก่าสุดที่ยังไม่ย้าย + จำนวนที่ครบกำหนดย้าย (>2 ปี)
        from services import media_archive as ma
        with Session(engine) as s:
            _archived = {r.line_message_pk
                         for r in s.exec(select(models.MediaArchive)).all()}
        _oldest = ma.scan_photos(_archived, limit=1)
        data["media_oldest"] = _oldest[0]["sent"] if _oldest else None
        data["media_due_date"] = (ma.due_date_of(_oldest[0]["sent"]).isoformat()
                                  if _oldest else None)
        data["media_n_due"] = len(ma.scan_photos(
            _archived, before=_dt.now().date() - _td(days=ma.RETENTION_DAYS),
            limit=200000))
        _HEALTH_CACHE["at"] = _dt.now()
        _HEALTH_CACHE["data"] = data
    level = "red" if data["free_pct"] < 10 else ("yellow" if data["free_pct"] < 20 else "ok")

    # ---- S1: สถานะสำรอง 3 ชั้น (อ่านสดทุกครั้ง — ไฟล์เล็ก + ปุ่มเปลี่ยนสถานะบ่อย)
    hot = None
    hot_age_h = None
    try:
        sp = Path(os.getenv("YK_BACKUP_STATUS", r"D:\YK_BACKUPS\last_run.json"))
        if sp.exists():
            hot = json.loads(sp.read_text(encoding="utf-8"))
            hot_age_h = round(
                (_dt.now() - _dt.fromisoformat(hot["ts"])).total_seconds() / 3600, 1)
    except (OSError, ValueError, KeyError):
        hot = {"ok": False, "error": "อ่านไฟล์สถานะไม่ได้"}
    hot_level = "none"
    if hot is not None:
        hot_level = "red" if (not hot.get("ok") or (hot_age_h or 0) > 26) else "ok"
    ext_days = None
    ext_drive = ""
    raw_ext = get_setting("external_backup_last")
    if raw_ext:
        try:
            t, _, ext_drive = raw_ext.partition("|")
            ext_days = (_dt.now() - _dt.fromisoformat(t)).days
        except ValueError:
            pass

    # error ล่าสุดจาก logs/app.log (อ่านท้ายไฟล์ — ไฟล์หมุน 2MB ไม่หนัก)
    recent_errors: list[str] = []
    try:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
            # เอาเฉพาะบรรทัดหัว ERROR/WARNING (ตัด traceback ยาว) 20 รายการล่าสุด
            heads = [ln for ln in lines
                     if " ERROR " in ln or " WARNING " in ln or " CRITICAL " in ln]
            recent_errors = heads[-20:][::-1]
    except OSError:
        pass

    from services import media_archive as ma
    arch_targets = [{"target": t, "label": ma.read_label(t)}
                    for t in _ext_backup_targets()]

    ctx = base_context(request)
    ctx.update({"h": data, "level": level,
                "hot": hot, "hot_age_h": hot_age_h, "hot_level": hot_level,
                "ext_days": ext_days, "ext_drive": ext_drive,
                "ext_state": _EXT_BACKUP, "ext_targets": _ext_backup_targets(),
                "arch_targets": arch_targets, "arch_state": _MEDIA_ARCH,
                "disk_tight": data["free_pct"] < ma.DISK_WARN_FREE_PCT,
                "recent_errors": recent_errors,
                "log_file": str(LOG_FILE)})
    return templates.TemplateResponse(request, "admin_server_health.html", ctx)


@app.get("/admin/plan", response_class=HTMLResponse)
def admin_plan(request: Request):
    """แพลน MVP ในระบบ (โอขอ 3ก.ค. "อยากเห็นแสงปลายอุโมงค์") — admin เท่านั้น (prefix /admin).

    อ่าน docs/PLAN_STATUS.json (สถานะ/วัน) + แผน/สเปค markdown 2 ไฟล์ — deploy ต้อง
    scp โฟลเดอร์ docs 3 ไฟล์นี้ขึ้น server ด้วยทุกครั้งที่แผนเปลี่ยน (YK_MVP/docs/).
    """
    import json as _json
    from pathlib import Path as _P

    docs = _P(__file__).resolve().parents[1] / "docs"

    def _read(name: str) -> str:
        try:
            return (docs / name).read_text(encoding="utf-8")
        except OSError:
            return f"(ยังไม่พบไฟล์ {name} บนเครื่องนี้ — ต้อง scp ขึ้น YK_MVP/docs/)"

    phases = []
    updated = "?"
    try:
        data = _json.loads(_read("PLAN_STATUS.json"))
        updated = data.get("updated", "?")
        for ph in data.get("phases", []):
            days = sum(t.get("days", 0) for t in ph["tasks"])
            done = sum(t.get("days", 0) for t in ph["tasks"] if t.get("status") == "done")
            phases.append({**ph, "days": round(days, 2), "done_days": round(done, 2),
                           "pct": round(done / days * 100) if days else 0})
    except Exception:
        pass
    total = round(sum(p["days"] for p in phases), 2)
    done_d = round(sum(p["done_days"] for p in phases), 2)
    n_tasks = sum(len(p["tasks"]) for p in phases)
    n_done = sum(1 for p in phases for t in p["tasks"] if t.get("status") == "done")
    remain = round(total - done_d, 2)
    ctx = base_context(request)
    ctx.update({
        "phases": phases, "updated": updated,
        "total_days": total, "done_days": done_d, "remain_days": remain,
        "pct": round(done_d / total * 100) if total else 0,
        "n_tasks": n_tasks, "n_done": n_done,
        "remain_weeks": max(1, round(remain / 5)),
        "md_plan": _read("MASTER_PLAN_2026-07.md"),
        "md_specs": _read("MVP_TASK_SPECS.md"),
        "md_waiting": _read("WAITING_ON_OAT.md"),
    })
    return templates.TemplateResponse(request, "admin_plan.html", ctx)


@app.get("/kb-payout", response_class=HTMLResponse)
def kb_payout_page(request: Request, amount: str = "", cust: str = "CY"):
    """KB จ่ายคืนเจ้าของงาน (CY/NHL/MOL/Siam i) — กรอกยอดโอน → จับคู่อินวอย + KB.

    อ่านอินวอยสดจาก Google Drive (read-only) ไม่แตะ payroll. เฉพาะ admin
    (permissions.py menu "kb"). ตรรกะอยู่ services/kb_payout.py (CLI ใช้ตัวเดียวกัน).
    ใบที่ติ๊ก "รับแล้ว" (KbSettle) ถูกตัดออกจากการจับคู่ — จับคู่ในเจ้าที่เลือกเท่านั้น
    (สลิปโอนบอกอยู่แล้วว่าลูกค้ารายไหนโอน).
    """
    from services import kb_payout as kbp

    ctx = base_context(request)
    error = None
    rows: list = []
    match = None
    amt = None
    try:
        rows = kbp.load_all()
    except Exception as e:  # Drive ล่ม/key หาย — โชว์ข้อความแทน 500
        error = f"อ่านอินวอยจาก Google Drive ไม่สำเร็จ: {e}"
    with Session(engine) as s:
        settled = {k.inv_no: k for k in s.exec(select(KbSettle)).all()}
    for r in rows:
        r["settled"] = settled.get(r["inv"])
    if cust not in kbp.CUSTOMERS:
        cust = "CY"
    amount_raw = (amount or "").strip()
    if amount_raw and not error:
        try:
            amt = float(amount_raw.replace(",", ""))
            open_cust = [r for r in rows if r["cust"] == cust and not r["settled"]]
            match = kbp.match_amount(open_cust, amt)
        except ValueError:
            error = "ยอดโอนต้องเป็นตัวเลข เช่น 19027.98"
    # section ต่อเจ้าของงาน: รายการ + ยอดค้าง/รับแล้ว + ผู้รับโอน
    sections = []
    for c, cfg in kbp.CUSTOMERS.items():
        crows = [r for r in rows if r["cust"] == c]
        copen = [r for r in crows if not r["settled"]]
        sections.append({
            "cust": c, "owner": cfg["owner"], "bank": cfg["bank"],
            "rate": cfg.get("rate"), "mode": cfg["mode"], "rows": crows,
            "n_open": len(copen),
            "kb_open": round(sum(r["kb"] for r in copen), 2),
            "kb_settled": round(sum(r["kb"] for r in crows if r["settled"]), 2),
        })
    ctx.update({
        "sections": sections, "cust": cust, "customers": list(kbp.CUSTOMERS.keys()),
        "match": match, "amount": amt, "amount_raw": amount_raw,
        "owner": kbp.KB_OWNERS[cust], "error": error,
    })
    return templates.TemplateResponse(request, "kb_payout.html", ctx)


@app.post("/kb-payout/settle")
def kb_payout_settle(request: Request, inv_no: str = Form(...), kb_amount: str = Form("0"),
                     transfer_amount: str = Form("0"), undo: str = Form("")):
    """ติ๊ก/ยกเลิกติ๊ก 'รับ KB แล้ว' รายใบ. inv_no รับหลายใบคั่น , (จากปุ่มบันทึกทั้งชุด)."""
    invs = [v.strip() for v in inv_no.split(",") if v.strip()]
    kbs = [v.strip() for v in (kb_amount or "0").split(",")]

    def _f(x: str) -> float:
        try:
            return float(x.replace(",", ""))
        except ValueError:
            return 0.0

    with Session(engine) as s:
        for i, inv in enumerate(invs):
            existing = s.exec(select(KbSettle).where(KbSettle.inv_no == inv)).first()
            if undo == "1":
                if existing:
                    audit_log(s, request, "kbsettle", existing.id or 0, "received",
                              "1", "0", note=inv)
                    s.delete(existing)
            elif not existing:
                audit_log(s, request, "kbsettle", 0, "received", "0", "1", note=inv)
                s.add(KbSettle(inv_no=inv, kb_amount=_f(kbs[i] if i < len(kbs) else "0"),
                               transfer_amount=_f(transfer_amount)))
        s.commit()
    return RedirectResponse("/kb-payout", status_code=303)


# A2: ใบเสร็จรับเงิน + หนังสือรับรองหัก ณ ที่จ่าย 50 ทวิ จากชุด KB ที่ติ๊กรับแล้ว
# ฟอร์มมาตรฐาน (โอเคาะ 4ก.ค.) — user ปรับ layout เองได้ที่ /admin/doc-designer
_KB_PREFIX_CUSTOMER = {"CYIV": "CY", "NHIV": "NHL", "MLIV": "MOL", "SIIV": "SIAM i"}


@app.get("/kb-payout/receipt", response_class=HTMLResponse)
def kb_receipt(request: Request, invs: str = ""):
    from services import doc_templates as dt
    from services.kb_payout import KB_OWNERS, KB_WHT

    inv_list = sorted({x.strip().upper() for x in invs.split(",") if x.strip()})
    if not inv_list:
        raise HTTPException(400, "ระบุ ?invs=เลขอินวอยคั่นด้วย ,")
    with Session(engine) as s:
        settles = s.exec(select(KbSettle).where(
            KbSettle.inv_no.in_(inv_list))).all()  # type: ignore[attr-defined]
        found = {x.inv_no for x in settles}
        missing = [i for i in inv_list if i not in found]
        if missing:
            raise HTTPException(400, f"ยังไม่ติ๊กรับ KB: {', '.join(missing)} — ติ๊กก่อนออกใบ")
        cust_keys = {_KB_PREFIX_CUSTOMER.get(i[:4], "?") for i in inv_list}
        if len(cust_keys) != 1 or "?" in cust_keys:
            raise HTTPException(400, "ชุดเดียวต้องเป็นเจ้าของงานรายเดียว (prefix อินวอยต้องชุดเดียวกัน)")
        owner = KB_OWNERS[cust_keys.pop()]

        kb_total = round(sum(x.kb_amount or 0 for x in settles), 2)
        wht = round(kb_total * KB_WHT, 2)
        transfer = round(kb_total * 0.9, 2)
        ref = ",".join(inv_list)
        u = current_user(request)
        by = u.username if u else ""
        no_receipt = dt.next_doc_no(s, "kb_receipt", ref, by=by)
        no_wht = dt.next_doc_no(s, "kb_wht", ref, by=by)
        today_th = date.today().strftime("%d/%m/%Y")
        ctx_receipt = {
            "doc_no": f"RC{no_receipt}", "doc_date": today_th,
            "payer_name": owner["owner"],
            "description": f"ค่าบริการดำเนินงานขนส่งตู้คอนเทนเนอร์ (KB) ชุดอินวอย {len(inv_list)} ใบ",
            "amount": f"{kb_total:,.2f}", "amount_text": dt.baht_text(kb_total),
            "invs": ", ".join(inv_list),
            "receiver_name": dt.COMPANY["name_en"],
            "note": f"โอนคืนเจ้าของงาน 90% = {transfer:,.2f} บาท ({owner['bank']})",
        }
        ctx_wht = {
            "doc_no": f"WT{no_wht}", "doc_date": today_th,
            "payee_name": owner["owner"],
            "payee_tax_id": "……………………………", "payee_address": "……………………………",
            "income_type": "ค่าบริการ/ค่านายหน้า (มาตรา 40(2))",
            "pay_date": today_th,
            "amount": f"{kb_total:,.2f}", "wht": f"{wht:,.2f}",
            "wht_text": dt.baht_text(wht),
        }
        pages = [
            {"title": "ใบเสร็จรับเงิน",
             "elements": dt.render_elements(dt.get_template(s, "kb_receipt"), ctx_receipt)},
            {"title": "หนังสือรับรองหัก ณ ที่จ่าย",
             "elements": dt.render_elements(dt.get_template(s, "kb_wht"), ctx_wht)},
        ]
    ctx = base_context(request)
    ctx.update({"pages": pages, "invs": invs})
    return templates.TemplateResponse(request, "doc_print.html", ctx)


@app.get("/admin/doc-designer", response_class=HTMLResponse)
def doc_designer(request: Request, key: str = "kb_receipt"):
    from services import doc_templates as dt

    if key not in dt.DEFAULT_TEMPLATES:
        raise HTTPException(404, "ไม่รู้จักฟอร์มนี้")
    with Session(engine) as s:
        tpl = dt.get_template(s, key)
        has_override = s.exec(select(models.DocTemplate)
                              .where(models.DocTemplate.key == key)).first() is not None
    ctx = base_context(request)
    ctx.update({"key": key, "tpl_name": tpl["name"],
                "elements_json": json.dumps(tpl["elements"], ensure_ascii=False),
                "placeholders": dt.PLACEHOLDER_DOC.get(key, ""),
                "all_keys": list(dt.DEFAULT_TEMPLATES),
                "has_override": has_override})
    return templates.TemplateResponse(request, "doc_designer.html", ctx)


@app.post("/admin/doc-designer/save")
async def doc_designer_save(request: Request):
    from services import doc_templates as dt

    payload = await request.json()
    key = str(payload.get("key") or "")
    elements = payload.get("elements")
    if key not in dt.DEFAULT_TEMPLATES:
        raise HTTPException(404, "ไม่รู้จักฟอร์มนี้")
    if not isinstance(elements, list):
        raise HTTPException(400, "elements ต้องเป็น list")
    u = current_user(request)
    with Session(engine) as s:
        row = s.exec(select(models.DocTemplate)
                     .where(models.DocTemplate.key == key)).first()
        if payload.get("reset"):
            if row:
                s.delete(row)
                audit_log(s, request, "doctemplate", row.id or 0, "reset", key, "default")
                s.commit()
            return JSONResponse({"ok": True, "reset": True})
        if row is None:
            row = models.DocTemplate(key=key, name=dt.DEFAULT_TEMPLATES[key]["name"])
        row.elements_json = json.dumps(elements, ensure_ascii=False)
        row.updated_by = u.username if u else ""
        row.updated_at = datetime.utcnow()
        s.add(row)
        audit_log(s, request, "doctemplate", row.id or 0, "layout", "", f"{len(elements)} ชิ้น", note=key)
        s.commit()
    return JSONResponse({"ok": True})


@app.get("/finance/vehicles", response_class=HTMLResponse)
def finance_vehicles(request: Request, month: str = "", site: str = ""):
    today = date.today()
    if not month:
        month = f"{today.year:04d}-{today.month:02d}"
    try:
        y, m = finance_svc.parse_month(month)
    except Exception:
        y, m = today.year, today.month
    with Session(engine) as s:
        rows = finance_svc.cost_per_vehicle(s, y, m, site)
        # D3: sparkline กำไรสุทธิ 6 เดือนย้อนหลัง (รวมเดือนที่ดู) ต่อคัน
        spark: dict[int, list[float]] = {}
        sy, sm = y, m
        hist: list[tuple[int, int]] = []
        for _ in range(6):
            hist.append((sy, sm))
            sy, sm = (sy, sm - 1) if sm > 1 else (sy - 1, 12)
        for hy, hm in reversed(hist):   # เก่า→ใหม่
            if (hy, hm) == (y, m):
                month_rows = rows
            else:
                month_rows = finance_svc.cost_per_vehicle(s, hy, hm, site)
            by_vid = {r["vehicle_id"]: r["net_margin"] for r in month_rows}
            for r in rows:
                spark.setdefault(r["vehicle_id"], []).append(
                    round(by_vid.get(r["vehicle_id"], 0.0)))
    for r in rows:
        r["spark"] = spark.get(r["vehicle_id"], [])
    totals = {
        "trips": sum(r["trips"] for r in rows),
        "revenue": sum(r["revenue"] for r in rows),
        "cost_fuel": sum(r["cost_fuel"] for r in rows),
        "cost_maint": sum(r["cost_maint"] for r in rows),
        "cost_driver": sum(r["cost_driver"] for r in rows),
        "cost_install": sum(r["cost_install"] for r in rows),
        "gross_margin": sum(r["gross_margin"] for r in rows),
        "net_margin": sum(r["net_margin"] for r in rows),
    }
    ctx = base_context(request)
    ctx.update({"month": month, "site": site, "rows": rows, "totals": totals})
    return templates.TemplateResponse(request, "finance_vehicles.html", ctx)


@app.get("/finance/revenue", response_class=HTMLResponse)
def finance_revenue(request: Request):
    """CFO รายได้ drill-down ไซต์→ลูกค้า→รถ. เลือกช่วงวันเอง (from/to ISO).
    ค่าเริ่มต้น = 30 วันล่าสุด. รายได้ = revenue_customer.
    อ่าน from/to/site จาก query_params (from/to เป็น reserved keyword ใน Python)."""
    today = date.today()
    # 'from'/'to' เป็น reserved-ish — รับผ่าน query params dict
    d_from = (request.query_params.get("from") or "").strip()
    d_to = (request.query_params.get("to") or "").strip()
    site = (request.query_params.get("site") or "").strip()
    start = _parse_date(d_from) or (today - timedelta(days=30))
    end = _parse_date(d_to) or today
    if start > end:
        start, end = end, start
    with Session(engine) as s:
        data = finance_svc.revenue_breakdown(s, start, end, site)
    ctx = base_context(request)
    ctx.update({
        "start": start, "end": end, "site": site,
        "sites": data["sites"], "totals": data["totals"],
        "has_other_sites": data["has_other_sites"],
    })
    return templates.TemplateResponse(request, "finance_revenue.html", ctx)


# D2: เงินหมุน/งบดุลย่อ 8 สัปดาห์ — เข้า (AR ตาม DUE จริงจากทะเบียนรับเช็ค) −
# ออก (เงินเดือนตามรอบ 3 ไซท์ + งวดหนี้ DebtAccount/Loan + petty/น้ำมันเฉลี่ย)
# มุมมองรายวันแบบเดิม (ค่าประมาณล้วน) ย้ายไป /finance/cashflow/daily
@app.get("/finance/cashflow", response_class=HTMLResponse)
def finance_cashflow_weeks(request: Request, opening: str = ""):
    from services import receivables as ar

    try:
        opening_f = float(opening.replace(",", "")) if opening.strip() else 0.0
    except ValueError:
        opening_f = 0.0
    ar_pending: list = []
    ar_error = None
    try:
        rows_ar, _missing = ar.load_all()
        with Session(engine) as s:
            settled_keys = {a.inv_key for a in s.exec(select(ArSettle)).all()}
        for r in rows_ar:
            key = f"{r['site']}:{r['inv']}" if r["inv"] else ""
            if key and key in settled_keys:
                r["received"] = True
        ar_pending = [r for r in rows_ar if not r["received"] and r["amount"] > 0]
    except Exception as e:
        ar_error = f"อ่านทะเบียนรับเช็คจาก Drive ไม่สำเร็จ: {e} — คอลัมน์เงินเข้าจะเป็น 0"
    with Session(engine) as s:
        data = finance_svc.weekly_cashflow(s, ar_pending, date.today(),
                                           opening=opening_f)
        n_debts = len(s.exec(select(models.DebtAccount)
                             .where(models.DebtAccount.active == True)).all())  # noqa: E712
    ctx = base_context(request)
    ctx.update({"data": data, "opening": opening, "ar_error": ar_error,
                "n_debts": n_debts, "today": date.today()})
    return templates.TemplateResponse(request, "finance_cashflow_weeks.html", ctx)


@app.get("/finance/debts", response_class=HTMLResponse)
def finance_debts(request: Request):
    """D2: หนี้/วงเงิน โอกรอกเอง (บัตรเครดิต/OD/เงินกู้ส่วนตัว/ไฟแนนซ์รถ)."""
    with Session(engine) as s:
        rows = s.exec(select(models.DebtAccount)
                      .order_by(models.DebtAccount.active.desc(),  # type: ignore[union-attr]
                                models.DebtAccount.due_day)).all()
    ctx = base_context(request)
    ctx.update({"rows": rows,
                "total_balance": sum(r.balance for r in rows if r.active),
                "total_monthly": sum(r.monthly_payment for r in rows if r.active)})
    return templates.TemplateResponse(request, "finance_debts.html", ctx)


@app.post("/finance/debts/save")
def finance_debts_save(request: Request, debt_id: str = Form(""),
                       name: str = Form(...), kind: str = Form("credit_card"),
                       credit_limit: str = Form("0"), balance: str = Form("0"),
                       interest_rate: str = Form("0"), statement_day: str = Form("0"),
                       due_day: str = Form("1"), monthly_payment: str = Form("0"),
                       plate: str = Form(""), note: str = Form("")):
    def _f(x):
        try:
            return float(str(x).replace(",", ""))
        except ValueError:
            return 0.0

    def _i(x, lo=0, hi=31):
        try:
            return min(hi, max(lo, int(x)))
        except ValueError:
            return lo

    with Session(engine) as s:
        d = s.get(models.DebtAccount, int(debt_id)) if debt_id.strip() else None
        if d is None:
            d = models.DebtAccount()
            audit_log(s, request, "debtaccount", 0, "create", "", name.strip())
        else:
            if d.balance != _f(balance):
                audit_log(s, request, "debtaccount", d.id, "balance",
                          d.balance, _f(balance), note=d.name)
            if d.monthly_payment != _f(monthly_payment):
                audit_log(s, request, "debtaccount", d.id, "monthly_payment",
                          d.monthly_payment, _f(monthly_payment), note=d.name)
        d.name = name.strip()
        d.kind = kind.strip() or "credit_card"
        d.credit_limit = _f(credit_limit)
        d.balance = _f(balance)
        d.interest_rate = _f(interest_rate)
        d.statement_day = _i(statement_day)
        d.due_day = _i(due_day, lo=1)
        d.monthly_payment = _f(monthly_payment)
        d.plate = plate.strip()
        d.note = note.strip()
        d.updated_at = datetime.utcnow()
        s.add(d)
        s.commit()
    return RedirectResponse("/finance/debts", status_code=303)


@app.post("/finance/debts/{debt_id}/toggle")
def finance_debts_toggle(debt_id: int, request: Request):
    """ปิด/เปิดบัญชีหนี้ (soft — ไม่ลบจริง เก็บประวัติ)."""
    with Session(engine) as s:
        d = s.get(models.DebtAccount, debt_id)
        if d:
            audit_log(s, request, "debtaccount", d.id, "active",
                      str(d.active), str(not d.active), note=d.name)
            d.active = not d.active
            d.updated_at = datetime.utcnow()
            s.add(d)
            s.commit()
    return RedirectResponse("/finance/debts", status_code=303)


@app.get("/finance/cashflow/daily", response_class=HTMLResponse)
def finance_cashflow(request: Request, days: int = 90):
    days = max(30, min(180, days))
    with Session(engine) as s:
        rows = finance_svc.cash_flow_projection(s, date.today(), days=days)

    # Compute running net
    running = 0.0
    for r in rows:
        if r["direction"] == "in":
            running += r["amount"]
        elif r["direction"] == "out":
            running -= r["amount"]
        r["running"] = running

    total_in = sum(r["amount"] for r in rows if r["direction"] == "in")
    total_out = sum(r["amount"] for r in rows if r["direction"] == "out")

    ctx = base_context(request)
    ctx.update({
        "rows": rows, "days": days,
        "total_in": total_in, "total_out": total_out,
        "net": total_in - total_out,
    })
    return templates.TemplateResponse(request, "finance_cashflow.html", ctx)


# ==========================================================================
# DRIVER PWA  (Phase 4 — Wave 1)
# Mobile-first pages: login / home / today's jobs / vehicle check / alcohol test
# ==========================================================================
from services import driver_auth as drv  # noqa: E402
import json as _json  # noqa: E402


def _driver_base_context(request: Request, emp: Optional[Employee]) -> dict:
    """Minimal context for mobile-facing driver templates (no office nav)."""
    return {
        "request": request,
        "emp": emp,
        "today": date.today().isoformat(),
        "now": datetime.now().strftime("%H:%M"),
        "check_items": models.VEHICLE_CHECK_ITEMS,
        "check_status_opts": models.VEHICLE_CHECK_STATUS,
    }


def _require_driver(request: Request, session: Session) -> Employee:
    """Return the current driver or raise redirect to login."""
    emp = drv.get_current_driver(request, session)
    if not emp:
        raise HTTPException(status_code=401, detail="unauthorized")
    return emp


@app.get("/driver/login", response_class=HTMLResponse)
def driver_login_page(request: Request, err: str = ""):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if emp:
            return RedirectResponse("/driver", status_code=303)
    ctx = _driver_base_context(request, None)
    ctx["err"] = err
    return templates.TemplateResponse(request, "driver_login.html", ctx)


@app.post("/driver/login")
def driver_login(
    request: Request,
    phone: str = Form(""),
    pin: str = Form(""),
):
    with Session(engine) as s:
        result = drv.attempt_login(s, phone, pin)
        if not result.ok:
            return RedirectResponse(f"/driver/login?err={result.error}", status_code=303)
        ua = request.headers.get("user-agent", "")
        token = drv.create_session(s, result.employee, device_info=ua)

    resp = RedirectResponse("/driver", status_code=303)
    drv.set_session_cookie(resp, token)
    return resp


@app.post("/driver/logout")
def driver_logout(request: Request):
    token = request.cookies.get(drv.COOKIE_NAME, "")
    if token:
        with Session(engine) as s:
            drv.revoke_session(s, token)
    resp = RedirectResponse("/driver/login", status_code=303)
    drv.clear_session_cookie(resp)
    return resp


@app.get("/driver", response_class=HTMLResponse)
def driver_home(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)

        # Today's jobs for this driver
        today = date.today()
        todays_jobs = s.exec(
            select(DailyJob).where(
                DailyJob.driver_id == emp.id,
                DailyJob.work_date == today,
            ).order_by(DailyJob.id)
        ).all()

        # Recent submissions (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_subs = s.exec(
            select(DriverSubmission).where(
                DriverSubmission.employee_id == emp.id,
                DriverSubmission.submitted_at >= week_ago,
            ).order_by(DriverSubmission.submitted_at.desc()).limit(20)
        ).all()

        # Did driver do today's vehicle check + alcohol?
        start_today = datetime.combine(today, datetime.min.time())
        done_check = s.exec(
            select(DriverSubmission).where(
                DriverSubmission.employee_id == emp.id,
                DriverSubmission.kind == "vehicle_check",
                DriverSubmission.submitted_at >= start_today,
            )
        ).first()
        done_alcohol = s.exec(
            select(DriverSubmission).where(
                DriverSubmission.employee_id == emp.id,
                DriverSubmission.kind == "alcohol_test",
                DriverSubmission.submitted_at >= start_today,
            )
        ).first()

    ctx = _driver_base_context(request, emp)
    ctx.update({
        "todays_jobs": todays_jobs,
        "recent_subs": recent_subs,
        "done_check": done_check is not None,
        "done_alcohol": done_alcohol is not None,
    })
    return templates.TemplateResponse(request, "driver_home.html", ctx)


@app.get("/driver/today", response_class=HTMLResponse)
def driver_today(request: Request, day: str = ""):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        wd = _parse_date(day) or date.today()
        jobs = s.exec(
            select(DailyJob).where(
                DailyJob.driver_id == emp.id,
                DailyJob.work_date == wd,
            ).order_by(DailyJob.id)
        ).all()
        # Also look ahead 7 days for planned jobs
        ahead = s.exec(
            select(DailyJob).where(
                DailyJob.driver_id == emp.id,
                DailyJob.work_date > wd,
                DailyJob.work_date <= wd + timedelta(days=7),
            ).order_by(DailyJob.work_date)
        ).all()

    ctx = _driver_base_context(request, emp)
    ctx.update({"wd": wd, "jobs": jobs, "ahead": ahead})
    return templates.TemplateResponse(request, "driver_today.html", ctx)


@app.get("/driver/check", response_class=HTMLResponse)
def driver_check_page(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        vehicles = s.exec(select(Vehicle).where(Vehicle.status == "active").order_by(Vehicle.plate_no)).all()
    ctx = _driver_base_context(request, emp)
    ctx["vehicles"] = vehicles
    return templates.TemplateResponse(request, "driver_check.html", ctx)


@app.post("/driver/check")
async def driver_check_submit(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)

        form = await request.form()
        vehicle_id = _parse_int(form.get("vehicle_id", ""))
        plate_raw = (form.get("plate_raw", "") or "").strip()
        gps_lat = _parse_float(form.get("gps_lat", "") or "0") or None
        gps_lng = _parse_float(form.get("gps_lng", "") or "0") or None
        gps_acc = _parse_float(form.get("gps_acc", "") or "0") or None
        note = (form.get("note", "") or "").strip()

        # Collect checklist answers
        answers = {}
        any_fail = False
        for item_key, _ in models.VEHICLE_CHECK_ITEMS:
            val = form.get(f"item_{item_key}", "ok")
            note_val = (form.get(f"note_{item_key}", "") or "").strip()
            answers[item_key] = {"status": val, "note": note_val}
            if val == "fail":
                any_fail = True

        # Optional photos
        photo_paths = []
        photos = form.getlist("photos") if hasattr(form, "getlist") else []
        for photo in photos:
            if hasattr(photo, "read"):
                data = await photo.read()
                if data and len(data) > 100:
                    rel = drv.save_photo(emp.id, "vehicle_check", data, ext="jpg")
                    photo_paths.append(rel)

        sub = DriverSubmission(
            employee_id=emp.id,
            kind="vehicle_check",
            vehicle_id=vehicle_id,
            plate_raw=plate_raw,
            gps_lat=gps_lat, gps_lng=gps_lng, gps_accuracy_m=gps_acc,
            photo_paths=",".join(photo_paths),
            data_json=_json.dumps({"items": answers, "note": note, "any_fail": any_fail}, ensure_ascii=False),
            device_info=request.headers.get("user-agent", "")[:200],
            review_status="flagged" if any_fail else "pending",
        )
        s.add(sub)
        s.commit()
        sub_id = sub.id
    return RedirectResponse(f"/driver?submitted=check#sub-{sub_id}", status_code=303)


@app.get("/driver/alcohol", response_class=HTMLResponse)
def driver_alcohol_page(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
    ctx = _driver_base_context(request, emp)
    return templates.TemplateResponse(request, "driver_alcohol.html", ctx)


@app.post("/driver/alcohol")
async def driver_alcohol_submit(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)

        form = await request.form()
        reading = (form.get("reading", "") or "").strip()
        gps_lat = _parse_float(form.get("gps_lat", "") or "0") or None
        gps_lng = _parse_float(form.get("gps_lng", "") or "0") or None
        gps_acc = _parse_float(form.get("gps_acc", "") or "0") or None
        note = (form.get("note", "") or "").strip()

        photo_paths = []
        photo = form.get("photo")
        if photo and hasattr(photo, "read"):
            data = await photo.read()
            if data and len(data) > 100:
                rel = drv.save_photo(emp.id, "alcohol_test", data, ext="jpg")
                photo_paths.append(rel)

        try:
            reading_val = float(reading) if reading else 0.0
        except ValueError:
            reading_val = 0.0
        flagged = reading_val > 0.0

        sub = DriverSubmission(
            employee_id=emp.id,
            kind="alcohol_test",
            gps_lat=gps_lat, gps_lng=gps_lng, gps_accuracy_m=gps_acc,
            photo_paths=",".join(photo_paths),
            data_json=_json.dumps({"reading": reading, "note": note}, ensure_ascii=False),
            device_info=request.headers.get("user-agent", "")[:200],
            review_status="flagged" if flagged else "pending",
        )
        s.add(sub)
        s.commit()
        sub_id = sub.id
    return RedirectResponse(f"/driver?submitted=alcohol#sub-{sub_id}", status_code=303)


# ---- E1: เช็คอิน 3 จุด + รูปตู้ 4 ด้าน + ปิดงาน (ย้ายของที่รกไลน์เข้าฟอร์ม) ----

def _driver_todays_jobs(s: Session, emp) -> list:
    return s.exec(select(DailyJob).where(
        DailyJob.driver_id == emp.id,
        DailyJob.work_date == date.today()).order_by(DailyJob.id)).all()


async def _driver_photos(form, emp_id: int, kind: str, field: str = "photos") -> list[str]:
    paths = []
    for photo in (form.getlist(field) if hasattr(form, "getlist") else []):
        if hasattr(photo, "read"):
            data = await photo.read()
            if data and len(data) > 100:
                paths.append(drv.save_photo(emp_id, kind, data, ext="jpg"))
    return paths


@app.get("/driver/checkin", response_class=HTMLResponse)
def driver_checkin_page(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        jobs = _driver_todays_jobs(s, emp)
    ctx = _driver_base_context(request, emp)
    ctx.update({"jobs": jobs, "points": models.CHECKIN_POINTS})
    return templates.TemplateResponse(request, "driver_checkin.html", ctx)


@app.post("/driver/checkin")
async def driver_checkin_submit(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        form = await request.form()
        point = (form.get("point", "") or "").strip()
        if point not in {k for k, _ in models.CHECKIN_POINTS}:
            raise HTTPException(400, "จุดเช็คอินไม่ถูกต้อง")
        job_id = _parse_int(form.get("daily_job_id", ""))
        photo_paths = await _driver_photos(form, emp.id, "checkin")
        sub = DriverSubmission(
            employee_id=emp.id, kind="checkin", daily_job_id=job_id,
            gps_lat=_parse_float(form.get("gps_lat", "") or "0") or None,
            gps_lng=_parse_float(form.get("gps_lng", "") or "0") or None,
            gps_accuracy_m=_parse_float(form.get("gps_acc", "") or "0") or None,
            photo_paths=",".join(photo_paths),
            data_json=_json.dumps({"point": point,
                                   "note": (form.get("note", "") or "").strip()},
                                  ensure_ascii=False),
            device_info=request.headers.get("user-agent", "")[:200],
        )
        s.add(sub)
        s.commit()
        sub_id = sub.id
    return RedirectResponse(f"/driver?submitted=checkin#sub-{sub_id}", status_code=303)


@app.get("/driver/container", response_class=HTMLResponse)
def driver_container_page(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        jobs = _driver_todays_jobs(s, emp)
    ctx = _driver_base_context(request, emp)
    ctx["jobs"] = jobs
    return templates.TemplateResponse(request, "driver_container.html", ctx)


_CONTAINER_SIDES = (("front", "หน้าตู้ (เห็นเบอร์ตู้)"), ("back", "หลังตู้/ประตู"),
                    ("left", "ข้างซ้าย"), ("right", "ข้างขวา"))


@app.post("/driver/container")
async def driver_container_submit(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        form = await request.form()
        job_id = _parse_int(form.get("daily_job_id", ""))
        sides: dict[str, str] = {}
        paths = []
        for side, _label in _CONTAINER_SIDES:
            photo = form.get(f"photo_{side}")
            if photo and hasattr(photo, "read"):
                data = await photo.read()
                if data and len(data) > 100:
                    rel = drv.save_photo(emp.id, "container_photo", data, ext="jpg")
                    sides[side] = rel
                    paths.append(rel)
        if not paths:
            raise HTTPException(400, "ต้องมีรูปอย่างน้อย 1 ด้าน")
        sub = DriverSubmission(
            employee_id=emp.id, kind="container_photo", daily_job_id=job_id,
            gps_lat=_parse_float(form.get("gps_lat", "") or "0") or None,
            gps_lng=_parse_float(form.get("gps_lng", "") or "0") or None,
            gps_accuracy_m=_parse_float(form.get("gps_acc", "") or "0") or None,
            photo_paths=",".join(paths),
            data_json=_json.dumps({"sides": sides,
                                   "container_no": (form.get("container_no", "") or "").strip(),
                                   "note": (form.get("note", "") or "").strip(),
                                   "complete_4_sides": len(sides) == 4},
                                  ensure_ascii=False),
            device_info=request.headers.get("user-agent", "")[:200],
            # ไม่ครบ 4 ด้าน = flagged ให้ออฟฟิศเห็นชัด (คนตัดสินเองว่ารับได้ไหม)
            review_status="pending" if len(sides) == 4 else "flagged",
        )
        s.add(sub)
        s.commit()
        sub_id = sub.id
    return RedirectResponse(f"/driver?submitted=container#sub-{sub_id}", status_code=303)


@app.get("/driver/done", response_class=HTMLResponse)
def driver_done_page(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        jobs = _driver_todays_jobs(s, emp)
    ctx = _driver_base_context(request, emp)
    ctx["jobs"] = jobs
    return templates.TemplateResponse(request, "driver_done.html", ctx)


@app.post("/driver/done")
async def driver_done_submit(request: Request):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        form = await request.form()
        job_id = _parse_int(form.get("daily_job_id", ""))
        photo_paths = await _driver_photos(form, emp.id, "job_done")
        sub = DriverSubmission(
            employee_id=emp.id, kind="job_done", daily_job_id=job_id,
            gps_lat=_parse_float(form.get("gps_lat", "") or "0") or None,
            gps_lng=_parse_float(form.get("gps_lng", "") or "0") or None,
            gps_accuracy_m=_parse_float(form.get("gps_acc", "") or "0") or None,
            photo_paths=",".join(photo_paths),
            data_json=_json.dumps({"note": (form.get("note", "") or "").strip()},
                                  ensure_ascii=False),
            device_info=request.headers.get("user-agent", "")[:200],
        )
        s.add(sub)
        s.commit()
        sub_id = sub.id
    return RedirectResponse(f"/driver?submitted=done#sub-{sub_id}", status_code=303)


@app.get("/driver/history", response_class=HTMLResponse)
def driver_history(request: Request, kind: str = ""):
    with Session(engine) as s:
        emp = drv.get_current_driver(request, s)
        if not emp:
            return RedirectResponse("/driver/login", status_code=303)
        stmt = select(DriverSubmission).where(DriverSubmission.employee_id == emp.id)
        if kind:
            stmt = stmt.where(DriverSubmission.kind == kind)
        subs = s.exec(stmt.order_by(DriverSubmission.submitted_at.desc()).limit(100)).all()

    ctx = _driver_base_context(request, emp)
    ctx.update({"subs": subs, "kind_filter": kind, "kinds": models.SUBMISSION_KINDS})
    return templates.TemplateResponse(request, "driver_history.html", ctx)


# --------------------------------------------------------------------------
# ADMIN — Driver PIN management + submissions review
# --------------------------------------------------------------------------

@app.get("/admin/drivers/pins", response_class=HTMLResponse)
def admin_driver_pins(request: Request):
    with Session(engine) as s:
        emps = s.exec(
            select(Employee).where(Employee.status == "active").order_by(Employee.full_name)
        ).all()
    ctx = base_context(request)
    ctx["emps"] = emps
    return templates.TemplateResponse(request, "admin_driver_pins.html", ctx)


@app.post("/admin/drivers/{emp_id:int}/set-pin")
def admin_set_driver_pin(emp_id: int, phone: str = Form(""), pin: str = Form("")):
    with Session(engine) as s:
        emp = s.get(Employee, emp_id)
        if not emp:
            raise HTTPException(404, "Employee not found")
        phone_norm = drv.normalize_phone(phone)
        if phone_norm:
            emp.phone = phone_norm
        if pin.strip():
            try:
                emp.pin_hash = drv.hash_pin(pin.strip())
                emp.pin_set_at = datetime.utcnow()
            except ValueError as e:
                raise HTTPException(400, str(e))
        emp.updated_at = datetime.utcnow()
        s.add(emp)
        # Revoke all existing sessions on PIN change
        for row in s.exec(select(DriverSession).where(DriverSession.employee_id == emp_id)).all():
            row.revoked = True
            s.add(row)
        s.commit()
    return RedirectResponse("/admin/drivers/pins", status_code=303)


@app.post("/admin/drivers/{emp_id:int}/clear-pin")
def admin_clear_driver_pin(emp_id: int):
    with Session(engine) as s:
        emp = s.get(Employee, emp_id)
        if not emp:
            raise HTTPException(404, "Employee not found")
        emp.pin_hash = ""
        emp.pin_set_at = None
        emp.updated_at = datetime.utcnow()
        s.add(emp)
        for row in s.exec(select(DriverSession).where(DriverSession.employee_id == emp_id)).all():
            row.revoked = True
            s.add(row)
        s.commit()
    return RedirectResponse("/admin/drivers/pins", status_code=303)


@app.get("/admin/submissions", response_class=HTMLResponse)
def admin_submissions(
    request: Request,
    driver_id: str = "",
    kind: str = "",
    review: str = "",
    day: str = "",
):
    with Session(engine) as s:
        stmt = select(DriverSubmission)
        did = _parse_int(driver_id)
        if did:
            stmt = stmt.where(DriverSubmission.employee_id == did)
        if kind:
            stmt = stmt.where(DriverSubmission.kind == kind)
        if review:
            stmt = stmt.where(DriverSubmission.review_status == review)
        if day:
            d = _parse_date(day)
            if d:
                d0 = datetime.combine(d, datetime.min.time())
                d1 = datetime.combine(d, datetime.max.time())
                stmt = stmt.where(DriverSubmission.submitted_at >= d0, DriverSubmission.submitted_at <= d1)
        subs = s.exec(stmt.order_by(DriverSubmission.submitted_at.desc()).limit(200)).all()
        emps = s.exec(select(Employee)).all()
        emp_map = {e.id: e for e in emps}
        vehicles = s.exec(select(Vehicle)).all()
        veh_map = {v.id: v for v in vehicles}

    # Parse data_json for display
    enriched = []
    for sub in subs:
        parsed = {}
        try:
            parsed = _json.loads(sub.data_json) if sub.data_json else {}
        except Exception:
            parsed = {}
        enriched.append({
            "sub": sub,
            "emp": emp_map.get(sub.employee_id),
            "vehicle": veh_map.get(sub.vehicle_id) if sub.vehicle_id else None,
            "data": parsed,
            "photos": [p for p in (sub.photo_paths or "").split(",") if p],
        })

    ctx = base_context(request)
    ctx.update({
        "rows": enriched,
        "driver_id": driver_id, "kind_filter": kind, "review_filter": review, "day": day,
        "emps": sorted([e for e in emps if e.status == "active"], key=lambda x: x.full_name),
        "kinds": models.SUBMISSION_KINDS,
        "review_statuses": models.REVIEW_STATUS,
    })
    return templates.TemplateResponse(request, "admin_submissions.html", ctx)


@app.post("/admin/submissions/{sub_id:int}/review")
def admin_submission_review(
    sub_id: int,
    status: str = Form("approved"),
    note: str = Form(""),
    reviewer: str = Form(""),
):
    with Session(engine) as s:
        sub = s.get(DriverSubmission, sub_id)
        if not sub:
            raise HTTPException(404, "Submission not found")
        sub.review_status = status
        sub.review_note = note.strip()
        sub.reviewed_by = reviewer.strip() or "admin"
        sub.reviewed_at = datetime.utcnow()
        s.add(sub)
        s.commit()
    return RedirectResponse("/admin/submissions", status_code=303)


def _find_free_port(start: int = 8010, count: int = 30, bind_host: str = "127.0.0.1") -> int:
    """Return first port where we can *actually listen* on bind_host.

    On Windows a plain bind() can succeed even if another process has the port
    with different SO_REUSEADDR flags. We force SO_EXCLUSIVEADDRUSE (same as
    uvicorn) + listen() so we test the exact same thing uvicorn will do.
    """
    import socket
    for port in range(start, start + count):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Match uvicorn's behaviour on Windows
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                except OSError:
                    pass
            sock.bind((bind_host, port))
            sock.listen(1)
            return port
        except OSError:
            continue
        finally:
            try:
                sock.close()
            except OSError:
                pass
    return start


def _primary_lan_ipv4() -> str:
    """Best-effort LAN IPv4 for printing (not loopback)."""
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        finally:
            s.close()
    except OSError:
        pass
    try:
        hostname = socket.gethostname()
        for _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = sockaddr[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return ""


def _open_browser_when_ready(port: int, path: str = "/daily", delay: float = 1.5) -> None:
    """Open the default browser once uvicorn has had a moment to bind."""
    import threading
    import webbrowser

    def _launch() -> None:
        try:
            webbrowser.open_new(f"http://127.0.0.1:{port}{path}")
        except Exception:  # pragma: no cover — browser opening is best-effort
            pass

    threading.Timer(delay, _launch).start()


# ==========================================================================
# IMPORT WIZARD  (/import)
# Web UI for uploading Excel files and importing Daily, PettyCash, Fuel, etc.
# ==========================================================================
from services import import_wizard as iwiz  # noqa: E402


@app.get("/import")
async def import_hub(request: Request):
    with Session(engine) as s:
        logs = s.exec(
            select(ImportLog).order_by(ImportLog.created_at.desc()).limit(50)  # type: ignore[arg-type]
        ).all()
    return templates.TemplateResponse(request, "import_hub.html", {
        "request": request,
        "logs": logs,
    })


@app.post("/import/sheets")
async def import_sheets(
    file: UploadFile = File(...),
):
    """Step 1: receive file, return sheet picker HTML fragment."""
    from html import escape as _esc
    data = await file.read()
    raw_name = file.filename or "upload.xlsx"
    temp_id = iwiz.save_upload(data, raw_name)
    try:
        sheets = iwiz.read_sheets(temp_id)
    except Exception:
        return HTMLResponse(
            '<div class="mt-4 text-red-600 text-sm">อ่านไฟล์ไม่ได้ — '
            'กรุณาอัปโหลดไฟล์ Excel (.xlsx) ที่ถูกต้อง</div>',
            status_code=400,
        )
    # Escape every value interpolated into HTML (filename + sheet names are
    # attacker-influenced). temp_id is a UUID hex so it's safe, but escape anyway.
    options = "".join(
        f'<option value="{_esc(s)}">{_esc(s)}</option>' for s in sheets
    )
    html = f"""
<div id="sheet-picker" class="mt-4 space-y-3">
  <input type="hidden" name="temp_id" value="{_esc(temp_id)}">
  <input type="hidden" name="file_name" value="{_esc(raw_name)}">
  <div>
    <label class="block text-sm font-medium text-gray-700 mb-1">เลือก Sheet</label>
    <select name="sheet_name" class="border rounded px-3 py-2 w-full"
            hx-post="/import/preview"
            hx-include="#import-form"
            hx-target="#preview-area"
            hx-trigger="change">
      <option value="">— เลือก Sheet —</option>
      {options}
    </select>
  </div>
</div>
"""
    return HTMLResponse(html)


@app.post("/import/preview")
async def import_preview(
    temp_id: str = Form(...),
    sheet_name: str = Form(...),
    file_name: str = Form(""),
    import_type: str = Form("daily"),
):
    """Step 2: show first 8 rows + type-specific config fields."""
    headers, rows = iwiz.preview_rows(temp_id, sheet_name, max_rows=8)
    if not headers:
        return HTMLResponse('<p class="text-red-600">ไม่พบข้อมูลในชีทนี้</p>')

    th = "".join(f"<th class='px-2 py-1 border text-xs'>{h}</th>" for h in headers[:20])
    tbody = ""
    for r in rows:
        tds = "".join(f"<td class='px-2 py-1 border text-xs'>{c}</td>" for c in r[:20])
        tbody += f"<tr>{tds}</tr>"

    site_select = """
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">ไซท์ (default)</label>
      <select name="site_code" class="border rounded px-3 py-2 w-full">
        <option value="LCB">LCB</option>
        <option value="AYU">AYU</option>
        <option value="BIGC">BIGC</option>
      </select>
    </div>"""

    if import_type == "daily":
        extra_fields = site_select + """
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">วันเริ่มรอบ (กรอง work_date)</label>
      <input type="date" name="cycle_start" class="border rounded px-3 py-2 w-full">
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">วันสิ้นรอบ (กรอง work_date)</label>
      <input type="date" name="cycle_end" class="border rounded px-3 py-2 w-full">
    </div>"""
        hint = """<p class="text-xs text-gray-600">ตัวอย่าง LCB ม.ค. 2026 (รอบ 16–15):
          <code>2025-12-16</code> ถึง <code>2026-01-15</code></p>"""
    elif import_type == "employee":
        extra_fields = site_select + """
    <div class="col-span-1">
      <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 mt-1">
        ชนะชน (code ซ้ำ) → ข้ามแถวนั้น ไม่ merge อัตโนมัติ — ดูรายการ conflicts ในผลลัพธ์
      </p>
    </div>"""
        hint = """<p class="text-xs text-gray-600">หัว column ที่รู้จัก: code/รหัส, full_name/ชื่อ-สกุล,
          nickname/ชื่อเล่น, phone/เบอร์โทร, id_card/เลขบัตร, site_code/ไซท์,
          start_date/วันเริ่มงาน, role/ตำแหน่ง, pay_mode, base_salary/เงินเดือน</p>"""
    elif import_type == "vehicle":
        extra_fields = site_select + """
    <div class="col-span-1">
      <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 mt-1">
        ทะเบียนซ้ำ → ข้ามแถวนั้น ไม่อัพเดทอัตโนมัติ — ดูรายการ conflicts ในผลลัพธ์
      </p>
    </div>"""
        hint = """<p class="text-xs text-gray-600">หัว column ที่รู้จัก: plate_no/ทะเบียน,
          vehicle_kind/ประเภท, truck_type/ชนิดรถ, site_code/ไซท์, nickname/ชื่อเล่น,
          brand/ยี่ห้อ, model/รุ่น, engine_no/เลขเครื่อง, chassis_no/เลขถัง</p>"""
    else:
        extra_fields = site_select
        hint = ""

    html = f"""
<div id="preview-area" class="mt-4 space-y-4">
  <div class="overflow-x-auto border rounded">
    <table class="text-left w-max">
      <thead class="bg-gray-100"><tr>{th}</tr></thead>
      <tbody>{tbody}</tbody>
    </table>
  </div>
  <div class="grid grid-cols-2 gap-3">
    {extra_fields}
  </div>
  {hint}
  <div class="flex gap-3">
    <button type="button"
            hx-post="/import/run"
            hx-include="#import-form"
            hx-target="#result-area"
            hx-vals='{{"dry_run":"1"}}'
            class="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600">
      Dry Run
    </button>
    <button type="button"
            hx-post="/import/run"
            hx-include="#import-form"
            hx-target="#result-area"
            hx-confirm="นำเข้าข้อมูลจริง — ยืนยัน?"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
      Import จริง
    </button>
  </div>
  <div id="result-area"></div>
</div>
"""
    return HTMLResponse(html)


@app.post("/import/run")
async def import_run(
    temp_id: str = Form(...),
    sheet_name: str = Form(...),
    file_name: str = Form(""),
    site_code: str = Form("LCB"),
    import_type: str = Form("daily"),
    cycle_start: str = Form(""),
    cycle_end: str = Form(""),
    dry_run: str = Form("0"),
):
    from datetime import date as _date_cls

    is_dry = dry_run not in ("0", "", "false", "False")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M")
    source_tag = f"{site_code.lower()}_{import_type}_{ts}_{temp_id[:6]}"

    try:
        with Session(engine) as s:
            if import_type == "daily":
                try:
                    cs = _date_cls.fromisoformat(cycle_start)
                    ce = _date_cls.fromisoformat(cycle_end)
                except ValueError:
                    return HTMLResponse('<p class="text-red-600">วันที่ไม่ถูกต้อง กรุณาใส่ วันเริ่มรอบ และ วันสิ้นรอบ</p>')
                if cs > ce:
                    return HTMLResponse('<p class="text-red-600">วันเริ่มรอบต้องไม่เกินวันสิ้นรอบ</p>')
                log = iwiz.import_daily(
                    session=s, temp_id=temp_id, sheet_name=sheet_name,
                    site_code=site_code, cycle_start=cs, cycle_end=ce,
                    source_tag=source_tag, file_name=file_name, dry_run=is_dry,
                )
            elif import_type == "employee":
                log = iwiz.import_employees(
                    session=s, temp_id=temp_id, sheet_name=sheet_name,
                    default_site=site_code, source_tag=source_tag,
                    file_name=file_name, dry_run=is_dry,
                )
            elif import_type == "vehicle":
                log = iwiz.import_vehicles(
                    session=s, temp_id=temp_id, sheet_name=sheet_name,
                    default_site=site_code, source_tag=source_tag,
                    file_name=file_name, dry_run=is_dry,
                )
            else:
                return HTMLResponse(f'<p class="text-red-600">ประเภท import ไม่รองรับ: {import_type}</p>')
    except Exception as exc:
        return HTMLResponse(f'<p class="text-red-600">เกิดข้อผิดพลาด: {exc}</p>')

    color = "yellow" if is_dry else "green"
    label = "Dry Run" if is_dry else "Import สำเร็จ"

    stat_rows = f"<li>แถว: <strong>{log.row_count}</strong></li>"
    if log.fee_count:
        stat_rows += f"<li>Fees: <strong>{log.fee_count}</strong></li>"
    if log.fuel_count:
        stat_rows += f"<li>Fuel: <strong>{log.fuel_count}</strong></li>"

    rollback_btn = ""
    if not is_dry and log.id and import_type == "daily":
        rollback_btn = f"""
<button hx-post="/import/{log.id}/rollback"
        hx-target="#result-area"
        hx-confirm="ย้อนกลับ import นี้?"
        class="mt-2 px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600">
  Rollback
</button>"""

    html = f"""
<div class="mt-3 p-4 bg-{color}-50 border border-{color}-300 rounded">
  <p class="font-semibold text-{color}-800">{label} — {import_type}</p>
  <ul class="text-sm mt-1 space-y-0.5">
    {stat_rows}
    <li class="text-gray-500 text-xs break-all">{log.note}</li>
  </ul>
  {rollback_btn}
</div>
"""
    resp = HTMLResponse(html)
    resp.headers["HX-Trigger"] = "refreshHistory"
    return resp


@app.post("/import/{log_id}/rollback")
async def import_rollback(request: Request, log_id: int):
    with Session(engine) as s:
        iwiz.rollback_import(s, log_id)
        logs = s.exec(
            select(ImportLog).order_by(ImportLog.created_at.desc()).limit(50)  # type: ignore[arg-type]
        ).all()
    return templates.TemplateResponse(request, "import_history_rows.html", {
        "request": request,
        "logs": logs,
    })


@app.get("/import/history-partial")
async def import_history_partial(request: Request):
    with Session(engine) as s:
        logs = s.exec(
            select(ImportLog).order_by(ImportLog.created_at.desc()).limit(50)  # type: ignore[arg-type]
        ).all()
    return templates.TemplateResponse(request, "import_history_rows.html", {
        "request": request,
        "logs": logs,
    })


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH PLANNER
# ─────────────────────────────────────────────────────────────────────────────

_DISPATCH_L_PER_TRIP: dict[str, float] = {
    "KAO": 50.0,
    "Conti": 50.0,
    "Haier": 100.0,
    "Lacation": 50.0,
    "KATOEN": 40.0,
    "คลังวาฬ": 25.0,
    "ฟรีโซน": 25.0,
    "เหรินเหอ": 70.0,
    "Oatside": 110.0,
}

_DISPATCH_JOB_TYPES = [
    "Haier", "KAO", "Conti", "Lacation", "KATOEN",
    "คลังวาฬ", "ฟรีโซน", "เหรินเหอ", "Oatside", "อื่นๆ",
]

_DISPATCH_SITES = ["LCB", "BIGC", "AYU"]


def _dispatch_gen_line_message(plan: DispatchPlan, lines: list[DispatchPlanLine],
                                vehicles: dict, drivers: dict) -> str:
    d = plan.plan_date
    date_str = f"{d.day:02d}/{d.month:02d}/{str(d.year)[2:]}"
    total = len([l for l in lines if l.vehicle_id or l.plate_raw])

    by_job: dict[str, list[DispatchPlanLine]] = {}
    for line in lines:
        by_job.setdefault(line.job_type or "อื่นๆ", []).append(line)

    parts = [f"📋 แผนงาน {plan.site_code} วันที่ {date_str}", f"รวม {total} คัน", ""]

    job_order = _DISPATCH_JOB_TYPES
    for jt in job_order:
        grp = by_job.get(jt, [])
        if not grp:
            continue
        lpt = _DISPATCH_L_PER_TRIP.get(jt, 0)
        fuel_note = f" ({int(lpt)} L/เที่ยว)" if lpt else ""
        parts.append(f"🚛 {jt}{fuel_note}")
        for line in grp:
            plate = vehicles.get(line.vehicle_id, {}).get("plate", line.plate_raw) if line.vehicle_id else line.plate_raw
            drv = drivers.get(line.driver_id, {}).get("name", line.driver_raw) if line.driver_id else line.driver_raw
            trips_str = f"{line.trips} เที่ยว" if line.trips else ""
            fuel_str = f"({int(line.fuel_liters)} L)" if line.fuel_liters else ""
            container_str = f"ตู้: {line.container_no}" if line.container_no else ""
            detail = " — ".join(x for x in [plate, drv, trips_str, fuel_str, container_str] if x)
            parts.append(detail)
        parts.append("")

    if plan.notes:
        parts.append(f"หมายเหตุ: {plan.notes}")

    return "\n".join(parts).strip()


@app.get("/dispatch/planner", response_class=HTMLResponse)
def dispatch_planner_list(request: Request, site: str = ""):
    with Session(engine) as s:
        q = select(DispatchPlan).order_by(DispatchPlan.plan_date.desc())  # type: ignore[arg-type]
        if site:
            q = q.where(DispatchPlan.site_code == site.upper())
        plans = s.exec(q).all()
    ctx = base_context(request)
    ctx.update({"plans": plans, "site": site, "sites": _DISPATCH_SITES})
    return templates.TemplateResponse(request, "dispatch_planner_list.html", ctx)


@app.get("/dispatch/planner/new", response_class=HTMLResponse)
def dispatch_planner_new_form(request: Request, site: str = "LCB", plan_date: str = ""):
    with Session(engine) as s:
        employees, vehicles, _ = _load_masters(s)
    ctx = base_context(request)
    ctx.update({
        "default_date": _parse_date(plan_date),
        "plan": None,
        "lines": [],
        "employees": employees,
        "vehicles": vehicles,
        "customers": [],
        "job_types": _DISPATCH_JOB_TYPES,
        "sites": _DISPATCH_SITES,
        "default_site": site.upper(),
        "l_per_trip_json": json.dumps(_DISPATCH_L_PER_TRIP),
    })
    return templates.TemplateResponse(request, "dispatch_planner_form.html", ctx)


@app.post("/dispatch/planner/new")
def dispatch_planner_create(
    request: Request,
    plan_date: str = Form(...),
    site_code: str = Form("LCB"),
    created_by: str = Form(""),
    notes: str = Form(""),
):
    pd_ = _parse_date(plan_date)
    if not pd_:
        raise HTTPException(400, "plan_date invalid")
    with Session(engine) as s:
        plan = DispatchPlan(
            plan_date=pd_,
            site_code=site_code.strip().upper(),
            created_by=created_by.strip(),
            notes=notes.strip(),
        )
        s.add(plan)
        s.commit()
        s.refresh(plan)
        plan_id = plan.id
    return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)


@app.get("/dispatch/planner/{plan_id}", response_class=HTMLResponse)
def dispatch_planner_detail(plan_id: int, request: Request):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        if not plan:
            raise HTTPException(404)
        lines = s.exec(
            select(DispatchPlanLine)
            .where(DispatchPlanLine.plan_id == plan_id)
            .order_by(DispatchPlanLine.seq, DispatchPlanLine.id)  # type: ignore[arg-type]
        ).all()
        audits = s.exec(
            select(DispatchPlanAudit)
            .where(DispatchPlanAudit.plan_id == plan_id)
            .order_by(DispatchPlanAudit.changed_at.desc())  # type: ignore[arg-type]
            .limit(50)
        ).all()
        employees, vehicles_list, _ = _load_masters(s)
        veh_map = {v.id: {"plate": v.plate_no, "nickname": v.nickname} for v in vehicles_list}
        drv_map = {e.id: {"name": e.full_name, "nickname": e.nickname} for e in employees}

        line_message = _dispatch_gen_line_message(plan, list(lines), veh_map, drv_map)

    ctx = base_context(request)
    ctx.update({
        "plan": plan,
        "lines": lines,
        "audits": audits,
        "employees": employees,
        "vehicles": vehicles_list,
        "job_types": _DISPATCH_JOB_TYPES,
        "l_per_trip_json": json.dumps(_DISPATCH_L_PER_TRIP),
        "line_message": line_message,
        "veh_map": veh_map,
        "drv_map": drv_map,
    })
    return templates.TemplateResponse(request, "dispatch_planner_detail.html", ctx)


@app.post("/dispatch/planner/{plan_id}/lines/add")
def dispatch_planner_add_line(
    plan_id: int,
    vehicle_id: str = Form(""),
    plate_raw: str = Form(""),
    driver_id: str = Form(""),
    driver_raw: str = Form(""),
    job_type: str = Form(""),
    trips: str = Form("1"),
    container_no: str = Form(""),
    notes_line: str = Form(""),
):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        if not plan:
            raise HTTPException(404)
        if plan.status == "submitted":
            raise HTTPException(400, "แผนนี้ submit แล้ว ไม่สามารถเพิ่มบรรทัดได้")
        trips_int = max(1, _parse_int(trips) or 1)
        lpt = _DISPATCH_L_PER_TRIP.get(job_type, 0.0)
        fuel = lpt * trips_int

        existing = s.exec(
            select(DispatchPlanLine).where(DispatchPlanLine.plan_id == plan_id)
        ).all()
        next_seq = max((l.seq for l in existing), default=0) + 1

        line = DispatchPlanLine(
            plan_id=plan_id,
            seq=next_seq,
            vehicle_id=_parse_int(vehicle_id),
            plate_raw=plate_raw.strip(),
            driver_id=_parse_int(driver_id),
            driver_raw=driver_raw.strip(),
            job_type=job_type.strip(),
            trips=trips_int,
            fuel_liters=fuel,
            container_no=container_no.strip(),
            notes=notes_line.strip(),
        )
        s.add(line)
        s.commit()
        s.refresh(line)

        audit = DispatchPlanAudit(
            plan_id=plan_id,
            line_id=line.id,
            action="add_line",
            new_value=f"{line.plate_raw or line.vehicle_id} | {line.job_type} | {line.trips} เที่ยว",
        )
        s.add(audit)
        plan.updated_at = datetime.utcnow()
        s.add(plan)
        s.commit()
    return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)


@app.post("/dispatch/planner/{plan_id}/lines/{line_id}/edit")
def dispatch_planner_edit_line(
    plan_id: int,
    line_id: int,
    vehicle_id: str = Form(""),
    plate_raw: str = Form(""),
    driver_id: str = Form(""),
    driver_raw: str = Form(""),
    job_type: str = Form(""),
    trips: str = Form("1"),
    container_no: str = Form(""),
    notes_line: str = Form(""),
    edit_reason: str = Form(""),
):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        line = s.get(DispatchPlanLine, line_id)
        if not plan or not line or line.plan_id != plan_id:
            raise HTTPException(404)
        if plan.status == "submitted" and not edit_reason.strip():
            raise HTTPException(400, "แผนนี้ submit แล้ว — ต้องระบุเหตุผลแก้ไข")

        old_snapshot = f"{line.plate_raw or line.vehicle_id} | {line.job_type} | {line.trips} เที่ยว"
        trips_int = max(1, _parse_int(trips) or 1)
        lpt = _DISPATCH_L_PER_TRIP.get(job_type, 0.0)

        line.vehicle_id = _parse_int(vehicle_id)
        line.plate_raw = plate_raw.strip()
        line.driver_id = _parse_int(driver_id)
        line.driver_raw = driver_raw.strip()
        line.job_type = job_type.strip()
        line.trips = trips_int
        line.fuel_liters = lpt * trips_int
        line.container_no = container_no.strip()
        line.notes = notes_line.strip()
        s.add(line)

        new_snapshot = f"{line.plate_raw or line.vehicle_id} | {line.job_type} | {line.trips} เที่ยว"
        audit = DispatchPlanAudit(
            plan_id=plan_id,
            line_id=line_id,
            action="edit_line",
            old_value=old_snapshot,
            new_value=new_snapshot,
            note=edit_reason.strip(),
        )
        s.add(audit)
        plan.updated_at = datetime.utcnow()
        s.add(plan)
        s.commit()
    return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)


@app.post("/dispatch/planner/{plan_id}/lines/{line_id}/delete")
def dispatch_planner_delete_line(
    plan_id: int,
    line_id: int,
    delete_reason: str = Form(""),
):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        line = s.get(DispatchPlanLine, line_id)
        if not plan or not line or line.plan_id != plan_id:
            raise HTTPException(404)
        if plan.status == "submitted":
            raise HTTPException(400, "แผนนี้ submit แล้ว ต้องระบุเหตุผลแก้ไข")

        snapshot = f"{line.plate_raw or line.vehicle_id} | {line.job_type} | {line.trips} เที่ยว"
        s.delete(line)

        audit = DispatchPlanAudit(
            plan_id=plan_id,
            line_id=line_id,
            action="delete_line",
            old_value=snapshot,
            note=delete_reason.strip(),
        )
        s.add(audit)
        plan.updated_at = datetime.utcnow()
        s.add(plan)
        s.commit()
    return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)


@app.post("/dispatch/planner/{plan_id}/submit")
def dispatch_planner_submit(plan_id: int):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        if not plan:
            raise HTTPException(404)
        if plan.status == "submitted":
            return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)

        lines = s.exec(
            select(DispatchPlanLine)
            .where(DispatchPlanLine.plan_id == plan_id)
            .order_by(DispatchPlanLine.seq)  # type: ignore[arg-type]
        ).all()

        for line in lines:
            if line.daily_job_id:
                continue
            job = DailyJob(
                work_date=plan.plan_date,
                site_code=plan.site_code,
                driver_id=line.driver_id,
                driver_raw_name=line.driver_raw,
                head_vehicle_id=line.vehicle_id,
                plate_no_raw=line.plate_raw,
                customer_name_raw=line.job_type,
                trip_type_code="dispatch",
                status_code="planned",
                fuel_liter=line.fuel_liters,
                remark=line.notes,
                source="dispatch_planner",
            )
            s.add(job)
            s.flush()
            line.daily_job_id = job.id
            s.add(line)

        plan.status = "submitted"
        plan.submitted_at = datetime.utcnow()
        plan.updated_at = datetime.utcnow()
        s.add(plan)

        audit = DispatchPlanAudit(
            plan_id=plan_id,
            action="submit",
            new_value=f"submitted {len(lines)} lines → DailyJob",
        )
        s.add(audit)
        s.commit()
    return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)


@app.post("/dispatch/planner/{plan_id}/reopen")
def dispatch_planner_reopen(plan_id: int, reopen_reason: str = Form("")):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        if not plan:
            raise HTTPException(404)
        plan.status = "draft"
        plan.updated_at = datetime.utcnow()
        s.add(plan)
        audit = DispatchPlanAudit(
            plan_id=plan_id,
            action="reopen",
            note=reopen_reason.strip(),
        )
        s.add(audit)
        s.commit()
    return RedirectResponse(url=f"/dispatch/planner/{plan_id}", status_code=303)


# ---------------------------------------------------------------------------
# B4: ปฏิทินกำลังรถ /calendar — ต่อวัน: รถทั้งหมด − จอง/วิ่งจริง − ซ่อมค้าง − คนลา
# display/planning เท่านั้น ไม่แตะเงิน. วันลามาจาก 2 ทาง: LeaveRecord (ลงจากปฏิทิน)
# + อ่านสดจากเดลี่ (leave_status / "ลาหยุด" ใน destination ที่ทีมคีย์อยู่แล้ว)
# ---------------------------------------------------------------------------

_TH_MONTH_FULL = ("", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม",
                  "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม",
                  "พฤศจิกายน", "ธันวาคม")


def _daily_row_kind(r) -> str:
    """แยกชนิดแถวเดลี่ (ตรรกะเดียวกับ payroll _count_work_days — ใช้ร่วม
    ปฏิทินรถ B4 + เช็คก่อนวางบิล C1): 'job' วิ่งงาน / 'idle' รถจอด-รองาน /
    'leave' ลา-ขาด-ป่วย / 'repair' ซ่อม-อุบัติเหตุ."""
    stat_blob = f"{r.status_code or ''} {r.leave_status or ''}".strip().lower()
    toks = {t for t in re.split(r"[\s/,;()\[\]\-_.]+", stat_blob) if t}
    if (
        bool((r.leave_status or "").strip())
        or "ลาหยุด" in (r.destination or "")
        or toks & {"ลา", "ขาด", "ป่วย", "ลากิจ", "ลาป่วย", "หยุด", "leave"}
    ):
        return "leave"
    if "ซ่อม" in stat_blob or "อุบัติเหตุ" in stat_blob:
        return "repair"
    if toks & {"รถจอด", "รองาน", "ไม่มีงาน", "idle"}:
        return "idle"
    return "job"


def _cal_month_bounds(month: str) -> tuple[date, date]:
    from calendar import monthrange
    try:
        y_s, m_s = month.split("-")
        first = date(int(y_s), int(m_s), 1)
    except (ValueError, AttributeError):
        first = date.today().replace(day=1)
    return first, first.replace(day=monthrange(first.year, first.month)[1])


@app.get("/calendar", response_class=HTMLResponse)
def fleet_calendar(request: Request, site: str = "LCB", month: str = ""):
    site = (site or "LCB").strip().upper()
    if site not in models.SITE_CODES:
        site = "LCB"
    first, last = _cal_month_bounds(month)
    today_d = date.today()

    with Session(engine) as s:
        vehicles = s.exec(
            select(Vehicle)
            .where(
                Vehicle.home_site_code == site,
                Vehicle.status == "active",
                Vehicle.vehicle_kind.in_(("truck", "head")),  # type: ignore[attr-defined]
            )
            .order_by(Vehicle.plate_no)  # type: ignore[arg-type]
        ).all()
        vids = {v.id for v in vehicles}
        vlabel = {v.id: v.plate_no + (f" ({v.nickname})" if v.nickname else "")
                  for v in vehicles}
        # เดลี่จริงส่วนใหญ่ไม่มี head_vehicle_id (ผูกด้วยข้อความทะเบียน) — match เอง
        plate2vid = {v.plate_no.strip(): v.id for v in vehicles}
        plate2vid.update({v.old_plate_no.strip(): v.id for v in vehicles
                          if len((v.old_plate_no or "").strip()) > 3})

        plan_rows = s.exec(
            select(DispatchPlan, DispatchPlanLine)
            .join(DispatchPlanLine, DispatchPlanLine.plan_id == DispatchPlan.id)
            .where(
                DispatchPlan.site_code == site,
                DispatchPlan.plan_date >= first,
                DispatchPlan.plan_date <= last,
            )
        ).all()
        djs = s.exec(
            select(DailyJob).where(
                DailyJob.site_code == site,
                DailyJob.work_date >= first,
                DailyJob.work_date <= last,
            )
        ).all()
        maints = s.exec(
            select(MaintRecord).where(
                MaintRecord.status == "in_progress",
                MaintRecord.work_date <= last,
                MaintRecord.vehicle_id.in_(vids),  # type: ignore[union-attr]
            )
        ).all() if vids else []
        leave_rows = s.exec(
            select(LeaveRecord, Employee)
            .join(Employee, Employee.id == LeaveRecord.driver_id)
            .where(
                LeaveRecord.leave_date >= first,
                LeaveRecord.leave_date <= last,
                Employee.home_site_code == site,
            )
        ).all()
        drivers = s.exec(
            select(Employee)
            .where(Employee.home_site_code == site, Employee.status == "active")
            .order_by(Employee.full_name)  # type: ignore[arg-type]
        ).all()

    # --- จอง/วิ่งจริง: set ต่อวัน key = vehicle_id (รถใน master) — plan กับเดลี่คันเดียวกันนับครั้งเดียว
    busy: dict[date, set[int]] = {}
    busy_detail: dict[date, list[dict]] = {}
    seen_busy: set[tuple[date, object]] = set()

    def _add_busy(d: date, vehicle_id, plate_raw: str, job: str, driver: str, src: str):
        if vehicle_id not in vids:
            vehicle_id = plate2vid.get((plate_raw or "").strip())
        key = vehicle_id if vehicle_id in vids else f"p:{(plate_raw or '').strip()}"
        if (d, key) in seen_busy:
            return
        seen_busy.add((d, key))
        if vehicle_id in vids:
            busy.setdefault(d, set()).add(vehicle_id)
            plate = vlabel[vehicle_id]
        else:
            plate = (plate_raw or "").strip() or "?"
            src += " (ทะเบียนไม่อยู่ใน master — ไม่หักจากรถว่าง)"
        busy_detail.setdefault(d, []).append(
            {"plate": plate, "job": job, "driver": driver, "src": src})

    for plan, line in plan_rows:
        _add_busy(plan.plan_date, line.vehicle_id, line.plate_raw,
                  line.job_type, line.driver_raw, "แผนงาน")
    _daily_leave: dict[date, list[dict]] = {}
    daily_repair: dict[date, dict[int, str]] = {}   # d -> {vehicle_id: เหตุ}
    for r in djs:
        kind = _daily_row_kind(r)
        if kind == "leave":
            _daily_leave.setdefault(r.work_date, []).append({
                "driver_id": r.driver_id,
                "name": r.driver_raw_name or "",
                "type": (r.leave_status or r.status_code or "ลาหยุด"),
                "src": "daily", "id": None, "note": "",
            })
            continue
        vid = r.head_vehicle_id if r.head_vehicle_id in vids \
            else plate2vid.get((r.plate_no_raw or "").strip())
        if kind == "repair":
            if vid in vids:
                daily_repair.setdefault(r.work_date, {})[vid] = r.status_code
            continue
        if kind == "idle":
            continue  # รถจอดว่าง — ไม่ใช่งานจอง
        if vid is None and not (r.plate_no_raw or "").strip():
            continue  # แถวไม่มีรถ (office/อื่นๆ) ไม่เกี่ยวกำลังรถ
        _add_busy(r.work_date, r.head_vehicle_id, r.plate_no_raw,
                  r.customer_name_raw or r.status_code or r.trip_type_code,
                  r.driver_raw_name, "เดลี่")

    # --- ซ่อมค้าง: นับตั้งแต่วันเริ่มซ่อม (in_progress) จนกว่าจะปิด record
    repair_from: dict[int, date] = {}
    repair_info: dict[int, dict] = {}
    for mrec in maints:
        cur = repair_from.get(mrec.vehicle_id)
        if cur is None or mrec.work_date < cur:
            repair_from[mrec.vehicle_id] = mrec.work_date
            repair_info[mrec.vehicle_id] = {
                "record_no": mrec.record_no, "since": mrec.work_date,
                "what": mrec.symptom or mrec.work_done or mrec.kind}

    # --- คนลา: LeaveRecord + เดลี่ (dedupe ต่อวันด้วย driver_id/ชื่อ)
    leave_by_day: dict[date, list[dict]] = {}
    _leave_seen: set[tuple[date, object]] = set()
    emp_name = {e.id: e.full_name for e in drivers}
    for rec, emp in leave_rows:
        k = (rec.leave_date, rec.driver_id)
        if k in _leave_seen:
            continue
        _leave_seen.add(k)
        leave_by_day.setdefault(rec.leave_date, []).append({
            "driver_id": rec.driver_id, "name": emp.full_name,
            "type": rec.leave_type, "src": "record", "id": rec.id,
            "note": rec.note})
    for d, items in _daily_leave.items():
        for it in items:
            k = (d, it["driver_id"] if it["driver_id"] else it["name"])
            if k in _leave_seen or (d, it["name"]) in _leave_seen:
                continue
            _leave_seen.add(k)
            if not it["name"] and it["driver_id"]:
                it["name"] = emp_name.get(it["driver_id"], f"#{it['driver_id']}")
            leave_by_day.setdefault(d, []).append(it)

    # --- ประกอบรายวัน + จัดเป็นสัปดาห์ (จันทร์เริ่ม)
    total = len(vehicles)
    days: list[dict] = []
    d = first
    while d <= last:
        b = busy.get(d, set())
        drep = daily_repair.get(d, {})
        open_rep = {vid for vid, frm in repair_from.items() if frm <= d}
        rep = (open_rep | set(drep)) - b
        lv = leave_by_day.get(d, [])
        repair_list = []
        for vid in sorted(rep):
            if vid in open_rep:
                repair_list.append(dict(repair_info[vid], plate=vlabel[vid]))
            else:
                repair_list.append({"plate": vlabel[vid], "since": d,
                                    "record_no": "จากเดลี่", "what": drep[vid]})
        days.append({
            "d": d, "iso": d.isoformat(), "num": d.day,
            "avail": max(total - len(b) - len(rep) - len(lv), 0),
            "busy_n": len(b), "repair_n": len(rep), "leave_n": len(lv),
            "busy_list": busy_detail.get(d, []),
            "repair_list": repair_list,
            "leave_list": lv,
            "is_today": d == today_d,
            "is_weekend": d.weekday() >= 5,
        })
        d += timedelta(days=1)
    weeks: list[list] = []
    row: list = [None] * first.weekday()
    for day in days:
        row.append(day)
        if len(row) == 7:
            weeks.append(row)
            row = []
    if row:
        weeks.append(row + [None] * (7 - len(row)))

    prev_m = (first - timedelta(days=1)).strftime("%Y-%m")
    next_m = (last + timedelta(days=1)).strftime("%Y-%m")
    u = current_user(request)
    ctx = base_context(request)
    ctx.update({
        "site": site, "sites": models.SITE_CODES,
        "month": first.strftime("%Y-%m"),
        "month_label": f"{_TH_MONTH_FULL[first.month]} {first.year}",
        "prev_m": prev_m, "next_m": next_m,
        "weeks": weeks, "total": total, "vehicles": vehicles,
        "drivers": drivers,
        "can_edit": bool(u) and perm_check(u.role, "/calendar", "POST") == "edit",
    })
    return templates.TemplateResponse(request, "calendar.html", ctx)


@app.post("/calendar/leave")
def calendar_leave_add(
    driver_id: int = Form(...),
    date_from: str = Form(...),
    date_to: str = Form(""),
    leave_type: str = Form("personal"),
    note: str = Form(""),
    site: str = Form("LCB"),
    month: str = Form(""),
):
    d1 = _parse_date(date_from)
    d2 = _parse_date(date_to) or d1
    if not d1:
        raise HTTPException(400, "date_from invalid")
    if d2 < d1:
        d1, d2 = d2, d1
    if (d2 - d1).days > 62:
        raise HTTPException(400, "ช่วงลายาวเกิน 62 วัน")
    with Session(engine) as s:
        if not s.get(Employee, driver_id):
            raise HTTPException(404, "ไม่พบพนักงาน")
        existing = {
            r.leave_date
            for r in s.exec(
                select(LeaveRecord).where(
                    LeaveRecord.driver_id == driver_id,
                    LeaveRecord.leave_date >= d1,
                    LeaveRecord.leave_date <= d2,
                )
            ).all()
        }
        d = d1
        while d <= d2:
            if d not in existing:
                s.add(LeaveRecord(driver_id=driver_id, leave_date=d,
                                  leave_type=leave_type.strip(), note=note.strip()))
            d += timedelta(days=1)
        s.commit()
    return RedirectResponse(
        url=f"/calendar?site={site}&month={month}#day-{d1.isoformat()}",
        status_code=303)


@app.post("/calendar/leave/{leave_id}/delete")
def calendar_leave_delete(leave_id: int, site: str = Form("LCB"), month: str = Form("")):
    with Session(engine) as s:
        rec = s.get(LeaveRecord, leave_id)
        if rec:
            s.delete(rec)
            s.commit()
    return RedirectResponse(url=f"/calendar?site={site}&month={month}", status_code=303)


@app.get("/dispatch/planner/{plan_id}/line-message", response_class=PlainTextResponse)
def dispatch_planner_line_message(plan_id: int):
    with Session(engine) as s:
        plan = s.get(DispatchPlan, plan_id)
        if not plan:
            raise HTTPException(404)
        lines = s.exec(
            select(DispatchPlanLine)
            .where(DispatchPlanLine.plan_id == plan_id)
            .order_by(DispatchPlanLine.seq)  # type: ignore[arg-type]
        ).all()
        employees, vehicles_list, _ = _load_masters(s)
        veh_map = {v.id: {"plate": v.plate_no, "nickname": v.nickname} for v in vehicles_list}
        drv_map = {e.id: {"name": e.full_name, "nickname": e.nickname} for e in employees}
    msg = _dispatch_gen_line_message(plan, list(lines), veh_map, drv_map)
    return PlainTextResponse(msg)


if __name__ == "__main__":
    import os
    import sys

    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    import uvicorn

    # 0.0.0.0 = รับจากเครื่องอื่นใน LAN ได้ · ตั้ง YK_BIND_HOST=127.0.0.1 ถ้าต้องการเปิดแค่เครื่องนี้
    bind_host = (os.environ.get("YK_BIND_HOST") or "0.0.0.0").strip()
    if bind_host not in ("127.0.0.1", "0.0.0.0", "::", "::1"):
        bind_host = "0.0.0.0"

    preferred = int(os.environ.get("YK_PORT", "0"))
    port = preferred if preferred else _find_free_port(8010, bind_host=bind_host)

    # If user pinned a port via YK_PORT but it's busy, roll forward rather than crash.
    if preferred:
        probe = _find_free_port(preferred, count=1, bind_host=bind_host)
        if probe != preferred:
            alt = _find_free_port(preferred + 1, bind_host=bind_host)
            print(f"[WARN] YK_PORT={preferred} is busy → using {alt} instead.")
            port = alt

    print("=" * 60)
    print(f"  Project YK — listening on http://127.0.0.1:{port} (เครื่องนี้)")
    if bind_host == "0.0.0.0":
        lan = _primary_lan_ipv4()
        if lan:
            print(f"  เครื่องอื่นใน LAN เปิด: http://{lan}:{port}/daily")
        else:
            print(f"  เครื่องอื่นใน LAN เปิด: http://<ไอพีเครื่องนี้>:{port}/daily")
        print("  (ถ้าเข้าไม่ได้ — เปิด Windows Firewall ให้พอร์ต TCP " + str(port) + ")")
    print(f"  เปิดหน้าเว็บอัตโนมัติใน 1-2 วินาที · กด CTRL+C เพื่อหยุด")
    print("=" * 60)

    _open_browser_when_ready(port)

    try:
        uvicorn.run(app, host=bind_host, port=port, reload=False)
    except OSError as err:
        print(f"\n[ERROR] Cannot bind port {port}: {err}")
        alt = _find_free_port(port + 1, bind_host=bind_host)
        if alt != port:
            print(f"        → Retrying on port {alt}...")
            _open_browser_when_ready(alt)
            uvicorn.run(app, host=bind_host, port=alt, reload=False)
