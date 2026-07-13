"""เทียบทุกไซท์ โหมดรอบจ่าย: BIGC anchor เดือน M ต้องโชว์งานวิ่งเดือน M-1 (โอ 13ก.ค.).

ธรรมเนียมโอ: "BigC เดือน 6" = วิ่งงาน 1-31 พ.ค. จ่าย 1 ก.ค. — งวดจ่ายเดียวกับ
LCB 16/5-15/6 (tag 2026-06) และ AYU 26/5-25/6 (tag 2026-06) แต่ BIGC tag = เดือนวิ่ง
(2026-05). เดิมหน้า compare map BIGC = ปฏิทินเดือน anchor ตรงๆ → แถว BIGC เป็น 0
เพราะไปมองเดือนวิ่งถัดไปที่ยังไม่เกิด.
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date

from sqlmodel import SQLModel, Session, select

import main as appmod
from db_config import engine
from models import AppUser, DailyJob


def test_compare_cycle_bigc_maps_to_prior_run_month():
    """anchor เดือนปัจจุบัน: BIGC → เดือนวิ่งก่อนหน้า, LCB/AYU → รอบที่จบในเดือน anchor (เดิม)."""
    today = date.today()
    cy, cm = today.year, today.month
    py, pm = appmod._shift_year_month(cy, cm, -1)
    anchor_tag = f"{cy:04d}-{cm:02d}"

    start, end, tag = appmod._compare_cycle_period("BIGC", cy, cm)
    assert (start, end) == appmod._month_bounds(py, pm)
    assert tag == f"{py:04d}-{pm:02d}"

    # LCB/AYU ต้องไม่ขยับ — รอบที่จบในเดือน anchor เหมือนเดิม
    assert appmod._compare_cycle_period("LCB", cy, cm) == \
        appmod._cycle_period_for_tag("LCB", anchor_tag)
    assert appmod._compare_cycle_period("AYU", cy, cm) == \
        appmod._cycle_period_for_tag("AYU", anchor_tag)


def test_compare_page_shows_bigc_prior_month_jobs_and_link():
    """หน้า /finance view=compare mode=cycle: แถว BIGC โชว์ช่วงเดือนก่อน + ลิงก์พา tag เดือนก่อน."""
    from starlette.testclient import TestClient

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()

    today = date.today()
    cy, cm = today.year, today.month
    py, pm = appmod._shift_year_month(cy, cm, -1)
    prev_start, prev_end = appmod._month_bounds(py, pm)
    prev_tag = f"{py:04d}-{pm:02d}"

    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # งาน BIGC เดือนก่อน (ต้องโผล่) + เดือน anchor (ต้องไม่โผล่ในแถว BIGC)
        s.add(DailyJob(site_code="BIGC", work_date=prev_start.replace(day=10),
                       revenue_customer=1234))
        s.add(DailyJob(site_code="BIGC", work_date=today, revenue_customer=9999))
        s.commit()

    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        r = c.get(f"/finance?view=compare&mode=cycle&month={cy:04d}-{cm:02d}",
                  follow_redirects=True)
    assert r.status_code == 200
    # ช่วงวันที่จริงของแถว BIGC = เดือนก่อนทั้งเดือน
    assert f"{prev_start.strftime('%d/%m/%y')}–{prev_end.strftime('%d/%m/%y')}" in r.text
    # ลิงก์กดชื่อไซท์ต้องพา tag เดือนก่อน (ให้หน้า single ตรงกับตัวเลขที่เห็น)
    assert f"site=BIGC&mode=cycle&month={prev_tag}" in r.text
