# -*- coding: utf-8 -*-
"""Error logging: 500 ต้องลงไฟล์ log พร้อม traceback + โชว์บน server-health
(เดิมแอปบน server รันเป็น SYSTEM task — stdout หายหมด ไม่มีร่องรอย 500 เลย)."""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, DailyJob


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # แถวราคาว่าง 1 แถว — ให้ fill-prices เรียก rate_find จริง (จุดที่เราทำให้พังในเทสต์)
        s.add(DailyJob(work_date=date(2026, 7, 2), site_code="LCB",
                       status_code="KLND", revenue_customer=0.0))
        s.commit()
    with TestClient(appmod.app, raise_server_exceptions=False) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_500_logged_to_file_and_friendly_page(client, monkeypatch):
    # ทำ route จริงพัง 1 จุดชั่วคราว (rate_find ระเบิด) → /billing/fill-prices 500
    def boom(*a, **k):
        raise RuntimeError("จำลองพังเพื่อทดสอบ log")
    monkeypatch.setattr(appmod, "rate_find", boom)
    if appmod.LOG_FILE.exists():
        appmod.LOG_FILE.unlink()
    r = client.get("/billing/fill-prices?month=2026-07")
    assert r.status_code == 500
    assert "ระบบขัดข้องชั่วคราว" in r.text          # หน้า error ภาษาคน ไม่ใช่ blank
    assert appmod.LOG_FILE.exists()
    log = appmod.LOG_FILE.read_text(encoding="utf-8")
    assert "จำลองพังเพื่อทดสอบ log" in log          # traceback ลงไฟล์
    assert "/billing/fill-prices" in log
    # server-health โชว์บรรทัด error
    b = client.get("/admin/server-health").text
    assert "ข้อผิดพลาดล่าสุดของระบบ" in b
    assert "billing/fill-prices" in b


# หมายเหตุลำดับ: เทสต์นี้ต้องอยู่ "หลัง" ตัวบน — มันเปิดไฟล์ log ค้างไว้ ทำให้
# LOG_FILE.unlink() ของตัวบนพังด้วย PermissionError บน Windows
def test_client_disconnect_noise_not_logged(client):
    """asyncio บน Windows โยน ConnectionResetError ทุกครั้งที่ client ตัดสายกลางคัน
    (uptime check/ปิดแท็บ) — ไม่ใช่บั๊ก แต่ท่วม log จนบัง error จริงบนหน้าสุขภาพเครื่อง."""
    import logging

    lg = logging.getLogger("asyncio")
    try:
        raise ConnectionResetError(10054, "An existing connection was forcibly closed")
    except ConnectionResetError:
        lg.error("Exception in callback _ProactorBasePipeTransport."
                 "_call_connection_lost(None)", exc_info=True)
    lg.error("asyncio พังจริงต้องเห็น")     # ปัญหาจริงของ asyncio ต้องไม่โดนกรองทิ้ง

    log = appmod.LOG_FILE.read_text(encoding="utf-8", errors="replace")
    assert "_call_connection_lost" not in log
    assert "asyncio พังจริงต้องเห็น" in log
