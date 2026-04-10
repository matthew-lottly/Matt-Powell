from __future__ import annotations

import numpy as np


def _check_same_shape(layers: dict[str, np.ndarray]) -> tuple[int, int]:
    shapes = {name: arr.shape for name, arr in layers.items()}
    if not shapes:
        raise ValueError("At least one raster layer is required")
    unique_shapes = set(shapes.values())
    if len(unique_shapes) != 1:
        raise ValueError(f"All raster layers must share the same shape: {shapes}")
    return next(iter(unique_shapes))


def normalize_01(arr: np.ndarray) -> np.ndarray:
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    if np.isclose(max_val, min_val):
        return np.zeros_like(arr, dtype=float)
    return (arr - min_val) / (max_val - min_val)


def weighted_overlay(layers: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    _check_same_shape(layers)

    unknown = set(weights) - set(layers)
    if unknown:
        raise ValueError(f"Weights reference missing layers: {sorted(unknown)}")

    missing = set(layers) - set(weights)
    if missing:
        raise ValueError(f"Layers missing weights: {sorted(missing)}")

    total_weight = float(sum(weights.values()))
    if total_weight <= 0:
        raise ValueError("Weights must sum to a positive value")

    # Normalize sum of weights to 1.0 while preserving relative influence.
    overlay = np.zeros_like(next(iter(layers.values())), dtype=float)
    for name, arr in layers.items():
        overlay += normalize_01(arr) * (weights[name] / total_weight)

    return np.clip(overlay, 0.0, 1.0)


def suitability_to_base_resistance(
    suitability: np.ndarray,
    min_cost: float = 1.0,
    max_cost: float = 10.0,
) -> np.ndarray:
    if min_cost <= 0 or max_cost <= min_cost:
        raise ValueError("Expected 0 < min_cost < max_cost")
    suitability = np.clip(suitability, 0.0, 1.0)
    inverted = 1.0 - suitability
    return min_cost + inverted * (max_cost - min_cost)


def apply_barrier_penalties(
    base_resistance: np.ndarray,
    road_mask: np.ndarray,
    urban_mask: np.ndarray,
    ag_mask: np.ndarray,
    road_cost: float,
    urban_cost: float,
    ag_cost: float,
    method: str = "max",
) -> np.ndarray:
    masks = {
        "road": road_mask.astype(bool),
        "urban": urban_mask.astype(bool),
        "ag": ag_mask.astype(bool),
    }

    shape = base_resistance.shape
    for name, mask in masks.items():
        if mask.shape != shape:
            raise ValueError(f"Barrier mask '{name}' does not match raster shape {shape}")

    if method not in {"max", "sum"}:
        raise ValueError("method must be 'max' or 'sum'")

    road_layer = np.where(masks["road"], road_cost, 0.0)
    urban_layer = np.where(masks["urban"], urban_cost, 0.0)
    ag_layer = np.where(masks["ag"], ag_cost, 0.0)

    if method == "max":
        penalties = np.maximum.reduce([road_layer, urban_layer, ag_layer])
    else:
        penalties = road_layer + urban_layer + ag_layer

    return base_resistance + penalties
