"""Observer utils."""

import logging
import os

import redis
import redis.asyncio
from fastapi import FastAPI

logger = logging.getLogger(__name__)


host = 'localhost' if os.getenv('ENV') == 'local' else 'redis'
try:
    redis_sync = redis.Redis(host=host, port=6379, decode_responses=True)
    redis_sync.ping()
except redis.exceptions.ConnectionError:
    redis_sync = None

app = FastAPI()


def get_sessions() -> list:
    """Get published sessions."""
    if not redis_sync:
        return []
    return list(redis_sync.smembers("observer:sessions"))


@app.get("/api/redirect-url")
def get_redirect_url(session_id: str):
    if not redis_sync:
        return {"url": None}
    url = redis_sync.get(f"observer:session:{session_id}:url")
    return {"url": url.decode() if url else None}
