from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

from .config import DemoScenario
from .io import load_array
from .corridor import corridor_mask, cumulative_cost_distance, least_cost_path
from .raster_ops import apply_barrier_penalties, suitability_to_base_resistance, weighted_overlay


def _build_layers_from_paths(layer_paths: dict[str, str | Path]) -> dict[str, np.ndarray]:
    required_layers = ["land_cover", "water_distance", "slope", "human_footprint"]
    for key in required_layers:
        if key not in layer_paths:
            raise ValueError(f"Missing required layer: {key}")

    layers: dict[str, np.ndarray] = {
        "land_cover": load_array(layer_paths["land_cover"]),
        "water_distance": load_array(layer_paths["water_distance"]),
        "slope": load_array(layer_paths["slope"]),
        "human_footprint": load_array(layer_paths["human_footprint"]),
    }

    if "prey" in layer_paths and layer_paths["prey"]:
        layers["prey"] = load_array(layer_paths["prey"])
    else:
        shape = next(iter(layers.values())).shape
        layers["prey"] = np.zeros(shape, dtype=float)

    return layers


def _build_resistance_from_paths(
    scenario: DemoScenario,
    layer_paths: dict[str, str | Path],
    barrier_paths: dict[str, str | Path],
) -> tuple[np.ndarray, np.ndarray]:
    layers = _build_layers_from_paths(layer_paths)

    road = load_array(barrier_paths["road"]).astype(bool)
    urban = load_array(barrier_paths["urban"]).astype(bool)
    ag = load_array(barrier_paths["agriculture"]).astype(bool)

    suitability = weighted_overlay(layers, scenario.suitability_weights.as_dict())
    base_resistance = suitability_to_base_resistance(suitability)
    resistance = apply_barrier_penalties(
        base_resistance,
        road,
        urban,
        ag,
        road_cost=scenario.barrier_costs.road_cost,
        urban_cost=scenario.barrier_costs.urban_cost,
        ag_cost=scenario.barrier_costs.agriculture_cost,
        method="max",
    )

    return suitability, resistance


def _patch_centroids(patch_raster: np.ndarray) -> list[tuple[int, tuple[int, int]]]:
    patch_ids = sorted(int(x) for x in np.unique(patch_raster) if int(x) > 0)
    centroids: list[tuple[int, tuple[int, int]]] = []
    for patch_id in patch_ids:
        rows, cols = np.where(patch_raster == patch_id)
        if rows.size == 0:
            continue
        row = int(np.rint(float(np.mean(rows))))
        col = int(np.rint(float(np.mean(cols))))
        centroids.append((patch_id, (row, col)))
    return centroids


def _synthetic_layers(shape: tuple[int, int], seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows, cols = shape
    y, x = np.indices((rows, cols))

    # Synthetic structure approximates ecologically plausible gradients.
    land_cover = np.sin(x / 20.0) + np.cos(y / 25.0) + rng.normal(0, 0.25, size=shape)
    water_distance = np.abs((x - cols * 0.2) / cols) + rng.normal(0, 0.05, size=shape)
    slope = np.hypot((x - cols * 0.5) / cols, (y - rows * 0.5) / rows)
    human_footprint = np.exp(-((x - cols * 0.8) ** 2 + (y - rows * 0.3) ** 2) / (2 * (0.18 * cols) ** 2))
    prey = np.exp(-((x - cols * 0.35) ** 2 + (y - rows * 0.7) ** 2) / (2 * (0.22 * cols) ** 2))

    return {
        "land_cover": land_cover,
        "water_distance": 1.0 - water_distance,
        "slope": 1.0 - slope,
        "human_footprint": 1.0 - human_footprint,
        "prey": prey,
    }


def _synthetic_barrier_masks(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows, cols = shape
    y, x = np.indices((rows, cols))

    road = ((x > cols * 0.45) & (x < cols * 0.5)) | ((y > rows * 0.58) & (y < rows * 0.62))
    urban = ((x - cols * 0.8) ** 2 + (y - rows * 0.28) ** 2) < (0.14 * cols) ** 2
    agriculture = (x > cols * 0.08) & (x < cols * 0.24) & (y > rows * 0.12) & (y < rows * 0.86)

    return road, urban, agriculture


def run_demo_workflow(scenario: DemoScenario, output_dir: str | Path) -> dict[str, float | int]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    layers = _synthetic_layers(scenario.raster_shape, scenario.random_seed)
    suitability = weighted_overlay(layers, scenario.suitability_weights.as_dict())
    base_resistance = suitability_to_base_resistance(suitability)

    road, urban, ag = _synthetic_barrier_masks(scenario.raster_shape)
    resistance = apply_barrier_penalties(
        base_resistance,
        road,
        urban,
        ag,
        road_cost=scenario.barrier_costs.road_cost,
        urban_cost=scenario.barrier_costs.urban_cost,
        ag_cost=scenario.barrier_costs.agriculture_cost,
        method="max",
    )

    source = (int(scenario.raster_shape[0] * 0.15), int(scenario.raster_shape[1] * 0.12))
    target = (int(scenario.raster_shape[0] * 0.82), int(scenario.raster_shape[1] * 0.88))

    cumulative = cumulative_cost_distance(resistance, source=source)
    path = least_cost_path(cumulative, source=source, target=target)
    corridor = corridor_mask(cumulative, quantile=scenario.corridor_quantile)

    summary = _write_outputs(
        output_dir=out_dir,
        scenario=scenario,
        suitability=suitability,
        resistance=resistance,
        cumulative=cumulative,
        corridor=corridor,
        path=path,
        source=source,
        target=target,
        mode="demo",
    )
    return summary


def run_real_workflow(
    scenario: DemoScenario,
    output_dir: str | Path,
    layer_paths: dict[str, str | Path],
    barrier_paths: dict[str, str | Path],
    source: tuple[int, int],
    target: tuple[int, int],
) -> dict[str, float | int]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suitability, resistance = _build_resistance_from_paths(scenario, layer_paths, barrier_paths)

    cumulative = cumulative_cost_distance(resistance, source=source)
    path = least_cost_path(cumulative, source=source, target=target)
    corridor = corridor_mask(cumulative, quantile=scenario.corridor_quantile)

    summary = _write_outputs(
        output_dir=out_dir,
        scenario=scenario,
        suitability=suitability,
        resistance=resistance,
        cumulative=cumulative,
        corridor=corridor,
        path=path,
        source=source,
        target=target,
        mode="real",
    )

    summary["source_row"] = int(source[0])
    summary["source_col"] = int(source[1])
    summary["target_row"] = int(target[0])
    summary["target_col"] = int(target[1])
    return summary


def run_multipatch_workflow(
    scenario: DemoScenario,
    output_dir: str | Path,
    layer_paths: dict[str, str | Path],
    barrier_paths: dict[str, str | Path],
    patch_raster_path: str | Path,
    max_pairs: int | None = None,
) -> dict[str, float | int]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suitability, resistance = _build_resistance_from_paths(scenario, layer_paths, barrier_paths)
    patch_raster = load_array(patch_raster_path)

    if patch_raster.shape != resistance.shape:
        raise ValueError("Patch raster shape must match resistance raster shape")

    centroids = _patch_centroids(patch_raster)
    if len(centroids) < 2:
        raise ValueError("Patch raster must contain at least two patch IDs > 0")

    pair_results: list[dict[str, float | int | str]] = []
    pairs = itertools.combinations(centroids, 2)
    if max_pairs is not None:
        pairs = itertools.islice(pairs, max_pairs)

    for (source_id, source_cell), (target_id, target_cell) in pairs:
        pair_name = f"patch_{source_id}_to_{target_id}"
        pair_dir = out_dir / pair_name
        pair_dir.mkdir(parents=True, exist_ok=True)

        cumulative = cumulative_cost_distance(resistance, source=source_cell)
        path = least_cost_path(cumulative, source=source_cell, target=target_cell)
        corridor = corridor_mask(cumulative, quantile=scenario.corridor_quantile)

        summary = _write_outputs(
            output_dir=pair_dir,
            scenario=scenario,
            suitability=suitability,
            resistance=resistance,
            cumulative=cumulative,
            corridor=corridor,
            path=path,
            source=source_cell,
            target=target_cell,
            mode="multipatch",
        )
        summary["source_patch_id"] = source_id
        summary["target_patch_id"] = target_id
        pair_results.append({"pair": pair_name, **summary})

    if not pair_results:
        raise ValueError("No patch pairs were generated; increase max_pairs or inspect patch raster")

    bundle = {
        "mode": "multipatch",
        "patch_count": len(centroids),
        "pair_count": len(pair_results),
        "mean_target_cost": float(np.mean([row["target_cumulative_cost"] for row in pair_results])),
    }

    (out_dir / "multipatch_summary.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    (out_dir / "pairs.json").write_text(json.dumps(pair_results, indent=2) + "\n", encoding="utf-8")
    return bundle


def _write_outputs(
    output_dir: Path,
    scenario: DemoScenario,
    suitability: np.ndarray,
    resistance: np.ndarray,
    cumulative: np.ndarray,
    corridor: np.ndarray,
    path: list[tuple[int, int]],
    source: tuple[int, int],
    target: tuple[int, int],
    mode: str,
) -> dict[str, float | int]:

    np.save(output_dir / "suitability.npy", suitability)
    np.save(output_dir / "resistance.npy", resistance)
    np.save(output_dir / "cumulative_cost.npy", cumulative)
    np.save(output_dir / "corridor_mask.npy", corridor.astype(np.uint8))

    path_array = np.array(path, dtype=int)
    np.savetxt(
        output_dir / "least_cost_path.csv",
        path_array,
        fmt="%d",
        delimiter=",",
        header="row,col",
        comments="",
    )

    summary = {
        "mode": mode,
        "rows": scenario.raster_shape[0],
        "cols": scenario.raster_shape[1],
        "corridor_cells": int(np.sum(corridor)),
        "corridor_fraction": float(np.mean(corridor)),
        "least_cost_path_steps": int(len(path)),
        "source_cumulative_cost": float(cumulative[source[0], source[1]]),
        "target_cumulative_cost": float(cumulative[target[0], target[1]]),
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def evaluate_cumulative_cost(cumulative_cost: np.ndarray, quantile: float) -> dict[str, float | int]:
    mask = corridor_mask(cumulative_cost, quantile)
    finite = cumulative_cost[np.isfinite(cumulative_cost)]
    return {
        "corridor_cells": int(np.sum(mask)),
        "corridor_fraction": float(np.mean(mask)),
        "min_cost": float(np.min(finite)),
        "mean_cost": float(np.mean(finite)),
        "max_cost": float(np.max(finite)),
    }
