# -*- coding: utf-8 -*-
"""หน้า สปส. /payroll/sso (โอสั่ง 14ก.ค. ให้หมิว): รวมคนขับทุกไซท์ของงวดจ่ายเดือนเดียวกัน
(LCB/AYU tag M + BIGC tag M-1 ตามกติกา _compare_cycle_period) โชว์รายได้รวม+เงินหัก สปส.
+ ปุ่มตั้ง "ไม่หัก" (custom_terms.ss_exempt — มีผลรอบที่ยังไม่ปิดเท่านั้น ห้ามแตะรอบ finalize)
+ ตารางยอดที่หักไว้ทั้งที่ตั้งไม่หัก (ให้หมิวโอนคืน). office เข้าไม่ได้ (เมนู payroll)."""
import json
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
import parts
from auth import hash_password
from models import AppUser, Employee, PayRun, PayRunItem


def _seed():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    parts.invalidate_cache()
    appmod.init_db()
    with Session(engine) as s:
        for uname, role in (("miw1", "admin"), ("office1", "office")):
            s.add(AppUser(username=uname, password_hash=hash_password("pw12345678"),
                          role=role, must_change_pw=False))
        d1 = Employee(code="D101", full_name="สมชาย ลานตู้", home_site_code="LCB", role="driver")
        d2 = Employee(code="D102", full_name="สมปอง บิ๊กซี", home_site_code="BIGC", role="driver")
        # d3: ตั้งไม่หักแล้ว แต่รอบเก่าเคยถูกหัก → ต้องโผล่ตารางเงินคืน
        d3 = Employee(code="D103", full_name="สมหมาย อยุธยา", home_site_code="AYU", role="driver",
                      custom_terms=json.dumps({"ss_exempt": True, "keep_me": "x"}, ensure_ascii=False))
        # d4: custom_terms เป็นข้อความเดิมที่ไม่ใช่ JSON — ห้าม toggle ทับ
        d4 = Employee(code="D104", full_name="สมศรี โน้ตเก่า", home_site_code="LCB", role="driver",
                      custom_terms="ข้อตกลงพิเศษ เขียนไว้เป็นข้อความ")
        s.add(d1); s.add(d2); s.add(d3); s.add(d4)
        s.commit()
        for e in (d1, d2, d3, d4):
            s.refresh(e)

        runs = {
            # งวดจ่ายเดือน 2026-06 = LCB 2026-06 + AYU 2026-06 + BIGC 2026-05
            "lcb06": PayRun(site_code="LCB", pay_cycle_tag="2026-06",
                            period_start=date(2026, 5, 16), period_end=date(2026, 6, 15),
                            status="finalized"),
            "bigc05": PayRun(site_code="BIGC", pay_cycle_tag="2026-05",
                             period_start=date(2026, 5, 1), period_end=date(2026, 5, 31),
                             status="finalized"),
            # AYU เดือนนี้ยัง draft — ห้ามเข้าตารางส่ง สปส. (ยังไม่จ่ายจริง)
            "ayu06": PayRun(site_code="AYU", pay_cycle_tag="2026-06",
                            period_start=date(2026, 5, 26), period_end=date(2026, 6, 25),
                            status="draft"),
            # รอบเก่าที่ d3 เคยถูกหัก (ก่อนตั้งไม่หัก)
            "ayu05": PayRun(site_code="AYU", pay_cycle_tag="2026-05",
                            period_start=date(2026, 4, 26), period_end=date(2026, 5, 25),
                            status="finalized"),
        }
        for r in runs.values():
            s.add(r)
        s.commit()
        for r in runs.values():
            s.refresh(r)
        s.add(PayRunItem(pay_run_id=runs["lcb06"].id, employee_id=d1.id, site_code="LCB",
                         pay_mode="lcb_mixed", gross_total=31234.56, social_security=436.0,
                         net_pay=30000.0))
        s.add(PayRunItem(pay_run_id=runs["lcb06"].id, employee_id=d4.id, site_code="LCB",
                         pay_mode="lcb_mixed", gross_total=20000.0, social_security=450.0,
                         net_pay=19000.0))
        s.add(PayRunItem(pay_run_id=runs["bigc05"].id, employee_id=d2.id, site_code="BIGC",
                         pay_mode="bigc_monthly", gross_total=18777.88, social_security=450.0,
                         net_pay=18000.0))
        s.add(PayRunItem(pay_run_id=runs["ayu06"].id, employee_id=d3.id, site_code="AYU",
                         pay_mode="ayu_mao", gross_total=55555.0, social_security=0.0,
                         net_pay=55555.0))
        s.add(PayRunItem(pay_run_id=runs["ayu05"].id, employee_id=d3.id, site_code="AYU",
                         pay_mode="ayu_mao", gross_total=12000.0, social_security=417.0,
                         net_pay=11583.0))
        s.commit()


@pytest.fixture()
def c_admin():
    _seed()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "miw1", "password": "pw12345678"})
        yield c
    parts.invalidate_cache()


URL = "/payroll/sso?month=2026-06"


def test_month_groups_sites_with_bigc_shift(c_admin):
    r = c_admin.get(URL)
    assert r.status_code == 200
    html = r.text
    assert "สมชาย ลานตู้" in html and "31,234.56" in html and "436.00" in html
    # BIGC งวดจ่ายเดือน 6 = tag 2026-05
    assert "สมปอง บิ๊กซี" in html and "18,777.88" in html
    # AYU ยัง draft — คนใน draft ห้ามเข้าตารางส่ง (55,555 ต้องไม่โผล่)
    assert "55,555.00" not in html
    # ยอดรวมเงินสมทบลูกจ้างของงวด: 436 + 450 + 450 = 1,336
    assert "1,336.00" in html


def test_refund_section_lists_exempt_with_past_deduction(c_admin):
    html = c_admin.get(URL).text
    assert "สมหมาย อยุธยา" in html      # ตั้งไม่หักแล้ว แต่ AYU 2026-05 เคยหัก 417
    assert "417.00" in html


def test_toggle_exempt_merges_custom_terms(c_admin):
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D101")).first()
        eid = emp.id
    r = c_admin.post("/payroll/sso/exempt",
                     data={"emp_id": str(eid), "exempt": "1", "month": "2026-06"},
                     follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D101")).first()
        assert json.loads(emp.custom_terms).get("ss_exempt") is True
        from models import AuditLog
        logs = s.exec(select(AuditLog).where(AuditLog.table_name == "employee",
                                             AuditLog.row_id == eid)).all()
        assert logs, "toggle ต้องลง AuditLog"
    # toggle กลับ — key หาย แต่ข้อมูลอื่นใน custom_terms ต้องอยู่ครบ
    c_admin.post("/payroll/sso/exempt",
                 data={"emp_id": str(eid), "exempt": "0", "month": "2026-06"})
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D101")).first()
        assert "ss_exempt" not in json.loads(emp.custom_terms or "{}")


def test_toggle_preserves_other_keys(c_admin):
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D103")).first()
        eid = emp.id
    c_admin.post("/payroll/sso/exempt",
                 data={"emp_id": str(eid), "exempt": "0", "month": "2026-06"})
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D103")).first()
        terms = json.loads(emp.custom_terms)
        assert terms.get("keep_me") == "x"
        assert "ss_exempt" not in terms


def test_toggle_refuses_non_json_custom_terms(c_admin):
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D104")).first()
        eid = emp.id
        before = emp.custom_terms
    r = c_admin.post("/payroll/sso/exempt",
                     data={"emp_id": str(eid), "exempt": "1", "month": "2026-06"},
                     follow_redirects=False)
    assert r.status_code == 400
    with Session(engine) as s:
        emp = s.exec(select(Employee).where(Employee.code == "D104")).first()
        assert emp.custom_terms == before   # ห้ามทับข้อความเดิม


def test_office_denied_and_login_required():
    _seed()
    with TestClient(appmod.app) as c:
        r = c.get("/payroll/sso", follow_redirects=False)
        assert r.status_code == 303          # ไม่ล็อกอิน → หน้า login
        c.post("/login", data={"username": "office1", "password": "pw12345678"})
        assert c.get("/payroll/sso", follow_redirects=False).status_code == 403
    parts.invalidate_cache()
