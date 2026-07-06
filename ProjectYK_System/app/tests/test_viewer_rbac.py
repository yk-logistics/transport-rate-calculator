# -*- coding: utf-8 -*-
"""S5⑦ (checklist ไตรมาส): role viewer ต้องอ่านได้อย่างเดียว — ปิดข้อค้าง
"ไม่มีรหัส viewer บน server ให้ทดสอบ" ด้วยเทสต์ e2e แทน (แรงกว่าลองมือ):
POST แก้ข้อมูล → 403, grid-data ไม่มีคอลัมน์เงิน/KB (fail closed), โซนเงินเข้าไม่ได้."""
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
from models import AppUser, DailyJob


@pytest.fixture()
def c_viewer():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    parts.invalidate_cache()
    appmod.init_db()
    with Session(engine) as s:
        s.add(AppUser(username="view1", password_hash=hash_password("pw12345678"),
                      role="viewer", must_change_pw=False))
        s.add(DailyJob(work_date=date(2026, 7, 1), site_code="LCB", status_code="KLND",
                       revenue_customer=4900.0, kb_amount=300.0, trip_fee_driver=600.0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "view1", "password": "pw12345678"})
        yield c
    parts.invalidate_cache()


def test_viewer_can_view_daily_grid(c_viewer):
    assert c_viewer.get("/daily/grid").status_code == 200


def test_viewer_grid_data_has_no_money_or_kb_columns(c_viewer):
    item = c_viewer.get("/api/daily/grid-data?site=LCB").json()["items"][0]
    assert "kb_amount" not in item            # daily.kb_col: admin เท่านั้น
    assert "revenue_customer" not in item     # daily.money_cols: viewer ไม่อยู่ใน default = hide
    assert "trip_fee_driver" not in item


def test_viewer_post_edit_gets_403(c_viewer):
    with Session(engine) as s:
        rid = s.exec(select(DailyJob)).first().id
    r = c_viewer.post("/api/daily/grid-save",
                      json={"rows": [{"id": rid, "remark": "hacked"}]},
                      follow_redirects=False)
    assert r.status_code == 403
    with Session(engine) as s:
        assert s.exec(select(DailyJob)).first().remark != "hacked"


def test_viewer_denied_money_zones(c_viewer):
    for path in ("/payroll", "/finance", "/kb-payout"):
        r = c_viewer.get(path, follow_redirects=False)
        assert r.status_code == 403, path
