"""
Data models for Project YK One-Platform (Phase 1.1).
Designed to cover 3 sites (AYU / BIGC / LCB) with flexible pay contracts.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SchemaInfo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    version: int
    applied_at: datetime = Field(default_factory=datetime.utcnow)


class AppUser(SQLModel, table=True):
    """A person who logs in to the back-office system (distinct from Employee, a payroll subject)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    display_name: str = ""
    role: str = Field(default="viewer", index=True)    # admin|office|accountant|viewer
    status: str = Field(default="active", index=True)  # active|disabled
    must_change_pw: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    full_name: str
    nickname: str = ""
    phone: str = ""
    id_card: str = ""
    bank_name: str = ""            # ธนาคารสำหรับโอนเงินเดือน เช่น "ไทยพาณิชย์"
    account_no: str = ""          # เลขบัญชี เช่น "688-444-0533"
    home_site_code: str = Field(index=True)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = Field(default="active", index=True)

    # role: distinguishes who gets a payroll run as driver vs other support people.
    # Values: driver | office | owner | mechanic | guard | other
    role: str = Field(default="driver", index=True)

    pay_mode: str = Field(default="ayu_trip")
    pay_cycle_policy: str = Field(default="site_default", index=True)
    base_salary: float = 0.0
    care_allowance: float = 0.0
    gross_share_rate: Optional[float] = None

    has_guarantee: bool = False
    guarantee_monthly_amount: float = 0.0

    deposit_target: float = 10000.0
    deposit_balance: float = 0.0

    social_security_base: float = 9000.0
    social_security_rate: float = 0.05

    # Driver PWA auth (Phase 4 — v14). PIN is 4-6 digits, hashed via driver_auth.
    pin_hash: str = Field(default="", index=True)
    pin_set_at: Optional[datetime] = None

    custom_terms: str = ""
    notes: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Vehicle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plate_no: str = Field(index=True, unique=True)
    vehicle_kind: str = Field(default="truck", index=True)
    truck_type: str = ""
    home_site_code: str = Field(default="", index=True)
    status: str = Field(default="active", index=True)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # v10: vehicle identity enrichment from RM history sheets
    nickname: str = Field(default="", index=True)   # "กระเพรา", "โหระพา", "อ้อย" — ชื่อเล่น LCB/BIGC
    old_plate_no: str = Field(default="", index=True)  # ทะเบียนเก่า
    brand: str = ""          # Isuzu / Volvo / Fuso / Hino / UD ...
    model: str = ""          # FVM34, FTR195, FTR240 ...
    engine_no: str = ""
    chassis_no: str = ""
    current_mile: float = 0.0    # latest known odometer reading — updated by PM/MaintRecord

    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    home_site_code: str = Field(default="", index=True)
    billing_profile_ref: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KbRule(SQLModel, table=True):
    """Default KB (ใต้โต๊ะ) ต่อ status_code (= ชื่อลูกค้าในไฟล์ LCB).

    required=True → แถวที่ status นี้แต่ kb_amount==0 จะถูกเตือน (กันลืม), ไม่บล็อก.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    status_code: str = Field(index=True, unique=True)
    default_kb: float = 0.0
    required: bool = False
    note: str = ""


class PayCycle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    site_code: str = Field(index=True, unique=True)
    cycle_start_day: int
    cycle_end_day: int
    pay_rule: str = ""
    notes: str = ""


class DailyJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    work_date: date = Field(index=True)
    site_code: str = Field(index=True)

    driver_id: Optional[int] = Field(default=None, foreign_key="employee.id", index=True)
    driver_raw_name: str = ""

    head_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    tail_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id")
    plate_no_raw: str = ""
    tail_plate_raw: str = ""

    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id", index=True)
    customer_name_raw: str = ""

    trip_group_id: Optional[int] = Field(default=None, index=True)
    trip_type_code: str = ""
    status_code: str = ""
    leave_status: str = ""

    origin: str = ""
    destination: str = ""
    pickup_location: str = ""
    store_code: str = ""
    truck_type_raw: str = ""
    doc_no: str = ""
    job_ref: str = ""
    container_no: str = ""
    container_size: str = ""

    revenue_customer: float = 0.0
    trip_fee_driver: float = 0.0

    # KB (ใต้โต๊ะ/commission) ต่อแถว — seed จาก KbRule ตาม status_code, แก้มือได้
    kb_amount: float = 0.0
    # ราคากลาง/over-market override — None = ใช้ revenue_customer เป็นฐานคิดเงินคนขับ
    price_override: Optional[float] = Field(default=None)

    fuel_liter: float = 0.0
    fuel_amount: float = 0.0
    fuel_station: str = ""
    fuel_rate_km_per_l: float = 0.0
    mile_snapshot: float = 0.0

    invoice_no: str = ""
    invoice_date: Optional[date] = None
    wht_53: float = 0.0

    # v30: ช่องอ้างอิงเพิ่มจากชีทเดลี่ (โชว์เป็นคอลัมน์แยก แทนการฝังใน remark)
    phone: str = ""              # เบอร์โทร (G)
    shared_vehicle: str = ""     # ใช้รถร่วม (AL)
    receive_inv_no: str = ""     # Receive/Inv.No. (AM)
    bl_booking: str = ""         # BL/Booking (L→ แยกจาก Job)
    fuel_date: Optional[date] = None   # วันเติมน้ำมัน (AC)
    gps_rate: float = 0.0        # เรท GPS (AJ)

    remark: str = ""

    # provenance: import_daily | manual | bigc_fuel_rate | (empty legacy)
    source: str = Field(default="", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DailyJobFee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    daily_job_id: int = Field(foreign_key="dailyjob.id", index=True)
    fee_type: str
    amount: float = 0.0
    remark: str = ""


class LeaveRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="employee.id", index=True)
    leave_date: date = Field(index=True)
    leave_type: str = ""
    note: str = ""


class AccidentCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_code: str = Field(index=True)
    driver_id: int = Field(foreign_key="employee.id", index=True)
    incident_date: date
    total_amount: float = 0.0
    status: str = "open"
    case_ref: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AccidentInstallment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="accidentcase.id", index=True)
    seq: int
    due_cycle: str = Field(index=True)
    amount: float
    status: str = "planned"
    actual_deducted_amount: float = 0.0
    notes: str = ""


class DriverDeposit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="employee.id", index=True)
    cycle: str = Field(index=True)
    amount_deducted: float
    running_balance_after: float
    notes: str = ""


class PettyCashTxn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    txn_date: date = Field(index=True)
    site_code: str = Field(index=True)

    direction: str = Field(default="out", index=True)
    amount: float = 0.0

    requester_raw: str = ""
    driver_id: Optional[int] = Field(default=None, foreign_key="employee.id", index=True)

    memo: str = ""

    category: str = Field(default="other", index=True)
    has_receipt: bool = False

    deduct_from_driver: bool = Field(default=False, index=True)
    deduct_amount: float = 0.0
    deduction_status: str = Field(default="pending", index=True)
    pay_cycle_tag: str = Field(default="", index=True)
    payroll_line_id: Optional[int] = None

    linked_vehicle_plate_raw: str = ""
    linked_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id")
    linked_daily_job_id: Optional[int] = Field(default=None, foreign_key="dailyjob.id")

    running_balance: float = 0.0
    note: str = ""

    pending_amount: float = 0.0
    pending_note: str = ""
    pending_cleared_at: Optional[date] = None

    status: str = Field(default="posted", index=True)
    source: str = Field(default="manual")

    parsed_confidence: float = 0.0
    parsed_payload_json: str = ""

    # provenance for LINE-slip-sourced entries (phase: lcb-slip-reader)
    slip_line_message_id: str = Field(default="", index=True)
    slip_media_path: str = ""
    slip_ref_code: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FuelTxn(SQLModel, table=True):
    """Fuel fill-up records. One row per fill event.

    Separate from DailyJob because fuel may be entered later, batch-imported
    from fuel-station invoices, or span multiple jobs.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    site_code: str = Field(default="", index=True)
    txn_date: date = Field(index=True)

    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    plate_no_raw: str = Field(default="", index=True)

    driver_id: Optional[int] = Field(default=None, foreign_key="employee.id", index=True)
    driver_raw_name: str = ""

    liter: float = 0.0
    amount: float = 0.0
    price_per_liter: float = 0.0
    rate_km_per_l: float = 0.0
    mile_snapshot: float = 0.0

    station: str = ""
    fill_type: str = ""

    daily_job_id: Optional[int] = Field(default=None, foreign_key="dailyjob.id", index=True)

    source: str = "manual"
    note: str = ""

    # When True, this fill is NOT deducted from the driver's pay (e.g. fuel
    # added before the driver started running, or the first full tank when
    # starting เหมา — บริษัทออกให้). Default False = deduct as before.
    exclude_from_driver: bool = Field(default=False)

    # B7 / B20 / "" (ไม่ระบุ) — ป้ายเกรดเท่านั้น ไม่เข้าสูตรเงิน (v31).
    fuel_grade: str = Field(default="")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class PayRun(SQLModel, table=True):
    """One payroll run per site+cycle (e.g. BIGC 2026-02)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    site_code: str = Field(index=True)
    pay_cycle_tag: str = Field(index=True)   # "2026-02" — labels the cycle
    period_start: date
    period_end: date
    status: str = Field(default="draft", index=True)  # draft | finalized | paid
    notes: str = ""

    # Per-run Social Security overrides (e.g. รัฐลด rate ชั่วคราวบาง period).
    # None = ใช้ default 5% / min 1650 / max 15000.
    ss_rate: Optional[float] = None
    ss_base_min: Optional[float] = None
    ss_base_max: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    finalized_at: Optional[datetime] = None
    finalized_by: str = ""


class PayRunItem(SQLModel, table=True):
    """One row per Employee per PayRun."""
    id: Optional[int] = Field(default=None, primary_key=True)
    pay_run_id: int = Field(foreign_key="payrun.id", index=True)
    employee_id: int = Field(foreign_key="employee.id", index=True)
    site_code: str = Field(default="", index=True)
    pay_mode: str = ""
    transfer_note: str = ""       # หมายเหตุหน้าโอนเงิน (แก้มือ override auto เช่น "ออก")

    days_worked: float = 0.0
    days_leave: float = 0.0
    days_absent: float = 0.0
    days_company_no_work: float = 0.0

    # Earnings
    base_salary_earned: float = 0.0       # proportional to attendance
    care_allowance_earned: float = 0.0    # LCB: 3000/30 × days_worked
    trip_fee_total: float = 0.0           # Σ DailyJob.trip_fee_driver
    fuel_rate_income: float = 0.0         # BIGC: liters left × 16฿ (can be negative)
    fuel_share_income: float = 0.0        # AYU/LCB mao: % of revenue − fuel cost
    guarantee_topup: float = 0.0          # AYU: if trip_fee < guarantee
    other_income: float = 0.0
    # LCB driver extras, broken out so the table/slip can show them separately.
    # These are a SUBSET of other_income (already summed into it), not additive.
    special_income: float = 0.0           # พิเศษ (เฉพาะ lcb_trip/lcb_mixed; เหมา=0)
    ot_income: float = 0.0                # OT (ทุก mode LCB)
    pickup_return_income: float = 0.0     # รับตู้/คืนตู้แทน (ทุก mode LCB)
    gross_total: float = 0.0

    # Audit breakdown for BIGC fuel rate
    fuel_budget_liter: float = 0.0        # Σ DailyJob.fuel_liter (admin's plan)
    fuel_consumed_liter: float = 0.0      # Σ FuelTxn.liter driver burned
    fuel_residual_liter: float = 0.0      # budget − consumed (+ adjust)

    # Deductions
    social_security: float = 0.0
    income_tax_withholding: float = 0.0
    deposit_install: float = 0.0
    accident_install: float = 0.0
    petty_cash_deduction: float = 0.0     # Σ PettyCashTxn that matches cycle tag
    fuel_cost_self: float = 0.0           # AYU/LCB mao: liters × price (driver pays)
    other_deduction: float = 0.0
    deduction_total: float = 0.0

    net_pay: float = 0.0

    computed_at: datetime = Field(default_factory=datetime.utcnow)
    note: str = ""


class PayRunAdjust(SQLModel, table=True):
    """Per-(PayRun, Employee) manual adjustments that SURVIVE recompute.

    Admin sometimes tweaks numbers for irregular cases (บริษัทสั่งวน/อ้อม,
    ข้อตกลงพิเศษ). Stored separately so the auto-calc can be re-run any time
    without losing admin intent.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    pay_run_id: int = Field(foreign_key="payrun.id", index=True)
    employee_id: int = Field(foreign_key="employee.id", index=True)

    # BIGC fuel rate adjustment (extra residual liters, +/-)
    fuel_adjust_liter: float = 0.0
    # Full manual override — if > 0, use this instead of auto-compute entirely
    fuel_rate_override_thb: Optional[float] = None

    # Days override (None = use auto-detection from DailyJob).
    # Use cases: ผู้ใช้ดูสภาพจริงและตัดสินใจเองว่าวันทำงาน/ลา/ขาดของรอบนี้คือกี่วัน
    days_worked_override: Optional[float] = None
    days_leave_override: Optional[float] = None
    days_absent_override: Optional[float] = None

    # Social Security override (per-employee, per-run). None → use Employee defaults.
    ss_rate_override: Optional[float] = None       # e.g. 0.03 (3%) ช่วงรัฐช่วย
    ss_base_min_override: Optional[float] = None   # default 1650
    ss_base_max_override: Optional[float] = None   # default 15000

    note: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BigcBranch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    branch_code: str = Field(index=True, unique=True)
    branch_name: str
    region: str = ""
    distance_km: float = 0.0
    customer_rate: float = 0.0
    driver_trip_fee: float = 0.0
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: str = ""


## =====================================================================
## Maintenance / Stock / Tire / PM module (new in schema v8)
## =====================================================================

class Vendor(SQLModel, table=True):
    """ร้านอะไหล่/ร้านซ่อม/ซัพพลายเออร์"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)   # auto V0001
    name: str
    kind: str = Field(default="parts", index=True)  # parts|tire|service|oil|other
    phone: str = ""
    contact_person: str = ""
    address: str = ""
    credit_terms: str = ""     # e.g. "เงินสด" / "เครดิต 30 วัน"
    notes: str = ""
    status: str = Field(default="active", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Part(SQLModel, table=True):
    """อะไหล่/สินค้าคงคลัง (รวมยางใน master ด้วย แต่มี is_tire=True)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)    # auto P0001
    name: str = Field(index=True)
    category: str = Field(default="other", index=True)  # engine|brake|electric|filter|oil|tire|suspension|tyre|other
    unit: str = Field(default="ชิ้น")           # ชิ้น | ลิตร | กก. | ม.
    default_price: float = 0.0                    # ราคาเฉลี่ย/ล่าสุด
    spec: str = ""                                # สเปค/รุ่น
    is_tire: bool = Field(default=False, index=True)
    min_stock_qty: float = 0.0                    # trigger alert ต่ำกว่านี้
    notes: str = ""
    status: str = Field(default="active", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StockTxn(SQLModel, table=True):
    """การเคลื่อนไหวสต็อก: รับเข้า / เบิกออก / ปรับปรุงยอด
    Stock level ณ ปัจจุบัน = Σ (direction=='in'?qty:-qty)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    txn_date: date = Field(index=True)
    part_id: int = Field(foreign_key="part.id", index=True)
    direction: str = Field(default="in", index=True)   # in | out | adjust
    qty: float = 0.0
    unit_price: float = 0.0
    total_amount: float = 0.0
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id")
    maint_record_id: Optional[int] = Field(default=None, foreign_key="maintrecord.id", index=True)
    linked_petty_cash_id: Optional[int] = Field(default=None, foreign_key="pettycashtxn.id")
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaintRecord(SQLModel, table=True):
    """บันทึกซ่อมบำรุง / บริการ / ตรวจ / เปลี่ยนยาง / อุบัติเหตุ"""
    id: Optional[int] = Field(default=None, primary_key=True)
    record_no: str = Field(index=True, unique=True)   # auto M000001
    work_date: date = Field(index=True)

    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    plate_raw: str = ""
    driver_id: Optional[int] = Field(default=None, foreign_key="employee.id")   # ใครนำรถมาซ่อม
    mile_snapshot: float = 0.0

    kind: str = Field(default="repair", index=True)
    # repair | service | inspection | tire_change | accident | other

    status: str = Field(default="done", index=True)
    # draft | in_progress | done | cancelled

    symptom: str = ""      # อาการก่อนซ่อม
    diagnosis: str = ""    # สาเหตุ
    work_done: str = ""    # รายละเอียดงานที่ทำ

    mechanic_name: str = ""
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id", index=True)

    labor_cost: float = 0.0        # ค่าแรง (แยกจากอะไหล่)
    parts_cost: float = 0.0        # Σ MaintPart.total
    total_cost: float = 0.0        # labor + parts + extra
    other_cost: float = 0.0

    paid_by: str = Field(default="cash", index=True)
    # cash | credit | petty_cash | deduct_driver
    linked_petty_cash_id: Optional[int] = Field(default=None, foreign_key="pettycashtxn.id")
    paid_at: Optional[date] = None

    pm_plan_id: Optional[int] = Field(default=None, foreign_key="pmplan.id", index=True)

    receipt_ref: str = ""
    notes: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaintPart(SQLModel, table=True):
    """อะไหล่ที่ใช้ใน MaintRecord (line item)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    maint_record_id: int = Field(foreign_key="maintrecord.id", index=True)
    part_id: Optional[int] = Field(default=None, foreign_key="part.id", index=True)
    part_name_raw: str = ""    # fallback ถ้าไม่มีใน Part master
    qty: float = 0.0
    unit_price: float = 0.0
    total: float = 0.0
    tire_id: Optional[int] = Field(default=None, foreign_key="tire.id")  # link to tire lifecycle
    note: str = ""


class Tire(SQLModel, table=True):
    """เส้นยางแต่ละเส้น (lifecycle tracking)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)    # auto T0001
    brand: str = ""                # Bridgestone / Michelin / ...
    model: str = ""                # R150
    spec: str = ""                 # 11R22.5 / 295/80R22.5
    serial_no: str = Field(default="", index=True)    # DOT/serial number

    purchase_date: Optional[date] = None
    purchase_price: float = 0.0
    purchase_vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id")

    status: str = Field(default="new", index=True)
    # new | in_use | stored | retreaded | scrapped

    current_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    current_position: str = Field(default="", index=True)   # position code e.g. "FL1", "RR2", "TRL-R3"
    mounted_at: Optional[date] = None
    mounted_mile: float = 0.0

    tread_depth_mm: float = 0.0    # ความหนาดอกยางปัจจุบัน (mm)
    retread_count: int = 0         # จำนวนครั้งที่ดอกยางหล่อซ้ำ

    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TireEvent(SQLModel, table=True):
    """เหตุการณ์ของเส้นยาง: mount/unmount/rotate/inspect/retread/scrap"""
    id: Optional[int] = Field(default=None, primary_key=True)
    tire_id: int = Field(foreign_key="tire.id", index=True)
    event_date: date = Field(index=True)
    event_type: str = Field(default="mount", index=True)
    # mount | unmount | rotate | inspect | retread | scrap

    from_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id")
    from_position: str = ""
    to_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id")
    to_position: str = ""

    mile: float = 0.0
    tread_before_mm: float = 0.0
    tread_after_mm: float = 0.0

    maint_record_id: Optional[int] = Field(default=None, foreign_key="maintrecord.id")
    note: str = ""
    photo_paths: str = ""        # comma-separated relative paths (uploads root)
    actor_name: str = ""         # name typed at magic-link entry
    actor_role: str = ""         # driver | mechanic | "" (office)
    condition_flag: str = ""     # driver report: ok | near | problem | ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PmPlan(SQLModel, table=True):
    """แผน PM (Preventive Maintenance) — ต่อรถคันหนึ่ง หรือ global (vehicle_id=None)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)    # auto PM0001
    name: str                                      # "เปลี่ยนน้ำมันเครื่อง"
    kind: str = Field(default="PM", index=True)   # PM | RM | inspection | other
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    # None = applies to all vehicles

    # v10: Fluid kind for PM categorisation (น้ำมันเครื่อง/เกียร์/เฟือง/จารบี/หล่อเย็น/กรอง/อื่น ๆ)
    fluid_kind: str = Field(default="other", index=True)
    # engine_oil | gear_oil | diff_oil | grease | coolant | filter | tire | battery | other

    interval_km: float = 0.0       # every N km (0 = not used)
    interval_days: int = 0         # every N days (0 = not used)
    alert_km_before: float = 1000.0  # v10: ถ้าเหลือน้อยกว่านี้ก็แจ้งเตือน

    last_done_date: Optional[date] = None
    last_done_mile: float = 0.0
    last_maint_record_id: Optional[int] = Field(default=None, foreign_key="maintrecord.id")

    next_due_date: Optional[date] = Field(default=None, index=True)
    next_due_mile: float = 0.0

    description: str = ""
    default_parts_csv: str = ""    # e.g. "P0001:4,P0002:1" — suggest parts on exec
    status: str = Field(default="active", index=True)
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =====================================================================
# v10: Maintenance extensions — VendorPrice, VehicleSpec, Inspection
# =====================================================================

class VendorPrice(SQLModel, table=True):
    """ราคา Part ต่อร้าน (เปรียบเทียบข้ามร้าน) — ต่อ (part_id, vendor_id) เอา record ล่าสุด"""
    id: Optional[int] = Field(default=None, primary_key=True)
    part_id: int = Field(foreign_key="part.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)

    unit_price: float = 0.0
    vat_included: bool = True
    currency: str = "THB"
    min_order_qty: float = 0.0
    lead_time_days: int = 0
    quoted_on: Optional[date] = None   # วันที่ได้ราคานี้

    use_count: int = 0                 # จำนวนครั้งที่ซื้อจากร้านนี้
    last_used_at: Optional[datetime] = None
    is_preferred: bool = Field(default=False, index=True)   # ปักหมุดร้านหลัก
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VehicleSpec(SQLModel, table=True):
    """Spec master ของการเติมของเหลว/อะไหล่ ต่อรุ่นรถ (brand + model)
    เช่น Isuzu FTR195 เกียร์ใช้ 80W-90 GL-4 6.5L
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    brand: str = Field(index=True)         # Isuzu | Fuso | Volvo | Hino | UD
    model: str = Field(index=True)         # FTR195 | FTR240 | FVM34 | ...
    fluid_kind: str = Field(index=True)    # engine_oil | gear_oil | diff_oil | grease | coolant | filter | other

    viscosity: str = ""        # 80W-90 / 85W-140 / 15W-40
    api_grade: str = ""        # GL-4 / GL-5 / CI-4 / CJ-4
    capacity_l: float = 0.0    # ปริมาณเติม (ลิตร)

    part_spec_ref: str = ""    # หมายเหตุเพิ่มเติม (เช่น "ใช้เกียร์ ZF ไม่ได้")
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaintInspection(SQLModel, table=True):
    """รายการตรวจเช็ครถประจำเดือน (monthly safety check)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    inspection_date: date = Field(index=True)
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    plate_raw: str = ""
    inspector_name: str = ""
    overall_status: str = Field(default="pass", index=True)  # pass | fail | partial
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaintInspectionItem(SQLModel, table=True):
    """แต่ละข้อในการตรวจเช็ค (เช่น LOGO ข้างประตู, ไฟหน้า, เบรค)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    inspection_id: int = Field(foreign_key="maintinspection.id", index=True)
    item_name: str
    status: str = Field(default="ok")    # ok | fail | warning | na
    remark: str = ""


FLUID_KINDS = (
    ("engine_oil",  "น้ำมันเครื่อง"),
    ("gear_oil",    "น้ำมันเกียร์"),
    ("diff_oil",    "น้ำมันเฟืองท้าย"),
    ("grease",      "จารบีล้อ"),
    ("coolant",     "น้ำยาหล่อเย็น"),
    ("filter",      "ไส้กรอง"),
    ("tire",        "ยาง"),
    ("battery",     "แบตเตอรี่"),
    ("other",       "อื่น ๆ"),
)

INSPECTION_STATUS = ("pass", "fail", "partial")
INSPECTION_ITEM_STATUS = ("ok", "fail", "warning", "na")


MAINT_KINDS = (
    ("repair",      "ซ่อม (แก้เหตุเสีย)"),
    ("service",     "บริการตามระยะ (PM)"),
    ("inspection",  "ตรวจสภาพ/เช็คระยะ"),
    ("tire_change", "เปลี่ยนยาง/สลับยาง"),
    ("accident",    "อุบัติเหตุ"),
    ("other",       "อื่น ๆ"),
)

MAINT_STATUS = (
    ("draft",        "ร่าง"),
    ("in_progress",  "กำลังซ่อม"),
    ("done",         "เสร็จสิ้น"),
    ("cancelled",    "ยกเลิก"),
)

MAINT_PAID_BY = (
    ("cash",           "เงินสด"),
    ("credit",         "เครดิตร้าน"),
    ("petty_cash",     "สดย่อย"),
    ("deduct_driver",  "หักคนขับ"),
)

PART_CATEGORIES = (
    ("engine",      "เครื่องยนต์"),
    ("brake",       "เบรก"),
    ("electric",    "ไฟฟ้า/แบตเตอรี่"),
    ("filter",      "ฟิลเตอร์/กรอง"),
    ("oil",         "น้ำมันเครื่อง/น้ำมันเกียร์"),
    ("tire",        "ยาง"),
    ("suspension",  "ช่วงล่าง"),
    ("cabin",       "ตัวถัง/ภายใน"),
    ("body",        "ซ่อมสี/ตัวถัง"),
    ("consumable",  "ของสิ้นเปลือง"),
    ("other",       "อื่น ๆ"),
)

PART_UNITS = ("ชิ้น", "คู่", "ชุด", "ลิตร", "กก.", "ม.", "กล่อง", "หลอด")

VENDOR_KINDS = (
    ("parts",   "ร้านอะไหล่"),
    ("tire",    "ร้านยาง"),
    ("service", "อู่ซ่อม/บริการ"),
    ("oil",     "ศูนย์น้ำมัน/โรงกลึง"),
    ("insurance", "ประกันภัย"),
    ("other",   "อื่น ๆ"),
)

TIRE_STATUS = (
    ("new",        "ใหม่ (ยังไม่ใช้)"),
    ("in_use",     "ใช้งานอยู่ (ติดตั้งบนรถ)"),
    ("stored",     "เก็บสต็อก"),
    ("retreaded",  "หล่อดอกซ้ำแล้ว"),
    ("scrapped",   "ทิ้ง/หมดสภาพ"),
)

TIRE_EVENT_TYPES = (
    ("mount",    "ติดตั้งขึ้นรถ"),
    ("unmount",  "ถอดออก"),
    ("rotate",   "สลับตำแหน่ง"),
    ("inspect",  "ตรวจสภาพ/วัดดอก"),
    ("retread",  "หล่อดอกซ้ำ"),
    ("scrap",    "ทิ้ง/หมดสภาพ"),
)

TIRE_CONDITION_FLAGS = (
    ("ok",      "ปกติ"),
    ("near",    "น่าจะใกล้หมด"),
    ("problem", "มีปัญหา (รั่ว/บวม/ฉีก)"),
)

PM_KINDS = (
    ("PM",         "PM (Preventive — ตามระยะ/เวลา)"),
    ("RM",         "RM (Reactive — ซ่อมแก้)"),
    ("inspection", "ตรวจสภาพประจำ"),
    ("other",      "อื่น ๆ"),
)

# Tire position codes — standard truck layout
# F = Front, R = Rear, L = Left, R = Right, TRL = Trailer (pup)
TIRE_POSITIONS_BY_KIND = {
    "6W":   ("FL", "FR", "RLO", "RLI", "RRO", "RRI"),   # 6 tires
    "10W":  ("FL", "FR", "RLO1", "RLI1", "RRO1", "RRI1",
             "RLO2", "RLI2", "RRO2", "RRI2"),            # 10 tires
    "10WL": ("FL", "FR", "RLO", "RLI", "RRO", "RRI",
             "TRL_L1", "TRL_R1", "TRL_L2", "TRL_R2"),
    "18W":  ("FL", "FR", "RLO1", "RLI1", "RRO1", "RRI1",
             "RLO2", "RLI2", "RRO2", "RRI2",
             "TRL_L1", "TRL_R1", "TRL_L2", "TRL_R2",
             "TRL_L3", "TRL_R3", "TRL_L4", "TRL_R4"),
    # Pup trailer with twin tyres each side, 2 axles = 8 wheels (YK real layout).
    "TRL8": ("TRL_LO1", "TRL_LI1", "TRL_RI1", "TRL_RO1",   # เพลาหน้า: ซ้ายนอก ซ้ายใน ขวาใน ขวานอก
             "TRL_LO2", "TRL_LI2", "TRL_RI2", "TRL_RO2"),  # เพลาหลัง
}

# Thai presentation labels for tire positions (DB keeps English codes).
TIRE_POSITION_TH = {
    "FL": "ซ้ายหน้า", "FR": "ขวาหน้า",
    "RLO": "ซ้ายหลังนอก", "RLI": "ซ้ายหลังใน", "RRI": "ขวาหลังใน", "RRO": "ขวาหลังนอก",
    "RLO1": "ซ้ายหลังนอก (เพลาหน้า)", "RLI1": "ซ้ายหลังใน (เพลาหน้า)",
    "RRI1": "ขวาหลังใน (เพลาหน้า)", "RRO1": "ขวาหลังนอก (เพลาหน้า)",
    "RLO2": "ซ้ายหลังนอก (เพลาหลัง)", "RLI2": "ซ้ายหลังใน (เพลาหลัง)",
    "RRI2": "ขวาหลังใน (เพลาหลัง)", "RRO2": "ขวาหลังนอก (เพลาหลัง)",
    "TRL_LO1": "หาง ซ้ายนอก (เพลาหน้า)", "TRL_LI1": "หาง ซ้ายใน (เพลาหน้า)",
    "TRL_RI1": "หาง ขวาใน (เพลาหน้า)", "TRL_RO1": "หาง ขวานอก (เพลาหน้า)",
    "TRL_LO2": "หาง ซ้ายนอก (เพลาหลัง)", "TRL_LI2": "หาง ซ้ายใน (เพลาหลัง)",
    "TRL_RI2": "หาง ขวาใน (เพลาหลัง)", "TRL_RO2": "หาง ขวานอก (เพลาหลัง)",
    # Single-tyre trailer axles (10WL / 18W layouts)
    "TRL_L1": "หาง ซ้าย (เพลา 1)", "TRL_R1": "หาง ขวา (เพลา 1)",
    "TRL_L2": "หาง ซ้าย (เพลา 2)", "TRL_R2": "หาง ขวา (เพลา 2)",
    "TRL_L3": "หาง ซ้าย (เพลา 3)", "TRL_R3": "หาง ขวา (เพลา 3)",
    "TRL_L4": "หาง ซ้าย (เพลา 4)", "TRL_R4": "หาง ขวา (เพลา 4)",
}


## =====================================================================
## Rate Book / Price Master — auto-learn from DailyJob history (schema v9)
## =====================================================================

class RateCard(SQLModel, table=True):
    """หนึ่งเรตหนึ่งกฎ — ตัว pattern match ให้ระบบ "จำ" ราคาที่ admin เคยกรอกไว้

    ครั้งแรก: admin กรอก DailyJob → auto สร้าง RateCard (source='auto')
    ครั้งต่อไป: ระบบ match context → suggest ค่าเดิม → admin แค่ยืนยัน
    admin ตั้งกฎ manual ก็ได้ (priority > auto) + รองรับ wildcard '*'
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    kind: str = Field(index=True)
    # fuel_budget_liter | revenue_customer | trip_fee_driver | toll_fee | other

    # Dimensions (all support wildcard '*' meaning "match any")
    site_code: str = Field(default="*", index=True)
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id", index=True)
    # customer_id = None  → wildcard (match any customer)

    vehicle_kind: str = Field(default="*", index=True)     # 6W | 10W | trailer | *
    trip_type_code: str = Field(default="*", index=True)   # 1BigC | 2BigC | 2++ | loading | backhaul | *
    origin: str = Field(default="*", index=True)
    destination: str = Field(default="*", index=True)
    pickup_location: str = Field(default="*", index=True)  # LCB focus: ชื่อโรงงาน Loading

    except_pattern: str = ""   # free-text annotation, e.g. "except destination=X,Y"

    rate_value: float = 0.0
    rate_unit: str = "THB"     # THB | L | km

    priority: int = 0          # higher wins on tie; manual>auto convention = 1>0
    source: str = Field(default="manual", index=True)  # manual | auto | import

    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    use_count: int = 0
    last_used_at: Optional[datetime] = None
    last_seen_job_id: Optional[int] = None

    status: str = Field(default="active", index=True)
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


RATE_KINDS = (
    ("fuel_budget_liter", "งบน้ำมัน (ลิตร)"),
    ("revenue_customer",  "ค่าขนส่ง (ลูกค้า)"),
    ("trip_fee_driver",   "ค่าเที่ยว (คนขับ)"),
    ("toll_fee",          "ค่าทางด่วน/Mflow"),
    ("other",             "อื่น ๆ"),
)


## =====================================================================
## Fuel-adjusted pricing (schema v11)
## =====================================================================

class FuelPriceIndex(SQLModel, table=True):
    """ราคาน้ำมันดีเซลรายเดือนสำหรับใช้อ้างอิงคิด Fuel Surcharge

    หนึ่งแถว = ราคา 1 เดือน/ภูมิภาค (region เผื่ออนาคตแยก กทม./ต่างจังหวัด)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    month: str = Field(index=True)        # "YYYY-MM" e.g. "2026-03"
    region: str = Field(default="BKK", index=True)
    diesel_price: float = 0.0             # baht/liter (ประกาศ ปตท./โรงกลั่น)
    source: str = ""                      # e.g. "PTT", "BangchakMOU", "internal"
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FuelSurchargeBand(SQLModel, table=True):
    """Step table กำหนด surcharge ตามช่วงราคาน้ำมันของแต่ละลูกค้า

    Match logic: fuel_min <= diesel_price < fuel_max → apply (pct + flat)
    effective_rate = base * (1 + pct/100) + flat
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id", index=True)
    # customer_id = None = wildcard (applies to all customers without specific band)

    trip_type_code: str = Field(default="*", index=True)   # 1BigC | 2BigC | loading | * ...
    vehicle_kind: str = Field(default="*", index=True)     # 6W | 10W | trailer | *

    fuel_min: float = 0.0                 # baht/L (inclusive)
    fuel_max: float = 999.0               # baht/L (exclusive)

    surcharge_pct: float = 0.0            # +% over base (e.g. 2.0 = +2%)
    surcharge_flat: float = 0.0           # +baht flat (per trip)

    # Which fuel price to look up:
    #   current  = price of the job's month
    #   prev1    = previous month (T-1)
    #   prev2    = 2 months earlier (T-2)
    fuel_ref_mode: str = Field(default="current", index=True)
    region: str = Field(default="BKK")

    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    priority: int = 0                     # higher wins; specific > wildcard
    status: str = Field(default="active", index=True)
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --------------------------------------------------------------------------
# FINANCE / DEBT (Phase 3 — schema v13)
# --------------------------------------------------------------------------

class Loan(SQLModel, table=True):
    """Debt/loan the owner or company is carrying.

    Supports:
    - Bank term loan (principal + rate + term → amortized monthly payment)
    - Hire purchase / installment (fixed monthly payment)
    - Revolving credit / overdraft (interest-only, variable balance)
    - Informal/family loan (flexible)

    `monthly_payment` is the actual scheduled payment (can be manually set).
    If set, overrides amortization calc. Else it's computed from principal+rate+term.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # L0001, L0002 ...

    lender: str = Field(index=True)              # "SCB", "KBANK", "พ่อ ก.", ...
    loan_kind: str = Field(default="term", index=True)  # term | hire_purchase | revolving | informal
    purpose: str = ""                              # "ซื้อรถ 71-0567", "หมุนเวียน", ...

    # Principal & interest
    principal: float = 0.0                         # original principal (บาท)
    annual_rate_pct: float = 0.0                   # e.g. 6.5 means 6.5% per year
    term_months: int = 0                           # 0 = no fixed term (revolving)

    # Dates
    start_date: Optional[date] = None
    first_payment_date: Optional[date] = None
    end_date: Optional[date] = None                # auto = start + term
    pay_day_of_month: int = 5                      # 1-28, default 5

    # Payment settings
    monthly_payment: float = 0.0                   # if > 0 overrides amortization calc
    current_balance: float = 0.0                   # outstanding balance (admin-maintained)

    # Collateral / notes
    collateral: str = ""                           # "รถ 71-0567"
    linked_vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)

    status: str = Field(default="active", index=True)  # active | paid_off | closed | defaulted
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LoanPayment(SQLModel, table=True):
    """Actual payment made against a Loan (admin logs this)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    loan_id: int = Field(foreign_key="loan.id", index=True)
    pay_date: date = Field(index=True)
    amount: float = 0.0                            # total paid
    principal_portion: float = 0.0                 # breakdown (optional)
    interest_portion: float = 0.0
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --------------------------------------------------------------------------
# DRIVER PWA (Phase 4 — schema v14)
# --------------------------------------------------------------------------

class DriverSession(SQLModel, table=True):
    """Login session for a driver (cookie-based, signed token)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id", index=True)
    token: str = Field(index=True, unique=True)
    device_info: str = ""             # user-agent hint
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    revoked: bool = Field(default=False, index=True)


class DriverSubmission(SQLModel, table=True):
    """Anything a driver submits from mobile: vehicle check, alcohol test,
    job photo, signature, etc. Generic + flexible.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    # Nullable: magic-link (login-less) submissions have no Employee; actor goes in data_json.
    employee_id: Optional[int] = Field(default=None, foreign_key="employee.id", index=True)
    submitted_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    kind: str = Field(index=True)
    # vehicle_check | alcohol_test | job_photo | signature | fuel_receipt | other

    # Vehicle context (optional)
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id", index=True)
    plate_raw: str = ""

    # Related daily job (if job-specific)
    daily_job_id: Optional[int] = Field(default=None, foreign_key="dailyjob.id", index=True)

    # GPS (optional — browser navigator.geolocation)
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    gps_accuracy_m: Optional[float] = None

    # Photo(s) — relative paths from uploads/ root (comma-separated if multiple)
    photo_paths: str = ""

    # Flexible JSON payload for checklist answers / alcohol reading / etc.
    data_json: str = ""

    # Admin review
    review_status: str = Field(default="pending", index=True)
    # pending | approved | flagged | archived
    review_note: str = ""
    reviewed_by: str = ""
    reviewed_at: Optional[datetime] = None

    # Device hint for tracing
    device_info: str = ""


class AccessLink(SQLModel, table=True):
    """Signed, time-limited magic link for login-less data entry (driver | mechanic).

    The signed token is the source of truth for role + expiry; this row is for
    audit (who generated it, usage) and explicit revocation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    short_code: str = Field(default="", index=True)   # short slug for /c/<code> URLs
    role: str = Field(default="driver", index=True)   # driver | mechanic
    created_by: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    revoked: bool = Field(default=False, index=True)
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    note: str = ""


class InboxEmail(SQLModel, table=True):
    """Inbound email items synced from IMAP for operations review."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_label: str = Field(default="ops", index=True)
    mailbox: str = Field(default="INBOX", index=True)
    imap_uid: str = Field(default="", index=True)

    message_id: str = Field(default="", index=True)
    thread_hint: str = ""
    sent_at: Optional[datetime] = Field(default=None, index=True)
    from_name: str = ""
    from_email: str = Field(default="", index=True)
    to_emails: str = ""
    cc_emails: str = ""
    subject: str = Field(default="", index=True)
    body_text: str = ""
    has_attachment: bool = Field(default=False, index=True)
    attachment_paths: str = ""

    # Classification and guardrails
    category: str = Field(default="other", index=True)
    confidence: float = 0.0
    risk_flags: str = ""
    suggested_site_code: str = ""
    suggested_customer: str = ""
    suggested_action: str = ""
    ai_provider: str = ""
    ai_note: str = ""
    needs_review: bool = Field(default=True, index=True)

    status: str = Field(default="new", index=True)  # new | reviewed | ignored | linked
    linked_daily_job_id: Optional[int] = Field(default=None, foreign_key="dailyjob.id", index=True)
    linked_petty_txn_id: Optional[int] = Field(default=None, foreign_key="pettycashtxn.id", index=True)
    note: str = ""

    source: str = Field(default="imap", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InboxSyncRun(SQLModel, table=True):
    """Audit log for each IMAP sync run."""
    id: Optional[int] = Field(default=None, primary_key=True)
    account_label: str = Field(default="ops", index=True)
    mailbox: str = Field(default="INBOX", index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    ended_at: Optional[datetime] = None
    status: str = Field(default="running", index=True)  # running | ok | error
    fetched_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    ignored_count: int = 0
    error_message: str = ""


class AppSetting(SQLModel, table=True):
    """Tiny generic key/value store for back-office runtime settings.

    First use: the LCB slip-reader on/off switch + read-since watermark, so โอ can
    control the auto-reader from the MVP UI instead of editing files on the server.
    """
    key: str = Field(primary_key=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


SUBMISSION_KINDS = (
    ("vehicle_check", "ตรวจรถก่อนวิ่ง"),
    ("alcohol_test",  "เป่าแอลกอฮอล์"),
    ("job_photo",     "รูปเอกสาร/ตู้/หลักฐานงาน"),
    ("fuel_receipt",  "ใบเสร็จน้ำมัน"),
    ("signature",     "ลายเซ็น"),
    ("other",         "อื่น ๆ"),
)

REVIEW_STATUS = (
    ("pending",  "รอตรวจ"),
    ("approved", "ผ่าน"),
    ("flagged",  "ทักท้วง"),
    ("archived", "เก็บถาวร"),
)

ACCESS_LINK_ROLES = (
    ("driver",   "คนขับ"),
    ("mechanic", "ช่าง"),
)

INBOX_EMAIL_STATUS = (
    ("new", "ใหม่"),
    ("reviewed", "ตรวจแล้ว"),
    ("ignored", "ไม่เกี่ยวงาน"),
    ("linked", "ผูกงานแล้ว"),
)

INBOX_EMAIL_CATEGORY = (
    ("booking", "จองเที่ยว/งานเข้า"),
    ("document", "เอกสาร/ใบงาน"),
    ("billing", "บิล/ใบแจ้งหนี้"),
    ("payment", "ชำระเงิน/การเงิน"),
    ("urgent", "เร่งด่วน"),
    ("other", "อื่น ๆ"),
)

# Vehicle check item catalog — keep in sync with UI
VEHICLE_CHECK_ITEMS = (
    ("tires_front",   "ยางหน้า (ดอก/ลม/รั่ว)"),
    ("tires_rear",    "ยางหลัง/พ่วง"),
    ("brakes",        "เบรค (หัว/หาง)"),
    ("lights_front",  "ไฟหน้า/สูง-ต่ำ"),
    ("lights_rear",   "ไฟท้าย/เบรค/ถอย"),
    ("signals",       "ไฟเลี้ยว/ฉุกเฉิน"),
    ("mirrors",       "กระจกมองข้าง/หลัง"),
    ("wipers",        "ที่ปัดน้ำฝน"),
    ("horn",          "แตร"),
    ("oil_level",     "น้ำมันเครื่อง (ระดับ)"),
    ("coolant",       "น้ำยาหม้อน้ำ"),
    ("air_pressure",  "ลมเบรค/ลมยาง"),
    ("seatbelt",      "เข็มขัดนิรภัย"),
    ("fire_ext",      "ถังดับเพลิง"),
    ("documents",     "เอกสาร (ใบขับขี่/ทะเบียน/พรบ.)"),
)

# Item status values
VEHICLE_CHECK_STATUS = (
    ("ok",      "ปกติ"),
    ("warn",    "ผิดปกติเล็กน้อย"),
    ("fail",    "ชำรุด/ต้องซ่อม"),
    ("na",      "ไม่มี/ไม่ตรวจ"),
)


LOAN_KINDS = (
    ("term",          "เงินกู้ธนาคาร (ผ่อนลดต้นลดดอก)"),
    ("hire_purchase", "ไฟแนนซ์/เช่าซื้อ (งวดคงที่)"),
    ("revolving",     "วงเงินหมุนเวียน/OD (ดอกเบี้ยต่อเดือน)"),
    ("informal",      "ยืมส่วนตัว/ญาติ/นายทุน"),
    ("factoring",     "Factoring (รับเงินก่อน หักดอก)"),
    ("other",         "อื่น ๆ"),
)

LOAN_STATUS = ("active", "paid_off", "closed", "defaulted")


FUEL_REF_MODES = (
    ("current", "เดือนงานปัจจุบัน"),
    ("prev1",   "เดือนก่อนหน้า (T-1)"),
    ("prev2",   "2 เดือนก่อนหน้า (T-2)"),
)

FUEL_REGIONS = (
    ("BKK",     "กรุงเทพฯ/ปริมณฑล"),
    ("EAST",    "ภาคตะวันออก (ชลบุรี/ฉะเชิงเทรา)"),
    ("CENTRAL", "ภาคกลาง (อยุธยา/สระบุรี)"),
    ("OTHER",   "อื่น ๆ"),
)

RATE_UNIT_BY_KIND = {
    "fuel_budget_liter": "L",
    "revenue_customer":  "THB",
    "trip_fee_driver":   "THB",
    "toll_fee":          "THB",
    "other":             "THB",
}


SITE_CODES = ("AYU", "BIGC", "LCB")

PAY_MODES = (
    ("bigc_monthly",  "BIGC — เงินเดือน 9000 + ค่าเที่ยว + ค่าเรทน้ำมัน 16฿"),
    ("bigc_standard", "BIGC — (legacy alias)"),
    ("lcb_monthly",   "LCB รายเที่ยว — 9240 + ค่าดูแลรถ 3000 + ค่าเที่ยว"),
    ("lcb_trip",      "LCB รายเที่ยว (legacy alias)"),
    ("lcb_mao",       "LCB เหมาน้ำมัน — 60% ของค่าขนส่ง (หักน้ำมันจริง)"),
    ("ayu_trip",      "AYU รายเที่ยว — ค่าเที่ยวเท่านั้น (+/- การันตี)"),
    ("ayu_mao",       "AYU เหมาน้ำมัน — 55-60% ของค่าขนส่ง"),
    ("none",          "ไม่มี (ออฟฟิส/พ่อ/ช่าง/เจ้าของ)"),
)

PAY_CYCLE_POLICIES = (
    ("site_default", "ตามรอบไซต์ของคนขับ (เดิม)"),
    ("cut_26_25", "ตัดรอบ 26→25"),
    ("cut_16_15", "ตัดรอบ 16→15"),
    ("calendar", "เดือนปฏิทิน (1→สิ้นเดือน)"),
    ("calendar_m1", "เดือนวิ่ง T-1 (เลื่อนไปเดือนก่อนหน้า)"),
)

EMPLOYEE_ROLES = (
    ("driver",   "คนขับ"),
    ("office",   "ออฟฟิส/แอดมิน"),
    ("owner",    "เจ้าของ/ผู้บริหาร"),
    ("mechanic", "ช่าง"),
    ("guard",    "ยาม/รปภ."),
    ("other",    "อื่นๆ"),
)

VEHICLE_KINDS = (
    ("truck", "รถคันเดียว (6W/10W ไม่มีหาง)"),
    ("head",  "รถหัวลาก"),
    ("tail",  "หางลาก"),
)

TRUCK_TYPES = ("6W", "10W", "10WL", "18W", "TRL8")

# Thai display labels for truck types (DB keeps the short code).
TRUCK_TYPE_TH = {
    "6W":   "6 ล้อ",
    "10W":  "10 ล้อ",
    "10WL": "10 ล้อ + หาง",
    "18W":  "18 ล้อ (หัวลาก + หาง)",
    "TRL8": "หางลาก (8 ล้อ คู่ 2 เพลา)",
}

VEHICLE_STATUS = ("active", "parked", "maintenance", "sold")

EMPLOYEE_STATUS = ("active", "left", "suspended")

LEAVE_STATUS_CHOICES = (
    ("",                 "— ทำงานปกติ —"),
    ("sick",             "ลาป่วย"),
    ("personal",         "ลากิจ/ลาส่วนตัว"),
    ("absent",           "ขาด/ไม่มา"),
    ("company_no_work",  "บริษัทไม่มีงาน (นับการันตี)"),
)

FEE_TYPES = (
    "lift", "yard", "clean", "shore", "port_entry", "weighing",
    "special", "ot", "pickup_return", "mflow", "shared_vehicle", "other",
)

PETTY_DIRECTIONS = (
    ("out", "จ่ายออก (expense)"),
    ("in",  "รับเข้าสดย่อย (income/transfer in)"),
)

PETTY_CATEGORIES = (
    ("toll",           "ค่าทางด่วน/Mflow"),
    ("fuel",           "น้ำมัน"),
    ("repair",         "ซ่อมรถ/อะไหล่"),
    ("parking",        "ค่าจอด/เข้า AO"),
    ("loading",        "ค่าลงของ/ค่าจ้าง"),
    ("fine",           "ค่าปรับ"),
    ("driver_advance", "พขร.เบิกเงิน (หักเงินเดือน)"),
    ("deposit_refund", "คืนเงินประกันตน"),
    ("salary_partial", "เบิกเงินเดือนล่วงหน้า"),
    ("owner_transfer", "โอนเข้าสดย่อย (จากเจ้าของ/บริษัท)"),
    ("customer_refund","คืนลูกค้า/ลูกค้าโอน"),
    ("tire",           "ยาง"),
    ("accident",       "ค่าเคลม/อุบัติเหตุ"),
    ("other",          "อื่น ๆ"),
)

DEDUCTION_STATUS = (
    ("pending",         "รอหัก"),
    ("deducted",        "หักแล้ว (โดยระบบ)"),
    ("settled_offline", "เคยหักแล้ว (นอกระบบ/ทอนไม่คืน)"),
    ("waived",          "ยกเลิก/ไม่หัก"),
)

PETTY_TXN_STATUS = (
    ("draft",          "ร่าง"),
    ("pending_review", "รอ AI อ่าน—รออนุมัติ"),
    ("posted",         "บันทึกแล้ว"),
    ("locked",         "ปิดรอบแล้ว (แก้ไม่ได้)"),
)

class ImportLog(SQLModel, table=True):
    """Audit log for every import batch run through the Import Wizard."""
    id: Optional[int] = Field(default=None, primary_key=True)
    import_type: str = Field(index=True)   # daily|petty|fuel|rm|pm|rate|master
    site_code: str = Field(default="", index=True)
    source_tag: str = Field(index=True)    # e.g. "lcb_daily_20251216_a1b2"
    file_name: str = ""
    sheet_name: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    row_count: int = 0
    fee_count: int = 0
    fuel_count: int = 0
    status: str = Field(default="done", index=True)  # done|dry_run|rolled_back|failed
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DispatchPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_date: date = Field(index=True)
    site_code: str = Field(index=True)
    status: str = Field(default="draft", index=True)  # draft | submitted
    created_by: str = Field(default="")
    submitted_at: Optional[datetime] = None
    line_message_cache: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DispatchPlanLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="dispatchplan.id", index=True)
    seq: int = Field(default=0)
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicle.id")
    plate_raw: str = ""
    driver_id: Optional[int] = Field(default=None, foreign_key="employee.id")
    driver_raw: str = ""
    job_type: str = ""  # Haier | KAO | Conti | Lacation | KATOEN | คลังวาฬ | ฟรีโซน | เหรินเหอ | Oatside
    trips: int = Field(default=1)
    fuel_liters: float = Field(default=0.0)
    container_no: str = ""
    notes: str = ""
    daily_job_id: Optional[int] = Field(default=None, foreign_key="dailyjob.id")


class DispatchPlanAudit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="dispatchplan.id", index=True)
    line_id: Optional[int] = Field(default=None)
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    changed_by: str = ""
    action: str = ""  # add_line | edit_line | delete_line | submit | reopen
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""
    note: str = ""


class DailyJobAudit(SQLModel, table=True):
    """ประวัติการแก้ไข DailyJob ในหน้า /daily — INSERT-only, ไม่แก้ของเดิม."""
    id: Optional[int] = Field(default=None, primary_key=True)
    daily_job_id: int = Field(index=True)
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    changed_by: str = ""
    action: str = ""  # edit | create | delete
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""


class DepositAudit(SQLModel, table=True):
    """ประวัติการแก้ยอดเงินประกันตนในหน้า /deposits — INSERT-only, ไม่แก้ของเดิม."""
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(index=True)
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    changed_by: str = ""
    field_name: str = ""        # deposit_balance | deposit_target
    old_value: str = ""
    new_value: str = ""
    reason: str = ""


TRIP_TYPE_CODES_BY_SITE: dict[str, tuple[tuple[str, str], ...]] = {
    "AYU": (
        ("",         "— ไม่ระบุ —"),
        ("mao",      "เหมาน้ำมัน"),
        ("trip",     "รายเที่ยว"),
    ),
    "BIGC": (
        ("",         "— ไม่ระบุ —"),
        ("รับรถ",    "รับรถ (event)"),
        ("1DH",      "1DH (Direct Backhaul)"),
        ("1Big c",   "1Big c (สายสั้นหลัก)"),
        ("1+",       "1+ (สายสั้นพ่วง)"),
        ("2BigC",    "2BigC (สายยาวหลัก)"),
        ("2++",      "2++ (สายยาวพ่วง)"),
    ),
    "LCB": (
        ("",         "— ไม่ระบุ —"),
        ("Export",   "Export"),
        ("Import",   "Import"),
        ("Domestic", "Domestic"),
    ),
}


class KbSettle(SQLModel, table=True):
    """อินวอยที่ 'รับ KB / ลูกค้าโอนแล้ว' บนหน้า /kb-payout (โอ 2ก.ค.).

    ติ๊กแล้ว = ตัดออกจากการจับคู่ยอดโอนและยอด KB ค้างรับ. ลบแถว = ยกเลิกติ๊ก.
    ไม่เกี่ยวกับ payroll/DailyJob — เป็นสมุดกันลืมของงาน KB เท่านั้น.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    inv_no: str = Field(index=True, unique=True)     # เช่น CYIV2606-023
    settled_on: date = Field(default_factory=date.today)
    kb_amount: float = 0.0          # KB ของใบนี้ตอนติ๊ก (กันสูตร/ไฟล์เปลี่ยนทีหลัง)
    transfer_amount: float = 0.0    # ยอดโอนของก้อนที่ใบนี้ถูกจ่ายมาด้วย (0 = ติ๊กเดี่ยว)
    note: str = ""


class TodoItem(SQLModel, table=True):
    """สมุดโน้ต/สิ่งที่ต้องทำของโอ (หน้า /todo) — จดเร็วแบบพิมพ์แชท ค้นได้ แนบรูปได้.

    แยกของใครของมันด้วย username; category = พิมพ์อิสระ (หมวดเกิดจากการใช้จริง);
    priority: 0 ปกติ / 1 ด่วน / 2 ด่วนมาก; media_json = รายชื่อไฟล์รูปใน _todo_media/<id>/.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    text: str = ""
    category: str = Field(default="", index=True)
    priority: int = 0
    due_date: Optional[date] = None
    status: str = Field(default="open", index=True)   # open | done
    created_at: datetime = Field(default_factory=datetime.utcnow)
    done_at: Optional[datetime] = None
    media_json: str = ""
