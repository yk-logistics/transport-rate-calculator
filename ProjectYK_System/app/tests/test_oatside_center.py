"""ศูนย์ Oatside (C3+C5): dashboard + แก้เงื่อนไขเอง (เขียนกลับ JSON + backup)."""
import json
import os, tempfile
from pathlib import Path

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
from services import oatside_runner as orun


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


@pytest.fixture()
def cfg_backup():
    """กันเทสต์แก้ไฟล์เงื่อนไขจริง — เก็บและคืนค่าเดิมเสมอ."""
    orig_cfg = orun.CONFIG.read_bytes()
    orig_ovr = orun.OVERRIDES.read_bytes()
    yield
    orun.CONFIG.write_bytes(orig_cfg)
    orun.OVERRIDES.write_bytes(orig_ovr)
    for b in orun.OATSIDE_DIR.glob("*.bak-*"):
        b.unlink(missing_ok=True)


def test_dashboard_and_settings_render(client):
    b = client.get("/oatside", follow_redirects=True).text
    assert "คำนวณรอบใหม่" in b and "Oatside" in b
    b = client.get("/oatside/settings", follow_redirects=True).text
    assert "ช่วงเรทค่าเที่ยว" in b and "ราคาดีเซลรายวัน" in b and "โหมดผู้เชี่ยวชาญ" in b


def test_save_diesel_price_adds_row_and_backup(client, cfg_backup):
    n_before = len(orun.load_json(orun.CONFIG)["diesel_price_history"])
    # ส่งแถวเดิมทั้งหมดกลับ + แถวใหม่ 1 แถว
    data = {}
    for i, r in enumerate(orun.load_json(orun.CONFIG)["diesel_price_history"]):
        data[f"{i}-date"] = r["date"]; data[f"{i}-price"] = str(r["price"])
        if r.get("source"):
            data[f"{i}-source"] = r["source"]
    data["new-date"] = "2026-07-03"; data["new-price"] = "32.5"
    r = client.post("/oatside/settings/diesel", data=data, follow_redirects=True)
    cfg = orun.load_json(orun.CONFIG)
    assert len(cfg["diesel_price_history"]) == n_before + 1
    assert {"date": "2026-07-03", "price": 32.5} == {k: cfg["diesel_price_history"][-1][k] for k in ("date", "price")}
    assert list(orun.OATSIDE_DIR.glob("oatside_config.json.bak-*"))  # มี backup


def test_save_rejects_bad_date(client, cfg_backup):
    r = client.post("/oatside/settings/diesel",
                    data={"new-date": "3/7/2026", "new-price": "30"}, follow_redirects=True)
    assert "ไม่บันทึก" in r.text
    # ไฟล์ไม่เปลี่ยน (แถวสุดท้ายไม่ใช่วันที่ผิด)
    assert not any(x.get("date") == "3/7/2026" for x in orun.load_json(orun.CONFIG)["diesel_price_history"])


def test_raw_mode_validates_json(client, cfg_backup):
    r = client.post("/oatside/settings/raw",
                    data={"which": "config", "json_text": "{ broken"}, follow_redirects=True)
    assert "ไม่บันทึก" in r.text


def test_run_requires_both_files(client):
    r = client.post("/oatside/run", data={}, follow_redirects=True)
    assert "ต้องเลือกไฟล์ครบ" in r.text
