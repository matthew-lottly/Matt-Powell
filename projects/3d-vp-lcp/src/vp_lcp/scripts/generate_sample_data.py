"""Generate a small synthetic LAS file for testing and tutorials.

Run:  python -m vp_lcp.scripts.generate_sample_data
"""

from __future__ import annotations

from pathlib import Path

import laspy
import numpy as np


def main() -> None:
    rng = np.random.default_rng(42)
    n_ground = 5000
    n_understory = 3000
    n_canopy = 4000

    # Ground plane with slight slope
    gx = rng.uniform(0, 50, n_ground)
    gy = rng.uniform(0, 50, n_ground)
    gz = 100.0 + 0.02 * gx + rng.normal(0, 0.1, n_ground)

    # Understory vegetation (2-6 m above ground)
    ux = rng.uniform(5, 45, n_understory)
    uy = rng.uniform(5, 45, n_understory)
    uz = 100.0 + 0.02 * ux + rng.uniform(2, 6, n_understory)

    # Canopy vegetation (10-20 m above ground), with a gap corridor
    cx = rng.uniform(0, 50, n_canopy * 2)
    cy = rng.uniform(0, 50, n_canopy * 2)
    # Remove points in a diagonal corridor to create a visible gap
    keep = ~((cx > 15) & (cx < 25) & (cy > 10) & (cy < 40))
    cx = cx[keep][:n_canopy]
    cy = cy[keep][:n_canopy]
    cz = 100.0 + 0.02 * cx + rng.uniform(10, 20, len(cx))

    all_x = np.concatenate([gx, ux, cx])
    all_y = np.concatenate([gy, uy, cy])
    all_z = np.concatenate([gz, uz, cz])

    # Classification: 2 = ground, 3/4/5 = vegetation
    cls_ground = np.full(n_ground, 2, dtype=np.uint8)
    cls_under = np.full(n_understory, 3, dtype=np.uint8)
    cls_canopy = np.full(len(cx), 5, dtype=np.uint8)
    all_cls = np.concatenate([cls_ground, cls_under, cls_canopy])

    header = laspy.LasHeader(point_format=0, version="1.2")
    header.offsets = np.array([0.0, 0.0, 0.0])
    header.scales = np.array([0.01, 0.01, 0.01])

    las = laspy.LasData(header)
    las.x = all_x
    las.y = all_y
    las.z = all_z
    las.classification = all_cls

    out_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "sample_lidar.las"
    las.write(str(out_path))
    print(f"Wrote {len(all_x)} points to {out_path}")


if __name__ == "__main__":
    main()
