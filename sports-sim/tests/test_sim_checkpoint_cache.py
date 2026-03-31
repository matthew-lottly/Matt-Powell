import asyncio
import json
from types import SimpleNamespace

import pytest


class FakeCache:
    def __init__(self):
        self.store = {}
        self.set_calls = []
        self.get_calls = []

    async def get(self, key):
        self.get_calls.append(key)
        return self.store.get(key)

    async def set(self, key, value, ttl=None):
        self.set_calls.append((key, value, ttl))
        self.store[key] = value


def test_simulation_checkpoint_cached(monkeypatch):
    # Run the original async logic inside asyncio.run for environments without pytest-asyncio
    async def _inner():
        # Use a fake cache that records set/get calls
        fake = FakeCache()

        # Patch get_cache to return our fake
        import src.sports_sim.cache.cache as cachemod

        # Set the global cache instance in the cache module before importing app
        monkeypatch.setattr(cachemod, "_GLOBAL_CACHE", fake, raising=False)

        import src.sports_sim.api.app as api_mod

        # Create a minimal CreateSimRequest payload for the API function directly
        from sports_sim.api.app import CreateSimRequest, create_simulation, run_simulation

        req = CreateSimRequest(sport="soccer", seed=42, home_team=None, away_team=None)

        # Call create_simulation and ensure cache set was called for sim snapshot
        summary = await create_simulation(req)
        gid = summary.game_id
        # Expect a cache set for initial state
        keys = [k for k, *_ in fake.set_calls]
        assert any(k.startswith(f"sim:{gid}:state") for k in keys)

        # Clear recorded calls and run the simulation
        fake.set_calls.clear()
        await run_simulation(gid)
        # After run, expect another checkpoint update
        keys2 = [k for k, *_ in fake.set_calls]
        assert any(k.startswith(f"sim:{gid}:state") for k in keys2)

    import asyncio

    asyncio.run(_inner())
