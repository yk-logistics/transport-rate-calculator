"""C1 เช็คความครบก่อนวางบิล: แถบ "พร้อมวางบิล?" บนหน้า /billing ต่อลูกค้า+เดือน
นับจากแถวเดลี่ทั้งหมดในช่วง (ไม่ใช่แค่ revenue>0): ราคาว่าง / ไม่มีเลขใบงาน /
ซ้ำ วัน+ทะเบียน+ตู้ — แถวรถจอด/ลา ไม่ใช่งานวางบิล ต้องไม่ถูกนับ
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

MONTH = "2026-07"
D = date(2026, 7, 10)


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # ลูกค้า KAO: งานครบ (ราคา+เลขใบงาน) 1 แถว → ไม่ติดธง
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KAO",
                       plate_no_raw="70-0001", doc_no="J-001",
                       destination="โรงงาน", revenue_customer=5000))
        # ลูกค้า NHL: ราคาว่าง 2 แถว + ไม่มีเลขใบงาน (แถวเดียวกัน)
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="NHL",
                       plate_no_raw="70-0002", destination="ลานตู้"))
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="NHL",
                       plate_no_raw="70-0003", destination="ลานตู้"))
        # ลูกค้า CJ: ตู้ซ้ำ วัน+ทะเบียน+ตู้เดียวกัน 2 แถว (มีราคา+เลขครบ)
        for _ in range(2):
            s.add(DailyJob(work_date=D, site_code="LCB", status_code="CJ",
                           plate_no_raw="70-0004", container_no="TCNU1234567",
                           doc_no="J-00x", destination="ท่าเรือ",
                           revenue_customer=4000))
        # รถจอด + ลา — ไม่ใช่งานวางบิล ห้ามติดธงราคาว่าง
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="รถจอด",
                       plate_no_raw="70-0005"))
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="ลา / ไม่พร้อม",
                       driver_raw_name="คนขับ ลา"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_ready_strip_counts(client):
    b = client.get(f"/billing?site=LCB&month={MONTH}").text
    # NHL: ราคาว่าง 2 + ไม่มีเลขใบงาน 2
    assert 'data-ready="NHL" data-noprice="2" data-nodoc="2" data-dup="0"' in b
    # CJ: ตู้ซ้ำ 2 แถว
    assert 'data-ready="CJ" data-noprice="0" data-nodoc="0" data-dup="2"' in b
    # KAO ครบ — ไม่มีการ์ดปัญหา
    assert 'data-ready="KAO"' not in b
    # แถวรถจอด/ลา ไม่โผล่เป็นลูกค้า
    assert 'data-ready="รถจอด"' not in b


def test_ready_all_green_when_fixed(client):
    with Session(engine) as s:
        for j in s.exec(select(DailyJob).where(DailyJob.status_code == "NHL")).all():
            j.revenue_customer = 3000; j.doc_no = "J-9"; s.add(j)
        dups = s.exec(select(DailyJob).where(DailyJob.status_code == "CJ")).all()
        s.delete(dups[1])
        s.commit()
    b = client.get(f"/billing?site=LCB&month={MONTH}").text
    assert 'data-ready="' not in b
    assert "พร้อมวางบิล" in b
