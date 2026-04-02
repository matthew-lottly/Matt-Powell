import asyncio

from sports_sim.cache.cache import SimpleMemoryCache, get_cache


def test_simple_memory_cache_set_get() -> None:
    c = SimpleMemoryCache()

    async def run():
        await c.set("k1", {"a": 1}, ttl=1)
        v = await c.get("k1")
        assert v == {"a": 1}
        # wait for expiry
        await asyncio.sleep(1.1)
        v2 = await c.get("k1")
        assert v2 is None

    asyncio.run(run())


def test_global_cache_singleton():
    c1 = get_cache()
    c2 = get_cache()
    assert c1 is c2
