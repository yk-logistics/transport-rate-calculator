# -*- coding: utf-8 -*-
"""D2 เงินหมุน 8 สัปดาห์: weekly_cashflow + DebtAccount CRUD + หน้า /finance/cashflow."""
import os
import tempfile
from datetime import date, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, AuditLog, DebtAccount, PayRun, PayRunItem
from services import finance as fin


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _seed_money(s):
    pr = PayRun(site_code="LCB", pay_cycle_tag="2026-06", status="finalized",
                period_start=date(2026, 5, 16), period_end=date(2026, 6, 15))
    s.add(pr); s.commit()
    s.add(PayRunItem(pay_run_id=pr.id, employee_id=1, net_pay=100000.0))
    s.add(PayRunItem(pay_run_id=pr.id, employee_id=2, net_pay=-500.0))  # ไม่นับ (net<0)
    s.add(DebtAccount(name="บัตรทดสอบ", kind="credit_card", balance=50000,
                      due_day=10, monthly_payment=7000, active=True))
    s.add(DebtAccount(name="ปิดแล้ว", kind="od", due_day=5, monthly_payment=9999,
                      active=False))
    s.commit()


def test_weekly_cashflow_shape_and_sources(client):
    start = date(2026, 7, 3)  # ศุกร์ → W1 = จันทร์ 29/6 – อาทิตย์ 5/7
    ar = [
        {"inv": "A1", "customer": "KAO", "net": 30000.0, "due": date(2026, 7, 4)},   # ใน W1
        {"inv": "A2", "customer": "KTL", "net": 20000.0, "due": date(2026, 6, 20)},  # เลยกำหนด → W1
        {"inv": "A3", "customer": "CJ", "net": 15000.0, "due": None},  # ไม่มี DUE → ไม่นับ
    ]
    with Session(engine) as s:
        _seed_money(s)
        data = fin.weekly_cashflow(s, ar, start, opening=10000.0)
    weeks = data["weeks"]
    assert len(weeks) == 8
    # W1 = AR due ในสัปดาห์ + เลยกำหนด
    assert weeks[0]["in_ar"] == 50000.0
    assert {r["inv"] for r in weeks[0]["ar_items"]} == {"A1", "A2"}
    # เงินเดือน LCB จ่ายวันที่ 1 (โอเคาะจริง 6ก.ค.) — นับเฉพาะ net>0 = 100,000 และมีลิงก์ย้อนรอบ
    pay = [e for w in weeks for e in w["payroll_items"]]
    assert pay and all(e["amount"] == 100000.0 for e in pay)
    assert all(e["date"].day == 1 for e in pay)
    assert pay[0]["href"].startswith("/payroll/")
    # งวดหนี้: เฉพาะบัญชี active (7,000 วันที่ 10) — บัญชีปิดไม่โผล่
    debts = [e for w in weeks for e in w["debt_items"]]
    assert debts and all(e["amount"] == 7000.0 for e in debts)
    # สะสมต่อเนื่อง: cum สัปดาห์แรก = opening + net
    assert weeks[0]["cum"] == round(10000.0 + weeks[0]["net"], 2)
    for i in range(1, 8):
        assert weeks[i]["cum"] == round(weeks[i - 1]["cum"] + weeks[i]["net"], 2)


def test_debts_crud_and_audit(client):
    r = client.post("/finance/debts/save", data={
        "name": "ไฟแนนซ์ 71-8967", "kind": "finance", "balance": "800,000",
        "due_day": "25", "monthly_payment": "18500", "plate": "71-8967"},
        follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        d = s.exec(select(DebtAccount)).first()
        assert d.balance == 800000.0 and d.plate == "71-8967"
        did = d.id
    # แก้ยอดค้าง → AuditLog
    client.post("/finance/debts/save", data={
        "debt_id": str(did), "name": "ไฟแนนซ์ 71-8967", "kind": "finance",
        "balance": "780000", "due_day": "25", "monthly_payment": "18500",
        "plate": "71-8967"})
    with Session(engine) as s:
        logs = s.exec(select(AuditLog).where(
            AuditLog.table_name == "debtaccount")).all()
        assert any(a.field == "balance" and a.new_value == "780000.0" for a in logs)
    # toggle ปิด
    client.post(f"/finance/debts/{did}/toggle")
    with Session(engine) as s:
        assert s.get(DebtAccount, did).active is False


def test_cashflow_page_renders_without_drive(client):
    with Session(engine) as s:
        _seed_money(s)
    r = client.get("/finance/cashflow?opening=50000")
    assert r.status_code == 200
    assert "เงินหมุนล่วงหน้า 8 สัปดาห์" in r.text
    assert "W8" in r.text
    # dev ไม่มี key Drive → ต้องขึ้นเตือน ไม่ใช่พัง
    assert ("อ่านทะเบียนรับเช็คจาก Drive ไม่สำเร็จ" in r.text) or ("W1" in r.text)


def test_debts_page_renders(client):
    with Session(engine) as s:
        _seed_money(s)
    r = client.get("/finance/debts")
    assert r.status_code == 200
    assert "บัตรทดสอบ" in r.text and "ปิดแล้ว" in r.text
