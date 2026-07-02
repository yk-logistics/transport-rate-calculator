"""P&L ต้องเห็น KB ทุกขั้นตอน ไม่ซ่อน (โอ 2ก.ค.): ค่าขนส่งโชว์เต็ม แล้วหัก
"KB คืนเจ้าของงาน" เป็นบรรทัดแยก ก่อนได้รายรับสุทธิ — KB ไม่ใช่รายได้บริษัท.
เดิม P&L รวมค่าขนส่งเต็มโดยไม่หัก KB เลย → กำไรบวมเท่ายอด KB.
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"

from datetime import date

from sqlmodel import SQLModel, Session

from db_config import engine
from models import DailyJob
from services import finance as finance_svc


def test_monthly_pnl_deducts_kb_as_explicit_line():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        # 2 เที่ยว มี KB + 1 เที่ยวไม่มี KB (เดือน มิ.ย. 2026)
        s.add(DailyJob(site_code="LCB", work_date=date(2026, 6, 5),
                       revenue_customer=2410, kb_amount=110))
        s.add(DailyJob(site_code="LCB", work_date=date(2026, 6, 6),
                       revenue_customer=4260, kb_amount=110))
        s.add(DailyJob(site_code="LCB", work_date=date(2026, 6, 7),
                       revenue_customer=5000, kb_amount=0))
        s.commit()
        pnl = finance_svc.monthly_pnl(s, 2026, 6, "LCB")

    assert pnl["revenue_transport"] == 11670          # ค่าขนส่งเต็ม ไม่ซ่อน
    assert pnl["kb_return"] == 220                    # KB เป็นบรรทัดแยก มองเห็น
    assert pnl["revenue_total"] == 11450              # รายรับจริง = เต็ม − KB
    assert pnl["net_profit"] == pnl["revenue_total"] - pnl["cost_total"]


def test_finance_pages_render_with_kb_line():
    """หน้า /finance และ /finance/pnl ต้องเปิดได้ (ไม่ 500) และมีบรรทัด KB โชว์."""
    os.environ["YK_INSECURE_COOKIES"] = "1"
    from starlette.testclient import TestClient
    from sqlmodel import select
    import main as appmod
    from models import AppUser, DailyJob

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(DailyJob(site_code="LCB", work_date=date.today().replace(day=5),
                       revenue_customer=2410, kb_amount=110))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        r1 = c.get("/finance", follow_redirects=True)
        assert r1.status_code == 200
        r2 = c.get(f"/finance/pnl?year={date.today().year}&site=LCB", follow_redirects=True)
        assert r2.status_code == 200
        assert "KB คืน" in r2.text
