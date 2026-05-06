"""Async Redis client with connection pooling and retry logic."""

import asyncio
from typing import Any, Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RedisClient:
    def __init__(self):
        self._pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)
        self._circuit_open = False
        self._circuit_failures = 0
        self._circuit_threshold = 5

    async def _check_circuit(self) -> bool:
        if self._circuit_open:
            return False
        return True

    async def _record_failure(self) -> None:
        self._circuit_failures += 1
        if self._circuit_failures >= self._circuit_threshold:
            self._circuit_open = True
            logger.warning("Redis circuit breaker opened")
            asyncio.get_running_loop().call_later(
                30,
                lambda: setattr(self, "_circuit_open", False)
                or setattr(self, "_circuit_failures", 0),
            )

    async def _record_success(self) -> None:
        self._circuit_failures = 0

    async def ping(self) -> bool:
        try:
            result = await self._client.ping()
            await self._record_success()
            return result
        except Exception:
            await self._record_failure()
            return False

    async def get(self, key: str) -> Optional[str]:
        if not await self._check_circuit():
            return None
        try:
            result = await self._client.get(key)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis GET failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not await self._check_circuit():
            return False
        try:
            import json

            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            if ttl:
                result = await self._client.setex(key, ttl, value)
            else:
                result = await self._client.set(key, value)
            await self._record_success()
            return bool(result)
        except Exception as e:
            await self._record_failure()
            logger.error("Redis SET failed", key=key, error=str(e))
            return False

    async def get_json(self, key: str) -> Optional[dict]:
        val = await self.get(key)
        if val:
            import json

            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    async def incr(self, key: str, ttl: Optional[int] = None) -> int:
        if not await self._check_circuit():
            return 0
        try:
            pipe = self._client.pipeline()
            await pipe.incr(key)
            if ttl:
                await pipe.expire(key, ttl)
            results = await pipe.execute()
            await self._record_success()
            return results[0]
        except Exception as e:
            await self._record_failure()
            logger.error("Redis INCR failed", key=key, error=str(e))
            return 0

    async def lpush(self, key: str, *values: Any) -> int:
        if not await self._check_circuit():
            return 0
        try:
            import json

            serialized = [
                json.dumps(v) if isinstance(v, (dict, list)) else v for v in values
            ]
            result = await self._client.lpush(key, *serialized)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis LPUSH failed", key=key, error=str(e))
            return 0

    async def lrange(self, key: str, start: int, end: int) -> list:
        if not await self._check_circuit():
            return []
        try:
            import json

            items = await self._client.lrange(key, start, end)
            result = []
            for item in items:
                try:
                    result.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    result.append(item)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis LRANGE failed", key=key, error=str(e))
            return []

    async def publish(self, channel: str, message: Any) -> int:
        if not await self._check_circuit():
            return 0
        try:
            import json

            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            result = await self._client.publish(channel, message)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis PUBLISH failed", channel=channel, error=str(e))
            return 0

    async def hset(self, name: str, mapping: dict) -> int:
        if not await self._check_circuit():
            return 0
        try:
            result = await self._client.hset(name, mapping=mapping)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis HSET failed", name=name, error=str(e))
            return 0

    async def hgetall(self, name: str) -> dict:
        if not await self._check_circuit():
            return {}
        try:
            result = await self._client.hgetall(name)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis HGETALL failed", name=name, error=str(e))
            return {}

    async def delete(self, *keys: str) -> int:
        if not await self._check_circuit():
            return 0
        try:
            result = await self._client.delete(*keys)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            logger.error("Redis DELETE failed", keys=keys, error=str(e))
            return 0

    async def close(self) -> None:
        await self._pool.aclose()

    async def check_rate_limit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Sliding window rate limit using sorted sets."""
        if not await self._check_circuit():
            return True, limit

        now = __import__("time").time()
        window_start = now - window
        rate_key = f"rl:{key}"

        pipe = self._client.pipeline()
        pipe.zremrangebyscore(rate_key, 0, window_start)
        pipe.zcard(rate_key)
        pipe.zadd(rate_key, {str(now): now})
        pipe.expire(rate_key, window + 1)
        results = await pipe.execute()

        current_count = results[1]
        remaining = max(0, limit - current_count)
        await self._record_success()
        return current_count < limit, remaining


redis_client = RedisClient()
