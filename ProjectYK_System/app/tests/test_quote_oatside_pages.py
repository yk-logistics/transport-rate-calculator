"""/quote (เครื่องคิดราคา) + /oatside/report — เสิร์ฟไฟล์เดิมตรงๆ ในระบบ (admin เท่านั้น)."""
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


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_quote_serves_calculator(client):
    r = client.get("/quote", follow_redirects=True)
    assert r.status_code == 200
    assert "คำนวณค่าขนส่งตามราคาน้ำมัน" in r.text   # title ของไฟล์เดิม


def test_oatside_report_serves_index(client):
    r = client.get("/oatside/report", follow_redirects=True)
    assert r.status_code == 200 and len(r.content) > 1000


def test_oatside_report_blocks_path_traversal(client):
    r = client.get("/oatside/report/../../app.db", follow_redirects=True)
    assert r.status_code == 404


def test_quote_admin_only():
    import permissions
    assert permissions.check("admin", "/quote", "GET") == "edit"
    for role in ("office", "accountant", "viewer"):
        assert permissions.check(role, "/quote", "GET") == "deny"
        assert permissions.check(role, "/oatside/report", "GET") == "deny"
