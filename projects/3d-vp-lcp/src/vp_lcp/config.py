"""Configuration models for 3D-VP-LCP runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
import json


@dataclass(slots=True)
class InputConfig:
    """Input and preprocessing configuration."""

    bbox: tuple[float, float, float, float] | None = None
    vegetation_classes: tuple[int, ...] = (3, 4, 5)
    ground_classes: tuple[int, ...] = (2,)
    normalization: str = "dtm-grid"
    ground_percentile: float = 2.0
    dtm_cell_size: float = 2.0
    voxel_size: float = 2.0
    min_height: float = 0.5
    # Optional polygon clip (path to JSON with [[x,y], ...] vertices)
    polygon_clip_path: str | None = None
    # Optional pre-aligned numpy arrays (.npy) for external raster layers
    slope_raster_path: str | None = None
    landcover_raster_path: str | None = None


@dataclass(slots=True)
class ResistanceConfig:
    """Weights for the per-voxel resistance model."""

    alpha: float = 1.2
    beta: float = 0.8
    gamma: float = 0.0
    delta: float = 0.0
    normalize: bool = False


@dataclass(slots=True)
class SpeciesConfig:
    """Species-specific movement constraints."""

    h_min: float = 0.5
    h_max: float = 20.0
    h_clear: float = 0.0
    w_clear: int = 1
    vgf_thresh: float = 0.6
    name: str = ""
    # Optional per-height-band resistance multipliers
    # Keys: "0-2m", "2-5m", "5-10m", "10m+" — values multiply the resistance
    stratum_weights: dict[str, float] | None = None

    @classmethod
    def load_species_profile(cls, path: "str | Path") -> "SpeciesConfig":
        """Load species parameters from a JSON profile file.

        The JSON may contain any subset of SpeciesConfig fields.
        Unknown keys are silently ignored.
        """
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in valid})


@dataclass(slots=True)
class RoutingConfig:
    """Graph routing and patch-selection configuration."""

    algorithm: str = "dijkstra"
    neighbours: int = 6
    source_margin: int = 1
    target_margin: int = 1


@dataclass(slots=True)
class OutputConfig:
    """Output artifact configuration."""

    output_dir: str = "outputs/latest-run"
    export_csv: bool = True
    export_geojson: bool = True
    export_report: bool = True
    export_surface: bool = False
    export_occupancy: bool = False
    export_vgf: bool = False
    export_cost_volume: bool = False


@dataclass(slots=True)
class PipelineConfig:
    """Top-level run configuration."""

    input: InputConfig = field(default_factory=InputConfig)
    resistance: ResistanceConfig = field(default_factory=ResistanceConfig)
    species: SpeciesConfig = field(default_factory=SpeciesConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_json(cls, path: str | Path) -> "PipelineConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            input=InputConfig(**raw.get("input", {})),
            resistance=ResistanceConfig(**raw.get("resistance", {})),
            species=SpeciesConfig(**raw.get("species", {})),
            routing=RoutingConfig(**raw.get("routing", {})),
            output=OutputConfig(**raw.get("output", {})),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
