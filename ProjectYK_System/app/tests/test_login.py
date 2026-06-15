def test_login_page_renders(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert "username" in r.text.lower()


def test_login_success_sets_session_and_redirects(client):
    r = client.post("/login", data={"username": "yk1", "password": "changeme1"},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    # must_change_pw -> redirect target is the password page
    assert "/account/password" in r.headers.get("location", "")


def test_login_wrong_password_rejected(client):
    r = client.post("/login", data={"username": "yk1", "password": "WRONG"},
                    follow_redirects=False)
    assert r.status_code in (200, 401)
    assert "/daily" not in r.headers.get("location", "")


def test_logout_clears_session(client):
    client.post("/login", data={"username": "yk1", "password": "changeme1"})
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")
