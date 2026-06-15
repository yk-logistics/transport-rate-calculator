import pytest
import login_guard as g


@pytest.fixture(autouse=True)
def _reset_guard():
    g.reset_all()
    yield
    g.reset_all()


def test_repeated_bad_logins_eventually_blocked(client):
    # yk1 exists with temp pw changeme1; hammer wrong passwords
    last = None
    for _ in range(g.MAX_USER_FAILS + 1):
        last = client.post("/login",
                           data={"username": "yk1", "password": "WRONG"},
                           headers={"CF-Connecting-IP": "5.5.5.5"},
                           follow_redirects=False)
    # after the lock kicks in, even the CORRECT password is refused while locked
    r = client.post("/login",
                    data={"username": "yk1", "password": "changeme1"},
                    headers={"CF-Connecting-IP": "5.5.5.5"},
                    follow_redirects=False)
    assert r.status_code == 429


def test_ip_spray_different_usernames_gets_429(client):
    r = None
    for i in range(g.MAX_IP_ATTEMPTS + 1):
        r = client.post("/login",
                        data={"username": f"ghost{i}", "password": "x"},
                        headers={"CF-Connecting-IP": "7.7.7.7"},
                        follow_redirects=False)
    assert r.status_code == 429
