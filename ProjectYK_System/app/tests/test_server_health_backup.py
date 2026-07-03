"""S1: การ์ดสำรอง 3 ชั้นบน /admin/server-health + ปุ่ม Backup ลงแผ่น (ชั้น 2).
ชั้น 2 ใช้ robocopy จริง (Windows มีเสมอ) ลง target ทดสอบผ่าน env — ไม่แตะไดรฟ์จริง.
"""
import json, os, tempfile, time
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


@pytest.fixture()
def client(tmp_path, monkeypatch):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u); s.commit()
    # ชั้น 1: ไฟล์สถานะปลอม (ts = 2 ชม.ที่แล้ว → ยังไม่ถึงเกณฑ์แดง 26 ชม.)
    from datetime import datetime, timedelta
    status = tmp_path / "last_run.json"
    status.write_text(json.dumps({
        "ok": True,
        "ts": (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds"),
        "zip": "yk_hot_20260703_030000.zip",
        "size_mb": 13.6, "drive_ok": False, "drive_error": "sa quota", "error": None,
    }), encoding="utf-8")
    monkeypatch.setenv("YK_BACKUP_STATUS", str(status))
    # ชั้น 2: source + target ทดสอบ
    line_dir = tmp_path / "line"; (line_dir / "line_media").mkdir(parents=True)
    (line_dir / "line_media" / "img1.jpg").write_bytes(b"x" * 100)
    hot_dir = tmp_path / "hot"; hot_dir.mkdir()
    (hot_dir / "yk_hot_test.zip").write_bytes(b"z" * 100)
    target = tmp_path / "extdrive"; target.mkdir()
    monkeypatch.setenv("YK_LINE_DIR", str(line_dir))
    monkeypatch.setenv("YK_BACKUP_ROOT", str(hot_dir))
    monkeypatch.setenv("YK_EXT_TEST_TARGET", str(target))
    appmod._HEALTH_CACHE["at"] = None  # กัน cache ข้ามเทสต์
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c, target


def test_health_page_shows_hot_backup(client):
    c, _ = client
    b = c.get("/admin/server-health").text
    assert "yk_hot_20260703_030000.zip" in b
    assert "13.6 MB" in b
    assert "Drive ยังไม่ทำงาน" in b          # SA quota → ธงเหลือง
    assert 'data-hot-level="ok"' in b        # 2 ชม.ที่แล้ว + ok → เขียว (แดงเมื่อ >26 ชม.)


def test_external_backup_runs_and_records(client):
    c, target = client
    r = c.post("/admin/server-health/backup-external",
               data={"target": str(target)}, follow_redirects=False)
    assert r.status_code == 303
    for _ in range(60):                      # รอ thread robocopy (ไฟล์จิ๋ว ~วินาที)
        if not appmod._EXT_BACKUP["running"]:
            break
        time.sleep(0.5)
    assert appmod._EXT_BACKUP["ok"] is True, appmod._EXT_BACKUP["log"]
    assert (Path(target) / "YK_BACKUP" / "YK_ARCHIVE.txt").exists()
    assert (Path(target) / "YK_BACKUP" / "line_media" / "img1.jpg").exists()
    assert (Path(target) / "YK_BACKUP" / "hot_zips" / "yk_hot_test.zip").exists()
    assert appmod.get_setting("external_backup_last").startswith("20")
    b = c.get("/admin/server-health").text
    assert "วันนี้" in b                      # การ์ดชั้น 2 อัปเดต


def test_external_backup_rejects_unknown_target(client):
    c, _ = client
    r = c.post("/admin/server-health/backup-external",
               data={"target": "Q:/"}, follow_redirects=False)
    assert r.status_code == 400
