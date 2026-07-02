"""หน้า /admin/plan — โชว์แผน+progress จาก docs/PLAN_STATUS.json (admin เท่านั้น)."""
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


def test_plan_page_renders_progress(client):
    b = client.get("/admin/plan", follow_redirects=True).text
    assert "แพลน MVP" in b
    assert "A1" in b and "ลง KB 23 แถว CY" in b   # จาก PLAN_STATUS.json (dev มีไฟล์จริง)
    assert "เสร็จ" in b                            # งาน done อย่างน้อย 1
    assert "วันทำ" in b                            # การ์ดสรุปวัน


def test_plan_admin_only():
    import permissions
    assert permissions.check("admin", "/admin/plan", "GET") == "edit"
    for role in ("office", "accountant", "viewer"):
        assert permissions.check(role, "/admin/plan", "GET") == "deny"
