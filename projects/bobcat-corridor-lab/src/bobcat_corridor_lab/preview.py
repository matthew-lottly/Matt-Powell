from __future__ import annotations

from pathlib import Path

import numpy as np


def render_preview_png(
    suitability_path: str | Path,
    corridor_mask_path: str | Path,
    path_csv: str | Path,
    output_png: str | Path,
    title: str = "Bobcat Corridor Preview",
) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "Preview rendering requires matplotlib. Install with: pip install bobcat-corridor-lab[viz]"
        ) from exc

    suitability = np.load(suitability_path)
    corridor = np.load(corridor_mask_path).astype(bool)

    path_pts = np.loadtxt(path_csv, delimiter=",", skiprows=1)
    if path_pts.ndim == 1:
        path_pts = np.expand_dims(path_pts, axis=0)

    out_path = Path(output_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6), dpi=180)
    base = ax.imshow(suitability, cmap="YlGn", interpolation="nearest")
    ax.imshow(np.where(corridor, 1.0, np.nan), cmap="OrRd", alpha=0.35, interpolation="nearest")
    ax.plot(path_pts[:, 1], path_pts[:, 0], color="#1f4e79", linewidth=2.0)

    ax.set_title(title)
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    fig.colorbar(base, ax=ax, fraction=0.045, pad=0.04, label="Suitability")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
