"""UX รอบ ก.ค. (docs/UX_REVIEW_2026-07.md):
- ข้อ 5: ตารางยาวหน้า /billing หัวตารางค้างตอนเลื่อน (sticky top-0) แบบ /maint/records
- ข้อ 6: มือถือ — เมนู 5 หมวดพับเป็น hamburger (จอ ≥md โชว์แถบเดิมเป๊ะ)
- ข้อ 8: /maint เมนูย่อยเรียงตามที่ใช้บ่อย — กล่องบิล/คีย์บิลยาง/บันทึกซ่อม
  ขึ้นก่อนพวก setup (ร้านค้า/อะไหล่/ติดตั้งยางชุดแรก)
"""
import os, tempfile
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
from models import AppUser, DailyJob


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(DailyJob(work_date=date(2026, 7, 10), site_code="LCB",
                       status_code="KAO", plate_no_raw="70-0001", doc_no="J1",
                       destination="โรงงานบางปะกง", revenue_customer=5000.0))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_nav_has_mobile_hamburger(client):
    """เมนูหลักต้องมีปุ่ม ☰ (โชว์เฉพาะจอแคบ md:hidden) และแถบเมนูซ่อนบนมือถือ
    (hidden md:flex) — เดสก์ท็อปเห็นแถบ 5 หมวดเหมือนเดิม."""
    b = client.get("/").text
    assert 'id="yk-nav-burger"' in b and "md:hidden" in b
    assert 'id="yk-nav-menu"' in b
    assert "hidden md:flex" in b


def test_billing_table_header_sticky(client):
    b = client.get("/billing?site=LCB&month=2026-07").text
    # ตารางรายลูกค้า (มีคอลัมน์ "ต้นทาง → ปลายทาง") ต้องมี thead แบบ sticky
    assert "ต้นทาง → ปลายทาง" in b
    assert 'thead class="bg-slate-50 text-slate-600 sticky top-0 z-10"' in b


def test_home_maint_alert_card(client):
    """ฟีเจอร์ใหม่ (แนว TMS: live maintenance visibility): หน้าแรกมีการ์ด
    "🔧 ซ่อมบำรุงต้องดู" เมื่อมี PM เลยกำหนด/ยางดอกต่ำ — ไม่มีของ = ไม่โชว์การ์ด."""
    from models import PmPlan, Tire
    from datetime import timedelta, date as _date
    b = client.get("/").text
    assert "ซ่อมบำรุงต้องดู" not in b          # ยังไม่มีอะไรค้าง → ไม่มีการ์ด
    with Session(engine) as s:
        s.add(PmPlan(code="PM0001", name="เปลี่ยนน้ำมันเครื่อง", status="active",
                     next_due_date=_date.today() - timedelta(days=3)))
        s.add(Tire(code="T0001", status="in_use", tread_depth_mm=2.0))
        s.commit()
    b = client.get("/").text
    assert "ซ่อมบำรุงต้องดู" in b
    assert "PM เลยกำหนด" in b and "ยางดอกต่ำ" in b


def test_home_invoice_overdue_card(client):
    """การ์ดหน้าแรก "ใบวางบิลเลยกำหนด" จากทะเบียน v52 (read-only) —
    นับเฉพาะ status issued/received ที่ due_date < วันนี้ (กติกาเดียวกับ
    n_overdue ของหน้า /billing/invoices); ไม่มีของ = ไม่โชว์การ์ด."""
    from models import Invoice
    from datetime import timedelta, date as _date
    b = client.get("/").text
    assert "ใบวางบิลเลยกำหนด" not in b
    today = _date.today()
    with Session(engine) as s:
        s.add(Invoice(inv_no="IV001", series="CY", inv_date=today - timedelta(days=40),
                      due_date=today - timedelta(days=10), status="issued"))
        s.add(Invoice(inv_no="IV002", series="CY", inv_date=today - timedelta(days=40),
                      due_date=today - timedelta(days=10), status="paid"))      # จ่ายแล้ว ไม่นับ
        s.add(Invoice(inv_no="IV003", series="CY", inv_date=today,
                      due_date=today + timedelta(days=30), status="issued"))    # ยังไม่ครบกำหนด
        s.commit()
    b = client.get("/").text
    assert "ใบวางบิลเลยกำหนด" in b
    assert 'id="home-inv-overdue">1<' in b


def test_maint_submenu_frequency_order(client):
    """เมนูย่อย /maint: ของใช้ประจำ (กล่องบิล → คีย์บิลยาง → บันทึกซ่อม)
    ต้องมาก่อนพวก setup ที่นานๆ ใช้ที (ร้านค้า/อู่ เป็นตัวแรกของกลุ่ม setup).
    เช็คด้วยข้อความ desc ที่มีเฉพาะในเมนูย่อย (ไม่ชนกับ nav/ปุ่มบน)."""
    b = client.get("/maint").text
    i_setup = b.index("ร้านอะไหล่/ยาง/อู่")          # desc ร้านค้า/อู่
    assert b.index("คัดบิลจากสแกนมือถือ") < i_setup   # desc กล่องบิล (ใหม่)
    assert b.index("บิลร้านยาง 1 ใบ") < i_setup       # desc คีย์บิลยาง
    assert b.index("ประวัติซ่อมทั้งหมด") < i_setup    # desc บันทึกซ่อม
