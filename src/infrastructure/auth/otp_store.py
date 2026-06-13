import random
import time
from typing import Protocol

import redis.asyncio as aioredis


class OtpStore(Protocol):
    async def save(self, phone: str, code: str, ttl_sec: int) -> None: ...
    async def get(self, phone: str) -> str | None: ...
    async def delete(self, phone: str) -> None: ...


class RedisOtpStore:
    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client

    def _key(self, phone: str) -> str:
        return f"otp:{phone}"

    async def save(self, phone: str, code: str, ttl_sec: int) -> None:
        await self._redis.set(self._key(phone), code.encode(), ex=ttl_sec)

    async def get(self, phone: str) -> str | None:
        raw = await self._redis.get(self._key(phone))
        if not raw:
            return None
        return raw.decode() if isinstance(raw, bytes) else str(raw)

    async def delete(self, phone: str) -> None:
        await self._redis.delete(self._key(phone))


class MemoryOtpStore:
    """Fallback when Redis is unavailable (local dev)."""

    def __init__(self):
        self._codes: dict[str, tuple[str, float]] = {}

    async def save(self, phone: str, code: str, ttl_sec: int) -> None:
        self._codes[phone] = (code, time.time() + ttl_sec)

    async def get(self, phone: str) -> str | None:
        entry = self._codes.get(phone)
        if not entry:
            return None
        code, expires = entry
        if time.time() > expires:
            self._codes.pop(phone, None)
            return None
        return code

    async def delete(self, phone: str) -> None:
        self._codes.pop(phone, None)


def generate_otp_code(length: int = 5) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))
