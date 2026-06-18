import sqlite3
import slip_reader.mvp_push as mp
from slip_reader.slip_source import company_slips


def test_push_sends_token_and_returns_json(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"status": "created", "id": 1}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr(mp.httpx, "post", fake_post)
    monkeypatch.setattr(mp.config, "SLIP_INGEST_TOKEN", "tok")
    out = mp.push({"slip_line_message_id": "1", "amount": 100.0})
    assert out["status"] == "created"
    assert captured["headers"]["X-Service-Token"] == "tok"


def test_company_slips_filters_company_side(tmp_path):
    db = tmp_path / "line_archive.db"
    con = sqlite3.connect(db)
    con.executescript("""
      create table line_group(group_id text, name text);
      create table line_user(user_id text, display_name text, alias text);
      create table line_message(line_message_id text, group_id text, user_id text,
        msg_type text, text text, media_path text, sent_at text);
      insert into line_group values('G','Y.K. หัวลาก LCB. ');
      insert into line_user values('u1','Miew','Miew');
      insert into line_user values('u2','นิพล','นิพล');
      insert into line_message values('m1','G','u1','image','', 'G\\2026-06\\a.jpg','2026-06-16 11:00:00');
      insert into line_message values('m2','G','u2','image','', 'G\\2026-06\\b.jpg','2026-06-16 11:01:00');
    """)
    con.commit()
    rows = company_slips(str(db), "หัวลาก LCB")
    assert len(rows) == 1 and rows[0]["message_id"] == "m1"
    assert rows[0]["day_ddmmyy"] == "16.06.26"
