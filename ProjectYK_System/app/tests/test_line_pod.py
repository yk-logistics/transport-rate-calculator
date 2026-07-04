# -*- coding: utf-8 -*-
"""F3 POD: เสนอผูกรูป↔เดลี่ (บริบท ±10 นาที, วัน ±1, ตู้/ทะเบียน) + review + evidence ZIP."""
import io, os, sqlite3, tempfile, zipfile
from datetime import date, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, DailyJob, JobMedia, LineGroupMap

D = date.today() - timedelta(days=1)


@pytest.fixture()
def line_db(tmp_path, monkeypatch):
    p = tmp_path / "line_archive.db"
    con = sqlite3.connect(p)
    con.executescript("""
        CREATE TABLE line_group (group_id TEXT PRIMARY KEY, name TEXT, discord_channel_id TEXT, joined_at TEXT, active INT);
        CREATE TABLE line_user (user_id TEXT PRIMARY KEY, display_name TEXT, alias TEXT);
        CREATE TABLE line_message (id INTEGER PRIMARY KEY, line_message_id TEXT, group_id TEXT,
            user_id TEXT, msg_type TEXT, text TEXT, media_path TEXT, sent_at TEXT, received_at TEXT, discord_forwarded INT);
    """)
    con.execute("INSERT INTO line_group VALUES ('g1','ลูกค้า KLND','','2026-06-01',1)")
    con.execute("INSERT INTO line_user VALUES ('u1','ประสาน','KLND')")
    media = tmp_path / "line_media"; media.mkdir()
    (media / "pod1.jpg").write_bytes(b"podjpg")
    ts = f"{D.isoformat()} 10:0"
    con.execute("INSERT INTO line_message VALUES (1,'m1','g1','u1','text','ส่งแล้วครับ ตู้ FFAU6453012 คัน 71-6803',NULL,?,?,1)", (ts + "0", ts + "0"))
    con.execute(f"INSERT INTO line_message VALUES (2,'m2','g1','u1','image','','{(media / 'pod1.jpg').as_posix()}',?,?,1)", (ts + "5", ts + "5"))
    con.commit(); con.close()
    monkeypatch.setenv("YK_LINE_DB", str(p))
    return p


@pytest.fixture()
def client(line_db):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        s.add(LineGroupMap(group_id="g1", label="ลูกค้า KLND", kind="customer",
                           customer_name="KLND", site_code="LCB", active=True))
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       plate_no_raw="71-6803", container_no="FFAU6453012",
                       revenue_customer=4900.0, invoice_no="KTIV2607-001"))
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       plate_no_raw="72-9999", container_no="XXXU0000000",
                       revenue_customer=4900.0, invoice_no=""))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def _job_id(cntr):
    with Session(engine) as s:
        return s.exec(select(DailyJob).where(DailyJob.container_no == cntr)).first().id


def test_pod_page_proposes_matching_job(client):
    r = client.get("/line/pod")
    assert r.status_code == 200
    assert "FFAU6453012" in r.text          # ตู้จากบริบทข้อความก่อนรูป
    assert "KTIV2607-001" in r.text         # แถวเดลี่ที่ match โผล่เป็นตัวเลือก


def test_link_then_photo_leaves_review(client):
    jid = _job_id("FFAU6453012")
    client.post("/line/pod/mark", data={"msg_id": 2, "action": "link", "job_id": jid})
    with Session(engine) as s:
        jm = s.exec(select(JobMedia)).first()
        assert jm.daily_job_id == jid and jm.status == "linked" and jm.by_user == "yk1"
    assert "ไม่มีรูปรอรีวิว" in client.get("/line/pod").text


def test_skip_records_and_hides(client):
    client.post("/line/pod/mark", data={"msg_id": 2, "action": "skip"})
    with Session(engine) as s:
        assert s.exec(select(JobMedia)).first().status == "skipped"
    assert "ไม่มีรูปรอรีวิว" in client.get("/line/pod").text


def test_evidence_page_and_zip(client):
    jid = _job_id("FFAU6453012")
    client.post("/line/pod/mark", data={"msg_id": 2, "action": "link", "job_id": jid})
    month = D.strftime("%Y-%m")
    r = client.get(f"/billing/evidence?series=KMMT&month={month}")
    assert r.status_code == 200
    assert "/line/media/2" in r.text            # thumbnail โผล่
    assert "ยังไม่มีรูป" in r.text                # แถวที่สองไม่มีรูป
    z = client.get(f"/billing/evidence?series=KMMT&month={month}&download=zip")
    assert z.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    names = zf.namelist()
    assert any("KTIV2607-001/" in n and "FFAU6453012" in n for n in names)
    assert zf.read(names[0]) == b"podjpg"


def test_jobref_and_docno_reverse_match(client):
    """เลข Job/doc ของเดลี่โผล่ในข้อความรอบรูป = match แรงสุด (วัดจริง 4ก.ค.: KLND/DHL)."""
    from services import line_pod as lp
    with Session(engine) as s:
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       plate_no_raw="71-0001", job_ref="KLND26-015737"))
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       plate_no_raw="71-0002", doc_no='"66144000327274/316'))
        s.commit()
        j1 = s.exec(select(DailyJob).where(DailyJob.job_ref == "KLND26-015737")).first()
        j2 = s.exec(select(DailyJob).where(DailyJob.plate_no_raw == "71-0002")).first()

        cand = {"sent_date": D, "containers": [], "plates": [],
                "ctx_text": "เช็คตู้หน่อยค่ะ JOB. KLND26-015737 AGENT. ONE"}
        m = lp.match_daily_jobs(s, cand, ("KLND",))
        assert m[0]["job_id"] == j1.id and m[0]["score"] >= 4

        cand = {"sent_date": D, "containers": [], "plates": [],
                "ctx_text": "ส่งงาน 66144000327274 เรียบร้อย"}
        m = lp.match_daily_jobs(s, cand, ("KLND",))
        assert m[0]["job_id"] == j2.id and m[0]["score"] >= 4


def test_dual_container_row_matches_either(client):
    """แถวตู้คู่ 'AAAA/BBBB' ต้อง match รูปที่อ้างตู้ใดตู้หนึ่ง (เจอจริงในเดลี่ 12 แถว/ไตรมาส)."""
    from services import line_pod as lp
    with Session(engine) as s:
        s.add(DailyJob(work_date=D, site_code="LCB", status_code="KLND",
                       container_no="TWCU2324417/TWCU2138876", plate_no_raw="71-0003"))
        s.commit()
        j = s.exec(select(DailyJob).where(DailyJob.plate_no_raw == "71-0003")).first()
        cand = {"sent_date": D, "containers": ["TWCU2138876"], "plates": [], "ctx_text": ""}
        m = lp.match_daily_jobs(s, cand, ("KLND",))
        assert m and m[0]["job_id"] == j.id and m[0]["score"] >= 3


def test_zip_empty_404(client):
    month = D.strftime("%Y-%m")
    assert client.get(f"/billing/evidence?series=KMMT&month={month}&download=zip").status_code == 404
