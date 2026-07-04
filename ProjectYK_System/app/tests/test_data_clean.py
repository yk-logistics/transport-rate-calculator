# -*- coding: utf-8 -*-
"""🧹 เลขใบสกปรก: normalize ตอนเซฟ grid + หน้าเก็บกวาด + audit ต่อแถว."""
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
from models import AppUser, DailyJob, DailyJobAudit


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(DailyJob(work_date=date(2026, 6, 15), site_code="LCB", status_code="KLND",
                       invoice_no="KTIV2606-035\t19/6/2026", revenue_customer=100))
        s.add(DailyJob(work_date=date(2026, 6, 15), site_code="LCB", status_code="KLND",
                       invoice_no="KTIV2606-036", revenue_customer=100))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_normalize_helper():
    assert appmod._normalize_invoice_no("KTIV2606-035\t19/6/2026") == "KTIV2606-035"
    assert appmod._normalize_invoice_no("  cyiv2606-5 ") == "CYIV2606-005"
    assert appmod._normalize_invoice_no("โน้ตอิสระ") == "โน้ตอิสระ"
    assert appmod._normalize_invoice_no("") == ""


def test_grid_save_normalizes(client):
    with Session(engine) as s:
        rid = s.exec(select(DailyJob).where(
            DailyJob.invoice_no == "KTIV2606-036")).first().id
    client.post("/api/daily/grid-save",
                json={"rows": [{"id": rid, "invoice_no": "ktiv2606-40\tขยะ"}]})
    with Session(engine) as s:
        assert s.get(DailyJob, rid).invoice_no == "KTIV2606-040"


def test_clean_page_and_fix(client):
    b = client.get("/admin/data-clean").text
    assert "KTIV2606-035" in b and "ล้างทั้งหมด (1 แถว)" in b
    client.post("/admin/data-clean/fix-invoices")
    with Session(engine) as s:
        rows = s.exec(select(DailyJob)).all()
        assert {r.invoice_no for r in rows} == {"KTIV2606-035", "KTIV2606-036"}
        a = s.exec(select(DailyJobAudit).where(
            DailyJobAudit.action == "data_clean")).all()
        assert len(a) == 1 and a[0].old_value.startswith("KTIV2606-035\t")
    assert "สะอาดทุกแถว" in client.get("/admin/data-clean").text
