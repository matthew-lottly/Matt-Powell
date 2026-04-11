from __future__ import annotations

from pathlib import Path

import numpy as np


def load_array(path: str | Path) -> np.ndarray:
    input_path = Path(path)
    suffix = input_path.suffix.lower()

    if suffix == ".npy":
        return np.load(input_path)

    if suffix == ".npz":
        payload = np.load(input_path)
        if not payload.files:
            raise ValueError(f"No arrays found in {input_path}")
        return payload[payload.files[0]]

    if suffix in {".tif", ".tiff"}:
        try:
            import rasterio
        except ImportError as exc:
            raise RuntimeError(
                "GeoTIFF loading requires rasterio. Install with: pip install bobcat-corridor-lab[geo]"
            ) from exc

        with rasterio.open(input_path) as dataset:
            return dataset.read(1)

    raise ValueError(f"Unsupported raster format for {input_path}. Use .npy, .npz, .tif, or .tiff")
