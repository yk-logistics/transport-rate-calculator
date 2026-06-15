from auth import hash_password, verify_password


def test_hash_then_verify_true():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h) is True


def test_verify_wrong_password_false():
    h = hash_password("s3cret")
    assert verify_password("nope", h) is False
