from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Optional
import os
import json

_REDIS_AVAILABLE = False
_aioredis = None
try:
    import aioredis as _aioredis  # type: ignore
    _REDIS_AVAILABLE = True
except Exception:
    _aioredis = None
    _REDIS_AVAILABLE = False


class SimpleMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            v = self._store.get(key)
            if not v:
                return None
            expires_at, value = v
            if expires_at and expires_at < time.time():
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.time() + ttl if ttl else 0
        async with self._lock:
            self._store[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            if key in self._store:
                del self._store[key]


_GLOBAL_CACHE: Optional[SimpleMemoryCache] = None


def get_cache() -> SimpleMemoryCache:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = SimpleMemoryCache()
    return _GLOBAL_CACHE


def cached(ttl: int = 300):
    """Decorator for async functions to cache results by args.

    Uses the global in-memory cache. Key is function name + repr(args)+repr(kwargs).
    """
    def deco(fn: Callable):
        async def wrapped(*args, **kwargs):
            cache = get_cache()
            key = f"{fn.__module__}.{fn.__name__}:{args}:{kwargs}"
            res = await cache.get(key)
            if res is not None:
                return res
            result = await fn(*args, **kwargs)
            await cache.set(key, result, ttl=ttl)
            return result

        return wrapped

    return deco


class RedisCache:
    def __init__(self, url: str):
        if not _REDIS_AVAILABLE:
            raise RuntimeError("aioredis is not installed")
        self._url = url
        self._client = None

    async def _ensure(self):
        if self._client is None:
            self._client = await _aioredis.from_url(self._url)

    async def get(self, key: str) -> Optional[Any]:
        await self._ensure()
        v = await self._client.get(key)
        if v is None:
            return None
        try:
            return json.loads(v)
        except Exception:
            return v

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self._ensure()
        data = json.dumps(value)
        if ttl:
            await self._client.set(key, data, ex=ttl)
        else:
            await self._client.set(key, data)

    async def delete(self, key: str) -> None:
        await self._ensure()
        await self._client.delete(key)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()


def configure_cache_from_env() -> None:
    """Configure global cache from environment `REDIS_URL` if available."""
    global _GLOBAL_CACHE
    url = os.getenv("REDIS_URL")
    if url and _REDIS_AVAILABLE:
        _GLOBAL_CACHE = RedisCache(url)
    else:
        _GLOBAL_CACHE = SimpleMemoryCache()


async def close_global_cache() -> None:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        return
    if isinstance(_GLOBAL_CACHE, RedisCache):
        await _GLOBAL_CACHE.close()
