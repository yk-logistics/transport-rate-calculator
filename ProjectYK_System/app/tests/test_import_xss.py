"""The /import/sheets handler builds an HTML fragment from the uploaded filename
and sheet names. Those must be HTML-escaped so a crafted name can't inject script.
"""
import io
from sqlmodel import Session, select
from db_config import engine
from models import AppUser
from auth import hash_password


def _login_admin(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.password_hash = hash_password("adminpass1")
        u.must_change_pw = False
        s.add(u)
        s.commit()
    client.post("/login", data={"username": "yk1", "password": "adminpass1"})
    return client


def test_malicious_filename_is_escaped(client):
    _login_admin(client)
    # a tiny xlsx is hard to forge; the handler reads sheets which may fail, but
    # the filename is echoed into the response BEFORE/around that. We assert the
    # raw script tag never appears unescaped in any response body.
    evil = '"><script>alert(1)</script>.xlsx'
    files = {"file": (evil, io.BytesIO(b"not a real xlsx"), "application/octet-stream")}
    r = client.post("/import/sheets", files=files)
    # Whatever the handler returns (fragment or error), it must not contain the
    # raw, unescaped script tag derived from the filename.
    assert "<script>alert(1)</script>" not in r.text
