"""Configuration file support for geoprompt (item 30)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ConfigError


@dataclass
class GeoPromptConfig:
    """Runtime configuration loaded from geoprompt.toml or CLI args."""

    input_path: str | None = None
    output_dir: str | None = None
    asset_path: str | None = None
    crs: str = "EPSG:4326"
    scale: float = 0.14
    power: float = 1.6
    top_n: int = 5
    no_plot: bool = False
    no_asset_copy: bool = False
    dry_run: bool = False
    overwrite: bool = False
    verbose: bool = False
    trace: bool = False
    output_format: str = "json"
    skip_expensive: bool = False
    colormap: str = "YlOrRd"
    chart_title: str | None = None
    chart_subtitle: str | None = None
    export_formats: list[str] = field(default_factory=lambda: ["png"])
    distance_cutoff: float | None = None
    negative_weight_policy: str = "reject"
    normalization: str = "none"


def load_config(path: str | Path | None = None) -> GeoPromptConfig:
    """Load configuration from a TOML file.

    Searches for geoprompt.toml in the current directory if no path given.
    """
    if path is None:
        candidate = Path("geoprompt.toml")
        if not candidate.exists():
            return GeoPromptConfig()
        path = candidate

    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc

    return _build_config(data)


def _build_config(data: dict[str, Any]) -> GeoPromptConfig:
    """Build a GeoPromptConfig from parsed TOML data."""
    geoprompt_data = data.get("geoprompt", data)
    config = GeoPromptConfig()

    field_map = {
        "input_path": str,
        "output_dir": str,
        "asset_path": str,
        "crs": str,
        "scale": float,
        "power": float,
        "top_n": int,
        "no_plot": bool,
        "no_asset_copy": bool,
        "dry_run": bool,
        "overwrite": bool,
        "verbose": bool,
        "trace": bool,
        "output_format": str,
        "skip_expensive": bool,
        "colormap": str,
        "chart_title": str,
        "chart_subtitle": str,
        "distance_cutoff": float,
        "negative_weight_policy": str,
        "normalization": str,
    }

    for key, cast in field_map.items():
        if key in geoprompt_data:
            setattr(config, key, cast(geoprompt_data[key]))

    if "export_formats" in geoprompt_data:
        config.export_formats = list(geoprompt_data["export_formats"])

    return config


__all__ = [
    "GeoPromptConfig",
    "load_config",
]
