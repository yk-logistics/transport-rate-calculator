# -*- coding: utf-8 -*-
"""P2 audit กลาง: AuditLog v37 + จุดเขียนสำคัญ + หน้า /admin/audit + per-field daily audit."""
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
from models import AppUser, AuditLog, DailyJob, DailyJobAudit, Employee, KbSettle


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(Employee(code="T001", full_name="ทดสอบ ใจดี", home_site_code="LCB",
                       bank_name="กสิกร", account_no="111-222-3333"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _emp_id():
    with Session(engine) as s:
        return s.exec(select(Employee).where(
            Employee.full_name == "ทดสอบ ใจดี")).first().id


def test_account_change_writes_audit(client):
    emp = _emp_id()
    with Session(engine) as s:
        from models import PayRun
        s.add(PayRun(site_code="LCB", pay_cycle_tag="2026-07",
                     period_start=date(2026, 7, 1), period_end=date(2026, 7, 31)))
        s.commit()
        run_id = s.exec(select(PayRun)).first().id
    client.post(f"/payroll/{run_id}/accounts/save",
                data={"emp_id": emp, "bank_name": "กสิกร", "account_no": "999-888-7777"})
    with Session(engine) as s:
        logs = s.exec(select(AuditLog).where(AuditLog.table_name == "employee")).all()
        assert len(logs) == 1  # ธนาคารไม่เปลี่ยน = ไม่ log; เลขบัญชีเปลี่ยน = log
        a = logs[0]
        assert a.field == "account_no"
        assert a.old_value == "111-222-3333" and a.new_value == "999-888-7777"
        assert a.user == "yk1"
        assert a.note == "ทดสอบ ใจดี"
        assert f"/payroll/{run_id}/accounts/save" == a.route


def test_kb_settle_writes_audit(client):
    client.post("/kb-payout/settle", data={"inv_no": "CYIV2606-001", "kb_amount": "716"})
    with Session(engine) as s:
        a = s.exec(select(AuditLog).where(AuditLog.table_name == "kbsettle")).all()
        assert len(a) == 1 and a[0].new_value == "1" and a[0].note == "CYIV2606-001"
        assert s.exec(select(KbSettle)).first() is not None
    # undo = log อีกแถว (insert-only)
    client.post("/kb-payout/settle", data={"inv_no": "CYIV2606-001", "undo": "1"})
    with Session(engine) as s:
        assert len(s.exec(select(AuditLog).where(
            AuditLog.table_name == "kbsettle")).all()) == 2


def test_admin_audit_page_merges_sources(client):
    with Session(engine) as s:
        s.add(DailyJob(work_date=date(2026, 7, 1), site_code="LCB",
                       status_code="KLND", revenue_customer=100.0))
        s.commit()
        job_id = s.exec(select(DailyJob)).first().id
        s.add(DailyJobAudit(daily_job_id=job_id, changed_by="yk1", action="edit",
                            field_name="revenue_customer", old_value="0", new_value="100"))
        s.add(AuditLog(user="yk1", table_name="payrun", row_id=1, field="status",
                       old_value="draft", new_value="finalized"))
        s.commit()
    r = client.get("/admin/audit?days=7")
    assert r.status_code == 200
    assert "revenue_customer" in r.text       # จาก DailyJobAudit
    assert "finalized" in r.text              # จาก AuditLog
    # filter ตาราง
    r2 = client.get("/admin/audit?days=7&table=payrun")
    assert "finalized" in r2.text and "revenue_customer" not in r2.text


def test_daily_audit_field_filter(client):
    with Session(engine) as s:
        s.add(DailyJob(work_date=date(2026, 7, 1), site_code="LCB",
                       status_code="KLND", revenue_customer=100.0))
        s.commit()
        job_id = s.exec(select(DailyJob)).first().id
        s.add(DailyJobAudit(daily_job_id=job_id, changed_by="yk1", action="edit",
                            field_name="revenue_customer", old_value="0", new_value="100"))
        s.add(DailyJobAudit(daily_job_id=job_id, changed_by="yk1", action="edit",
                            field_name="remark", old_value="", new_value="x"))
        s.commit()
    all_rows = client.get(f"/api/daily/{job_id}/audit").json()["rows"]
    assert len(all_rows) == 2
    one = client.get(f"/api/daily/{job_id}/audit?field=revenue_customer").json()["rows"]
    assert len(one) == 1 and one[0]["field"] == "revenue_customer"
