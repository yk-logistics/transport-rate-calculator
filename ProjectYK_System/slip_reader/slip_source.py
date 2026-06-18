from __future__ import annotations
import os
import sqlite3

COMPANY = ["Miew", "Khao", "Luktan", "ตาล", "หมิว"]


def _media_root(db_path):
    return os.path.join(os.path.dirname(db_path), "line_media")


def company_slips(db_path, group_like="หัวลาก LCB", since=None):
    """Company-side image messages (candidate slips) from the LCB group.

    Returns [{message_id, sent_at, media_abspath, day_ddmmyy}]. Filters to the
    company side (Miew / ตาล / …) — driver photos are job docs, not transfer slips.
    """
    con = sqlite3.connect(db_path)
    row = con.execute("select group_id from line_group where name like ?",
                      (f"%{group_like}%",)).fetchone()
    if not row:
        return []
    gid = row[0]
    q = ("select m.line_message_id, m.sent_at, m.media_path, "
         "coalesce(u.alias,u.display_name) who "
         "from line_message m left join line_user u on u.user_id=m.user_id "
         "where m.group_id=? and m.msg_type='image' and m.media_path is not null")
    args = [gid]
    if since:
        q += " and m.sent_at >= ?"
        args.append(since)
    q += " order by m.sent_at"
    out = []
    for mid, sent, media, who in con.execute(q, args):
        if not who or not any(c in who for c in COMPANY):
            continue
        dd = sent[8:10]
        mm = sent[5:7]
        yy = sent[2:4]
        out.append({"message_id": mid, "sent_at": sent,
                    "media_abspath": os.path.join(_media_root(db_path), media),
                    "day_ddmmyy": f"{dd}.{mm}.{yy}"})
    return out


def day_plans(db_path, group_like, day_ddmmyy):
    """All long text messages in the group whose body mentions the target day.

    Returns [(sent_at, text)] for plan_context.plan_lookup to pick the latest.
    """
    con = sqlite3.connect(db_path)
    gid = con.execute("select group_id from line_group where name like ?",
                      (f"%{group_like}%",)).fetchone()[0]
    rows = con.execute(
        "select sent_at, text from line_message where group_id=? and msg_type='text' "
        "and text is not null and length(text)>200 order by sent_at", (gid,)).fetchall()
    return [(s, t) for (s, t) in rows if day_ddmmyy in t]
