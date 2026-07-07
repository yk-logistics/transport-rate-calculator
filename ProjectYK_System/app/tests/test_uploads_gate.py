"""S2 follow-up: /uploads ต้องไม่ public — เสิร์ฟเฉพาะ session ระบบ หรือ access-link token.

ผู้ใช้ /uploads จริงมี 3 ทาง (สำรวจ 6ก.ค.):
  1. หน้า admin (/admin/submissions, /tires/vehicle) — มี AppUser session
  2. API "ดูรูปงานนี้" ใน grid — มี AppUser session
  3. /check/mechanic ผ่าน magic link — ไม่มี session ต้องพ่วง ?t=<token> ที่รูป
Driver PWA ไม่โหลด /uploads เลย (preview เป็น client-side ก่อนอัปโหลด).
"""
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from db_config import engine
from models import AccessLink, AppUser
from auth import hash_password
import services.access_link as al
import main as appmod


def _make_upload_file():
    name = f"test_gate_{uuid.uuid4().hex}.jpg"
    path = appmod._uploads_dir / name
    path.write_bytes(b"fake-jpeg-bytes")
    return name, path


def _make_link(role="mechanic", hours=1):
    tok = al.make_token(role, ttl_seconds=hours * 3600)
    with Session(engine) as s:
        s.add(AccessLink(token=tok, role=role, created_by="test",
                         expires_at=datetime.utcnow() + timedelta(hours=hours)))
        s.commit()
    return tok


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_uploads_rejects_anonymous(client):
    name, path = _make_upload_file()
    try:
        r = client.get(f"/uploads/{name}", follow_redirects=False)
        assert r.status_code in (401, 403)
    finally:
        path.unlink()


def test_uploads_serves_logged_in_user(client):
    name, path = _make_upload_file()
    try:
        _login_admin(client)
        r = client.get(f"/uploads/{name}")
        assert r.status_code == 200
        assert r.content == b"fake-jpeg-bytes"
    finally:
        path.unlink()


def test_uploads_serves_valid_access_link_token(client):
    name, path = _make_upload_file()
    try:
        tok = _make_link("mechanic")
        r = client.get(f"/uploads/{name}?t={tok}")
        assert r.status_code == 200
        assert r.content == b"fake-jpeg-bytes"
    finally:
        path.unlink()


def test_uploads_token_fetch_does_not_inflate_use_count(client):
    """โหลดรูปด้วย token ไม่บวก use_count — ตัวนับ /admin/check-links ต้องหมายถึง
    'เปิดลิงก์กี่ครั้ง' ไม่ใช่โดนบวกตามจำนวนรูปในหน้า."""
    name, path = _make_upload_file()
    try:
        tok = _make_link("mechanic")
        for _ in range(3):
            assert client.get(f"/uploads/{name}?t={tok}").status_code == 200
        with Session(engine) as s:
            link = s.exec(select(AccessLink)).first()
            assert link.use_count == 0
    finally:
        path.unlink()


def test_uploads_rejects_bad_token(client):
    name, path = _make_upload_file()
    try:
        r = client.get(f"/uploads/{name}?t=not-a-real-token", follow_redirects=False)
        assert r.status_code in (401, 403)
    finally:
        path.unlink()


def test_uploads_blocks_path_traversal(client):
    _login_admin(client)
    # เข้ารหัส .. กันไคลเอนต์ normalize path ก่อนส่ง
    r = client.get("/uploads/..%2Fmain.py", follow_redirects=False)
    assert r.status_code in (400, 403, 404)
    assert b"FastAPI" not in r.content


def test_uploads_missing_file_404_when_authed(client):
    _login_admin(client)
    r = client.get("/uploads/no_such_file_xyz.jpg")
    assert r.status_code == 404


def test_check_mechanic_photo_urls_carry_token(client):
    """หน้า /check/mechanic ฝังรูปด้วย ?t=<token> — ไม่งั้นช่างเห็นรูปไม่ขึ้นหลังปิด public."""
    from models import Tire, TireEvent
    with Session(engine) as s:
        tire = Tire(code="T-TEST1")
        s.add(tire); s.commit(); s.refresh(tire)
        s.add(TireEvent(tire_id=tire.id, event_date=datetime.utcnow().date(),
                        event_type="inspect", condition_flag="crack",
                        tread_after_mm=0.0, photo_paths="ph1.jpg"))
        s.commit()
    tok = _make_link("mechanic")
    r = client.get(f"/check/mechanic?t={tok}")
    assert r.status_code == 200
    assert f"/uploads/ph1.jpg?t={tok}" in r.text
