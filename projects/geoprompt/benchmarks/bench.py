"""Benchmark suite for geoprompt key tools.

Run: python benchmarks/bench.py
"""
from __future__ import annotations

import random
import time
from geoprompt import GeoPromptFrame


def _random_frame(n: int, seed: int = 42) -> GeoPromptFrame:
    rng = random.Random(seed)
    return GeoPromptFrame.from_records([
        {"site_id": f"p{i}", "value": rng.uniform(0, 100),
         "geometry": {"type": "Point", "coordinates": (rng.uniform(0, 100), rng.uniform(0, 100))}}
        for i in range(n)
    ])


def bench(name: str, func, *args, repeats: int = 3, **kwargs) -> None:
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        func(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    avg = sum(times) / len(times)
    best = min(times)
    print(f"{name:40s}  avg={avg:.4f}s  best={best:.4f}s  (n={repeats})")


def main() -> None:
    print("=" * 70)
    print("GeoPrompt Benchmark Suite")
    print("=" * 70)

    for n in (50, 200, 500):
        frame = _random_frame(n)
        print(f"\n--- {n} points ---")
        bench(f"spatial_lag (k=4, n={n})", frame.spatial_lag, "value", k=4)
        bench(f"spatial_autocorrelation (n={n})", frame.spatial_autocorrelation, "value", k=4)
        bench(f"idw_interpolation (n={n})", frame.idw_interpolation, "value", grid_resolution=10)
        bench(f"kernel_density (n={n})", frame.kernel_density, grid_resolution=10)
        bench(f"kriging_surface (n={n})", frame.kriging_surface, "value", grid_resolution=10)
        bench(f"hotspot_getis_ord (n={n})", frame.hotspot_getis_ord, "value", mode="k_nearest", k=4)
        bench(f"dbscan_cluster (n={n})", frame.dbscan_cluster, eps=10.0, min_samples=3)
        bench(f"nearest_neighbor_distance (n={n})", frame.nearest_neighbor_distance)
        bench(f"buffer (n={n})", frame.buffer, 5.0)
        bench(f"convex_hulls (n={n})", frame.convex_hulls)

    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
