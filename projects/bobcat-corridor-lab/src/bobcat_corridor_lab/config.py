from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SuitabilityWeights:
    land_cover: float
    water_distance: float
    slope: float
    human_footprint: float
    prey: float

    def as_dict(self) -> dict[str, float]:
        return {
            "land_cover": self.land_cover,
            "water_distance": self.water_distance,
            "slope": self.slope,
            "human_footprint": self.human_footprint,
            "prey": self.prey,
        }


@dataclass(frozen=True)
class BarrierCosts:
    road_cost: float
    urban_cost: float
    agriculture_cost: float


@dataclass(frozen=True)
class DemoScenario:
    raster_shape: tuple[int, int]
    random_seed: int
    suitability_weights: SuitabilityWeights
    barrier_costs: BarrierCosts
    corridor_quantile: float


def _validate_shape(shape: list[int]) -> tuple[int, int]:
    if len(shape) != 2 or shape[0] < 10 or shape[1] < 10:
        raise ValueError("raster_shape must be [rows, cols] with each value >= 10")
    return shape[0], shape[1]


def _validate_quantile(value: float) -> float:
    if value <= 0 or value >= 1:
        raise ValueError("corridor_quantile must be between 0 and 1 (exclusive)")
    return value


def load_scenario(path: str | Path) -> DemoScenario:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))

    weights = SuitabilityWeights(**data["suitability_weights"])
    barriers = BarrierCosts(**data["barrier_costs"])

    return DemoScenario(
        raster_shape=_validate_shape(data["raster_shape"]),
        random_seed=int(data["random_seed"]),
        suitability_weights=weights,
        barrier_costs=barriers,
        corridor_quantile=_validate_quantile(float(data["corridor_quantile"])),
    )


def write_default_scenario(path: str | Path) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    default = {
        "raster_shape": [180, 220],
        "random_seed": 44,
        "suitability_weights": {
            "land_cover": 0.40,
            "water_distance": 0.20,
            "slope": 0.15,
            "human_footprint": 0.15,
            "prey": 0.10,
        },
        "barrier_costs": {
            "road_cost": 10.0,
            "urban_cost": 8.0,
            "agriculture_cost": 3.0,
        },
        "corridor_quantile": 0.10,
    }

    out_path.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")
    return out_path
