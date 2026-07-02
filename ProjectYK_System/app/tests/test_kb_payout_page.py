"""หน้า /kb-payout: โอกรอกยอดโอนเอง → จับคู่อินวอย + KB โดยไม่ต้องมี AI
(กฎ feedback-no-ai-dependency 2ก.ค.). เทสต์ไม่ต่อ Drive จริง — mock load_all.
"""
import os, tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser
from services import kb_payout as kbp

# อินวอยจำลอง (เลขจากเคสจริง 1ก.ค.: โอน 19,027.98 = 023+026 หัก1%เฉพาะขนส่ง)
FAKE_ROWS = [
    {"inv": "CYIV2606-023", "customer": "JUN TAI", "quote": 4329, "ot": 200,
     "qty": 2, "transport": 10000.0, "ot_sheet": 0, "advances": 3214.98,
     "grand_total": 13214.98, "month_folder": "6.2026", "kb": 1142.0, "cust": "CY"},
    {"inv": "CYIV2606-026", "customer": "JUN TAI", "quote": 4329, "ot": 100,
     "qty": 1, "transport": 5000.0, "ot_sheet": 0, "advances": 963.0,
     "grand_total": 5963.0, "month_folder": "6.2026", "kb": 571.0, "cust": "CY"},
    {"inv": "CYIV2606-001", "customer": "MINKANG", "quote": 4284, "ot": 0,
     "qty": 1, "transport": 5000.0, "ot_sheet": 0, "advances": 100.0,
     "grand_total": 5100.0, "month_folder": "6.2026", "kb": 716.0, "cust": "CY"},
]


def test_kb_formula():
    assert kbp.kb_of({"transport": 10000, "quote": 4600, "qty": 2, "ot": 100}) == 700.0
    assert kbp.kb_of({"transport": 5000, "quote": 4200, "qty": 1, "ot": 0}) == 800.0


def test_match_amount_unique():
    res = kbp.match_amount(FAKE_ROWS, 19027.98)
    assert res["variant"] == "หัก ณ ที่จ่าย 1% เฉพาะค่าขนส่ง"
    assert len(res["combos"]) == 1
    c = res["combos"][0]
    assert {r["inv"] for r in c["invoices"]} == {"CYIV2606-023", "CYIV2606-026"}
    assert c["kb_total"] == 1713.0
    assert c["payout"] == 1541.7
    assert c["wht_cert"] == 51.39


def test_match_amount_not_found():
    assert kbp.match_amount(FAKE_ROWS, 123.45)["combos"] == []


@pytest.fixture()
def client(monkeypatch):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    monkeypatch.setattr(kbp, "load_all", lambda: list(FAKE_ROWS))
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_page_renders_and_matches(client):
    b = client.get("/kb-payout?amount=19027.98", follow_redirects=True).text
    assert "CYIV2606-023" in b and "CYIV2606-026" in b
    assert "1,541.70" in b          # ยอดโอนคืนเจ้าของงาน 90%
    assert "ชาญณรงค์" in b          # ชื่อผู้รับ
    assert "51.39" in b             # ใบหัก ณ ที่จ่าย 3%


def test_page_no_amount_lists_invoices(client):
    b = client.get("/kb-payout", follow_redirects=True).text
    assert "CYIV2606-001" in b
    assert "716" in b


def test_settle_excludes_from_match_and_undo(client):
    """ติ๊กใบรับแล้ว → หายจากการจับคู่; ยกเลิกติ๊ก → กลับมาจับคู่ได้."""
    # ติ๊ก 023 → ยอด 19,027.98 ต้องจับคู่ไม่เจอแล้ว
    client.post("/kb-payout/settle", data={"inv_no": "CYIV2606-023", "kb_amount": "1142"})
    b = client.get("/kb-payout?amount=19027.98", follow_redirects=True).text
    assert "ไม่เจอชุดอินวอย" in b
    assert "ติ๊กรับแล้ว" in b          # ใบอื่นยังมีปุ่มติ๊ก
    # ยกเลิกติ๊ก → จับคู่เจอเหมือนเดิม
    client.post("/kb-payout/settle", data={"inv_no": "CYIV2606-023", "undo": "1"})
    b = client.get("/kb-payout?amount=19027.98", follow_redirects=True).text
    assert "1,541.70" in b


def test_batch_settle_after_match(client):
    """ปุ่ม 'บันทึกรับแล้วทั้งชุด' ส่งหลายใบคั่น , — ทุกใบถูกติ๊ก + ยอดค้างรับลด."""
    from models import KbSettle
    client.post("/kb-payout/settle", data={
        "inv_no": "CYIV2606-023,CYIV2606-026",
        "kb_amount": "1142,571", "transfer_amount": "19027.98"})
    with Session(engine) as s:
        rows = s.exec(select(KbSettle)).all()
        assert {r.inv_no for r in rows} == {"CYIV2606-023", "CYIV2606-026"}
        assert all(r.transfer_amount == 19027.98 for r in rows)
    b = client.get("/kb-payout", follow_redirects=True).text
    assert "ค้างรับ 1 ใบ" in b        # เหลือ 001 ใบเดียว
    # cleanup — ตารางแชร์กับเทสต์อื่นใน module
    client.post("/kb-payout/settle", data={"inv_no": "CYIV2606-023,CYIV2606-026", "undo": "1"})


def test_kb_menu_admin_only():
    """permissions: /kb-payout เห็นเฉพาะ admin — office/accountant/viewer โดน deny."""
    import permissions
    assert permissions.check("admin", "/kb-payout", "GET") == "edit"
    for role in ("office", "accountant", "viewer"):
        assert permissions.check(role, "/kb-payout", "GET") == "deny"
