def test_change_password_clears_must_change_and_works(client):
    client.post("/login", data={"username": "yk1", "password": "changeme1"})
    r = client.post("/account/password",
                    data={"old_password": "changeme1",
                          "new_password": "newpass123",
                          "confirm": "newpass123"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    # old password no longer works
    client.get("/logout")
    bad = client.post("/login", data={"username": "yk1", "password": "changeme1"},
                      follow_redirects=False)
    assert bad.status_code == 401
    # new password works and no longer forces change
    ok = client.post("/login", data={"username": "yk1", "password": "newpass123"},
                     follow_redirects=False)
    assert "/account/password" not in ok.headers.get("location", "")


def test_change_password_mismatch_rejected(client):
    # Use a dedicated user so this test is independent of yk1's mutated password.
    from sqlmodel import Session, select
    from db_config import engine
    from models import AppUser
    from auth import hash_password
    with Session(engine) as s:
        if not s.exec(select(AppUser).where(AppUser.username == "pwtest")).first():
            s.add(AppUser(username="pwtest", password_hash=hash_password("origpass1"),
                          display_name="pwtest", role="viewer", status="active",
                          must_change_pw=False))
            s.commit()
    client.post("/login", data={"username": "pwtest", "password": "origpass1"})
    r = client.post("/account/password",
                    data={"old_password": "origpass1",
                          "new_password": "aaaaaa11",
                          "confirm": "bbbbbb22"},
                    follow_redirects=False)
    assert r.status_code in (200, 400)
