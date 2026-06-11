import base64
import hashlib
import hmac

from line_api import verify_signature

SECRET = "test-secret"
BODY = b'{"events":[]}'


def good_sig(secret: str, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def test_valid_signature_passes():
    assert verify_signature(SECRET, BODY, good_sig(SECRET, BODY)) is True


def test_bad_signature_fails():
    assert verify_signature(SECRET, BODY, "AAAA") is False
    assert verify_signature(SECRET, BODY, "") is False
    assert verify_signature(SECRET, BODY, None) is False
    assert verify_signature(SECRET, b'{"tampered":1}', good_sig(SECRET, BODY)) is False
