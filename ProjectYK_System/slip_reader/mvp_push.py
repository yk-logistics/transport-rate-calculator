from __future__ import annotations
import httpx
from . import config


def push(payload: dict) -> dict:
    r = httpx.post(config.MVP_INGEST_URL, json=payload,
                   headers={"X-Service-Token": config.SLIP_INGEST_TOKEN},
                   timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ingest failed {r.status_code}: {r.text[:200]}")
    return r.json()
