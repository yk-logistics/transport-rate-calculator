# -*- coding: utf-8 -*-
"""P1 สิทธิ์รายชิ้นส่วน: default ในโค้ด + ปรับสดที่ /admin/permissions + บังคับจริง
(ซ่อนคอลัมน์เงิน/KB จาก payload grid, ห้ามเขียน, ปุ่มแก้บัญชี 403)."""
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
from models import AppUser, DailyJob, Employee, PayRun


@pytest.fixture()
def clients():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    parts.invalidate_cache()
    appmod.init_db()
    with Session(engine) as s:
        admin = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        admin.must_change_pw = False; s.add(admin)
        s.add(AppUser(username="off1", password_hash=hash_password("pw12345678"),
                      role="office", must_change_pw=False))
        s.add(DailyJob(work_date=date(2026, 7, 1), site_code="LCB", status_code="KLND",
                       revenue_customer=4900.0, kb_amount=300.0, trip_fee_driver=600.0))
        s.commit()
    with TestClient(appmod.app) as c_admin, TestClient(appmod.app) as c_off:
        c_admin.post("/login", data={"username": "yk1", "password": "changeme1"})
        c_off.post("/login", data={"username": "off1", "password": "pw12345678"})
        yield c_admin, c_off
    parts.invalidate_cache()


def _grid_item(c):
    return c.get("/api/daily/grid-data?site=LCB").json()["items"][0]


def test_defaults_admin_sees_office_no_kb(clients):
    c_admin, c_off = clients
    assert "kb_amount" in _grid_item(c_admin)
    item = _grid_item(c_off)
    assert "kb_amount" not in item                    # daily.kb_col: office = hide
    assert item["revenue_customer"] == 4900.0         # daily.money_cols: office = edit


def test_office_cannot_write_kb(clients):
    _, c_off = clients
    with Session(engine) as s:
        rid = s.exec(select(DailyJob)).first().id
    r = c_off.post("/api/daily/grid-save",
                   json={"rows": [{"id": rid, "kb_amount": 999, "remark": "ok"}]})
    body = r.json()
    assert any("no_permission:kb_amount" in e.get("error", "") for e in body.get("errors", []))
    with Session(engine) as s:
        row = s.exec(select(DailyJob)).first()
        assert row.kb_amount == 300.0                 # ไม่ถูกเขียน
        assert row.remark == "ok"                     # ช่องอื่นเขียนได้ปกติ


def test_admin_page_tick_changes_live(clients):
    c_admin, c_off = clients
    # office เดิมเห็นคอลัมน์เงิน → โอติ๊กเป็น hide → payload ต้องหาย ไม่ต้อง restart
    c_admin.post("/admin/permissions/save", data={
        "part_key": "daily.money_cols", "role": "office", "level": "hide"})
    assert "revenue_customer" not in _grid_item(c_off)
    # กลับ default
    c_admin.post("/admin/permissions/save", data={
        "part_key": "daily.money_cols", "role": "office", "level": "default"})
    assert _grid_item(c_off)["revenue_customer"] == 4900.0


def test_user_override_beats_role(clients):
    c_admin, c_off = clients
    c_admin.post("/admin/permissions/save", data={
        "part_key": "daily.kb_col", "username": "off1", "level": "view"})
    assert "kb_amount" in _grid_item(c_off)           # override รายคนชนะ role


def test_edit_account_forbidden_for_office(clients):
    c_admin, c_off = clients
    with Session(engine) as s:
        s.add(Employee(code="T9", full_name="ทดสอบ", home_site_code="LCB"))
        s.add(PayRun(site_code="LCB", pay_cycle_tag="2026-07",
                     period_start=date(2026, 7, 1), period_end=date(2026, 7, 31)))
        s.commit()
        emp_id = s.exec(select(Employee).where(Employee.code == "T9")).first().id
        run_id = s.exec(select(PayRun)).first().id
    r = c_off.post(f"/payroll/{run_id}/accounts/save",
                   data={"emp_id": emp_id, "bank_name": "x", "account_no": "1"})
    assert r.status_code == 403


def test_admin_permissions_page(clients):
    c_admin, _ = clients
    r = c_admin.get("/admin/permissions")
    assert r.status_code == 200
    assert "daily.kb_col" in r.text and "transfer.edit_account" in r.text
