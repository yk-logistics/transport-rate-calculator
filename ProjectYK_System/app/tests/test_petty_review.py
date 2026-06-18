from sqlmodel import Session, select
from db_config import engine
from models import PettyCashTxn, AppUser
from auth import hash_password
from datetime import date


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1"); u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def _mk_pending(msg_id="618000000000000020", amount=1280.0):
    with Session(engine) as s:
        t = PettyCashTxn(txn_date=date(2026, 6, 16), site_code="LCB", amount=amount,
                         direction="out", category="other", requester_raw="ปกรณ์",
                         memo="ปกรณ์ คืนตู้", status="pending_review",
                         source="line_slip", slip_line_message_id=msg_id)
        s.add(t); s.commit(); s.refresh(t)
        return t.id


def test_review_lists_pending(client):
    _login_admin(client); _mk_pending()
    r = client.get("/petty/review")
    assert r.status_code == 200 and "ปกรณ์" in r.text


def test_approve_posts_entry(client):
    _login_admin(client); pid = _mk_pending(msg_id="618000000000000021")
    r = client.post(f"/petty/review/{pid}/approve", data={}, follow_redirects=False)
    assert r.status_code in (302, 303)
    with Session(engine) as s:
        assert s.get(PettyCashTxn, pid).status == "posted"


def test_approve_with_override(client):
    _login_admin(client); pid = _mk_pending(msg_id="618000000000000022", amount=100.0)
    client.post(f"/petty/review/{pid}/approve",
                data={"amount": "107", "category": "loading"}, follow_redirects=False)
    with Session(engine) as s:
        t = s.get(PettyCashTxn, pid)
        assert t.amount == 107.0 and t.category == "loading" and t.status == "posted"


def test_reject_sets_draft(client):
    _login_admin(client); pid = _mk_pending(msg_id="618000000000000023")
    client.post(f"/petty/review/{pid}/reject", data={}, follow_redirects=False)
    with Session(engine) as s:
        assert s.get(PettyCashTxn, pid).status == "draft"
