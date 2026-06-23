import os

SLIP_ENGINE = os.environ.get("SLIP_ENGINE", "claude")
MVP_INGEST_URL = os.environ.get("MVP_INGEST_URL", "http://127.0.0.1:8010/api/petty/ingest")
SLIP_INGEST_TOKEN = os.environ.get("YK_SLIP_INGEST_TOKEN", "")

# Sibling service endpoints for the on/off control, derived from the ingest URL
# (…/api/petty/ingest → …/api/petty/slip-config).
_BASE = MVP_INGEST_URL.rsplit("/", 1)[0]            # …/api/petty
SLIP_CONFIG_URL = f"{_BASE}/slip-config"
SLIP_REPORT_URL = f"{_BASE}/slip-config/report"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Sonnet 4.6 default: dry-run showed it reads Thai driver names far more accurately
# than Haiku (the names drive who gets paid), for ~3x cost still cheap at this volume.
CLAUDE_MODEL = os.environ.get("SLIP_CLAUDE_MODEL", "claude-sonnet-4-6")
