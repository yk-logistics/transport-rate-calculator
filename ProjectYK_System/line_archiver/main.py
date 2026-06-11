"""line_archiver — FastAPI service (port 8020)

รับ webhook จาก LINE → Archiver จัดการเก็บ + forward
แยกขาดจากแอป MVP (port 8010) โดยสิ้นเชิง
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

import db
from archiver import Archiver
from config import load_config
from discord_api import DiscordClient
from line_api import LineClient, verify_signature

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("line_archiver")

BASE = Path(__file__).parent
MEDIA_ROOT = BASE / "line_media"
RETRY_INTERVAL = 300  # วินาที — กวาดข้อความที่ยังไม่ได้ forward

cfg = load_config(BASE / ".env")
line = LineClient(cfg.line_access_token)
discord = DiscordClient(cfg.discord_bot_token, cfg.discord_guild_id)


def make_archiver() -> Archiver:
    return Archiver(db.connect(), line, discord, MEDIA_ROOT)


def _retry_once() -> None:
    arch = make_archiver()
    try:
        arch.retry_pending()
    finally:
        arch.conn.close()


async def retry_loop() -> None:
    while True:
        await asyncio.sleep(RETRY_INTERVAL)
        try:
            await asyncio.to_thread(_retry_once)
        except Exception:
            log.exception("retry loop error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(retry_loop())
    log.info("line_archiver started, media root: %s", MEDIA_ROOT)
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/line/webhook")
async def line_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")
    if not verify_signature(cfg.line_channel_secret, body, signature):
        raise HTTPException(status_code=403, detail="bad signature")
    payload = json.loads(body)

    def process() -> None:
        arch = make_archiver()
        try:
            for event in payload.get("events", []):
                try:
                    arch.handle_event(event)
                except Exception:
                    # event เดียวพังต้องไม่ทำให้ทั้ง batch fail (LINE จะ redeliver ทั้งก้อน)
                    log.exception("event failed: %s", event.get("type"))
        finally:
            arch.conn.close()

    await asyncio.to_thread(process)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
