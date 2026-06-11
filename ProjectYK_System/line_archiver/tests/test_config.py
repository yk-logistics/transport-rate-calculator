from config import parse_env


def test_parse_env_basic():
    text = "LINE_CHANNEL_SECRET=abc123\nDISCORD_BOT_TOKEN=tok.en=with=equals\n"
    vals = parse_env(text)
    assert vals["LINE_CHANNEL_SECRET"] == "abc123"
    assert vals["DISCORD_BOT_TOKEN"] == "tok.en=with=equals"


def test_parse_env_skips_comments_and_blanks():
    text = "# comment\n\nKEY = value \nbadline\n"
    vals = parse_env(text)
    assert vals == {"KEY": "value"}
