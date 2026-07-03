"""หน้า /calendar (B4): ปฏิทินกำลังรถต่อไซท์ — ว่าง = รถทั้งหมด − จอง/ใช้จริง − ซ่อม − คนลา
+ ลงบันทึกลาเร็วจากปฏิทิน (LeaveRecord) — display/planning เท่านั้น ไม่แตะเงิน
"""
import os, re, tempfile
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
from models import (
    AppUser, Employee, Vehicle, DailyJob, LeaveRecord,
    DispatchPlan, DispatchPlanLine, MaintRecord,
)

MONTH = "2026-07"


def _day_attrs(html: str, d: str) -> dict:
    """ดึงตัวเลขจาก data-attribute ของช่องวัน (ลำดับ attr คงที่ในตาราง)."""
    m = re.search(
        rf'data-d="{d}" data-avail="(\d+)" data-busy="(\d+)"'
        rf' data-repair="(\d+)" data-leave="(\d+)"', html)
    assert m, f"ไม่เจอช่องวัน {d} ในหน้า"
    return {"avail": int(m[1]), "busy": int(m[2]),
            "repair": int(m[3]), "leave": int(m[4])}


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # รถ LCB 3 คัน active + 1 คัน inactive (ต้องไม่ถูกนับ)
        s.add(Vehicle(plate_no="70-0001", vehicle_kind="truck", home_site_code="LCB"))
        s.add(Vehicle(plate_no="70-0002", vehicle_kind="head", home_site_code="LCB"))
        s.add(Vehicle(plate_no="70-0003", vehicle_kind="truck", home_site_code="LCB"))
        s.add(Vehicle(plate_no="70-0009", vehicle_kind="truck", home_site_code="LCB",
                      status="inactive"))
        # หางลาก — ไม่ใช่กำลังรถอิสระ ต้องไม่ถูกนับ
        s.add(Vehicle(plate_no="71-9999", vehicle_kind="tail", home_site_code="LCB"))
        s.add(Employee(code="T001", full_name="ทดสอบ หนึ่ง", home_site_code="LCB"))
        s.add(Employee(code="T002", full_name="ทดสอบ สอง", home_site_code="LCB"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _ids(s):
    v = {x.plate_no: x.id for x in s.exec(select(Vehicle)).all()}
    e = {x.code: x.id for x in s.exec(select(Employee)).all()}
    return v, e


def test_page_renders(client):
    b = client.get(f"/calendar?site=LCB&month={MONTH}").text
    assert "ปฏิทิน" in b and "LCB" in b
    # เดือน ก.ค. 2026 มี 31 วัน — ทุกวันมีช่อง และวันว่างเปล่า = ว่าง 3 คัน
    assert _day_attrs(b, "2026-07-08") == {"avail": 3, "busy": 0, "repair": 0, "leave": 0}


def test_month_math_booked_repair_leave(client):
    with Session(engine) as s:
        v, e = _ids(s)
        # จอง 10/7: แผนงาน + คัน 0001 (และเดลี่คันเดียวกัน — ต้องไม่นับซ้ำ)
        plan = DispatchPlan(plan_date=date(2026, 7, 10), site_code="LCB")
        s.add(plan); s.flush()
        s.add(DispatchPlanLine(plan_id=plan.id, vehicle_id=v["70-0001"],
                               plate_raw="70-0001", job_type="KAO"))
        s.add(DailyJob(work_date=date(2026, 7, 10), site_code="LCB",
                       head_vehicle_id=v["70-0001"], plate_no_raw="70-0001"))
        # ซ่อมค้าง (in_progress) คัน 0002 เริ่ม 9/7 → นับซ่อมตั้งแต่ 9/7 เป็นต้นไป
        s.add(MaintRecord(record_no="MTEST01", work_date=date(2026, 7, 9),
                          vehicle_id=v["70-0002"], status="in_progress"))
        # คนลา 10/7 จาก LeaveRecord
        s.add(LeaveRecord(driver_id=e["T001"], leave_date=date(2026, 7, 10),
                          leave_type="personal"))
        s.commit()
    b = client.get(f"/calendar?site=LCB&month={MONTH}").text
    # 10/7: รวม 3 − จอง 1 − ซ่อม 1 − ลา 1 = ว่าง 0
    assert _day_attrs(b, "2026-07-10") == {"avail": 0, "busy": 1, "repair": 1, "leave": 1}
    # 9/7: ซ่อมอย่างเดียว → ว่าง 2
    assert _day_attrs(b, "2026-07-09") == {"avail": 2, "busy": 0, "repair": 1, "leave": 0}
    # 8/7: ก่อนซ่อมเริ่ม → ว่าง 3
    assert _day_attrs(b, "2026-07-08")["avail"] == 3


def test_busy_resolves_plate_text(client):
    """เดลี่จริง (LCB/AYU) ไม่มี head_vehicle_id — ผูกด้วย plate_no_raw ข้อความ
    ต้อง match เข้าทะเบียน master แล้วนับเป็นรถไม่ว่าง."""
    with Session(engine) as s:
        s.add(DailyJob(work_date=date(2026, 7, 25), site_code="LCB",
                       plate_no_raw="70-0003", driver_raw_name="ทดสอบ หนึ่ง"))
        s.commit()
    b = client.get(f"/calendar?site=LCB&month={MONTH}").text
    assert _day_attrs(b, "2026-07-25") == {"avail": 2, "busy": 1, "repair": 0, "leave": 0}


def test_daily_row_kinds_idle_repair_leave(client):
    """แถวเดลี่ LCB จริง: status_code เป็นชื่อลูกค้า (=วิ่งงาน) ปน "รถจอด" (=ว่าง!),
    "ลา / ไม่พร้อม" (=ลา), "รถซ่อม/รถอุบัติเหตุ" (=ซ่อม) — ต้องแยกให้ถูก."""
    with Session(engine) as s:
        v, e = _ids(s)
        d = date(2026, 7, 28)
        s.add(DailyJob(work_date=d, site_code="LCB", plate_no_raw="70-0001",
                       status_code="KAO"))                      # งานจริง → busy
        s.add(DailyJob(work_date=d, site_code="LCB", plate_no_raw="70-0002",
                       status_code="รถจอด"))                    # จอด → ว่าง
        s.add(DailyJob(work_date=d, site_code="LCB", plate_no_raw="70-0003",
                       status_code="รถซ่อม"))                   # ซ่อม → repair
        s.add(DailyJob(work_date=d, site_code="LCB", driver_id=e["T001"],
                       status_code="ลา / ไม่พร้อม"))            # ลา → leave
        s.commit()
    b = client.get(f"/calendar?site=LCB&month={MONTH}").text
    # รวม 3 − วิ่ง 1 − ซ่อม 1 − ลา 1 = ว่าง 0 (คัน 0002 จอดว่างแต่คนลา 1 หักตามสูตร)
    assert _day_attrs(b, "2026-07-28") == {"avail": 0, "busy": 1, "repair": 1, "leave": 1}


def test_leave_from_daily_rows_counted(client):
    """วันลาที่ทีมคีย์ในเดลี่ (leave_status / "ลาหยุด" ใน destination) ต้องโผล่ในปฏิทินเอง."""
    with Session(engine) as s:
        v, e = _ids(s)
        s.add(DailyJob(work_date=date(2026, 7, 15), site_code="LCB",
                       driver_id=e["T001"], leave_status="sick"))
        s.add(DailyJob(work_date=date(2026, 7, 15), site_code="LCB",
                       driver_raw_name="ทดสอบ สอง", destination="ลาหยุด"))
        s.commit()
    b = client.get(f"/calendar?site=LCB&month={MONTH}").text
    assert _day_attrs(b, "2026-07-15")["leave"] == 2


def test_leave_post_range_dedupe_delete(client):
    with Session(engine) as s:
        _, e = _ids(s)
        emp_id = e["T002"]
    r = client.post("/calendar/leave", data={
        "driver_id": emp_id, "date_from": "2026-07-20", "date_to": "2026-07-21",
        "leave_type": "personal", "note": "ลากลับบ้าน",
        "site": "LCB", "month": MONTH}, follow_redirects=False)
    assert r.status_code in (302, 303)
    # ยิงซ้ำ — ต้องไม่เพิ่มแถวซ้ำ
    client.post("/calendar/leave", data={
        "driver_id": emp_id, "date_from": "2026-07-20", "date_to": "2026-07-21",
        "leave_type": "personal", "site": "LCB", "month": MONTH})
    with Session(engine) as s:
        rows = s.exec(select(LeaveRecord).where(LeaveRecord.driver_id == emp_id)).all()
        assert [r.leave_date.isoformat() for r in rows] == ["2026-07-20", "2026-07-21"]
        first_id = rows[0].id
    b = client.get(f"/calendar?site=LCB&month={MONTH}").text
    assert _day_attrs(b, "2026-07-20")["leave"] == 1
    client.post(f"/calendar/leave/{first_id}/delete",
                data={"site": "LCB", "month": MONTH})
    with Session(engine) as s:
        left = s.exec(select(LeaveRecord).where(LeaveRecord.driver_id == emp_id)).all()
        assert len(left) == 1 and left[0].leave_date.isoformat() == "2026-07-21"


def test_calendar_permissions():
    """หัวหน้าไซท์ (office) ลงลาได้; บัญชี/viewer ดูอย่างเดียว."""
    import permissions
    assert permissions.check("admin", "/calendar", "GET") == "edit"
    assert permissions.check("office", "/calendar", "POST") == "edit"
    assert permissions.check("accountant", "/calendar", "GET") == "view"
    assert permissions.check("accountant", "/calendar/leave", "POST") == "deny"
    assert permissions.check("viewer", "/calendar", "GET") == "view"
