"""COPY-LOCK guard: payruns whose net was copied verbatim from the salary sheet
(notes contain "[COPY-LOCK]") must NOT be recomputed via the /payroll/{id}/recompute
route — recomputing would overwrite the correct hand-loaded net with wrong engine
output. Engine-computed runs (no marker) must still recompute normally.

Regression guard for night-run 2026-06-28 (BIGC/AYU/LCB-history onboarded by copy).
"""
import os, tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import Employee, PayRun, PayRunItem, DailyJob, AppUser


@pytest.fixture()
def client_with_runs():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)

        # one driver, one daily job so the engine has something to compute
        s.add(Employee(id=97, code="D97", full_name="นาย นิพล สีโนนม่วง", pay_mode="lcb_trip",
                       home_site_code="LCB", status="active", base_salary=9240, care_allowance=3000))
        s.add(DailyJob(site_code="LCB", driver_id=97, work_date=date(2026, 5, 20),
                       status_code="KAO", revenue_customer=5000, trip_fee_driver=3000))

        # Run #2: a normal engine-computed draft (no COPY-LOCK) — recompute allowed
        s.add(PayRun(id=2, site_code="LCB", pay_cycle_tag="2026-06",
                     period_start=date(2026, 5, 16), period_end=date(2026, 6, 15),
                     status="draft", notes="normal engine run"))
        # Run #3: a copy-loaded draft ([COPY-LOCK]) with a hand-set net — recompute blocked
        s.add(PayRun(id=3, site_code="BIGC", pay_cycle_tag="2026-05",
                     period_start=date(2026, 5, 1), period_end=date(2026, 5, 31),
                     status="draft", notes="[COPY-LOCK] BIGC 2026-05 — net ลอกจาก รวม YK"))
        s.commit()

        from services.payroll import compute_pay_run
        compute_pay_run(s, s.get(PayRun, 2), recompute=True)

        # hand-load run #3's item with a net the engine would NOT produce (copy semantics)
        s.add(PayRunItem(pay_run_id=3, employee_id=97, site_code="BIGC",
                         pay_mode="bigc_monthly", days_worked=0,
                         gross_total=110614.0, net_pay=110614.0, computed_at=None,
                         note="ลอกยอด"))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _net(run_id):
    with Session(engine) as s:
        items = s.exec(select(PayRunItem).where(PayRunItem.pay_run_id == run_id)).all()
        return round(sum((i.net_pay or 0) for i in items), 2)


def test_copy_lock_blocks_recompute(client_with_runs):
    """Recompute on a [COPY-LOCK] run is rejected and the hand-loaded net is preserved."""
    before = _net(3)
    assert before == 110614.0  # the copied figure
    r = client_with_runs.post("/payroll/3/recompute", follow_redirects=False)
    # guard redirects with ?err=copylock instead of running compute_pay_run
    assert r.status_code == 303
    assert "copylock" in r.headers.get("location", "")
    after = _net(3)
    assert after == before, f"COPY-LOCK run net changed: {before} -> {after}"


def test_normal_run_still_recomputes(client_with_runs):
    """A run WITHOUT [COPY-LOCK] recomputes normally (guard does not over-block)."""
    r = client_with_runs.post("/payroll/2/recompute", follow_redirects=False)
    assert r.status_code == 303
    assert "copylock" not in r.headers.get("location", "")
    # run #2 was engine-computed from the daily job; net is positive and present
    assert _net(2) > 0
