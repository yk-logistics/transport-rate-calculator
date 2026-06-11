from discord_api import channel_name_for


def test_thai_name_kept_spaces_dashed():
    assert channel_name_for("ทีมงาน LCB") == "line-ทีมงาน-lcb"


def test_strips_forbidden_chars():
    assert channel_name_for("A/B (test)!") == "line-ab-test"


def test_empty_falls_back():
    assert channel_name_for("") == "line-group"
    assert channel_name_for(None) == "line-group"
