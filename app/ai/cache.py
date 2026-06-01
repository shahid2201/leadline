import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class AIResultCache:
    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._redis_url = redis_url
        self._ttl_seconds = ttl_seconds

    async def get(self, key: str) -> dict[str, Any] | None:
        client = Redis.from_url(self._redis_url, decode_responses=True)
        try:
            value = await client.get(key)
            if not value:
                return None
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
            return None
        except Exception:  # noqa: BLE001
            logger.exception("AI cache get failed", extra={"cache_key": key})
            return None
        finally:
            await client.aclose()

    async def set(self, key: str, value: dict[str, Any]) -> None:
        client = Redis.from_url(self._redis_url, decode_responses=True)
        try:
            await client.set(key, json.dumps(value), ex=self._ttl_seconds)
        except Exception:  # noqa: BLE001
            logger.exception("AI cache set failed", extra={"cache_key": key})
        finally:
            await client.aclose()
