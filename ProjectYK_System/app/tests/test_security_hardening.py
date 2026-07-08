"""Verify session-cookie hardening + response security headers.

These defend a logged-in session against a compromised/hostile network or a
malicious script: HttpOnly (JS can't read the cookie), Secure (never sent over
plain HTTP), SameSite (CSRF), plus HSTS / anti-clickjacking / nosniff headers.
"""


def _login_cookie_header(client):
    # Trigger a session cookie. TestClient uses http:// so we can't assert the
    # Secure attribute is *applied* here (Starlette omits Secure on insecure
    # transport), but we CAN assert HttpOnly + SameSite are present, and that
    # the app is configured with https_only=True (checked separately below).
    r = client.post("/login", data={"username": "yk1", "password": "changeme1"},
                    follow_redirects=False)
    return r.headers.get("set-cookie", "")


def test_session_cookie_is_httponly_and_samesite(client):
    cookie = _login_cookie_header(client)
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()


def test_app_configured_max_age_and_secure_in_prod():
    # Inspect the configured SessionMiddleware. Tests run with
    # YK_INSECURE_COOKIES=1 (http TestClient), so https_only is False here, but
    # a session timeout must always be set, and production (env unset) is Secure.
    import os
    import main
    found = None
    for mw in main.app.user_middleware:
        if mw.cls.__name__ == "SessionMiddleware":
            found = mw
            break
    assert found is not None
    kw = found.kwargs
    assert kw.get("max_age") and kw["max_age"] <= 60 * 60 * 12  # <= 12h
    # Secure flag is gated only by the explicit insecure-dev env var.
    assert os.environ.get("YK_INSECURE_COOKIES") == "1"  # tests opt out
    assert kw.get("https_only") is False  # because of the opt-out above


def test_security_headers_present(client):
    r = client.get("/login")
    h = {k.lower(): v for k, v in r.headers.items()}
    assert h.get("x-frame-options") == "DENY"
    assert h.get("x-content-type-options") == "nosniff"
    assert "strict-transport-security" in h
    assert "referrer-policy" in h


def _driver_cookie_secure(monkeypatch, insecure_env):
    # Call set_session_cookie directly against a real Response and read back the
    # Secure attribute of the driver session cookie. Same env gate as the main
    # SessionMiddleware (YK_INSECURE_COOKIES), so prod (env unset) => Secure.
    import os
    from starlette.responses import Response
    from services import driver_auth

    if insecure_env is None:
        monkeypatch.delenv("YK_INSECURE_COOKIES", raising=False)
    else:
        monkeypatch.setenv("YK_INSECURE_COOKIES", insecure_env)
    resp = Response()
    driver_auth.set_session_cookie(resp, "dummy-token")
    header = resp.headers.get("set-cookie", "")
    return "secure" in header.lower(), header


def test_driver_cookie_secure_in_prod(monkeypatch):
    # Production leaves YK_INSECURE_COOKIES unset -> driver cookie must be Secure
    # so drv_session is never sent over plain HTTP (matches the main app cookie).
    is_secure, header = _driver_cookie_secure(monkeypatch, None)
    assert "httponly" in header.lower()      # JS can't read it
    assert "samesite=lax" in header.lower()  # CSRF defence
    assert is_secure, f"driver cookie missing Secure in prod: {header!r}"


def test_driver_cookie_not_secure_in_insecure_dev(monkeypatch):
    # Local http dev / TestClient opts out via YK_INSECURE_COOKIES=1 so login
    # over plain http still works.
    is_secure, header = _driver_cookie_secure(monkeypatch, "1")
    assert not is_secure, f"driver cookie should skip Secure in dev: {header!r}"


def _oauth_state_cookie_secure(monkeypatch, secure_flag):
    # The Gmail OAuth CSRF-state cookie is a security cookie too (guards the
    # oauth callback). It rides the module-level _secure_cookies flag, which is
    # frozen at import (same flag the SessionMiddleware uses), so we patch the
    # flag directly rather than the env. Stub the authorize-URL builder so we
    # don't need real Google OAuth config.
    import main
    monkeypatch.setattr(main, "build_authorize_url", lambda state: "https://example/authorize")
    monkeypatch.setattr(main, "_secure_cookies", secure_flag)
    resp = main.email_oauth_start()
    header = resp.headers.get("set-cookie", "")
    return "secure" in header.lower(), header


def test_oauth_state_cookie_secure_in_prod(monkeypatch):
    # Production => _secure_cookies is True => OAuth state cookie must be Secure.
    is_secure, header = _oauth_state_cookie_secure(monkeypatch, True)
    assert "email_oauth_state" in header
    assert "httponly" in header.lower()
    assert is_secure, f"oauth_state cookie missing Secure in prod: {header!r}"


def test_oauth_state_cookie_not_secure_in_insecure_dev(monkeypatch):
    # Local http dev => _secure_cookies is False => no Secure so it still works.
    is_secure, _ = _oauth_state_cookie_secure(monkeypatch, False)
    assert not is_secure
