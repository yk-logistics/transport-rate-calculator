"""The driver PWA (/driver/*) has its OWN auth (DriverSession + PIN), separate
from AppUser RBAC. RBAC must not hijack it — but /driver/* must still require a
driver session (not be wide open).
"""


def test_driver_login_page_not_hijacked_by_admin_rbac(client):
    # Unauthenticated hit to the driver login page must show the driver login,
    # NOT bounce to the admin /login.
    r = client.get("/driver/login", follow_redirects=False)
    assert r.status_code == 200  # driver login page renders


def test_driver_protected_page_requires_driver_session(client):
    # Without a driver session, a protected driver page must redirect to the
    # DRIVER login (its own auth), not be served and not hit admin /login.
    r = client.get("/driver/today", follow_redirects=False)
    assert r.status_code in (302, 303)
    loc = r.headers.get("location", "")
    assert "/driver/login" in loc  # driver's own gate, not admin /login
