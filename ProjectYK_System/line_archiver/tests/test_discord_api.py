import json

import httpx

from discord_api import DiscordClient, channel_name_for


def test_thai_name_kept_spaces_dashed():
    assert channel_name_for("ทีมงาน LCB") == "line-ทีมงาน-lcb"


def test_strips_forbidden_chars():
    assert channel_name_for("A/B (test)!") == "line-ab-test"


def test_empty_falls_back():
    assert channel_name_for("") == "line-group"
    assert channel_name_for(None) == "line-group"


# ---- category methods (httpx.MockTransport — ไม่แตะเน็ตจริง) ----

def make_client(handler) -> DiscordClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return DiscordClient("tok", "guild1", http=http)


def test_ensure_category_creates_when_missing():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(200, json=[])  # ยังไม่มี category
        body = json.loads(request.content)
        assert body["type"] == 4 and body["name"] == "ซ่อมบำรุง"
        return httpx.Response(201, json={"id": "cat-1"})

    client = make_client(handler)
    assert client.ensure_category("ซ่อมบำรุง") == "cat-1"
    assert ("POST", "/api/v10/guilds/guild1/channels") in calls


def test_ensure_category_reuses_existing_and_caches():
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            posts.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[
                {"id": "cat-9", "name": "ซ่อมบำรุง", "type": 4},
                {"id": "ch-1", "name": "line-foo", "type": 0},
            ])
        return httpx.Response(201, json={"id": "should-not-happen"})

    client = make_client(handler)
    assert client.ensure_category("ซ่อมบำรุง") == "cat-9"
    assert client.ensure_category("ซ่อมบำรุง") == "cat-9"  # cache hit
    assert posts == []  # ไม่สร้างใหม่


def test_move_channel_sends_parent_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "ch-1", "parent_id": "cat-1"})

    client = make_client(handler)
    client.move_channel("ch-1", "cat-1")
    assert seen["method"] == "PATCH"
    assert seen["path"] == "/api/v10/channels/ch-1"
    assert seen["body"] == {"parent_id": "cat-1"}
