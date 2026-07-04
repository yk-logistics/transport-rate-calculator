# -*- coding: utf-8 -*-
"""CSV โอนชุดธนาคาร: net>0 เท่านั้น เรียงตามธนาคาร + แถวรวม + BOM."""
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
from models import AppUser, Employee, PayRun, PayRunItem


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        e1 = Employee(code="A1", full_name="กสิกร หนึ่ง", home_site_code="LCB",
                      bank_name="กสิกร", account_no="111")
        e2 = Employee(code="A2", full_name="กรุงเทพ สอง", home_site_code="LCB",
                      bank_name="กรุงเทพ", account_no="222")
        e3 = Employee(code="A3", full_name="ติดลบ สาม", home_site_code="LCB",
                      bank_name="กสิกร", account_no="333")
        pr = PayRun(site_code="LCB", pay_cycle_tag="2026-07",
                    period_start=date(2026, 7, 1), period_end=date(2026, 7, 31))
        s.add(e1); s.add(e2); s.add(e3); s.add(pr); s.commit()
        s.add(PayRunItem(pay_run_id=pr.id, employee_id=e1.id, net_pay=12000.50))
        s.add(PayRunItem(pay_run_id=pr.id, employee_id=e2.id, net_pay=8000.00))
        s.add(PayRunItem(pay_run_id=pr.id, employee_id=e3.id, net_pay=-500.00))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_csv_content(client):
    with Session(engine) as s:
        rid = s.exec(select(PayRun)).first().id
    r = client.get(f"/payroll/{rid}/accounts.csv")
    assert r.status_code == 200
    body = r.content.decode("utf-8-sig")          # BOM ต้องมี (decode ด้วย sig ผ่าน)
    lines = [x for x in body.strip().splitlines() if x]
    assert lines[0].startswith("ธนาคาร")
    assert "ติดลบ สาม" not in body                 # net<0 ไม่ออก
    # เรียงตามธนาคาร: กรุงเทพ ก่อน กสิกร
    assert body.index("กรุงเทพ") < body.index("กสิกร,111")
    assert "12000.50" in body and "8000.00" in body
    assert "20000.50" in body                      # แถวรวม
    assert "2 คน" in body
