def test_app_boots(client):
    r = client.get("/login")
    assert r.status_code in (200, 404)  # route added later; harness just confirms boot
