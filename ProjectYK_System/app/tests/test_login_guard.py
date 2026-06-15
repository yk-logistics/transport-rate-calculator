import time
import pytest
import login_guard as g


@pytest.fixture(autouse=True)
def _reset_guard():
    g.reset_all()
    yield
    g.reset_all()


def test_username_locks_after_max_failures():
    for _ in range(g.MAX_USER_FAILS):
        g.record_failure(username="bob", ip="1.1.1.1")
    assert g.is_username_locked("bob") is True
    # a different user is unaffected
    assert g.is_username_locked("alice") is False


def test_success_clears_username_failures():
    for _ in range(g.MAX_USER_FAILS - 1):
        g.record_failure(username="bob", ip="1.1.1.1")
    g.record_success(username="bob", ip="1.1.1.1")
    assert g.is_username_locked("bob") is False


def test_ip_rate_limit_blocks_rapid_attempts_even_with_changing_usernames():
    # Simulate one IP spraying many different usernames quickly.
    for i in range(g.MAX_IP_ATTEMPTS):
        g.record_attempt(ip="9.9.9.9")
    assert g.is_ip_blocked("9.9.9.9") is True
    # a different IP is fine
    assert g.is_ip_blocked("8.8.8.8") is False


def test_username_lock_expires_after_cooldown(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(g.time, "time", lambda: t[0])
    for _ in range(g.MAX_USER_FAILS):
        g.record_failure(username="bob", ip="1.1.1.1")
    assert g.is_username_locked("bob") is True
    t[0] += g.USER_LOCK_SECONDS + 1
    assert g.is_username_locked("bob") is False
