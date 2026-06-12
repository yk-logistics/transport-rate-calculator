import db


def make_conn():
    return db.connect(":memory:")


def test_insert_message_and_dedupe():
    conn = make_conn()
    ok = db.insert_message(conn, line_message_id="m1", group_id="g1", user_id="u1",
                           msg_type="text", text="สวัสดี", sent_at="2026-06-11 09:00:00")
    assert ok is True
    dup = db.insert_message(conn, line_message_id="m1", group_id="g1", user_id="u1",
                            msg_type="text", text="สวัสดี", sent_at="2026-06-11 09:00:00")
    assert dup is False
    rows = conn.execute("SELECT * FROM line_message").fetchall()
    assert len(rows) == 1
    assert rows[0]["discord_forwarded"] == 0


def test_pending_and_mark_forwarded():
    conn = make_conn()
    db.insert_message(conn, line_message_id="m1", group_id="g1", user_id="u1",
                      msg_type="text", text="a", sent_at="2026-06-11 09:00:00")
    db.insert_message(conn, line_message_id="m2", group_id="g1", user_id="u1",
                      msg_type="text", text="b", sent_at="2026-06-11 09:01:00")
    assert [r["line_message_id"] for r in db.pending_forwards(conn)] == ["m1", "m2"]
    db.mark_forwarded(conn, "m1")
    assert [r["line_message_id"] for r in db.pending_forwards(conn)] == ["m2"]


def test_ensure_group_and_channel():
    conn = make_conn()
    g = db.ensure_group(conn, "g1", joined_at="2026-06-11 09:00:00")
    assert g["group_id"] == "g1" and g["discord_channel_id"] is None
    db.set_group_name(conn, "g1", "ทีมงาน LCB")
    db.set_group_channel(conn, "g1", "ch99")
    g = db.ensure_group(conn, "g1")  # เรียกซ้ำต้องไม่ทับค่าเดิม
    assert g["name"] == "ทีมงาน LCB" and g["discord_channel_id"] == "ch99"


def test_set_group_category():
    conn = make_conn()
    db.ensure_group(conn, "g1")
    db.set_group_category(conn, "g1", "ซ่อมบำรุง")
    g = db.ensure_group(conn, "g1")
    assert g["category"] == "ซ่อมบำรุง"


def test_upsert_user_keeps_alias():
    conn = make_conn()
    db.upsert_user(conn, "u1", "สมชาย")
    conn.execute("UPDATE line_user SET alias='ชายโม่' WHERE user_id='u1'")
    conn.commit()
    db.upsert_user(conn, "u1", "สมชาย ใจดี")  # ชื่อ LINE เปลี่ยน
    row = db.get_user(conn, "u1")
    assert row["display_name"] == "สมชาย ใจดี"
    assert row["alias"] == "ชายโม่"
