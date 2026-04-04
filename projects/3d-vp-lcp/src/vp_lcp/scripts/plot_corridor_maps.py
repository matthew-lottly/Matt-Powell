"""Create 2D and 3D map figures from corridor.csv outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_corridor(csv_path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
            zs.append(float(row["z"]))
    return (
        np.asarray(xs, dtype=np.float64),
        np.asarray(ys, dtype=np.float64),
        np.asarray(zs, dtype=np.float64),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Render 2D and 3D corridor map figures.")
    parser.add_argument("--corridor-csv", required=True, help="Path to corridor.csv")
    parser.add_argument("--out-2d", required=True, help="Path to output 2D PNG")
    parser.add_argument("--out-3d", required=True, help="Path to output 3D PNG")
    args = parser.parse_args(argv)

    xs, ys, zs = load_corridor(args.corridor_csv)
    if xs.size == 0:
        raise ValueError("corridor.csv has no rows")

    out_2d = Path(args.out_2d)
    out_3d = Path(args.out_3d)
    out_2d.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 6))
    sc = plt.scatter(xs, ys, c=zs, cmap="viridis", s=30)
    plt.plot(xs, ys, linewidth=1.2, alpha=0.8)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("Connectivity Corridor (2D map)")
    cbar = plt.colorbar(sc)
    cbar.set_label("Z (height)")
    plt.tight_layout()
    plt.savefig(out_2d, dpi=150)
    plt.close()

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(xs, ys, zs, c=zs, cmap="viridis", s=26)
    ax.plot(xs, ys, zs, linewidth=1.2, alpha=0.9)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Connectivity Corridor (3D)")
    plt.tight_layout()
    plt.savefig(out_3d, dpi=150)
    plt.close(fig)

    print(out_2d)
    print(out_3d)


if __name__ == "__main__":
    main()
