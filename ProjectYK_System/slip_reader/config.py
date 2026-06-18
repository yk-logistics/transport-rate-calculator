import os

SLIP_ENGINE = os.environ.get("SLIP_ENGINE", "claude")
MVP_INGEST_URL = os.environ.get("MVP_INGEST_URL", "http://127.0.0.1:8010/api/petty/ingest")
SLIP_INGEST_TOKEN = os.environ.get("YK_SLIP_INGEST_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("SLIP_CLAUDE_MODEL", "claude-haiku-4-5")
