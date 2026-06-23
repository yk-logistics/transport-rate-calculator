from __future__ import annotations
import httpx
from . import config

_HEADERS = lambda: {"X-Service-Token": config.SLIP_INGEST_TOKEN}


def fetch_config() -> dict:
    """Ask the MVP whether the reader is enabled, from what date, and if a 'check
    now' was requested. On ANY error (MVP down, bad token) return enabled=False —
    fail safe so we never spend API money when we can't confirm we're enabled.
    """
    try:
        r = httpx.get(config.SLIP_CONFIG_URL, headers=_HEADERS(), timeout=15)
        if r.status_code != 200:
            return {"enabled": False, "since": "", "run_now": False, "error": f"http {r.status_code}"}
        return r.json()
    except Exception as e:
        return {"enabled": False, "since": "", "run_now": False, "error": str(e)}


def report(result: str, ack_run_now: bool = False) -> None:
    """Post the run result back to the MVP for status display + ack the run_now flag."""
    try:
        httpx.post(config.SLIP_REPORT_URL, headers=_HEADERS(),
                   json={"result": result, "ack_run_now": ack_run_now}, timeout=15)
    except Exception:
        pass  # status reporting is best-effort; never fail the run over it
