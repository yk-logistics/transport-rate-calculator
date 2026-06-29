"""Payroll print-all page: สรุป + โอนเงิน + สลิปรายคน in one printable page,
plus per-driver transfer note (auto + manual override) and bank fields.
"""
import os, re, tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import Employee, PayRun, PayRunItem, DailyJob, AppUser


@pytest.fixture()
def client_with_run():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=97, code="D97", full_name="นาย นิพล สีโนนม่วง", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000,
                       gross_share_rate=0.60, bank_name="กสิกร", account_no="090-141-4432"))
        # วันชัย: ลาออกกลางรอบ (end_date ภายในรอบ) แต่ยังมีงาน → ยังได้รับเงินรอบนี้ + auto-note "ออก"
        s.add(Employee(id=2, code="D2", full_name="นาย วันชัย ออกแล้ว", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", end_date=date(2026, 5, 20),
                       base_salary=9240, care_allowance=3000))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        s.add(DailyJob(site_code="LCB", driver_id=97, work_date=date(2026, 5, 20),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=3000))
        s.add(DailyJob(site_code="LCB", driver_id=2, work_date=date(2026, 5, 18),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=350))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 2), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_print_page_has_three_blocks(client_with_run):
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    # three sections
    assert "สรุป" in b
    assert "โอนเงิน" in b
    # bank account shows on transfer page
    assert "090-141-4432" in b
    assert "กสิกร" in b


def test_transfer_note_auto_for_resigned(client_with_run):
    # วันชัย end_date in period -> auto note "ออก"
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert "ออก" in r.text


def test_transfer_note_manual_override(client_with_run):
    r = client_with_run.post("/payroll/2/employee/97/transfer-note",
                             data={"note": "คืนประกันตน 10,000"}, follow_redirects=False)
    assert r.status_code in (200, 303)
    with Session(engine) as s:
        it = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == 2,
                                             PayRunItem.employee_id == 97)).first()
        assert it.transfer_note == "คืนประกันตน 10,000"
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert "คืนประกันตน 10,000" in r.text


def test_slip_does_not_show_ytd(client_with_run):
    """สลิปคนขับ (option 1, โอ 2026-06-28): ไม่โชว์ยอดสะสมทั้งปี — คนขับเห็นแค่
    งวดนี้ (รายได้/หัก/สุทธิ + ภาษีงวดนี้ถ้ามี). ยอดสะสมไปอยู่หน้าภาษีแทน."""
    r = client_with_run.get("/payroll/2/print", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "สะสมทั้งปี" not in b, "slip should NOT show YTD totals (moved to tax page)"


def test_tax_page_renders(client_with_run):
    """หน้าภาษี /payroll/{id}/tax โหลดได้ + โชว์คอลัมน์รายได้/ภาษีสะสม."""
    r = client_with_run.get("/payroll/2/tax", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "สรุปภาษีหัก ณ ที่จ่าย" in b
    assert "รายได้สะสมทั้งปี" in b
    assert "ภาษีสะสมทั้งปี" in b
    assert "นิพล" in b


# ---- สลิป 2 เวอร์ชัน: ผู้บริหาร(เห็น KB) vs คนขับ(ซ่อน KB) + เดลี่รายวัน ----
@pytest.fixture()
def client_kb():
    """mao driver with distinct ค่าขนส่งจริง(rev) / ราคากลาง(override) / KB, + a trip driver."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # เหมา: rev 7456 (ค่าขนส่งจริง), override 5500 (ราคากลาง), KB 333 (ใต้โต๊ะ)
        s.add(Employee(id=99, code="D99", full_name="นาย วิโรจน์ เหมสงวน", pay_mode="lcb_mao",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000,
                       gross_share_rate=0.60, bank_name="กสิกร", account_no="111-1"))
        # เที่ยว
        s.add(Employee(id=90, code="D90", full_name="นาย สุวิทย์ สุขล้อม", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000,
                       bank_name="กสิกร", account_no="222-2"))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        # mao daily: distinct rev/override/kb — use sentinel numbers easy to grep
        s.add(DailyJob(site_code="LCB", driver_id=99, work_date=date(2026, 5, 18),
                       status_code="DHL Overflow", destination="TIPS CD", plate_no_raw="72-1218",
                       revenue_customer=7456, price_override=5500, kb_amount=333, trip_fee_driver=3300))
        s.add(DailyJob(site_code="LCB", driver_id=90, work_date=date(2026, 5, 18),
                       status_code="NHL", destination="SCS2",
                       revenue_customer=2410, kb_amount=110, trip_fee_driver=200))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 2), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _slip_body(html):
    """ตัด <style>…</style> ออกก่อนเช็คเลข — กันชนค่าสีใน CSS เช่น #333."""
    return re.sub(r"<style.*?</style>", "", html, flags=re.S)


def test_driver_slip_hides_kb_and_real_revenue(client_kb):
    """สลิปคนขับ (default): ต้องไม่มี KB(333) และไม่มีราคาฝั่งบริษัทเลย —
    ทั้งค่าขนส่งจริง(7456) และราคากลาง(5500). คนขับเหมาเห็นแค่ค่าเที่ยวที่ได้จริง(3300).

    หมายเหตุ: เดิมเทสต์คาดว่าเหมา 'เห็นราคากลาง 5,500'. หลัง redesign สลิป
    ([[project-driver-pay-breakdown-daily-slip]]) สลิปคนขับโชว์แค่เงินที่คนขับได้ —
    ราคากลางถูกถอดออกด้วย (ปลอดภัยกว่าเดิม: ซ่อนทุกตัวเลขฝั่งบริษัท ไม่ใช่แค่ KB)."""
    r = client_kb.get("/payroll/2/print", follow_redirects=True)
    assert r.status_code == 200
    b = _slip_body(r.text)
    assert "333" not in b, "KB ใต้โต๊ะ ต้องไม่โผล่ในสลิปคนขับ!"
    assert "7,456" not in b and "7456" not in b, "ค่าขนส่งจริง ต้องไม่โผล่ในสลิปคนขับ"
    assert "5,500" not in b and "5500" not in b, "ราคากลางก็ไม่โผล่ในสลิปคนขับแล้ว (redesign)"
    assert "3,300" in b or "3300" in b, "คนขับเหมาต้องเห็นค่าเที่ยวที่ได้จริง"


@pytest.fixture()
def client_with_fuel_grade():
    """รอบที่มีบิลน้ำมัน + FuelTxn ผูก daily_job มี fuel_grade — เพื่อยืนยันว่าหน้า
    print-all (วนทุกคนผ่าน _slip_body.html) ไม่ 500 เพราะ fuel_grade_by_job."""
    from models import FuelTxn
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(id=97, code="D97", full_name="นาย นิพล สีโนนม่วง", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000,
                       bank_name="กสิกร", account_no="090-1"))
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15), status="draft"))
        dj = DailyJob(site_code="LCB", driver_id=97, work_date=date(2026, 5, 20),
                      status_code="KAO", destination="SCS2", plate_no_raw="72-1217",
                      revenue_customer=5000, trip_fee_driver=350,
                      fuel_liter=50, fuel_amount=1760)
        s.add(dj); s.flush()
        s.add(FuelTxn(site_code="LCB", driver_id=97, txn_date=date(2026, 5, 20),
                      plate_no_raw="72-1217", liter=50, amount=1760,
                      daily_job_id=dj.id, fuel_grade="B20", source="test_fg"))
        s.commit()
        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 2), recompute=True); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_print_all_renders_with_fuel_grade(client_with_fuel_grade):
    """หน้า print-all ต้องไม่ 500 เมื่อมีบิลน้ำมัน + ต้องโชว์ป้ายเกรด B20.
    (regression: _slip_body.html ใช้ fuel_grade_by_job ซึ่ง print-all ต้องส่งผ่าน {% with %})"""
    r = client_with_fuel_grade.get("/payroll/2/print", follow_redirects=True)
    assert r.status_code == 200, "print-all 500 — fuel_grade_by_job ไม่ถูกส่งเข้า include?"
    assert "B20" in r.text, "ป้ายเกรด B20 ต้องโชว์ในสลิป print-all"


def test_boss_slip_shows_kb_and_real_revenue(client_kb):
    """สลิปผู้บริหาร (?for=boss): เห็น KB(333) + ค่าขนส่งจริง(7456) + ราคากลาง(5500)."""
    r = client_kb.get("/payroll/2/print?for=boss", follow_redirects=True)
    assert r.status_code == 200
    b = r.text
    assert "333" in b, "ผู้บริหารต้องเห็น KB"
    assert ("7,456" in b or "7456" in b), "ผู้บริหารต้องเห็นค่าขนส่งจริง"


def test_trip_driver_slip_no_central_price(client_kb):
    """สลิปคนขับ คนรายเที่ยว: ไม่โชว์ราคากลาง/KB ของงาน — เห็นแค่ค่าเที่ยวที่ได้.
    KB 110 ของงานเที่ยวต้องไม่โผล่."""
    r = client_kb.get("/payroll/2/print", follow_redirects=True)
    b = r.text
    assert "110" not in b, "KB ของคนเที่ยวต้องไม่โผล่ในสลิปคนขับ"


def test_slip_shows_daily_rows(client_kb):
    """สลิปต้องมีเดลี่รายวัน (วันที่ + ปลายทาง + ทะเบียนรถ)."""
    r = client_kb.get("/payroll/2/print", follow_redirects=True)
    b = r.text
    assert "TIPS CD" in b or "SCS2" in b, "ต้องโชว์เดลี่รายวัน (ปลายทาง)"
    assert "ทะเบียน" in b, "หัวตารางต้องมีคอลัมน์ทะเบียน"
    assert "72-1218" in b, "ต้องโชว์ทะเบียนรถในเดลี่"


def test_transfer_note_deposit_refund_for_resigned():
    """คนลาออกที่ยังมีเงินประกันตนค้าง → auto-note 'คืนประกันตน {ยอด}'."""
    emp = Employee(code="X", full_name="ออกแล้ว", status="inactive", deposit_balance=8000)
    item = PayRunItem(pay_run_id=1, employee_id=1, pay_mode="lcb_trip")
    note = appmod._auto_transfer_note(emp, item, date(2026, 6, 15))
    assert "ออก" in note
    assert "คืนประกันตน" in note and "8,000" in note


def test_transfer_note_no_refund_when_deposit_zero():
    """คนลาออกที่คืนประกันตนหมดแล้ว (balance 0) → ไม่ต้องมีโน้ตคืน."""
    emp = Employee(code="Y", full_name="ออกแล้ว2", status="inactive", deposit_balance=0)
    item = PayRunItem(pay_run_id=1, employee_id=2, pay_mode="lcb_trip")
    note = appmod._auto_transfer_note(emp, item, date(2026, 6, 15))
    assert "ออก" in note
    assert "คืนประกันตน" not in note


def test_pdf_filename_title_reflects_version(client_kb):
    """ชื่อไฟล์ PDF (= <title>) บอกเวอร์ชัน คนขับ/ผู้บริหาร เพื่อกัน save ทับกัน."""
    rd = client_kb.get("/payroll/2/print", follow_redirects=True)
    rb = client_kb.get("/payroll/2/print?for=boss", follow_redirects=True)
    assert "เงินเดือน_LCB_2026-06_คนขับ" in rd.text
    assert "เงินเดือน_LCB_2026-06_ผู้บริหาร" in rb.text
    assert "เซฟ PDF" in rd.text
