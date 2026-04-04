"""Memory and performance profiling for geoprompt (items 36-37).

Run: python benchmarks/profile_runner.py
"""
from __future__ import annotations

import random
import sys
import time
import tracemalloc

from geoprompt import GeoPromptFrame


def _random_frame(n: int, seed: int = 42) -> GeoPromptFrame:
    rng = random.Random(seed)
    records = []
    for i in range(n):
        gt = rng.choice(["Point", "LineString", "Polygon"])
        if gt == "Point":
            geom = {"type": "Point", "coordinates": [rng.uniform(-180, 180), rng.uniform(-90, 90)]}
        elif gt == "LineString":
            geom = {"type": "LineString", "coordinates": [
                [rng.uniform(-180, 180), rng.uniform(-90, 90)] for _ in range(rng.randint(2, 5))
            ]}
        else:
            cx, cy = rng.uniform(-180, 180), rng.uniform(-90, 90)
            s = rng.uniform(0.01, 0.1)
            geom = {"type": "Polygon", "coordinates": [[cx, cy], [cx + s, cy], [cx + s, cy + s], [cx, cy + s]]}
        records.append({
            "site_id": f"s{i}",
            "demand_index": rng.uniform(0.1, 1.0),
            "capacity_index": rng.uniform(0.1, 1.0),
            "priority_index": rng.uniform(0.1, 1.0),
            "geometry": geom,
        })
    return GeoPromptFrame.from_records(records)


def profile_operation(name: str, func, *args, **kwargs) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"{name:45s}  time={elapsed:.4f}s  mem_peak={peak / 1024:.1f}KB")
    return {"name": name, "elapsed": elapsed, "peak_kb": peak / 1024}


def main() -> None:
    print("=" * 70)
    print("GeoPrompt Profile Runner")
    print("=" * 70)

    results = []
    for n in (25, 100, 250):
        frame = _random_frame(n)
        print(f"\n--- {n} features (mixed geometries) ---")
        results.append(profile_operation(
            f"neighborhood_pressure (n={n})",
            frame.neighborhood_pressure, "demand_index", scale=0.14, power=1.6,
        ))
        results.append(profile_operation(
            f"nearest_neighbors (k=1, n={n})",
            frame.nearest_neighbors, k=1,
        ))
        results.append(profile_operation(
            f"distance_matrix (n={n})",
            frame.distance_matrix,
        ))
        results.append(profile_operation(
            f"interaction_table (n={n})",
            frame.interaction_table, "capacity_index", "demand_index", scale=0.16, power=1.5,
        ))

    print("\n" + "=" * 70)
    print("Profile complete.")

    # Check for regressions: no single operation should exceed 30s for n=250
    slow = [r for r in results if r["elapsed"] > 30]
    if slow:
        print(f"\nWARNING: {len(slow)} operations exceeded 30s threshold")
        for r in slow:
            print(f"  {r['name']}: {r['elapsed']:.2f}s")
        sys.exit(1)


if __name__ == "__main__":
    main()
