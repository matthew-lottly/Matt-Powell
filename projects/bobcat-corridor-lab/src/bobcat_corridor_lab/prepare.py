from __future__ import annotations

import json
from pathlib import Path

import numpy as np


_RESAMPLING_MAP = {
    "nearest": "nearest",
    "bilinear": "bilinear",
    "cubic": "cubic",
}


def prepare_raster_stack(
    reference_raster: str | Path,
    layers: dict[str, str | Path],
    output_dir: str | Path,
    resampling: str = "bilinear",
) -> dict[str, str]:
    if resampling not in _RESAMPLING_MAP:
        raise ValueError("resampling must be one of: nearest, bilinear, cubic")

    try:
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.warp import reproject
    except ImportError as exc:
        raise RuntimeError(
            "Raster preparation requires rasterio. Install with: pip install bobcat-corridor-lab[geo]"
        ) from exc

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(reference_raster) as ref:
        dst_crs = ref.crs
        dst_transform = ref.transform
        dst_height = ref.height
        dst_width = ref.width

    manifest: dict[str, str] = {}
    for layer_name, layer_path in layers.items():
        with rasterio.open(layer_path) as src:
            src_arr = src.read(1)
            dst_arr = np.zeros((dst_height, dst_width), dtype=np.float32)

            reproject(
                source=src_arr,
                destination=dst_arr,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=getattr(Resampling, _RESAMPLING_MAP[resampling]),
            )

            output_path = out_dir / f"{layer_name}.npy"
            np.save(output_path, dst_arr)
            manifest[layer_name] = str(output_path)

    (out_dir / "stack_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
